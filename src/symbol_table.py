"""
Módulo da Tabela de Símbolos do Compilador Java (AV3).
Armazena palavras reservadas, tipos, classes, métodos, campos e variáveis,
com suporte a escopos hierárquicos e ordem determinística de inserção.
"""

from typing import Optional, List, Dict, Any


class SymbolTable:
    """
    Tabela de símbolos didática e com suporte a escopos aninhados.
    Armazena palavras reservadas, tipos nativos e identificadores declarados
    (classes, interfaces, enums, métodos, campos, variáveis locais e parâmetros).
    """

    def __init__(self, init_builtins: bool = True):
        self._init_builtins_flag = init_builtins
        self._symbols: List[Dict[str, Any]] = []
        self._by_name: Dict[str, Dict[str, Any]] = {}
        # Pilha de escopos para resolução local vs global
        self._scopes: List[Dict[str, Dict[str, Any]]] = [{}]

        if init_builtins:
            self._load_builtins()

    def _load_builtins(self):
        """
        Pré-registra tipos nativos e palavras-chave.
        'int' é palavra-chave reservada da linguagem.
        'String' é um nome de tipo (classe padrão de Java), classificado como 'tipo'.
        """
        self.declare("int", "tipo", "-", category="palavra_reservada")
        self.declare("String", "tipo", "-", category="tipo")

    def enter_scope(self):
        """Abre um novo nível de escopo (ex: entrar em uma classe, método ou bloco)."""
        self._scopes.append({})

    def exit_scope(self):
        """Fecha o escopo atual, retornando ao escopo pai."""
        if len(self._scopes) > 1:
            self._scopes.pop()

    def declare(self, name: str, type_name: str, line, category: str = "variavel") -> bool:
        """
        Declara um novo símbolo no escopo corrente.
        Retorna False se o símbolo já tiver sido declarado no mesmo escopo.
        """
        if not name:
            return False

        current_scope = self._scopes[-1]
        if name in current_scope:
            return False

        symbol = {
            "name": name,
            "category": category,
            "type": type_name,
            "line": line,
            "order": len(self._symbols) + 1,
        }
        current_scope[name] = symbol
        self._symbols.append(symbol)
        self._by_name[name] = symbol
        return True

    def lookup(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Busca um símbolo do escopo mais interno para o mais externo.
        Retorna apenas símbolos acessíveis nos escopos atualmente ativos.
        """
        if not name:
            return None
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def exists(self, name: str) -> bool:
        """Verifica se o identificador existe em qualquer escopo visível ou já registrado na tabela."""
        return (self.lookup(name) is not None) or (name in self._by_name)

    def all(self) -> List[Dict[str, Any]]:
        """Retorna todos os símbolos declarados em ordem de inserção."""
        return list(self._symbols)

    def clear(self):
        """Limpa a tabela de símbolos e recarrega os tipos padrão."""
        self._symbols.clear()
        self._by_name.clear()
        self._scopes = [{}]
        if self._init_builtins_flag:
            self._load_builtins()

    def print_table(self):
        """Exibe a tabela formatada no terminal."""
        print("\n=== TABELA DE SÍMBOLOS ===")
        if not self._symbols:
            print("(vazia)")
            return
        print(f"{'Ordem':<8}{'Identificador':<18}{'Categoria':<20}{'Tipo':<10}{'Linha':<8}")
        print("-" * 64)
        for s in self._symbols:
            print(f"{s['order']:<8}{s['name']:<18}{s['category']:<20}{s['type']:<10}{str(s['line']):<8}")
