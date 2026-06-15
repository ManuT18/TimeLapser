# -*- coding: utf-8 -*-
from utils.helpers import load_custom_fonts
from ui.main_window import TimelapseApp
import customtkinter as ctk

def main():
    try:
        load_custom_fonts()
    except Exception:
        pass

    # Configuración base de CustomTkinter
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    app = TimelapseApp()
    app.mainloop()

if __name__ == "__main__":
    main()
