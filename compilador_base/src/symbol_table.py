class SymbolTable:
    def __init__(self):
        self._symbols = []
        self._by_name = {}

    def declare(self, name, type_name, line):
        if name in self._by_name:
            return False
        symbol = {
            "name": name,
            "type": type_name,
            "line": line,
            "order": len(self._symbols) + 1,
        }
        self._symbols.append(symbol)
        self._by_name[name] = symbol
        return True

    def lookup(self, name):
        return self._by_name.get(name)

    def all(self):
        return list(self._symbols)

    def print_table(self):
        print("\n=== TABELA DE SÍMBOLOS ===")
        if not self._symbols:
            print("(vazia)")
            return
        print(f"{'Ordem':<8}{'Identificador':<18}{'Tipo':<12}{'Linha':<8}")
        print("-" * 46)
        for s in self._symbols:
            print(f"{s['order']:<8}{s['name']:<18}{s['type']:<12}{s['line']:<8}")
