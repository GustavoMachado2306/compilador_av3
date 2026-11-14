"""Pacote de interfaces com o usuário (Tkinter GUI, Web GUI local e CLI)."""

from .cli import (
    launch_gui_with_fallback,
    main,
    run_file,
    run_interactive_cli,
    run_source_cli,
    setup_console_encoding,
)
from .gui import CompiladorGUI, TKINTER_AVAILABLE
from .web_gui import build_analysis_payload, create_web_server, start_web_gui

__all__ = [
    "CompiladorGUI",
    "TKINTER_AVAILABLE",
    "build_analysis_payload",
    "create_web_server",
    "start_web_gui",
    "setup_console_encoding",
    "run_source_cli",
    "run_file",
    "run_interactive_cli",
    "launch_gui_with_fallback",
    "main",
]

