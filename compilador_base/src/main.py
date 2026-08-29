import sys
from pathlib import Path

from .lexer import Lexer
from .parser import Parser
from .symbol_table import SymbolTable
from .semantic import SemanticAnalyzer


def run_file(path):
    source = Path(path).read_text(encoding="utf-8")

    print("=== CÓDIGO FONTE ===")
    print(source)

    print("=== ANÁLISE LÉXICA ===")
    tokens = Lexer(source).tokenize()
    for token in tokens:
        print(token)

    print("\n=== ANÁLISE SINTÁTICA / AST ===")
    ast = Parser(tokens).parse()
    print(ast.pretty())

    print("\n=== TABELA DE SÍMBOLOS / ANÁLISE SEMÂNTICA ===")
    symbols = SymbolTable()
    errors = SemanticAnalyzer(symbols).analyze(ast)
    symbols.print_table()

    if errors:
        print("\nERROS SEMÂNTICOS:")
        for error in errors:
            print(error)
    else:
        print("\n[OK] Validação semântica concluída sem erros básicos.")


def main():
    if len(sys.argv) != 2:
        print("Uso: python -m src.main <arquivo.java>")
        raise SystemExit(1)
    run_file(sys.argv[1])


if __name__ == "__main__":
    main()
