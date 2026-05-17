# -*- coding: utf-8 -*-
import os
import sys
import threading
import queue
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

# Carga dinámica de fuentes Google Sans en Windows
def load_custom_fonts():
    import ctypes
    import os
    import sys
    
    if hasattr(sys, '_MEIPASS'):
        font_dir = sys._MEIPASS
    else:
        font_dir = os.path.dirname(os.path.abspath(__file__))
        
    font_files = ["GoogleSans-Regular.ttf", "GoogleSans-Bold.ttf", "GoogleSans-Medium.ttf"]
    for font_file in font_files:
        font_path = os.path.join(font_dir, font_file)
        if os.path.exists(font_path):
            ctypes.windll.gdi32.AddFontResourceW(font_path)

try:
    load_custom_fonts()
except Exception:
    pass

# Configuración base de CustomTkinter
ctk.set_appearance_mode("light")  # Forzamos el modo claro premium
ctk.set_default_color_theme("blue")  # Tema azul por defecto (coincide con nuestro acento #1A73E8)

# Constantes de Color Secundarias para Elementos Nativos/Customizados
BG_MAIN = "#F8F9FA"         # Gris muy claro
BG_CARD = "#FFFFFF"         # Blanco puro
BORDER_COLOR = "#DADCE0"    # Borde sutil
FG_TEXT = "#202124"         # Texto oscuro
FG_MUTED = "#5F6368"        # Texto secundario
ACCENT_COLOR = "#1A73E8"    # Azul corporativo
CONSOLE_BG = "#202124"      # Consola oscura
CONSOLE_FG = "#FFFFFF"      # Texto de consola blanco
DANGER_COLOR = "#D93025"    # Rojo para cancelaciones
DANGER_HOVER = "#B31412"    # Rojo hover
SECONDARY_BG = "#F1F3F4"    # Fondo secundario
SECONDARY_HOVER = "#E8EAED" # Fondo secundario hover

def format_time(seconds):
    """Formatea segundos en HH:MM:SS."""
    if seconds < 0: return "00:00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class HoverToolTip:
    """Clase personalizada para crear tooltips flotantes al pasar el mouse por encima de un widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        border = ctk.CTkFrame(tw, fg_color=BORDER_COLOR, corner_radius=6)
        border.pack(fill=tk.BOTH, expand=True)
        
        label = ctk.CTkLabel(border, text=self.text, fg_color="#202124", text_color="white",
                             corner_radius=4, padx=10, pady=5, 
                             font=ctk.CTkFont(family="Google Sans", size=11))
        label.pack(padx=1, pady=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class PremiumCard(ctk.CTkFrame):
    """Contenedor de tarjeta con bordes redondeados y sombra sutil (CustomTkinter)."""
    def __init__(self, master, title_text, icon="", tooltip_text="", **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR, **kwargs)
        
        # Header de la tarjeta
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill=ctk.X, padx=20, pady=(10, 2))
        
        # Decorador lateral azul
        accent = ctk.CTkFrame(header, fg_color=ACCENT_COLOR, width=4, height=16, corner_radius=2)
        accent.pack(side=ctk.LEFT, padx=(0, 10))
        accent.pack_propagate(False)
        
        # Icono (si existe) separado para evitar problemas de alineación
        if icon:
            ctk.CTkLabel(
                header,
                text=icon,
                font=ctk.CTkFont(size=14),
                text_color=ACCENT_COLOR
            ).pack(side=ctk.LEFT, padx=(0, 6))
        
        # Título
        ctk.CTkLabel(
            header, 
            text=title_text, 
            font=ctk.CTkFont(family="Google Sans", size=14, weight="bold"),
            text_color=ACCENT_COLOR
        ).pack(side=ctk.LEFT)
        
        # Icono de información (Tooltip)
        if tooltip_text:
            info_lbl = ctk.CTkLabel(
                header,
                text="ℹ️",
                font=ctk.CTkFont(size=14),
                text_color=FG_MUTED,
                cursor="hand2"
            )
            info_lbl.pack(side=ctk.LEFT, padx=(8, 0))
            HoverToolTip(info_lbl, tooltip_text)
        
        # Línea divisoria
        divider = ctk.CTkFrame(self, fg_color=BORDER_COLOR, height=1)
        divider.pack(fill=ctk.X, padx=20, pady=(2, 5))
        
        # Área de contenido
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill=ctk.BOTH, expand=True, padx=20, pady=(0, 10))

class TimelapseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Creador de Timelapses Profesional")
        self.geometry("1080x920")
        self.resizable(False, False) # Evita que se deforme si la maximizan
        self.configure(fg_color=BG_MAIN)
        
        # Variables de estado
        self.selected_dir = ctk.StringVar(value="")
        self.output_file = ctk.StringVar(value="")
        self.speed_multiplier = ctk.DoubleVar(value=20.0)
        self.mute_audio = ctk.BooleanVar(value=True)
        self.ffmpeg_path = ctk.StringVar(value="ffmpeg")
        
        self.video_files = []
        self.total_original_duration_sec = 0.0  # Duración original precisa calculada
        
        self.log_queue = queue.Queue()
        self.is_processing = False
        self.process = None
        self.start_time = 0.0 # Para calcular ETA
        self.was_cancelled = False
        
        self.setup_ttk_styles()
        self.build_ui()
        self.detect_ffmpeg()
        self.after(100, self.process_queue)

    def setup_ttk_styles(self):
        """Estiliza los componentes nativos ttk (Treeview) para combinar con el tema claro de CTk."""
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
        # Contenedor principal
        self.main_scroll = ctk.CTkFrame(self, fg_color="transparent", bg_color="transparent")
        self.main_scroll.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

        # --- HEADER ---
        header_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        header_frame.pack(fill=ctk.X, pady=(5, 10), padx=10)
        
        ctk.CTkLabel(header_frame, text="🎬", font=ctk.CTkFont(size=28)).pack(side=ctk.LEFT, padx=(0, 15))
        
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side=ctk.LEFT)
        ctk.CTkLabel(title_box, text="Timelapse Creator", font=ctk.CTkFont(family="Google Sans", size=24, weight="bold"), text_color=FG_TEXT).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Une y acelera fragmentos cronológicos en un solo timelapse fluido", font=ctk.CTkFont(family="Google Sans", size=13), text_color=FG_MUTED).pack(anchor="w")

        # Botón de ayuda global
        self.btn_help = ctk.CTkButton(header_frame, text="ℹ️ Ayuda", width=80, fg_color="#E8F0FE", text_color=ACCENT_COLOR, hover_color="#D2E3FC", font=ctk.CTkFont(family="Google Sans", weight="bold"), command=self.show_global_help)
        self.btn_help.pack(side=ctk.RIGHT, anchor="n")

        # --- FILA SUPERIOR (Lado a Lado) ---
        top_row = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        top_row.pack(fill=ctk.X, pady=(0, 10), padx=10)
        
        # 1. Directorio de Origen
        dir_card = PremiumCard(top_row, "Directorio de Origen (MicroSD)", icon="📁", tooltip_text="Selecciona la carpeta o unidad donde están guardados\nlos videos originales de tu cámara.")
        dir_card.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=(0, 5))
        
        dir_layout = ctk.CTkFrame(dir_card.content, fg_color="transparent")
        dir_layout.pack(fill=ctk.X, pady=(10, 0))
        self.dir_entry = ctk.CTkEntry(dir_layout, textvariable=self.selected_dir, height=30, font=ctk.CTkFont(family="Google Sans", size=12))
        self.dir_entry.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))
        
        self.btn_browse_dir = ctk.CTkButton(dir_layout, text="Buscar", fg_color="#F1F3F4", text_color=FG_TEXT, hover_color="#E8EAED", height=30, font=ctk.CTkFont(family="Google Sans", weight="bold"), command=self.browse_directory)
        self.btn_browse_dir.pack(side=ctk.RIGHT)
        
        # Mensaje de ayuda/UX para rellenar de forma premium el espacio vertical
        self.dir_help_desc = ctk.CTkLabel(
            dir_card.content,
            text="💡 Selecciona la carpeta raíz que contiene tus grabaciones.\nSe escanearán automáticamente todas las subcarpetas.",
            font=ctk.CTkFont(family="Google Sans", size=11, slant="italic"),
            text_color=FG_MUTED,
            justify=tk.LEFT,
            anchor="w"
        )
        self.dir_help_desc.pack(fill=ctk.X, pady=(15, 0))

        # 2. Configuración de Exportación
        params_card = PremiumCard(top_row, "Exportación", icon="⚙️", tooltip_text="Configura a qué velocidad se acelerará el video\ny dónde se guardará el archivo resultante.")
        params_card.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=(5, 0))
        
        params_layout = ctk.CTkFrame(params_card.content, fg_color="transparent")
        params_layout.pack(fill=ctk.X)
        
        speed_header = ctk.CTkFrame(params_layout, fg_color="transparent")
        speed_header.pack(fill=ctk.X, pady=(0, 5))
        ctk.CTkLabel(speed_header, text="Velocidad:", font=ctk.CTkFont(family="Google Sans", weight="bold")).pack(side=ctk.LEFT)
        self.speed_val_label = ctk.CTkLabel(speed_header, text="20.0x", font=ctk.CTkFont(family="Google Sans", weight="bold"), text_color=ACCENT_COLOR)
        self.speed_val_label.pack(side=ctk.LEFT, padx=10)
        self.audio_check = ctk.CTkSwitch(speed_header, text="Silenciar audio", variable=self.mute_audio, font=ctk.CTkFont(family="Google Sans", size=12))
        self.audio_check.pack(side=ctk.RIGHT)
        
        self.speed_slider = ctk.CTkSlider(params_layout, from_=20.0, to=500.0, number_of_steps=960, variable=self.speed_multiplier, command=self.update_speed_label)
        self.speed_slider.pack(fill=ctk.X, pady=(0, 10))

        dest_layout = ctk.CTkFrame(params_layout, fg_color="transparent")
        dest_layout.pack(fill=ctk.X)
        self.dest_entry = ctk.CTkEntry(dest_layout, textvariable=self.output_file, height=30, font=ctk.CTkFont(family="Google Sans", size=12))
        self.dest_entry.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))
        self.btn_browse_out = ctk.CTkButton(dest_layout, text="Destino", fg_color="#F1F3F4", text_color=FG_TEXT, hover_color="#E8EAED", height=30, width=70, font=ctk.CTkFont(family="Google Sans", weight="bold"), command=self.browse_output_file)
        self.btn_browse_out.pack(side=ctk.RIGHT)

        # --- SECCIÓN TABLA Y ESTADÍSTICAS ---
        list_card = PremiumCard(self.main_scroll, "Clips Originales Detectados", icon="📊", tooltip_text="Lista ordenada de todos los fragmentos que se van\na unir para formar tu timelapse.")
        list_card.pack(fill=ctk.BOTH, expand=True, pady=(0, 10), padx=10)
        
        stats_frame_top = ctk.CTkFrame(list_card.content, fg_color="transparent")
        stats_frame_top.pack(fill=ctk.X, pady=(0, 5))
        
        self.summary_label = ctk.CTkLabel(stats_frame_top, text="Esperando carpeta...", font=ctk.CTkFont(family="Google Sans", weight="bold"), text_color=FG_MUTED)
        self.summary_label.pack(side=ctk.LEFT)
        
        self.est_time_label = ctk.CTkLabel(stats_frame_top, text="Tiempo estimado: --:--:--", font=ctk.CTkFont(family="Google Sans", size=12, slant="italic", weight="bold"), text_color=ACCENT_COLOR)
        self.est_time_label.pack(side=ctk.RIGHT)

        tree_container = ctk.CTkFrame(list_card.content, fg_color="transparent")
        tree_container.pack(fill=ctk.BOTH, expand=True, pady=(0, 5))
        
        self.tree_scroll = ctk.CTkScrollbar(tree_container)
        self.tree_scroll.pack(side=ctk.RIGHT, fill=ctk.Y)
        
        self.tree = ttk.Treeview(tree_container, columns=("Index", "Subfolder", "Filename", "Fullpath"), show="headings", yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.configure(command=self.tree.yview)
        self.tree.heading("Index", text="#", anchor=tk.W)
        self.tree.heading("Subfolder", text="Carpeta de Origen", anchor=tk.W)
        self.tree.heading("Filename", text="Nombre del Clip", anchor=tk.W)
        self.tree.heading("Fullpath", text="Ruta Absoluta", anchor=tk.W)
        self.tree.column("Index", width=50, stretch=False)
        self.tree.column("Subfolder", width=180, stretch=False)
        self.tree.column("Filename", width=150, stretch=False)
        self.tree.column("Fullpath", width=400, stretch=tk.YES)
        self.tree.pack(fill=ctk.BOTH, expand=True)

        # --- SECCIÓN INFERIOR: CONSOLA Y BOTONES ---
        action_card = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        action_card.pack(fill=ctk.X, pady=(0, 5), padx=10)
        
        bottom_split = ctk.CTkFrame(action_card, fg_color="transparent")
        bottom_split.pack(fill=ctk.X)
        
        # Izquierda: Consola Grande y Progreso
        console_container = ctk.CTkFrame(bottom_split, fg_color="transparent")
        console_container.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=(0, 15))
        
        self.console_text = tk.Text(console_container, height=8, bg=CONSOLE_BG, fg=CONSOLE_FG, font=("Consolas", 10), relief=tk.FLAT, padx=12, pady=12, insertbackground="white")
        self.console_text.pack(fill=ctk.BOTH, expand=True)
        
        self.console_text.tag_config("info", foreground="#8AB4F8")
        self.console_text.tag_config("warning", foreground="#FDD663")
        self.console_text.tag_config("error", foreground="#F28B82")
        self.console_text.tag_config("success", foreground="#81C995")
        self.console_text.tag_config("ffmpeg", foreground="#D7AEFB")
        
        prog_eta_frame = ctk.CTkFrame(console_container, fg_color="transparent")
        prog_eta_frame.pack(fill=ctk.X, pady=(10, 0))
        
        self.progress_bar = ctk.CTkProgressBar(
            prog_eta_frame, 
            mode='determinate', 
            height=8,
            corner_radius=4,
            progress_color="#34A853",
            fg_color="#E8EAED"
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill=ctk.X, pady=(0, 5))
        
        stats_line = ctk.CTkFrame(prog_eta_frame, fg_color="transparent")
        stats_line.pack(fill=ctk.X)
        self.progress_lbl = ctk.CTkLabel(stats_line, text="0%", font=ctk.CTkFont(family="Google Sans", weight="bold"), text_color=FG_MUTED)
        self.progress_lbl.pack(side=ctk.LEFT)
        self.eta_label = ctk.CTkLabel(stats_line, text="Tiempo estimado: --:--", font=ctk.CTkFont(family="Google Sans", size=13, weight="bold"), text_color=ACCENT_COLOR)
        self.eta_label.pack(side=ctk.RIGHT)
        

        
        # Derecha: Botones Exclusivamente
        btn_panel = ctk.CTkFrame(bottom_split, fg_color="transparent")
        btn_panel.pack(side=ctk.RIGHT, fill=ctk.Y, pady=20)
        
        # Botones Blancos (Generar arriba de Cancelar)
        self.btn_generate = ctk.CTkButton(btn_panel, text="Generar Timelapse", text_color="white", fg_color=ACCENT_COLOR, hover_color="#1557B0", height=45, font=ctk.CTkFont(family="Google Sans", weight="bold", size=13), command=self.start_timelapse, state="disabled")
        self.btn_generate.pack(fill=ctk.X, pady=(0, 10))

        self.btn_cancel = ctk.CTkButton(btn_panel, text="Cancelar", text_color="white", fg_color=DANGER_COLOR, hover_color=DANGER_HOVER, height=45, font=ctk.CTkFont(family="Google Sans", weight="bold", size=13), command=self.cancel_timelapse, state="disabled")
        self.btn_cancel.pack(fill=ctk.X, pady=(0, 10))

        self.btn_open_file = ctk.CTkButton(btn_panel, text="Ir al archivo", text_color="white", fg_color="#34A853", hover_color="#2D9248", height=45, font=ctk.CTkFont(family="Google Sans", weight="bold", size=13), command=self.open_output_folder, state="disabled")
        self.btn_open_file.pack(fill=ctk.X)

        self.console_write("--- Consola de Inicialización lista ---\n")

    def update_speed_label(self, val):
        """Actualiza el label numérico y recalcula el tiempo final estimado."""
        rounded_val = round(float(val) * 2.0) / 2.0
        self.speed_val_label.configure(text=f"{rounded_val:.1f}x")
        
        if self.total_original_duration_sec > 0:
            est_final_sec = self.total_original_duration_sec / rounded_val
            formatted_time = format_time(est_final_sec)
            self.est_time_label.configure(text=f"Tiempo estimado final: {formatted_time}", text_color=FG_TEXT)
        else:
            self.est_time_label.configure(text="Tiempo estimado: --:--:--", text_color=FG_MUTED)

    def console_write(self, text):
        """Escribe un mensaje de forma segura en la consola interna de texto con etiquetas de color."""
        self.console_text.config(state=tk.NORMAL)
        start_idx = self.console_text.index("end - 1c")
        self.console_text.insert(tk.END, text)
        end_idx = self.console_text.index("end - 1c")
        
        if "[Info]" in text or "Escaneando" in text or "detectaron" in text:
            self.console_text.tag_add("info", start_idx, end_idx)
        elif "[ADVERTENCIA]" in text or "WARNING" in text:
            self.console_text.tag_add("warning", start_idx, end_idx)
        elif "[Error]" in text or "[Fallo Técnico]" in text or "Failed" in text or "error:" in text.lower():
            self.console_text.tag_add("error", start_idx, end_idx)
        elif "[ÉXITO]" in text or "correctamente" in text or "completado" in text:
            self.console_text.tag_add("success", start_idx, end_idx)
        elif "[FFmpeg]" in text or "Ejecutando:" in text or "Tiempo estimado:" in text or "frame=" in text or "fps=" in text or "size=" in text or "Procesando..." in text:
            self.console_text.tag_add("ffmpeg", start_idx, end_idx)
        else:
            self.console_text.tag_add("ffmpeg", start_idx, end_idx)
            
        self.console_text.see(tk.END)
        self.console_text.config(state=tk.DISABLED)

    def browse_directory(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta raíz con los videos")
        if folder:
            self.selected_dir.set(folder)
            self.console_write(f"[Info] Escaneando de forma recursiva: {folder}\n")
            threading.Thread(target=self.scan_videos_multithreaded, args=(folder,), daemon=True).start()

    def _get_video_duration(self, filepath, ffprobe_bin):
        import subprocess
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
        import re
        import concurrent.futures
        self.log_queue.put(("[Info] Buscando archivos compatibles...\n", None))
        self.btn_generate.configure(state="disabled")
        self.btn_browse_dir.configure(state="disabled")
        
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

    def browse_output_file(self):
        file_path = filedialog.asksaveasfilename(
            title="Guardar Timelapse Como",
            defaultextension=".mp4",
            filetypes=[("Video MP4", "*.mp4"), ("Todos los archivos", "*.*")]
        )
        if file_path:
            self.output_file.set(file_path)

    def detect_ffmpeg(self):
        import subprocess
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.ffmpeg_path.set("ffmpeg")
            self.console_write("[FFmpeg] Detectado exitosamente en las variables de entorno globales.\n")
        except (subprocess.CalledProcessError, FileNotFoundError):
            common_paths = [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                "/usr/bin/ffmpeg",
                "/usr/local/bin/ffmpeg"
            ]
            found = False
            for path in common_paths:
                if os.path.exists(path):
                    self.ffmpeg_path.set(path)
                    self.console_write(f"[FFmpeg] Detectado en ruta alternativa: {path}\n")
                    found = True
                    break
            if not found:
                self.console_write("[ADVERTENCIA] FFmpeg no fue detectado automáticamente. Asegúrese de instalarlo.\n")
                self.ffmpeg_path.set("")
                messagebox.showerror(
                    "FFmpeg no encontrado",
                    "No se detectó FFmpeg en el sistema.\n\n"
                    "Es necesario instalarlo para generar los timelapses.\n"
                    "Podés instalarlo fácilmente abriendo CMD como administrador y ejecutando el siguiente comando:\n\n"
                    "winget install ffmpeg"
                )

    def start_timelapse(self):
        if not self.video_files:
            messagebox.showerror("Error", "No hay archivos cargados.")
            return
        if not self.ffmpeg_path.get():
            messagebox.showerror(
                "FFmpeg no encontrado",
                "No se detectó FFmpeg en el sistema.\n\n"
                "Es necesario instalarlo para generar los timelapses.\n"
                "Podés instalarlo fácilmente abriendo CMD como administrador y ejecutando el siguiente comando:\n\n"
                "winget install ffmpeg"
            )
            return
        if not self.output_file.get():
            messagebox.showerror("Error", "Especifique archivo de salida.")
            return

        self.is_processing = True
        self.was_cancelled = False
        self.btn_generate.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.btn_open_file.configure(state="disabled")
        self.dir_entry.configure(state="disabled")
        self.dest_entry.configure(state="disabled")
        self.speed_slider.configure(state="disabled")
        self.audio_check.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_lbl.configure(text="0%")
        self.eta_label.configure(text="Tiempo estimado: Calculando...")
        self.start_time = time.time()
        
        self.console_write("\n=== Iniciando Renderizado del Timelapse ===\n")
        threading.Thread(target=self.run_ffmpeg_pipeline, daemon=True).start()

    def run_ffmpeg_pipeline(self):
        import tempfile
        import subprocess
        import re
        temp_list = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                temp_list = f.name
                for file_path in self.video_files:
                    escaped_path = os.path.abspath(file_path).replace("\\", "/").replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            multiplier = round(float(self.speed_multiplier.get()) * 2.0) / 2.0
            pts_ratio = 1.0 / multiplier
            video_filter = f"setpts={pts_ratio}*PTS"
            
            audio_args = []
            if self.mute_audio.get():
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

            cmd = [
                self.ffmpeg_path.get(),
                "-y", "-f", "concat", "-safe", "0", "-i", temp_list,
                "-filter:v", video_filter
            ] + audio_args + [
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                self.output_file.get()
            ]
            
            self.log_queue.put((f"[FFmpeg] Ejecutando comando...\n", None))
            expected_final_dur = self.total_original_duration_sec / multiplier
            
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            while True:
                line = self.process.stderr.readline()
                if not line:
                    break
                
                time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                if time_match:
                    h, m, s = map(float, time_match.groups())
                    current_processed_seconds = (h * 3600) + (m * 60) + s
                    
                    percentage = (current_processed_seconds / expected_final_dur) if expected_final_dur > 0 else 0
                    percentage = min(1.0, max(0.0, percentage))
                    
                    elapsed_time = time.time() - self.start_time
                    eta_text = "Calculando..."
                    
                    if percentage > 0.01 and elapsed_time > 3.0:
                        processing_speed = current_processed_seconds / elapsed_time
                        if processing_speed > 0:
                            remaining_sec = (expected_final_dur - current_processed_seconds) / processing_speed
                            eta_text = format_time(remaining_sec)
                    
                    self.log_queue.put(("PROCESS_UPDATE", (percentage, current_processed_seconds, expected_final_dur, eta_text)))
                else:
                    self.log_queue.put((line, None))
            
            self.process.wait()
            ret_code = self.process.returncode
            
            if ret_code == 0:
                self.log_queue.put(("[ÉXITO] El timelapse se ha generado correctamente.\n", 1.0))
            elif ret_code in (-9, 15, 1):
                self.log_queue.put(("[Detenido] Proceso finalizado/cancelado.\n", 0.0))
            else:
                self.log_queue.put((f"[Error] FFmpeg finalizó con código: {ret_code}\n", 0.0))

        except Exception as e:
            self.log_queue.put((f"[Fallo Técnico] Error: {str(e)}\n", 0.0))
        finally:
            if temp_list and os.path.exists(temp_list):
                try: os.remove(temp_list)
                except OSError: pass
            self.log_queue.put(("PROCESS_FINISHED", None))

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
                    self.btn_generate.configure(state="disabled")
                    self.btn_browse_dir.configure(state="normal")
                    self.video_files = []
                    self.total_original_duration_sec = 0.0
                    self.update_speed_label(self.speed_multiplier.get())
                elif msg == "UI_UPDATE_SCAN_SUCCESS":
                    root_folder = data
                    default_out = os.path.join(root_folder, "timelapse_generado.mp4")
                    self.output_file.set(default_out)
                    
                    total_clips = len(self.video_files)
                    formatted_orig = format_time(self.total_original_duration_sec)
                    
                    self.summary_label.configure(
                        text=f"Total: {total_clips} videos. Duración Original Real: {formatted_orig}. Listo.",
                        text_color=ACCENT_COLOR
                    )
                    self.console_write(f"[Info] Procesamiento completado. Duración exacta: {formatted_orig}\n")
                    self.btn_generate.configure(state="normal")
                    self.btn_browse_dir.configure(state="normal")
                    self.update_speed_label(self.speed_multiplier.get())
                    
                elif msg == "PROCESS_UPDATE":
                    percentage, current_processed, expected_dur, eta_text = data
                    self.progress_bar.set(percentage)
                    self.progress_lbl.configure(text=f"{int(percentage*100)}%")
                    self.eta_label.configure(text=f"Tiempo estimado: {eta_text}")
                    if int(current_processed) % 30 == 0:
                        self.console_write(f"Procesando... {current_processed:.1f}s / {expected_dur:.1f}s | Progreso: {percentage*100:.1f}%\n")
                elif msg == "PROCESS_FINISHED":
                    self.finalize_process()
                else:
                    self.console_write(msg)
                    if isinstance(data, float):
                        self.progress_bar.set(data)
                        self.progress_lbl.configure(text=f"{int(data*100)}%")
                
                self.log_queue.task_done()
        except queue.Empty:
            pass
        self.after(100, self.process_queue)

    def play_notification_sound(self, success=True):
        """Reproduce un sonido de notificación premium usando winsound en Windows."""
        try:
            import winsound
            if success:
                # Éxito: Tres tonos ascendentes alegres y rápidos (Do - Mi - Sol)
                winsound.Beep(523, 100) # C5
                winsound.Beep(659, 100) # E5
                winsound.Beep(784, 250) # G5
            else:
                # Error: Dos tonos graves descendentes (Fa# - Do#)
                winsound.Beep(370, 180) # F#4
                winsound.Beep(277, 350) # C#4
        except Exception:
            pass

    def show_global_help(self):
        help_win = tk.Toplevel(self)
        help_win.title("Ayuda - Timelapse Creator")
        help_win.geometry("550x370")
        help_win.configure(bg=BG_CARD)
        help_win.resizable(False, False)
        help_win.transient(self)
        help_win.grab_set()
        
        content = ctk.CTkFrame(help_win, fg_color=BG_CARD, corner_radius=0)
        content.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        ctk.CTkLabel(content, text="¿Cómo funciona Timelapse Creator?", font=ctk.CTkFont(family="Google Sans", size=18, weight="bold"), text_color=ACCENT_COLOR).pack(anchor="w", pady=(0, 15))
        
        info_text = (
            "1. Directorio de Origen:\n"
            "   Seleccioná la carpeta raíz de tu memoria SD. El programa buscará "
            "automáticamente todos los clips de video en esa carpeta y sus subcarpetas.\n\n"
            "2. Orden Cronológico:\n"
            "   Los clips se ordenarán automáticamente por nombre/fecha para garantizar "
            "que el timelapse siga una línea de tiempo perfecta.\n\n"
            "3. Velocidad y FFmpeg:\n"
            "   El multiplicador acelera todos los videos sin perder calidad gracias a "
            "FFmpeg. Por ejemplo, 30x significa que 30 minutos de vida real "
            "pasarán en 1 minuto de video.\n\n"
            "Al hacer clic en 'Generar', el sistema unirá y acelerará todos los fragmentos "
            "creando un único video final súper fluido."
        )
        
        lbl = ctk.CTkLabel(content, text=info_text, font=ctk.CTkFont(family="Google Sans", size=13), text_color=FG_TEXT, justify=tk.LEFT, wraplength=480)
        lbl.pack(anchor="w", fill=tk.BOTH, expand=True)
        
        ctk.CTkButton(content, text="Entendido", fg_color=ACCENT_COLOR, hover_color="#1557B0", font=ctk.CTkFont(family="Google Sans", weight="bold"), command=help_win.destroy).pack(pady=(15, 0))

    def open_output_folder(self):
        import subprocess
        import os
        import sys
        file_path = self.output_file.get()
        if os.path.exists(file_path):
            if sys.platform == "win32":
                subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
            else:
                import platform
                if platform.system() == "Darwin":
                    subprocess.run(['open', '-R', file_path])
                else:
                    subprocess.run(['xdg-open', os.path.dirname(file_path)])

    def finalize_process(self):
        self.is_processing = False
        self.btn_generate.configure(state="normal")
        self.btn_cancel.configure(state="disabled")
        self.dir_entry.configure(state="normal")
        self.dest_entry.configure(state="normal")
        self.speed_slider.configure(state="normal")
        self.audio_check.configure(state="normal")
        
        if self.progress_bar.get() >= 0.99:
            self.eta_label.configure(text="Tiempo estimado: COMPLETADO", text_color="#1E8E3E")
            self.btn_open_file.configure(state="normal")
            self.play_notification_sound(success=True)
            messagebox.showinfo("Completado", f"Timelapse creado en:\n{self.output_file.get()}")
        else:
            if not self.was_cancelled:
                self.play_notification_sound(success=False)

    def cancel_timelapse(self):
        if self.process and self.is_processing:
            if messagebox.askyesno("Confirmar Cancelación", "¿Abortar creación de timelapse?"):
                self.console_write("\n[Acción] Cancelación iniciada...\n")
                self.was_cancelled = True
                self.process.terminate()
                self.is_processing = False
                self.eta_label.configure(text="Tiempo estimado: CANCELADO", text_color=DANGER_COLOR)

if __name__ == "__main__":
    app = TimelapseApp()
    app.mainloop()
