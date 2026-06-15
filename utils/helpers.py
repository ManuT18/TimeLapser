# -*- coding: utf-8 -*-
import os
import sys

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

def load_custom_fonts():
    """Carga dinámica de fuentes Google Sans en Windows"""
    import ctypes
    
    if hasattr(sys, '_MEIPASS'):
        font_dir = sys._MEIPASS
    else:
        # Volvemos 2 niveles arriba (de utils/helpers.py al root)
        font_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    font_files = ["GoogleSans-Regular.ttf", "GoogleSans-Bold.ttf", "GoogleSans-Medium.ttf"]
    for font_file in font_files:
        font_path = os.path.join(font_dir, font_file)
        if os.path.exists(font_path):
            try:
                ctypes.windll.gdi32.AddFontResourceW(font_path)
            except Exception:
                pass

def format_time(seconds):
    """Formatea segundos en HH:MM:SS."""
    if seconds < 0: return "00:00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
