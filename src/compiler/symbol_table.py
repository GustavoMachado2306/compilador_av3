"""
Módulo da Tabela de Símbolos do Compilador Java (AV3).
Armazena palavras reservadas, tipos, classes, métodos, campos e variáveis,
com suporte a escopos hierárquicos e ordem determinística de inserção.
"""

from typing import Optional, List, Dict, Any, Sequence, Set


class SymbolTable:
    """
    Tabela de símbolos didática e com suporte a escopos aninhados.
    Armazena palavras reservadas, tipos nativos/referência e identificadores declarados
    (classes, interfaces, enums, records, métodos, campos, variáveis locais e parâmetros),
    preservando a ordem determinística de inserção sem duplicar palavras reservadas.
    """

    PRIMITIVE_TYPE_KEYWORDS = frozenset({
        "byte", "short", "char", "int", "long", "float", "double", "boolean", "void"
    })

    def __init__(self, init_builtins: bool = True):
        self._init_builtins_flag = init_builtins
        self._symbols: List[Dict[str, Any]] = []
        self._by_name: Dict[str, Dict[str, Any]] = {}
        self._reserved_keywords: Set[str] = set()
        self._known_types: Set[str] = set()
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
        if self.declare("int", "tipo", "-", category="palavra_reservada"):
            self._reserved_keywords.add("int")
            self._known_types.add("int")
        if self.declare("String", "tipo", "-", category="tipo"):
            self._known_types.add("String")

    def register_keyword(self, name: str, line: Any = "-") -> bool:
        """Registra uma palavra reservada reconhecida pelo Lexer uma única vez no escopo global."""
        if not name or name in self._reserved_keywords or name in self._scopes[0]:
            return False
        sym_type = "tipo" if name in self.PRIMITIVE_TYPE_KEYWORDS else "-"
        symbol = {
            "name": name,
            "category": "palavra_reservada",
            "type": sym_type,
            "line": line,
            "is_static": False,
            "order": len(self._symbols) + 1,
        }
        self._scopes[0][name] = symbol
        self._symbols.append(symbol)
        self._by_name[name] = symbol
        self._reserved_keywords.add(name)
        if sym_type == "tipo":
            self._known_types.add(name)
        return True

    def register_type(self, name: str, line: Any = "-", category: str = "tipo") -> bool:
        """Registra um tipo primitivo ou de referência conhecido uma única vez no escopo global."""
        if not name or name in self._known_types or name in self._reserved_keywords or name in self._scopes[0]:
            return False
        symbol = {
            "name": name,
            "category": category,
            "type": "tipo",
            "line": line,
            "is_static": False,
            "order": len(self._symbols) + 1,
        }
        self._scopes[0][name] = symbol
        self._symbols.append(symbol)
        self._by_name[name] = symbol
        self._known_types.add(name)
        return True

    def register_from_tokens(self, tokens: Sequence[Any]) -> None:
        """
        Registra palavras reservadas identificadas pelo Lexer em ordem de aparição,
        sem duplicar ocorrências repetidas.
        """
        for tok in tokens or ():
            tok_type = getattr(tok, "type", None)
            if tok_type is not None and getattr(tok_type, "name", "").startswith("KEYWORD_"):
                self.register_keyword(tok.lexeme, tok.line)

    def enter_scope(self):
        """Abre um novo nível de escopo (ex: entrar em uma classe, método ou bloco)."""
        self._scopes.append({})

    def exit_scope(self):
        """Fecha o escopo atual, retornando ao escopo pai."""
        if len(self._scopes) > 1:
            self._scopes.pop()

    def declare(self, name: str, type_name: str, line, category: str = "variavel", is_static: bool = False, **extra) -> bool:
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
            "is_static": is_static,
            "order": len(self._symbols) + 1,
            **extra,
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

    def get_symbol(self, name: str) -> Optional[Dict[str, Any]]:
        """Retorna o símbolo registrado na tabela pelo nome, mesmo após o fechamento de escopos."""
        return self._by_name.get(name)

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Retorna o símbolo registrado na tabela pelo nome."""
        return self._by_name.get(name)

    def all(self) -> List[Dict[str, Any]]:
        """Retorna todos os símbolos declarados em ordem de inserção."""
        return list(self._symbols)

    def clear(self):
        """Limpa a tabela de símbolos e recarrega os tipos padrão."""
        self._symbols.clear()
        self._by_name.clear()
        self._reserved_keywords.clear()
        self._known_types.clear()
        self._scopes = [{}]
        if self._init_builtins_flag:
            self._load_builtins()

    def print_table(self):
        """Exibe a tabela formatada no terminal."""
        print("\n=== TABELA DE SÍMBOLOS ===")
        if not self._symbols:
            print("(vazia)")
            return
        print(f"{'Ordem':<8}{'Identificador':<22}{'Categoria':<20}{'Tipo':<18}{'Linha':<8}")
        print("-" * 76)
        for s in self._symbols:
            print(f"{s['order']:<8}{s['name']:<22}{s['category']:<20}{s['type']:<18}{str(s['line']):<8}")
