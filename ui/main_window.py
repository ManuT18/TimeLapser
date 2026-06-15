import os
import sys
import time
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import threading

from utils.helpers import (
    BG_MAIN, BG_CARD, BORDER_COLOR, FG_TEXT, FG_MUTED, ACCENT_COLOR, 
    CONSOLE_BG, CONSOLE_FG, DANGER_COLOR, DANGER_HOVER, SECONDARY_BG, 
    SECONDARY_HOVER, format_time
)
from ui.components import PremiumCard, HoverToolTip
from core.processor import TimelapseProcessor

class TimelapseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Creador de Timelapses Profesional")
        self.geometry("1500x1000")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)
        
        # Variables globales de estado
        self.selected_dir = ctk.StringVar(value="")
        self.output_base = ctk.StringVar(value="")
        self.ffmpeg_path = ctk.StringVar(value="ffmpeg")
        self.num_timelapses = ctk.IntVar(value=1)
        self.use_gpu = ctk.BooleanVar(value=True)
        
        # Lista para guardar los widgets/variables de cada fila de config
        self.config_rows = []
        # Lista para las barras de progreso
        self.progress_bars = {}
        
        self.log_queue = queue.Queue()
        self.processor = TimelapseProcessor(self.log_queue, self.ffmpeg_path)
        
        self.setup_ttk_styles()
        self.build_ui()
        self.detect_ffmpeg()
        self.after(100, self.process_queue)
        
        self.rebuild_config_rows()

    def setup_ttk_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=BG_CARD,
                        foreground=FG_TEXT,
                        rowheight=24,
                        fieldbackground=BG_CARD,
                        borderwidth=0,
                        font=("Google Sans", 10))
        style.map("Treeview",
                  background=[("selected", "#E8F0FE")],
                  foreground=[("selected", ACCENT_COLOR)])
                  
        style.configure("Treeview.Heading",
                        background="#F1F3F4",
                        foreground=FG_MUTED,
                        font=("Google Sans", 10, "bold"),
                        borderwidth=1,
                        bordercolor=BORDER_COLOR)

    def build_ui(self):
        self.main_scroll = ctk.CTkFrame(self, fg_color="transparent", bg_color="transparent")
        self.main_scroll.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

        # --- HEADER ---
        header_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        header_frame.pack(fill=ctk.X, pady=(5, 10), padx=10)
        
        ctk.CTkLabel(header_frame, text="🎬", font=ctk.CTkFont(size=28)).pack(side=ctk.LEFT, padx=(0, 15))
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side=ctk.LEFT)
        ctk.CTkLabel(title_box, text="Timelapse Creator", font=ctk.CTkFont(family="Google Sans", size=24, weight="bold"), text_color=FG_TEXT).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Crea múltiples timelapses simultáneamente con FFmpeg", font=ctk.CTkFont(family="Google Sans", size=13), text_color=FG_MUTED).pack(anchor="w")

        self.btn_help = ctk.CTkButton(header_frame, text="❔ Ayuda", width=80, fg_color="#E8F0FE", text_color=ACCENT_COLOR, hover_color="#D2E3FC", font=ctk.CTkFont(family="Google Sans", weight="bold"), command=self.show_global_help)
        self.btn_help.pack(side=ctk.RIGHT, anchor="n")

        # --- TOP SPLIT (Archivos+Clips | Timelapses) ---
        top_split = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        top_split.pack(fill=ctk.BOTH, expand=True, pady=(0, 10), padx=10)
        
        top_split.grid_columnconfigure(0, weight=2)
        top_split.grid_columnconfigure(1, weight=3)
        top_split.grid_rowconfigure(0, weight=1)
        
        # 1. Izquierda: Archivos y Clips
        left_card = PremiumCard(top_split, "Archivos y Clips Originales", icon="📁")
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Rutas
        rutas_frame = ctk.CTkFrame(left_card.content, fg_color="transparent")
        rutas_frame.pack(fill=ctk.X, pady=(0, 15))
        
        orig_frame = ctk.CTkFrame(rutas_frame, fg_color="transparent")
        orig_frame.pack(fill=ctk.X, pady=(0, 5))
        ctk.CTkLabel(orig_frame, text="Directorio Origen:", width=120, anchor="w", font=ctk.CTkFont(family="Google Sans", weight="bold")).pack(side=ctk.LEFT)
        self.dir_entry = ctk.CTkEntry(orig_frame, textvariable=self.selected_dir, height=30, font=ctk.CTkFont(family="Google Sans", size=12))
        self.dir_entry.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))
        self.btn_browse_dir = ctk.CTkButton(orig_frame, text="Buscar", fg_color="#F1F3F4", text_color=FG_TEXT, hover_color="#E8EAED", height=30, width=70, font=ctk.CTkFont(family="Google Sans", weight="bold"), command=self.browse_directory)
        self.btn_browse_dir.pack(side=ctk.RIGHT)
        
        dest_frame = ctk.CTkFrame(rutas_frame, fg_color="transparent")
        dest_frame.pack(fill=ctk.X, pady=(5, 0))
        ctk.CTkLabel(dest_frame, text="Archivo Destino:", width=120, anchor="w", font=ctk.CTkFont(family="Google Sans", weight="bold")).pack(side=ctk.LEFT)
        self.dest_entry = ctk.CTkEntry(dest_frame, textvariable=self.output_base, height=30, font=ctk.CTkFont(family="Google Sans", size=12))
        self.dest_entry.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))
        self.btn_browse_out = ctk.CTkButton(dest_frame, text="Buscar", fg_color="#F1F3F4", text_color=FG_TEXT, hover_color="#E8EAED", height=30, width=70, font=ctk.CTkFont(family="Google Sans", weight="bold"), command=self.browse_output_file)
        self.btn_browse_out.pack(side=ctk.RIGHT)
        
        # Divisor
        ctk.CTkFrame(left_card.content, height=1, fg_color=BORDER_COLOR).pack(fill=ctk.X, pady=(5, 10))
        
        # Estadísticas y Clips
        stats_frame_top = ctk.CTkFrame(left_card.content, fg_color="transparent")
        stats_frame_top.pack(fill=ctk.X, pady=(0, 5))
        
        self.summary_label = ctk.CTkLabel(stats_frame_top, text="Esperando carpeta...", font=ctk.CTkFont(family="Google Sans", weight="bold"), text_color=FG_MUTED)
        self.summary_label.pack(side=ctk.LEFT)

        tree_container = ctk.CTkFrame(left_card.content, fg_color="transparent")
        tree_container.pack(fill=ctk.BOTH, expand=True)
        
        self.tree_scroll = ctk.CTkScrollbar(tree_container)
        self.tree_scroll.pack(side=ctk.RIGHT, fill=ctk.Y)
        
        self.tree = ttk.Treeview(tree_container, columns=("Index", "Subfolder", "Filename", "Fullpath"), show="headings", yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.configure(command=self.tree.yview)
        self.tree.heading("Index", text="#", anchor=tk.W)
        self.tree.heading("Subfolder", text="Carpeta", anchor=tk.W)
        self.tree.heading("Filename", text="Clip", anchor=tk.W)
        self.tree.heading("Fullpath", text="Ruta Absoluta", anchor=tk.W)
        self.tree.column("Index", width=50, stretch=False)
        self.tree.column("Subfolder", width=120, stretch=False)
        self.tree.column("Filename", width=150, stretch=False)
        self.tree.column("Fullpath", width=300, stretch=tk.YES)
        self.tree.pack(fill=ctk.BOTH, expand=True)

        # 2. Derecha: Timelapses
        right_card = PremiumCard(top_split, "Timelapses", icon="⚙️")
        right_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        top_multi = ctk.CTkFrame(right_card.content, fg_color="transparent")
        top_multi.pack(fill=ctk.X, pady=(0, 5))
        ctk.CTkLabel(top_multi, text="Cantidad a generar:", font=ctk.CTkFont(family="Google Sans", weight="bold")).pack(side=ctk.LEFT)
        
        spin_frame = ctk.CTkFrame(top_multi, fg_color="transparent")
        spin_frame.pack(side=ctk.LEFT, padx=10)
        
        ctk.CTkButton(spin_frame, text="-", width=30, height=30, command=lambda: self.change_num_timelapses(-1)).pack(side=ctk.LEFT, padx=(0, 5))
        self.lbl_num = ctk.CTkLabel(spin_frame, textvariable=self.num_timelapses, font=ctk.CTkFont(family="Google Sans", weight="bold"), width=20)
        self.lbl_num.pack(side=ctk.LEFT)
        ctk.CTkButton(spin_frame, text="+", width=30, height=30, command=lambda: self.change_num_timelapses(1)).pack(side=ctk.LEFT, padx=(5, 0))

        ctk.CTkSwitch(top_multi, text="GPU (NVENC)", variable=self.use_gpu, font=ctk.CTkFont(family="Google Sans", size=12, weight="bold")).pack(side=ctk.RIGHT, padx=10)

        self.configs_container = ctk.CTkScrollableFrame(right_card.content, fg_color="transparent")
        self.configs_container.pack(fill=ctk.BOTH, expand=True, pady=(10, 0))

        # --- CONSOLA Y BOTONES ---
        middle_split = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        middle_split.pack(fill=ctk.X, pady=(0, 10), padx=10)
        
        console_container = ctk.CTkFrame(middle_split, fg_color="transparent")
        console_container.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=(0, 15))
        
        self.console_text = tk.Text(console_container, height=12, bg="#1E1E1E", fg="#D4D4D4", font=("Consolas", 11), relief=tk.FLAT, padx=12, pady=12, insertbackground="white")
        self.console_text.pack(fill=ctk.BOTH, expand=True)
        
        self.console_text.tag_config("header", foreground="#FF79C6", font=("Consolas", 11, "bold"))
        self.console_text.tag_config("info", foreground="#8BE9FD")
        self.console_text.tag_config("error", foreground="#FF5555", font=("Consolas", 11, "bold"))
        self.console_text.tag_config("success", foreground="#50FA7B", font=("Consolas", 11, "bold"))
        self.console_text.tag_config("default", foreground="#F8F8F2")
        
        btn_panel = ctk.CTkFrame(middle_split, fg_color="transparent")
        btn_panel.pack(side=ctk.RIGHT, fill=ctk.Y)
        
        self.btn_generate = ctk.CTkButton(btn_panel, text="Generar Todo", text_color="white", fg_color=ACCENT_COLOR, hover_color="#1557B0", height=45, width=150, font=ctk.CTkFont(family="Google Sans", weight="bold", size=13), command=self.start_timelapses, state="disabled")
        self.btn_generate.pack(fill=ctk.X, pady=(0, 10))

        self.btn_cancel = ctk.CTkButton(btn_panel, text="Cancelar", text_color="white", fg_color=DANGER_COLOR, hover_color=DANGER_HOVER, height=45, width=150, font=ctk.CTkFont(family="Google Sans", weight="bold", size=13), command=self.cancel_timelapses, state="disabled")
        self.btn_cancel.pack(fill=ctk.X, pady=(0, 10))

        self.btn_open_file = ctk.CTkButton(btn_panel, text="Ir a la carpeta", text_color="white", fg_color="#34A853", hover_color="#2D9248", height=45, width=150, font=ctk.CTkFont(family="Google Sans", weight="bold", size=13), command=self.open_output_folder, state="disabled")
        self.btn_open_file.pack(fill=ctk.X)

        # --- BARRAS DE PROGRESO ---
        self.progress_container = ctk.CTkScrollableFrame(self.main_scroll, height=150, fg_color="transparent")
        self.progress_container.pack(fill=ctk.X, padx=10, pady=(0, 0))

        self.console_write("--- Creador de Timelapses Paralelo listo ---\n")

    def change_num_timelapses(self, delta):
        new_val = self.num_timelapses.get() + delta
        if 1 <= new_val <= 10:
            self.num_timelapses.set(new_val)
            self.rebuild_config_rows()

    def rebuild_config_rows(self):
        for widget in self.configs_container.winfo_children():
            widget.destroy()
        
        self.config_rows = []
        n = self.num_timelapses.get()
        for i in range(n):
            row_id = i + 1
            row_frame = ctk.CTkFrame(self.configs_container, fg_color=SECONDARY_BG, corner_radius=6)
            row_frame.pack(fill=ctk.X, pady=(0, 5), padx=5)
            
            ctk.CTkLabel(row_frame, text=f"TL #{row_id}", width=50, font=ctk.CTkFont(family="Google Sans", weight="bold", size=13), text_color=ACCENT_COLOR).pack(side=ctk.LEFT, padx=10, pady=10)
            
            duration_var = ctk.StringVar(value="15")
            mute_var = ctk.BooleanVar(value=True)
            
            controls_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            controls_frame.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=10, pady=10)
            
            ctk.CTkLabel(controls_frame, text="Duración (segs):", font=ctk.CTkFont(family="Google Sans", weight="bold", size=12)).pack(side=ctk.LEFT)
            entry = ctk.CTkEntry(controls_frame, textvariable=duration_var, width=60, height=28)
            entry.pack(side=ctk.LEFT, padx=(10, 0))
            
            ctk.CTkSwitch(row_frame, text="Sin Audio", variable=mute_var, font=ctk.CTkFont(family="Google Sans", size=12)).pack(side=ctk.RIGHT, padx=15)
            
            self.config_rows.append({
                'id': row_id,
                'duration': duration_var,
                'mute': mute_var
            })

    def browse_directory(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta raíz con los videos")
        if folder:
            self.selected_dir.set(folder)
            threading.Thread(target=self.processor.scan_videos_multithreaded, args=(folder,), daemon=True).start()

    def browse_output_file(self):
        file_path = filedialog.asksaveasfilename(
            title="Guardar Timelapse Base Como",
            defaultextension=".mp4",
            filetypes=[("Video MP4", "*.mp4")]
        )
        if file_path:
            self.output_base.set(file_path)

    def detect_ffmpeg(self):
        import subprocess
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            self.ffmpeg_path.set("ffmpeg")
            self.console_write("[Info] FFmpeg detectado exitosamente.\n")
        except:
            self.console_write("[Error] FFmpeg no detectado en PATH. Instalalo con 'winget install ffmpeg'.\n")

    def console_write(self, text):
        self.console_text.config(state=tk.NORMAL)
        start_idx = self.console_text.index("end - 1c")
        self.console_text.insert(tk.END, text)
        end_idx = self.console_text.index("end - 1c")
        
        if "=== " in text: self.console_text.tag_add("header", start_idx, end_idx)
        elif "[Info]" in text: self.console_text.tag_add("info", start_idx, end_idx)
        elif "[Error]" in text or "[Fallo Técnico]" in text: self.console_text.tag_add("error", start_idx, end_idx)
        elif "[ÉXITO]" in text: self.console_text.tag_add("success", start_idx, end_idx)
        else: self.console_text.tag_add("default", start_idx, end_idx)
            
        self.console_text.see(tk.END)
        self.console_text.config(state=tk.DISABLED)

    def start_timelapses(self):
        if not self.processor.video_files:
            messagebox.showerror("Error", "No hay archivos cargados.")
            return
        if not self.output_base.get():
            messagebox.showerror("Error", "Seleccione un archivo destino base.")
            return

        configs = []
        base_dir = os.path.dirname(self.output_base.get())
        base_name, base_ext = os.path.splitext(os.path.basename(self.output_base.get()))
        
        for row in self.config_rows:
            rid = row['id']
            try:
                val = float(row['duration'].get())
                if val <= 0: raise ValueError
            except ValueError:
                messagebox.showerror("Error", f"TL #{rid}: Duración inválida.")
                return
            
            out_file = os.path.join(base_dir, f"{base_name}_{rid}{base_ext}") if len(self.config_rows) > 1 else self.output_base.get()
            
            configs.append({
                'id': rid,
                'mode': 'duration', # Siempre duración ahora
                'value': val,
                'mute': row['mute'].get(),
                'output_file': out_file,
                'use_gpu': self.use_gpu.get()
            })

        self.btn_generate.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.btn_open_file.configure(state="disabled")
        self.dir_entry.configure(state="disabled")
        self.dest_entry.configure(state="disabled")
        
        # Preparar barras de progreso
        for widget in self.progress_container.winfo_children():
            widget.destroy()
        
        self.progress_bars = {}
        for config in configs:
            rid = config['id']
            frame = ctk.CTkFrame(self.progress_container, fg_color="transparent")
            frame.pack(fill=ctk.X, pady=(0, 5))
            ctk.CTkLabel(frame, text=f"TL #{rid}", width=50, font=ctk.CTkFont(weight="bold", size=12)).pack(side=ctk.LEFT)
            pbar = ctk.CTkProgressBar(frame, mode='determinate', height=8, progress_color="#34A853")
            pbar.set(0)
            pbar.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=10)
            lbl = ctk.CTkLabel(frame, text="0%", width=40, font=ctk.CTkFont(size=11))
            lbl.pack(side=ctk.RIGHT)
            self.progress_bars[rid] = (pbar, lbl)

        self.console_write("\n=== Iniciando Renderizado de Timelapses en Paralelo ===\n")
        threading.Thread(target=self.processor.run_all_pipelines, args=(configs,), daemon=True).start()

    def cancel_timelapses(self):
        if self.processor.is_processing:
            if messagebox.askyesno("Confirmar", "¿Abortar todos los timelapses?"):
                self.console_write("\n[Info] Cancelando procesos...\n")
                self.processor.cancel_all()

    def open_output_folder(self):
        import subprocess
        import os
        import sys
        file_path = self.output_base.get()
        dir_path = os.path.dirname(file_path) if file_path else ""
        if os.path.exists(dir_path):
            if sys.platform == "win32":
                subprocess.run(['explorer', os.path.normpath(dir_path)])
            else:
                import platform
                if platform.system() == "Darwin":
                    subprocess.run(['open', dir_path])
                else:
                    subprocess.run(['xdg-open', dir_path])

    def process_queue(self):
        try:
            while True:
                msg, data = self.log_queue.get_nowait()
                
                if msg == "UI_CLEAR_TREE":
                    for item in self.tree.get_children():
                        self.tree.delete(item)
                elif msg == "UI_INSERT_TREE":
                    self.tree.insert("", tk.END, values=data)
                elif msg == "UI_UPDATE_NO_FILES":
                    self.summary_label.configure(text="No se encontraron archivos válidos.", text_color=DANGER_COLOR)
                elif msg == "UI_UPDATE_SCAN_SUCCESS":
                    root_folder = data
                    default_out = os.path.join(root_folder, "timelapse_generado.mp4")
                    self.output_base.set(default_out)
                    total_clips = len(self.processor.video_files)
                    formatted_orig = format_time(self.processor.total_original_duration_sec)
                    self.summary_label.configure(
                        text=f"Total: {total_clips} videos. Duración Original: {formatted_orig}.",
                        text_color=ACCENT_COLOR
                    )
                    self.btn_generate.configure(state="normal")
                    
                elif msg == "PROCESS_UPDATE":
                    tl_id, percentage, total_percentage, curr_sec, exp_sec = data
                    if tl_id in self.progress_bars:
                        pbar, lbl = self.progress_bars[tl_id]
                        pbar.set(percentage)
                        lbl.configure(text=f"{int(percentage*100)}%")
                elif msg == "PROCESS_FINISHED":
                    self.btn_generate.configure(state="normal")
                    self.btn_cancel.configure(state="disabled")
                    self.btn_open_file.configure(state="normal")
                    self.dir_entry.configure(state="normal")
                    self.dest_entry.configure(state="normal")
                    self.console_write("=== Procesamiento Finalizado ===\n")
                else:
                    self.console_write(msg)
                
                self.log_queue.task_done()
        except queue.Empty:
            pass
        self.after(100, self.process_queue)

    def show_global_help(self):
        messagebox.showinfo("Ayuda", "Selecciona el origen y destino base.\nAgrega los timelapses que necesites e indica la duración final deseada de cada uno.\nDale a Generar Todo para procesarlos en paralelo.")
