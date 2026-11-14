"""
Pipeline principal do compilador (análise léxica, sintática, tabela de símbolos e semântica).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .ast_nodes import Program
from .lexer import Lexer, LexicalError
from .parser import Parser, SyntacticError
from .semantic import SemanticAnalyzer
from .symbol_table import SymbolTable
from .token import Token


@dataclass
class AnalysisResult:
    """Resultado estruturado e unificado da execução do pipeline do compilador."""
    source: str
    tokens: List[Token] = field(default_factory=list)
    ast: Optional[Program] = None
    symbol_table: Optional[SymbolTable] = None
    lexical_error: Optional[LexicalError] = None
    lexical_errors: List[LexicalError] = field(default_factory=list)
    syntactic_error: Optional[SyntacticError] = None
    semantic_errors: List[str] = field(default_factory=list)
    success: bool = False

    @property
    def has_errors(self) -> bool:
        return bool(self.lexical_error or self.lexical_errors or self.syntactic_error or self.semantic_errors)


def analyze_source(
    source: str,
    enable_preview_primitive_patterns: bool = False,
) -> AnalysisResult:
    """Executa o pipeline completo do compilador sobre uma string e retorna um AnalysisResult."""
    if source is None:
        source = ""
    result = AnalysisResult(source=source)

    # 1. Análise Léxica
    lexer = Lexer(source)
    try:
        result.tokens = lexer.tokenize()
    except LexicalError as err:
        result.lexical_error = err
        result.lexical_errors = [err]
        result.tokens = err.tokens or getattr(lexer, "tokens", [])
        return result

    if lexer.errors:
        result.lexical_error = lexer.errors[0]
        result.lexical_errors = list(lexer.errors)
        return result

    # 2. Análise Sintática
    parser = Parser(result.tokens, enable_preview_primitive_patterns=enable_preview_primitive_patterns)
    try:
        result.ast = parser.parse()
    except SyntacticError as err:
        result.syntactic_error = err
        return result

    # 3. Tabela de Símbolos e Análise Semântica
    symbols = SymbolTable()
    symbols.register_from_tokens(result.tokens)
    analyzer = SemanticAnalyzer(
        symbols,
        enable_preview_primitive_patterns=enable_preview_primitive_patterns,
    )
    errors = analyzer.analyze(result.ast)
    result.symbol_table = symbols
    result.semantic_errors = errors

    result.success = not result.has_errors
    return result


def read_source_file(path_str):
    """Lê o arquivo fonte de forma segura, tratando erros de entrada."""
    if path_str is None or not str(path_str).strip():
        return None, "[ERRO DE ENTRADA]\nCaminho do arquivo não pode ser vazio."
    try:
        path = Path(path_str)
        if not path.exists():
            return None, f"[ERRO DE ENTRADA]\nArquivo não encontrado: '{path_str}'."
        if path.is_dir():
            return None, f"[ERRO DE ENTRADA]\nO caminho informado é um diretório, não um arquivo: '{path_str}'."

        try:
            content = path.read_text(encoding="utf-8-sig")
            return content, None
        except UnicodeDecodeError:
            return None, f"[ERRO DE ENTRADA]\nFalha de codificação: o arquivo '{path_str}' não está em formato UTF-8 válido."
        except PermissionError:
            return None, f"[ERRO DE ENTRADA]\nPermissão negada ao tentar ler o arquivo: '{path_str}'."
        except OSError as e:
            return None, f"[ERRO DE ENTRADA]\nErro ao acessar o arquivo '{path_str}': {e}."
    except PermissionError:
        return None, f"[ERRO DE ENTRADA]\nPermissão negada para acessar o caminho: '{path_str}'."
    except OSError as e:
        return None, f"[ERRO DE ENTRADA]\nCaminho inválido ou erro de sistema: '{path_str}' ({e})."

