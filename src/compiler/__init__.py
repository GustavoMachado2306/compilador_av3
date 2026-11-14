"""Pacote principal do núcleo do compilador (léxico, sintático, AST, tabela de símbolos e semântica)."""

from .ast_nodes import Program
from .lexer import Lexer, LexicalError
from .parser import Parser, SyntacticError
from .pipeline import AnalysisResult, analyze_source, analyze_sources, read_source_file
from .semantic import SemanticAnalyzer, SemanticError
from .symbol_table import SymbolTable
from .token import Token, TokenType

__all__ = [
    "Token",
    "TokenType",
    "Lexer",
    "LexicalError",
    "Parser",
    "SyntacticError",
    "Program",
    "SymbolTable",
    "SemanticAnalyzer",
    "SemanticError",
    "AnalysisResult",
    "analyze_source",
    "analyze_sources",
    "read_source_file",
]

