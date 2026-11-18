"""
Módulo da Tabela de Símbolos do Compilador Java (AV3).
Armazena palavras reservadas, tipos, classes, métodos, campos e variáveis,
com suporte a escopos hierárquicos e ordem determinística de inserção.
"""

from dataclasses import fields as dataclass_fields, is_dataclass
from typing import Optional, List, Dict, Any, Sequence, Set

from .lexer import SPECIAL_LITERAL_CLASSIFICATIONS, classify_keyword


class SymbolTable:
    """
    Tabela de símbolos didática e com suporte a escopos aninhados.
    Armazena palavras reservadas, literais reservados, tipos nativos/referência e
    identificadores declarados (classes, interfaces, enums, records, métodos, campos,
    variáveis locais e parâmetros), preservando a ordem determinística de inserção
    sem duplicar palavras reservadas.
    """

    PRIMITIVE_TYPE_KEYWORDS = frozenset({
        "byte", "short", "char", "int", "long", "float", "double", "boolean", "void"
    })
    TYPE_CLASSIFICATIONS = frozenset({"tipo", "tipo_primitivo", "tipo_vazio"})

    def __init__(self, init_builtins: bool = True):
        self._init_builtins_flag = init_builtins
        self._symbols: List[Dict[str, Any]] = []
        self._by_name: Dict[str, Dict[str, Any]] = {}
        self._reserved_keywords: Set[str] = set()
        self._reserved_literals: Set[str] = set()
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
        if self.declare("int", classify_keyword("int"), "-", category="palavra_reservada"):
            self._reserved_keywords.add("int")
            self._known_types.add("int")
        if self.declare("String", "tipo", "-", category="tipo"):
            self._known_types.add("String")

    def register_keyword(self, name: str, line: Any = "-", contextual: bool = False) -> bool:
        """Registra uma palavra reservada (ou contextual em uso sintático) sem duplicar no escopo global."""
        if not name or name in self._reserved_keywords or name in self._scopes[0]:
            return False
        sym_type = classify_keyword(name, include_contextual=True if contextual else True)
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
        if sym_type in self.TYPE_CLASSIFICATIONS:
            self._known_types.add(name)
        return True

    def register_literal(self, name: str, line: Any = "-") -> bool:
        """Registra literais reservados ('true', 'false', 'null') preservando sua natureza de literal."""
        if not name or name in self._reserved_literals:
            return False
        sym_type = SPECIAL_LITERAL_CLASSIFICATIONS.get(name, "literal")
        symbol = {
            "name": name,
            "category": "literal_reservado",
            "type": sym_type,
            "line": line,
            "is_static": False,
            "order": len(self._symbols) + 1,
        }
        self._symbols.append(symbol)
        if name not in self._by_name:
            self._by_name[name] = symbol
        self._reserved_literals.add(name)
        return True

    def register_type(self, name: str, line: Any = "-", category: str = "tipo") -> bool:
        """Registra um tipo primitivo ou de referência conhecido uma única vez no escopo global."""
        if not name or name in self._known_types or name in self._reserved_keywords or name in self._scopes[0]:
            return False
        sym_type = classify_keyword(name, include_contextual=True) if category == "palavra_reservada" else "tipo"
        symbol = {
            "name": name,
            "category": category,
            "type": sym_type,
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
        Registra palavras reservadas e literais reservados identificados pelo Lexer
        em ordem de aparição, sem duplicar ocorrências repetidas.
        """
        for tok in tokens or ():
            tok_type = getattr(tok, "type", None)
            type_name = getattr(tok_type, "name", "") if tok_type is not None else ""
            if type_name.startswith("KEYWORD_"):
                self.register_keyword(tok.lexeme, tok.line)
            elif type_name in ("BOOLEAN_LITERAL", "NULL_LITERAL"):
                self.register_literal(tok.lexeme, tok.line)

    def register_from_ast(self, root: Any) -> None:
        """
        Registra palavras-chave contextuais (Java SE 26) somente quando aparecem na AST
        em seu papel sintático próprio, evitando classificar identificadores comuns.
        """
        if root is None:
            return

        visited: Set[int] = set()
        stack: List[Any] = [root]

        while stack:
            node = stack.pop()
            if node is None:
                continue
            if isinstance(node, (list, tuple)):
                for item in reversed(node):
                    stack.append(item)
                continue
            if not is_dataclass(node):
                continue

            obj_id = id(node)
            if obj_id in visited:
                continue
            visited.add(obj_id)

            cls_name = type(node).__name__
            line = getattr(node, "line", "-")

            if cls_name == "RecordDeclaration":
                self.register_keyword("record", line, contextual=True)
            elif cls_name == "YieldStatement":
                self.register_keyword("yield", line, contextual=True)
            elif cls_name == "Guard":
                self.register_keyword("when", line, contextual=True)
            elif getattr(node, "is_module", False) and hasattr(node, "is_wildcard"):
                self.register_keyword("module", line, contextual=True)
            elif cls_name == "ModuleDeclaration":
                if getattr(node, "is_open", False):
                    self.register_keyword("open", line, contextual=True)
                self.register_keyword("module", line, contextual=True)
            elif cls_name == "RequiresDirective":
                self.register_keyword("requires", line, contextual=True)
                if getattr(node, "is_transitive", False):
                    self.register_keyword("transitive", line, contextual=True)
            elif cls_name == "ExportsDirective":
                self.register_keyword("exports", line, contextual=True)
                if getattr(node, "to_modules", None):
                    self.register_keyword("to", line, contextual=True)
            elif cls_name == "OpensDirective":
                self.register_keyword("opens", line, contextual=True)
                if getattr(node, "to_modules", None):
                    self.register_keyword("to", line, contextual=True)
            elif cls_name == "UsesDirective":
                self.register_keyword("uses", line, contextual=True)
            elif cls_name == "ProvidesDirective":
                self.register_keyword("provides", line, contextual=True)
                if getattr(node, "with_types", None):
                    self.register_keyword("with", line, contextual=True)

            modifiers = getattr(node, "modifiers", None)
            if isinstance(modifiers, (list, tuple)):
                for mod in modifiers:
                    if mod in ("sealed", "non-sealed"):
                        self.register_keyword(mod, line, contextual=True)

            if getattr(node, "permits_types", None):
                self.register_keyword("permits", line, contextual=True)

            if getattr(node, "is_var", False):
                self.register_keyword("var", line, contextual=True)

            for f in reversed(dataclass_fields(node)):
                val = getattr(node, f.name, None)
                if val is not None and (is_dataclass(val) or isinstance(val, (list, tuple))):
                    stack.append(val)

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
        self._reserved_literals.clear()
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
        print(f"{'Ordem':<8}{'Identificador':<22}{'Categoria':<20}{'Tipo':<22}{'Linha':<8}")
        print("-" * 80)
        for s in self._symbols:
            print(f"{s['order']:<8}{s['name']:<22}{s['category']:<20}{s['type']:<22}{str(s['line']):<8}")
