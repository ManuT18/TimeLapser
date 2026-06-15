import os
import sys
import threading
import queue
import time
import subprocess
import re
import tempfile
import concurrent.futures

class TimelapseProcessor:
    def __init__(self, log_queue, ffmpeg_path):
        self.log_queue = log_queue
        self.ffmpeg_path = ffmpeg_path
        self.video_files = []
        self.total_original_duration_sec = 0.0
        self.is_processing = False
        self.was_cancelled = False
        self.active_processes = []
        self.start_time = 0.0

    def _get_video_duration(self, filepath, ffprobe_bin):
        try:
            cmd = [ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filepath]
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=5
            )
            return float(result.stdout.strip())
        except Exception:
            return 60.0

    def scan_videos_multithreaded(self, root_folder):
        self.log_queue.put(("[Info] Buscando archivos compatibles...\n", None))
        
        extensions = ('.mp4', '.avi', '.mkv', '.mov', '.3gp', '.m4v')
        raw_files = []
        for root, _, files in os.walk(root_folder):
            for file in files:
                if file.lower().endswith(extensions):
                    raw_files.append(os.path.join(root, file))
        
        if not raw_files:
            self.log_queue.put(("UI_UPDATE_NO_FILES", None))
            return

        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
        
        raw_files.sort(key=natural_sort_key)
        self.video_files = raw_files
        
        self.log_queue.put(("UI_CLEAR_TREE", None))
        for idx, file_path in enumerate(self.video_files, 1):
            subfolder = os.path.basename(os.path.dirname(file_path))
            filename = os.path.basename(file_path)
            self.log_queue.put(("UI_INSERT_TREE", (idx, subfolder, filename, file_path)))
            
        self.log_queue.put((f"[Info] Extrayendo duración precisa de {len(self.video_files)} clips en paralelo...\n", None))
        
        ffmpeg_bin = self.ffmpeg_path.get()
        ffprobe_bin = "ffprobe"
        if os.path.isabs(ffmpeg_bin):
            base_dir = os.path.dirname(ffmpeg_bin)
            ffprobe_bin = os.path.join(base_dir, "ffprobe.exe" if sys.platform == "win32" else "ffprobe")
        
        total_duration = 0.0
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            durations = executor.map(lambda f: self._get_video_duration(f, ffprobe_bin), self.video_files)
            total_duration = sum(durations)
            
        self.total_original_duration_sec = total_duration
        self.log_queue.put(("UI_UPDATE_SCAN_SUCCESS", root_folder))

    def run_all_pipelines(self, configs):
        """Ejecuta multiples instancias de ffmpeg en paralelo."""
        self.is_processing = True
        self.was_cancelled = False
        self.active_processes = []
        self.start_time = time.time()
        
        # Diccionario para trackear el progreso individual
        # id -> progress percentage (0.0 to 1.0)
        self.progress_tracker = {config['id']: 0.0 for config in configs}
        
        def run_single(config):
            self.run_ffmpeg_pipeline(config)
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(configs)) as executor:
            futures = [executor.submit(run_single, config) for config in configs]
            concurrent.futures.wait(futures)
            
        if not self.was_cancelled:
            self.log_queue.put(("PROCESS_FINISHED", None))
        self.is_processing = False

    def run_ffmpeg_pipeline(self, config):
        tl_id = config['id']
        mode = config['mode']
        mute = config['mute']
        output_file = config['output_file']
        val = config['value'] # multiplicador o duración
        
        temp_list = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                temp_list = f.name
                for file_path in self.video_files:
                    escaped_path = os.path.abspath(file_path).replace("\\", "/").replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            if mode == "multi":
                multiplier = val
            else:
                multiplier = self.total_original_duration_sec / val if val > 0 else 20.0
                
            pts_ratio = 1.0 / multiplier
            video_filter = f"setpts={pts_ratio}*PTS"
            
            audio_args = []
            if mute:
                audio_args = ["-an"]
            else:
                atempo_chain = []
                remaining_speed = multiplier
                while remaining_speed > 2.0:
                    atempo_chain.append("atempo=2.0")
                    remaining_speed /= 2.0
                if remaining_speed >= 0.5:
                    atempo_chain.append(f"atempo={remaining_speed:.4f}")
                if atempo_chain:
                    audio_args = ["-filter:a", ",".join(atempo_chain)]

            use_gpu = config.get('use_gpu', False)
            if use_gpu:
                encoder_args = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]
            else:
                encoder_args = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23"]

            cmd = [
                self.ffmpeg_path.get(),
                "-y", "-f", "concat", "-safe", "0", "-i", temp_list,
                "-filter:v", video_filter
            ] + audio_args + encoder_args + [
                output_file
            ]
            
            self.log_queue.put((f"[Timelapse {tl_id}] Ejecutando comando...\n", None))
            expected_final_dur = self.total_original_duration_sec / multiplier
            
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            self.active_processes.append(process)
            
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                
                time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                if time_match:
                    h, m, s = map(float, time_match.groups())
                    current_processed_seconds = (h * 3600) + (m * 60) + s
                    
                    percentage = (current_processed_seconds / expected_final_dur) if expected_final_dur > 0 else 0
                    percentage = min(1.0, max(0.0, percentage))
                    
                    self.progress_tracker[tl_id] = percentage
                    
                    # Calcular el porcentaje de TODOS
                    total_percentage = sum(self.progress_tracker.values()) / len(self.progress_tracker)
                    
                    self.log_queue.put(("PROCESS_UPDATE", (tl_id, percentage, total_percentage, current_processed_seconds, expected_final_dur)))
                else:
                    if "frame=" in line or "fps=" in line or "size=" in line or "time=" in line or "speed=" in line:
                         pass # Skip printing every ffmpeg info line to avoid clutter, just rely on regex match
                    elif not line.isspace():
                         self.log_queue.put((f"[Timelapse {tl_id}] {line}", None))
            
            process.wait()
            ret_code = process.returncode
            if process in self.active_processes:
                self.active_processes.remove(process)
            
            if ret_code == 0:
                self.progress_tracker[tl_id] = 1.0
                total_percentage = sum(self.progress_tracker.values()) / len(self.progress_tracker)
                self.log_queue.put(("PROCESS_UPDATE", (tl_id, 1.0, total_percentage, expected_final_dur, expected_final_dur)))
                self.log_queue.put((f"[ÉXITO] Timelapse {tl_id} completado correctamente.\n", None))
            elif ret_code in (-9, 15, 1) or self.was_cancelled:
                self.log_queue.put((f"[Detenido] Timelapse {tl_id} finalizado/cancelado.\n", None))
            else:
                self.log_queue.put((f"[Error] Timelapse {tl_id} finalizó con código: {ret_code}\n", None))

        except Exception as e:
            self.log_queue.put((f"[Fallo Técnico] Timelapse {tl_id} Error: {str(e)}\n", None))
        finally:
            if temp_list and os.path.exists(temp_list):
                try: os.remove(temp_list)
                except OSError: pass

    def cancel_all(self):
        self.was_cancelled = True
        for process in self.active_processes:
            try:
                process.terminate()
            except Exception:
                pass
        self.active_processes.clear()
        self.is_processing = False
