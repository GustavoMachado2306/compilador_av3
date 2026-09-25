class SymbolTable:
    """Tabela de símbolos didática que armazena palavras reservadas, identificadores/variáveis,
    seus tipos, categorias e linhas correspondentes, com ordem determinística de inserção."""

    def __init__(self, init_builtins: bool = True):
        self._init_builtins_flag = init_builtins
        self._symbols = []
        self._by_name = {}
        if init_builtins:
            self._load_builtins()

    def _load_builtins(self):
        # Palavras reservadas e tipos nativos pré-registrados conforme o Barema da AV3
        self.declare("int", "tipo", "-", category="palavra_reservada")
        self.declare("String", "tipo", "-", category="palavra_reservada")

    def declare(self, name: str, type_name: str, line, category: str = "variavel"):
        if not name or name in self._by_name:
            return False
        symbol = {
            "name": name,
            "category": category,
            "type": type_name,
            "line": line,
            "order": len(self._symbols) + 1,
        }
        self._symbols.append(symbol)
        self._by_name[name] = symbol
        return True

    def lookup(self, name: str):
        if not name:
            return None
        return self._by_name.get(name)

    def exists(self, name: str):
        return bool(name and name in self._by_name)

    def all(self):
        return list(self._symbols)

    def clear(self):
        self._symbols.clear()
        self._by_name.clear()
        if self._init_builtins_flag:
            self._load_builtins()

    def print_table(self):
        print("\n=== TABELA DE SÍMBOLOS ===")
        if not self._symbols:
            print("(vazia)")
            return
        print(f"{'Ordem':<8}{'Identificador':<18}{'Categoria':<20}{'Tipo':<10}{'Linha':<8}")
        print("-" * 64)
        for s in self._symbols:
            print(f"{s['order']:<8}{s['name']:<18}{s['category']:<20}{s['type']:<10}{str(s['line']):<8}")
