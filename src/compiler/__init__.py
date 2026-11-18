"""Pacote principal do núcleo do compilador (léxico, sintático, AST, tabela de símbolos e semântica)."""

from .ast_nodes import Program
from .lexer import (
    CONTEXTUAL_KEYWORD_CLASSIFICATIONS,
    KEYWORD_CLASSIFICATIONS,
    SPECIAL_LITERAL_CLASSIFICATIONS,
    WORD_CLASSIFICATIONS,
    Lexer,
    LexicalError,
    classify_keyword,
)
from .parser import Parser, SyntacticError
from .pipeline import AnalysisResult, analyze_source, read_source_file
from .semantic import SemanticAnalyzer, SemanticError
from .symbol_table import SymbolTable
from .token import Token, TokenType

__all__ = [
    "Token",
    "TokenType",
    "Lexer",
    "LexicalError",
    "classify_keyword",
    "KEYWORD_CLASSIFICATIONS",
    "SPECIAL_LITERAL_CLASSIFICATIONS",
    "CONTEXTUAL_KEYWORD_CLASSIFICATIONS",
    "WORD_CLASSIFICATIONS",
    "Parser",
    "SyntacticError",
    "Program",
    "SymbolTable",
    "SemanticAnalyzer",
    "SemanticError",
    "AnalysisResult",
    "analyze_source",
    "read_source_file",
]

