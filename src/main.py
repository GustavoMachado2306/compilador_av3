import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

from .token import Token
from .lexer import Lexer, LexicalError
from .parser import Parser, SyntacticError
from .symbol_table import SymbolTable
from .semantic import SemanticAnalyzer
from .ast_nodes import Program


@dataclass
class AnalysisResult:
    """Resultado estruturado e unificado da execução do pipeline do compilador."""
    source: str
    tokens: List[Token] = field(default_factory=list)
    ast: Optional[Program] = None
    symbol_table: Optional[SymbolTable] = None
    lexical_error: Optional[LexicalError] = None
    syntactic_error: Optional[SyntacticError] = None
    semantic_errors: List[str] = field(default_factory=list)
    success: bool = False

    @property
    def has_errors(self) -> bool:
        return bool(self.lexical_error or self.syntactic_error or self.semantic_errors)


def analyze_source(source: str) -> AnalysisResult:
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
        result.tokens = err.tokens or getattr(lexer, "tokens", [])
        return result

    # 2. Análise Sintática
    parser = Parser(result.tokens)
    try:
        result.ast = parser.parse()
    except SyntacticError as err:
        result.syntactic_error = err
        return result

    # 3. Tabela de Símbolos e Análise Semântica
    symbols = SymbolTable()
    analyzer = SemanticAnalyzer(symbols)
    errors = analyzer.analyze(result.ast)
    result.symbol_table = symbols
    result.semantic_errors = errors

    result.success = not result.has_errors
    return result


def setup_console_encoding():
    """Garante suporte a UTF-8 no stdout/stderr no Windows sem falhas de codificação."""
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


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


def run_file(path):
    """Executa o pipeline completo do compilador de forma controlada via CLI."""
    setup_console_encoding()
    source, error = read_source_file(path)
    if error:
        print(error)
        return 1

    print("=== CÓDIGO FONTE ===")
    if not source.strip():
        print("(arquivo vazio)")
    else:
        print(source)

    result = analyze_source(source)

    print("\n=== ANÁLISE LÉXICA ===")
    for token in result.tokens:
        print(token)
    if result.lexical_error:
        print(f"\n{result.lexical_error}")
        return 1

    print("\n=== ANÁLISE SINTÁTICA / AST ===")
    if result.syntactic_error:
        print(f"\n{result.syntactic_error}")
        return 1
    if result.ast:
        print(result.ast.pretty())

    print("\n=== TABELA DE SÍMBOLOS / ANÁLISE SEMÂNTICA ===")
    if result.symbol_table:
        result.symbol_table.print_table()

    if result.semantic_errors:
        print(f"\nERROS SEMÂNTICOS ({len(result.semantic_errors)}):")
        for err in result.semantic_errors:
            print(err)
        return 1
    else:
        print("\n[OK] Validação semântica concluída sem erros básicos.")
        return 0


def main():
    if len(sys.argv) != 2:
        print("[ERRO DE ENTRADA]\nUso incorreto: arquivo fonte não informado.")
        print("Uso: python -m src.main <arquivo.java>")
        sys.exit(1)

    try:
        exit_code = run_file(sys.argv[1])
        sys.exit(exit_code)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[ERRO INESPERADO]\n{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
