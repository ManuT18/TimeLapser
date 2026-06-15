# Contexto del Proyecto

## Estado General
TIMELAPSER es una aplicación de escritorio multiplataforma (en Python) que automatiza y acelera el proceso de creación de timelapses a partir de clips de video concatenados. Utiliza `ffmpeg` y `ffprobe` en segundo plano para realizar el análisis de duración y la renderización en paralelo de múltiples configuraciones de timelapse (velocidad, duración objetivo, audio y aceleración por hardware GPU). Cuenta con una interfaz gráfica moderna de escritorio basada en `CustomTkinter`.

## Arquitectura y Decisiones
- **Lenguaje**: Python 3.
- **Interfaz Gráfica**: `customtkinter` (modo claro forzado por defecto, tema azul) y fuentes personalizadas de Google Sans.
- **Procesamiento de Video**:
  - `ffmpeg` (con soporte para concat demuxer, aceleración por hardware NVENC con `h264_nvenc` para NVIDIA GPUs, y codificación estándar en CPU con `libx264`).
  - `ffprobe` escaneando clips de video en paralelo mediante `ThreadPoolExecutor` para estimar la duración total original de forma precisa.
- **Estructura de Carpetas**:
  - `creador_de_timelapses.py`: Script principal de entrada.
  - `core/`: Contiene `processor.py` que coordina las llamadas asíncronas de subprocess a FFmpeg y el escaneo multihilo de videos.
  - `ui/`: Módulos de la interfaz gráfica y ventanas (`main_window.py`).
  - `utils/`: Métodos auxiliares y de carga de recursos (`helpers.py`).

## Tareas Completadas (Recientes)
- [x] Arquitectura de procesamiento multihilo con soporte para cancelación y tracking de progreso en tiempo real de múltiples colas ffmpeg concurrentes.
- [x] Detección inteligente de duraciones con FFprobe multihilo (ThreadPoolExecutor con hasta 8 workers).
- [x] Interfaz gráfica adaptada con CustomTkinter y soporte de fuentes externas Google Sans.
- [x] Filtros de audio `atempo` en bucle para permitir aceleración del sonido sin colapsar el pitch si el timelapse no está silenciado.
- [x] Configuración del empaquetado para standalone EXE de Windows mediante PyInstaller (`creador_de_timelapses.spec`).

## Próximos Pasos (TODO)
- [ ] Implementar un selector visual para buscar y elegir la ruta del binario `ffmpeg` si no está en el PATH global del sistema.
- [ ] Soportar perfiles de renderizado personalizados adicionales (ej. formato 9:16 vertical para redes sociales o resolución 4K).
- [ ] Optimizar la actualización de la barra de progreso de la UI para evitar parpadeos cuando se procesan muchas tareas en paralelo.

## Problemas Abiertos o Notas
- Las plataformas que no sean Windows pueden requerir configuraciones de flags diferentes en `subprocess.Popen` para evitar consolas fantasmas.
