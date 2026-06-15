import tkinter as tk
import customtkinter as ctk
from utils.helpers import BORDER_COLOR, BG_CARD, ACCENT_COLOR, FG_MUTED

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
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        try:
            tw.wm_attributes("-topmost", True)
        except Exception:
            pass
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
                text="ⓘ",
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
