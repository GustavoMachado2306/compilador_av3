"""
Ponto de entrada unificado do Compilador AV3.
Conecta o pacote do compilador (`src.compiler`) às interfaces (`src.interfaces`)
e preserva retrocompatibilidade para importações via `src.main`.
"""

from .compiler.pipeline import (
    AnalysisResult,
    analyze_source,
    analyze_sources,
    read_source_file,
)
from .interfaces.cli import (
    launch_gui_with_fallback,
    main,
    run_file,
    run_interactive_cli,
    run_source_cli,
    setup_console_encoding,
)

__all__ = [
    "AnalysisResult",
    "analyze_source",
    "analyze_sources",
    "read_source_file",
    "setup_console_encoding",
    "run_source_cli",
    "run_file",
    "run_interactive_cli",
    "launch_gui_with_fallback",
    "main",
]

if __name__ == "__main__":
    main()
