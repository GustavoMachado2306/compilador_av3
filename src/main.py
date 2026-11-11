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
    lexical_errors: List[LexicalError] = field(default_factory=list)
    syntactic_error: Optional[SyntacticError] = None
    semantic_errors: List[str] = field(default_factory=list)
    unresolved_checks: List[str] = field(default_factory=list)
    success: bool = False

    @property
    def has_errors(self) -> bool:
        return bool(self.lexical_error or self.lexical_errors or self.syntactic_error or self.semantic_errors)


def analyze_source(source: str, enable_preview_primitive_patterns: bool = False) -> AnalysisResult:
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
    analyzer = SemanticAnalyzer(symbols, enable_preview_primitive_patterns=enable_preview_primitive_patterns)
    errors = analyzer.analyze(result.ast)
    result.symbol_table = symbols
    result.semantic_errors = errors
    result.unresolved_checks = list(getattr(analyzer, "unresolved_checks", []))

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


def run_source_cli(source: str) -> int:
    """Imprime no terminal Código Fonte, Tokens, Tabela de Símbolos, AST, Semântica e Erros."""
    setup_console_encoding()
    print("=== CÓDIGO FONTE ===")
    if not source or not source.strip():
        print("(arquivo vazio)")
    else:
        print(source)

    result = analyze_source(source)

    print("\n=== ANÁLISE LÉXICA ===")
    for token in result.tokens:
        print(token)
    if result.lexical_errors:
        for err in result.lexical_errors:
            print(f"\n{err}")
        return 1
    elif result.lexical_error:
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


def run_file(path):
    """Executa o pipeline completo do compilador de forma controlada via CLI."""
    setup_console_encoding()
    source, error = read_source_file(path)
    if error:
        print(error)
        return 1
    return run_source_cli(source)


def launch_gui_with_fallback():
    """
    Tenta abrir a interface gráfica Tkinter. Se falhar ao importar ou inicializar
    a janela, inicia automaticamente a Interface Web Local no navegador.
    """
    setup_console_encoding()
    try:
        from .gui import CompiladorGUI, TKINTER_AVAILABLE
        if not TKINTER_AVAILABLE:
            raise ImportError("Pacote 'tkinter' não instalado neste ambiente.")
        app = CompiladorGUI()
        app.mainloop()
        return 0
    except (ImportError, Exception) as exc:
        print(f"[AVISO] Não foi possível abrir a interface Tkinter ({exc}).")
        print("[FALLBACK] Iniciando automaticamente a Interface Web Local no navegador...")
        from .web_gui import start_web_gui
        start_web_gui()
        return 0


def run_interactive_cli():
    """Modo CLI interativo para terminais puros / SSH sem navegador gráfico."""
    setup_console_encoding()
    examples_dir = Path(__file__).resolve().parent.parent / "examples"
    example_files = sorted(examples_dir.glob("*.java")) if examples_dir.exists() else []

    print("================================================================")
    print(" COMPILADOR AV3 — MODO TERMINAL (CLI)")
    print("================================================================")
    if example_files:
        print("Arquivos disponíveis em examples/:")
        for idx, ef in enumerate(example_files, start=1):
            print(f"  [{idx}] {ef.name}")
    print("Digite o número de um exemplo, o caminho de um arquivo .java,")
    print("ou uma linha de código Java direta para analisar:")

    try:
        choice = input("> ").strip()
    except EOFError:
        choice = "1" if example_files else "int x = 10;"

    if not choice:
        return run_source_cli("")

    if choice.isdigit() and example_files:
        idx = int(choice) - 1
        if 0 <= idx < len(example_files):
            return run_file(str(example_files[idx]))

    candidate_path = Path(choice)
    if candidate_path.exists() and candidate_path.is_file():
        return run_file(str(candidate_path))

    if choice.endswith((".java", ".c", ".txt")) and not ("=" in choice or ";" in choice):
        return run_file(choice)

    return run_source_cli(choice)


def main(argv=None):
    setup_console_encoding()
    args = list(sys.argv[1:] if argv is None else argv)

    # 1. Sem argumentos: tenta Tkinter e faz fallback automático para Web GUI
    if not args:
        sys.exit(launch_gui_with_fallback())

    # 2. Flag --web: abre diretamente a Interface Web Local no navegador
    if args[0] == "--web":
        from .web_gui import start_web_gui
        start_web_gui()
        sys.exit(0)

    # 3. Flag --cli: executa no terminal (com arquivo opcional ou interativo)
    if args[0] == "--cli":
        if len(args) >= 2:
            sys.exit(run_file(args[1]))
        sys.exit(run_interactive_cli())

    # 4. Caminho de arquivo direto: python -m src.main caminho/arquivo.java
    if len(args) == 1:
        try:
            exit_code = run_file(args[0])
            sys.exit(exit_code)
        except SystemExit:
            raise
        except Exception as exc:
            print(f"[ERRO INESPERADO]\n{exc}")
            sys.exit(1)

    print("[ERRO DE ENTRADA]\nUso incorreto dos argumentos.")
    print("Uso:")
    print("  python -m src.main                  (Interface Tkinter com fallback automático para Web)")
    print("  python -m src.main --web            (Interface Web Local no navegador)")
    print("  python -m src.main --cli [arquivo]  (Modo Terminal / CLI)")
    print("  python -m src.main <arquivo.java>   (Análise direta de arquivo no terminal)")
    sys.exit(1)


if __name__ == "__main__":
    main()
