"""
Módulo do Analisador Semântico do Compilador Java (AV3).
Implementa uma camada semântica enxuta, clara e previsível sobre a AST:
- Tabela de símbolos e escopos aninhados (blocos, métodos, construtores, laços, catch, lambdas).
- Detecção de identificadores não declarados e declarações duplicadas no mesmo escopo.
- Tipagem básica (primitivos, void, String, null e tipos declarados localmente), widening numérico,
  concatenação de String, expressões e atribuições simples/compostas.
- Validação de estruturas de controle (condições booleanas, return, break/continue) e chamadas locais.
- Tolerância para referências externas (ex: System.out.println) e construções modernas (generics,
  records, patterns, lambdas, switch expressions, try-with-resources) sem falsos positivos.
"""

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .ast_nodes import (
    ASTNode,
    Annotation,
    AnnotationInterfaceDeclaration,
    ArrayAccess,
    ArrayCreationExpression,
    ArrayInitializer,
    AssertStatement,
    Assignment,
    BinaryOp,
    Block,
    BreakStatement,
    CastExpression,
    CatchClause,
    ClassDeclaration,
    ClassLiteral,
    CompilationUnit,
    ConditionalExpression,
    ConstructorBody,
    ConstructorDeclaration,
    ContinueStatement,
    Declaration,
    DoWhileStatement,
    EmptyStatement,
    EnhancedForStatement,
    EnumConstant,
    EnumDeclaration,
    ExpressionStatement,
    FieldDeclaration,
    ForStatement,
    Identifier,
    IfStatement,
    InstanceInitializer,
    InstanceOfExpression,
    InterfaceConstantDeclaration,
    InterfaceDeclaration,
    InterfaceMethodDeclaration,
    LabeledStatement,
    LambdaExpression,
    Literal,
    LocalVariableDeclaration,
    MemberAccess,
    MethodCall,
    MethodDeclaration,
    MethodReference,
    ModuleDeclaration,
    ObjectCreationExpression,
    PatternInstanceOfExpression,
    PatternVariable,
    Program,
    RecordDeclaration,
    RecordPattern,
    ReturnStatement,
    StatementExpressionList,
    StaticInitializer,
    SuperclassConstructorInvocation,
    AlternateConstructorInvocation,
    SwitchCase,
    SwitchExpression,
    SwitchRule,
    SwitchStatement,
    SynchronizedStatement,
    ThrowStatement,
    TryStatement,
    TypePattern,
    TypeReference,
    UnaryOp,
    WhileStatement,
    YieldStatement,
)


UNKNOWN_TYPE = "desconhecido"


class SemanticError(str):
    """Exceção/mensagem estruturada de erro semântico compatível com string."""

    def __new__(cls, message: str, line: int):
        formatted = f"[ERRO SEMÂNTICO]\nLinha {line}:\n{message}"
        instance = super().__new__(cls, formatted)
        instance.message = message
        instance.line = line
        return instance


class SemanticAnalyzer:
    """
    Analisador semântico acadêmico simplificado.
    Mantém o contrato público com `main.py`, `gui.py` e `web_gui.py`,
    verificando escopos, declarações, tipos básicos, controle de fluxo e chamadas locais.
    """

    PRIMITIVE_TYPES = frozenset({"byte", "short", "char", "int", "long", "float", "double", "boolean"})
    INTEGRAL_TYPES = frozenset({"byte", "short", "char", "int", "long"})
    NUMERIC_TYPES = frozenset({"byte", "short", "char", "int", "long", "float", "double"})
    WIDENING_PRIMITIVE_TARGETS: Dict[str, Set[str]] = {
        "byte": {"short", "int", "long", "float", "double"},
        "short": {"int", "long", "float", "double"},
        "char": {"int", "long", "float", "double"},
        "int": {"long", "float", "double"},
        "long": {"float", "double"},
        "float": {"double"},
    }
    NUMERIC_PROMOTION_ORDER = ("double", "float", "long", "int")
    PRIMITIVE_TO_WRAPPER = {
        "byte": "Byte",
        "short": "Short",
        "char": "Character",
        "int": "Integer",
        "long": "Long",
        "float": "Float",
        "double": "Double",
        "boolean": "Boolean",
    }
    WRAPPER_TO_PRIMITIVE = {v: k for k, v in PRIMITIVE_TO_WRAPPER.items()}
    COMMON_EXTERNAL_TYPES = frozenset({
        "Object", "String", "StringBuilder", "StringBuffer", "CharSequence",
        "System", "Math", "Integer", "Long", "Double", "Float", "Boolean",
        "Character", "Byte", "Short", "Number", "Void", "Class", "Enum", "Record",
        "Throwable", "Exception", "RuntimeException", "Error", "Thread", "Runnable",
        "List", "ArrayList", "LinkedList", "Set", "HashSet", "Map", "HashMap",
        "Collection", "Iterable", "Iterator", "Optional", "Arrays", "Collections",
        "Objects", "Scanner", "AutoCloseable", "Comparable", "Serializable",
    })
    STRING_METHODS: Dict[str, str] = {
        "length": "int",
        "isEmpty": "boolean",
        "isBlank": "boolean",
        "equals": "boolean",
        "equalsIgnoreCase": "boolean",
        "contains": "boolean",
        "startsWith": "boolean",
        "endsWith": "boolean",
        "charAt": "char",
        "substring": "String",
        "toLowerCase": "String",
        "toUpperCase": "String",
        "trim": "String",
        "strip": "String",
        "replace": "String",
        "concat": "String",
        "indexOf": "int",
        "compareTo": "int",
        "toString": "String",
    }

    def __init__(
        self,
        symbol_table,
        enable_preview_primitive_patterns: bool = False,
        classpath: Optional[Sequence[str]] = None,
        include_stdlib: bool = True,
        max_class_major: Optional[int] = None,
    ):
        self.symbols = symbol_table
        self.symbol_table = symbol_table
        # Parâmetros legados aceitos como no-op para manter compatibilidade com main.py e testes
        self.enable_preview_primitive_patterns = enable_preview_primitive_patterns
        self._classpath = list(classpath) if classpath is not None else []
        self._include_stdlib = include_stdlib
        self._max_class_major = max_class_major

        self.errors: List[SemanticError] = []
        self.unresolved_checks: List[str] = []
        self._reset_state()

    def _reset_state(self) -> None:
        self.errors = []
        self.unresolved_checks = []
        self._local_scopes: List[Dict[str, str]] = [{}]
        self._declared_types: Dict[str, Dict[str, Any]] = {}
        self._imported_names: Set[str] = set()
        self._has_static_wildcard: bool = False
        self._package_prefixes: Set[str] = {"java", "javax", "sun", "org", "com"}
        self._current_type_stack: List[str] = []
        self._current_return_type: Optional[str] = None
        self._type_param_stack: List[Set[str]] = []
        self._loop_depth: int = 0
        self._switch_depth: int = 0
        self._active_labels: Set[str] = set()
        self._inferred_types: Dict[int, str] = {}

    def get_classpath_coverage(self) -> Dict[str, Any]:
        """Retorna metadados compatíveis indicando o modo simplificado sem classpath binário."""
        return {
            "mode": "core",
            "stdlib_loaded": False,
            "classpath_entries": [],
            "resolved_external_types": 0,
        }

    # ------------------------------------------------------------------
    # Pontos de entrada públicos
    # ------------------------------------------------------------------

    def analyze(self, program: Optional[ASTNode]) -> List[SemanticError]:
        """Executa a análise semântica sobre um Program / CompilationUnit."""
        self._reset_state()
        if not program:
            return self.errors

        if isinstance(program, CompilationUnit):
            self._preindex_unit(program)
            self._analyze_compilation_unit(program)
        else:
            for stmt in getattr(program, "statements", []) or []:
                self.analyze_statement(stmt)

        return self.errors

    def analyze_units(self, units: Sequence[ASTNode]) -> List[SemanticError]:
        """Executa a análise semântica conjunta sobre múltiplas CompilationUnits."""
        self._reset_state()
        if not units:
            return self.errors

        for unit in units:
            if isinstance(unit, CompilationUnit):
                self._preindex_unit(unit)

        for unit in units:
            if isinstance(unit, CompilationUnit):
                self._analyze_compilation_unit(unit)
            else:
                for stmt in getattr(unit, "statements", []) or []:
                    self.analyze_statement(stmt)

        return self.errors

    # ------------------------------------------------------------------
    # Utilitários de erro, escopo e tipos
    # ------------------------------------------------------------------

    def _error(self, message: str, line: Optional[int]) -> None:
        self.errors.append(SemanticError(message, line if line is not None else 1))

    def _enter_scope(self) -> None:
        self._local_scopes.append({})
        self.symbols.enter_scope()

    def _exit_scope(self) -> None:
        if len(self._local_scopes) > 1:
            self._local_scopes.pop()
        self.symbols.exit_scope()

    def _lookup_local(self, name: str) -> Optional[str]:
        for scope in reversed(self._local_scopes):
            if name in scope:
                return scope[name]
        return None

    def _declare_variable(self, name: str, type_str: str, line: int, category: str = "variavel") -> bool:
        """Declara variável ou parâmetro no escopo atual e na Tabela de Símbolos."""
        if not name or name == "_":
            return True
        if name in self._local_scopes[-1]:
            self._error(f"Variável '{name}' declarada novamente no mesmo escopo.", line)
            return False
        self._local_scopes[-1][name] = type_str or UNKNOWN_TYPE
        self.symbols.declare(name, type_str or UNKNOWN_TYPE, line, category=category)
        return True

    def _is_active_type_param(self, name: str) -> bool:
        base = self._strip_generics_and_array(name)
        return any(base in frame for frame in self._type_param_stack)

    @staticmethod
    def _strip_generics_and_array(type_str: str) -> str:
        text = (type_str or "").strip()
        if "<" in text:
            text = text.split("<", 1)[0].strip()
        while text.endswith("[]"):
            text = text[:-2].strip()
        if "." in text:
            text = text.rsplit(".", 1)[-1].strip()
        return text

    @staticmethod
    def _array_dims(type_str: str) -> int:
        dims = 0
        text = (type_str or "").strip()
        while text.endswith("[]"):
            dims += 1
            text = text[:-2].strip()
        return dims

    def _type_to_str(self, type_node: Any, extra_dims: int = 0, register_line: Optional[int] = None) -> str:
        """Converte TypeReference ou string em representação textual canônica preservando dimensões."""
        if type_node is None:
            return UNKNOWN_TYPE
        if isinstance(type_node, str):
            base = type_node.strip() or UNKNOWN_TYPE
            dims = extra_dims
        elif isinstance(type_node, TypeReference):
            raw_name = getattr(type_node, "name", "") or UNKNOWN_TYPE
            base = raw_name.rsplit(".", 1)[-1] if "." in raw_name else raw_name
            dims = int(getattr(type_node, "array_dimensions", 0) or 0) + int(extra_dims or 0)
            if getattr(type_node, "is_varargs", False) and dims == 0:
                dims = 1
        else:
            base = getattr(type_node, "name", None) or str(type_node)
            dims = int(extra_dims or 0)

        if base == "var":
            if register_line is not None and hasattr(self.symbols, "register_type"):
                self.symbols.register_type("var", register_line, category="palavra_reservada")
            return "var" + ("[]" * dims)

        full = f"{base}{'[]' * dims}"
        if register_line is not None:
            self._register_reference_type(base, register_line)
        return full

    def _register_reference_type(self, base_name: str, line: int) -> None:
        """Registra tipos de referência externos utilizados no código sem duplicar tipos declarados."""
        clean = self._strip_generics_and_array(base_name)
        if (
            not clean
            or clean in self.PRIMITIVE_TYPES
            or clean in ("void", "var", "null", UNKNOWN_TYPE)
            or clean in self._declared_types
            or self._is_active_type_param(clean)
        ):
            return
        if hasattr(self.symbols, "register_type"):
            self.symbols.register_type(clean, line, category="tipo")

    def _push_type_parameters(self, type_params: Optional[Sequence[Any]]) -> None:
        names: Set[str] = set()
        for tp in type_params or ():
            tp_name = getattr(tp, "name", None)
            if tp_name:
                names.add(tp_name)
        self._type_param_stack.append(names)

    def _pop_type_parameters(self) -> None:
        if self._type_param_stack:
            self._type_param_stack.pop()

    # ------------------------------------------------------------------
    # Passo 1: Pré-indexação de tipos e membros declarados
    # ------------------------------------------------------------------

    def _preindex_unit(self, unit: CompilationUnit) -> None:
        pkg = getattr(unit, "package", None)
        pkg_name = getattr(pkg, "name", None) if pkg else None
        if pkg_name:
            self._package_prefixes.add(pkg_name.split(".", 1)[0])

        for imp in getattr(unit, "imports", []) or []:
            imp_name = getattr(imp, "name", None) or ""
            if imp_name:
                self._package_prefixes.add(imp_name.split(".", 1)[0])
                if getattr(imp, "is_static", False) and getattr(imp, "is_wildcard", False):
                    self._has_static_wildcard = True
                if not getattr(imp, "is_wildcard", False):
                    self._imported_names.add(imp_name.rsplit(".", 1)[-1])

        for type_decl in getattr(unit, "type_declarations", []) or []:
            self._preindex_type_decl(type_decl)

    def _preindex_type_decl(self, node: ASTNode) -> None:
        name = getattr(node, "name", None)
        if not name:
            return

        kind = "classe"
        if isinstance(node, InterfaceDeclaration):
            kind = "interface"
        elif isinstance(node, EnumDeclaration):
            kind = "enum"
        elif isinstance(node, RecordDeclaration):
            kind = "record"
        elif isinstance(node, AnnotationInterfaceDeclaration):
            kind = "interface"

        supertypes: List[str] = []
        ext = getattr(node, "extends_type", None)
        if ext is not None:
            supertypes.append(self._strip_generics_and_array(self._type_to_str(ext)))
        for ext_t in getattr(node, "extends_types", []) or []:
            supertypes.append(self._strip_generics_and_array(self._type_to_str(ext_t)))
        for impl_t in getattr(node, "implements_types", []) or []:
            supertypes.append(self._strip_generics_and_array(self._type_to_str(impl_t)))

        info = self._declared_types.setdefault(
            name,
            {
                "kind": kind,
                "supertypes": [s for s in supertypes if s and s != UNKNOWN_TYPE],
                "fields": {},
                "methods": {},
                "constructors": [],
            },
        )
        # Registra declaração de tipo na tabela de símbolos na ordem de declaração
        self.symbols.declare(name, name, getattr(node, "line", 1), category=kind)

        # Record components viram campos, métodos acessores e construtor canônico
        if isinstance(node, RecordDeclaration):
            header = getattr(node, "header", None)
            comp_list = getattr(header, "component_list", None) if header else None
            comps = getattr(comp_list, "components", []) if comp_list else []
            comp_param_types: List[Tuple[str, bool]] = []
            for comp in comps:
                c_type = self._type_to_str(getattr(comp, "type_ref", None))
                c_name = getattr(comp, "name", None)
                if c_name:
                    info["fields"][c_name] = c_type
                    info["methods"].setdefault(c_name, []).append(([], c_type))
                    comp_param_types.append((c_type, bool(getattr(comp, "is_varargs", False))))
            if comps:
                info["constructors"].append(comp_param_types)

        if isinstance(node, EnumDeclaration):
            for const in getattr(node, "constants", []) or []:
                c_name = getattr(const, "name", None)
                if c_name:
                    info["fields"][c_name] = name

        for member in self._iter_type_members(node):
            self._preindex_member(info, name, member)
            if isinstance(member, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
                self._preindex_type_decl(member)

    def _iter_type_members(self, node: ASTNode) -> List[ASTNode]:
        raw: List[ASTNode] = list(getattr(node, "members", []) or [])
        body = getattr(node, "body", None)
        if body is not None:
            if hasattr(body, "members") and body.members:
                raw.extend(body.members)
            if hasattr(body, "declarations") and body.declarations:
                raw.extend(body.declarations)
            bd = getattr(body, "body_declarations", None)
            if bd is not None and getattr(bd, "members", None):
                raw.extend(bd.members)
        # Evita duplicação quando Parser preenche tanto node.members quanto node.body
        unique: List[ASTNode] = []
        seen_ids: Set[int] = set()
        for m in raw:
            if id(m) not in seen_ids:
                seen_ids.add(id(m))
                unique.append(m)
        return unique

    def _preindex_member(self, type_info: Dict[str, Any], owner_name: str, member: ASTNode) -> None:
        if isinstance(member, FieldDeclaration):
            base_type = getattr(member, "type_ref", None)
            for decl in getattr(member, "declarators", []) or []:
                d_id = getattr(decl, "id", None)
                m_name = getattr(d_id, "name", None) if d_id else None
                dims = getattr(d_id, "dims", 0) if d_id else 0
                if m_name and m_name != "_":
                    type_info["fields"][m_name] = self._type_to_str(base_type, extra_dims=dims)
        elif isinstance(member, MethodDeclaration):
            m_name = getattr(member, "name", None)
            if not m_name:
                return
            ret = self._type_to_str(getattr(member, "return_type", None), extra_dims=int(getattr(member, "dims", 0) or 0))
            params = self._extract_param_signature(getattr(member, "parameters", []))
            type_info["methods"].setdefault(m_name, []).append((params, ret))
        elif isinstance(member, ConstructorDeclaration):
            params = self._extract_param_signature(getattr(member, "parameters", []))
            type_info["constructors"].append(params)

    def _extract_param_signature(self, parameters: Optional[Sequence[Any]]) -> List[Tuple[str, bool]]:
        sig: List[Tuple[str, bool]] = []
        for p in parameters or ():
            p_dims = int(getattr(p, "dims", 0) or 0)
            is_varargs = bool(getattr(p, "is_varargs", False))
            p_type = self._type_to_str(getattr(p, "type_ref", None), extra_dims=p_dims + (1 if is_varargs else 0))
            sig.append((p_type, is_varargs))
        return sig

    # ------------------------------------------------------------------
    # Passo 2: Análise de CompilationUnit, tipos e membros
    # ------------------------------------------------------------------

    def _analyze_compilation_unit(self, unit: CompilationUnit) -> None:
        for ann in self._extract_unit_annotations(unit):
            self._check_annotation(ann)

        for type_decl in getattr(unit, "type_declarations", []) or []:
            self._analyze_type_declaration(type_decl)

        for member in getattr(unit, "class_members", []) or []:
            self._analyze_class_member(member, owner_kind="classe")

        statements = getattr(unit, "statements", []) or []
        if statements:
            for stmt in statements:
                self.analyze_statement(stmt)

    def _extract_unit_annotations(self, unit: CompilationUnit) -> List[ASTNode]:
        annos: List[ASTNode] = []
        pkg = getattr(unit, "package", None)
        if pkg is not None:
            for m in getattr(pkg, "modifiers", []) or []:
                if isinstance(m, Annotation):
                    annos.append(m)
            annos.extend(getattr(pkg, "annotations", []) or [])
        mod = getattr(unit, "module_declaration", None)
        if mod is not None:
            annos.extend(getattr(mod, "annotations", []) or [])
        return annos

    def _analyze_type_declaration(self, node: ASTNode) -> None:
        if isinstance(node, ClassDeclaration):
            self.analyze_class(node)
        elif isinstance(node, InterfaceDeclaration):
            self.analyze_interface(node)
        elif isinstance(node, EnumDeclaration):
            self.analyze_enum(node)
        elif isinstance(node, RecordDeclaration):
            self.analyze_record(node)
        elif isinstance(node, AnnotationInterfaceDeclaration):
            self.analyze_annotation_interface(node)

    def analyze_class(self, cls_node: ClassDeclaration, is_nested: bool = False, is_local: bool = False) -> None:
        self._analyze_type_body(cls_node, owner_kind="classe")

    def analyze_interface(self, iface_node: InterfaceDeclaration, is_nested: bool = False, is_local: bool = False) -> None:
        self._analyze_type_body(iface_node, owner_kind="interface")

    def analyze_enum(self, enum_node: EnumDeclaration, is_nested: bool = False, is_local: bool = False) -> None:
        for const in getattr(enum_node, "constants", []) or []:
            line = getattr(const, "line", getattr(enum_node, "line", 1))
            if getattr(const, "name", None):
                self.symbols.declare(const.name, enum_node.name, line, category="constante_enum", is_static=True)
            for arg in getattr(const, "arguments", []) or []:
                self.check_expression(arg)
            cbody = getattr(const, "body", None)
            if cbody is not None:
                cbody_members = getattr(cbody, "members", []) or []
                self._current_type_stack.append(enum_node.name)
                self._enter_scope()
                try:
                    for m in cbody_members:
                        if isinstance(m, FieldDeclaration):
                            base_t = getattr(m, "type_ref", None)
                            for decl in getattr(m, "declarators", []) or []:
                                d_id = getattr(decl, "id", None)
                                f_name = getattr(d_id, "name", None) if d_id else None
                                if f_name and f_name != "_":
                                    self._local_scopes[-1][f_name] = self._type_to_str(base_t, extra_dims=int(getattr(d_id, "dims", 0) or 0))
                    for m in cbody_members:
                        self._analyze_class_member(m, owner_kind="enum")
                finally:
                    self._exit_scope()
                    self._current_type_stack.pop()
        self._analyze_type_body(enum_node, owner_kind="enum")

    def analyze_record(self, rec_node: RecordDeclaration, is_nested: bool = False, is_local: bool = False) -> None:
        header = getattr(rec_node, "header", None)
        comp_list = getattr(header, "component_list", None) if header else None
        comps = getattr(comp_list, "components", []) if comp_list else []
        comp_names: List[Tuple[str, str, int]] = []
        seen_comps: Set[str] = set()
        for comp in comps:
            c_line = getattr(comp, "line", getattr(rec_node, "line", 1))
            c_type = self._type_to_str(
                getattr(comp, "type_ref", None),
                extra_dims=1 if getattr(comp, "is_varargs", False) else 0,
                register_line=c_line,
            )
            c_name = getattr(comp, "name", None)
            if c_name:
                if c_name in seen_comps:
                    self._error(f"Componente de record '{c_name}' duplicado em '{rec_node.name}'.", c_line)
                else:
                    seen_comps.add(c_name)
                    self.symbols.declare(c_name, c_type, c_line, category="componente_record")
                    comp_names.append((c_name, c_type, c_line))

        self._analyze_type_body(rec_node, owner_kind="record", record_components=comp_names)

    def analyze_annotation_interface(
        self,
        ann_node: AnnotationInterfaceDeclaration,
        is_nested: bool = False,
        is_local: bool = False,
    ) -> None:
        self._analyze_type_body(ann_node, owner_kind="interface")

    def _analyze_type_body(
        self,
        type_node: ASTNode,
        owner_kind: str,
        record_components: Optional[List[Tuple[str, str, int]]] = None,
    ) -> None:
        name = getattr(type_node, "name", "")
        line = getattr(type_node, "line", 1)

        for ann in getattr(type_node, "annotations", []) or []:
            self._check_annotation(ann)
        for mod in getattr(type_node, "modifiers", []) or []:
            if isinstance(mod, Annotation):
                self._check_annotation(mod)

        # Registra referências em extends/implements/permits
        for ref_attr in ("extends_type",):
            ref = getattr(type_node, ref_attr, None)
            if ref is not None:
                self._type_to_str(ref, register_line=line)
        for list_attr in ("extends_types", "implements_types", "permits_types"):
            for ref in getattr(type_node, list_attr, []) or []:
                self._type_to_str(ref, register_line=line)

        self._push_type_parameters(getattr(type_node, "type_parameters", []))
        self._current_type_stack.append(name)
        seen_fields: Set[str] = set()
        try:
            for member in self._iter_type_members(type_node):
                if isinstance(member, FieldDeclaration):
                    self._analyze_field_declaration(
                        member,
                        is_interface=(owner_kind == "interface" or isinstance(member, InterfaceConstantDeclaration)),
                        seen_fields=seen_fields,
                    )
                else:
                    self._analyze_class_member(member, owner_kind=owner_kind, record_components=record_components)
        finally:
            self._current_type_stack.pop()
            self._pop_type_parameters()

    def _analyze_class_member(
        self,
        member: ASTNode,
        owner_kind: str = "classe",
        record_components: Optional[List[Tuple[str, str, int]]] = None,
    ) -> None:
        if isinstance(member, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
            self._analyze_type_declaration(member)
        elif isinstance(member, FieldDeclaration):
            self._analyze_field_declaration(member, is_interface=(owner_kind == "interface"))
        elif isinstance(member, MethodDeclaration):
            self._analyze_method_declaration(member)
        elif isinstance(member, ConstructorDeclaration):
            self._analyze_constructor_declaration(member, record_components=record_components)
        elif isinstance(member, (InstanceInitializer, StaticInitializer)):
            block = getattr(member, "block", None)
            if block is not None:
                self.analyze_block(block)

    def _analyze_field_declaration(
        self,
        member: FieldDeclaration,
        is_interface: bool = False,
        seen_fields: Optional[Set[str]] = None,
    ) -> None:
        for ann in getattr(member, "annotations", []) or []:
            self._check_annotation(ann)
        mods = [m for m in (getattr(member, "modifiers", []) or []) if not isinstance(m, Annotation)]
        is_static = is_interface or ("static" in mods)
        category = "constante_interface" if is_interface else "campo"

        base_ref = getattr(member, "type_ref", None)
        for decl in getattr(member, "declarators", []) or []:
            d_id = getattr(decl, "id", None)
            f_name = getattr(d_id, "name", None) if d_id else None
            d_line = getattr(d_id, "line", None) or getattr(decl, "line", None) or getattr(member, "line", 1)
            dims = int(getattr(d_id, "dims", 0) or 0) if d_id else 0
            f_type = self._type_to_str(base_ref, extra_dims=dims, register_line=d_line)

            if f_name and f_name != "_":
                if seen_fields is not None:
                    if f_name in seen_fields:
                        self._error(f"Campo '{f_name}' declarado novamente na mesma classe.", d_line)
                    else:
                        seen_fields.add(f_name)
                self.symbols.declare(f_name, f_type, d_line, category=category, is_static=is_static)

            init = getattr(decl, "initializer", None)
            if init is not None:
                self._check_initializer(f_type, init, f_name or "campo", d_line)

    def _analyze_method_declaration(self, method: MethodDeclaration) -> None:
        m_line = getattr(method, "line", 1)
        mods = [m for m in (getattr(method, "modifiers", []) or []) if not isinstance(m, Annotation)]
        is_static = "static" in mods
        ret_type = self._type_to_str(
            getattr(method, "return_type", None),
            extra_dims=int(getattr(method, "dims", 0) or 0),
            register_line=m_line,
        )
        self.symbols.declare(method.name, ret_type, m_line, category="metodo", is_static=is_static)

        for ann in getattr(method, "annotations", []) or []:
            self._check_annotation(ann)

        self._push_type_parameters(getattr(method, "type_parameters", []))
        self._enter_scope()
        prev_return = self._current_return_type
        self._current_return_type = ret_type
        try:
            self._declare_parameters(getattr(method, "parameters", []))
            body = getattr(method, "body", None)
            if isinstance(body, Block):
                self.analyze_block(body, reuse_current_scope=True)
            elif body is not None:
                self.analyze_statement(body)
        finally:
            self._current_return_type = prev_return
            self._exit_scope()
            self._pop_type_parameters()

    def _analyze_constructor_declaration(
        self,
        ctor: ConstructorDeclaration,
        record_components: Optional[List[Tuple[str, str, int]]] = None,
    ) -> None:
        c_line = getattr(ctor, "line", 1)
        self.symbols.declare(ctor.name, ctor.name, c_line, category="construtor")

        for ann in getattr(ctor, "annotations", []) or []:
            self._check_annotation(ann)

        self._push_type_parameters(getattr(ctor, "type_parameters", []))
        self._enter_scope()
        prev_return = self._current_return_type
        self._current_return_type = "void"
        try:
            params = getattr(ctor, "parameters", None)
            if params:
                self._declare_parameters(params)
            elif record_components:
                # Construtor compacto de record recebe implicitamente os componentes no escopo
                for comp_name, comp_type, _ in record_components:
                    self._local_scopes[-1][comp_name] = comp_type

            body = getattr(ctor, "body", None)
            if isinstance(body, ConstructorBody):
                for s in getattr(body, "prologue", []) or []:
                    self.analyze_statement(s)
                inv = getattr(body, "constructor_invocation", None)
                if inv is not None:
                    for arg in getattr(inv, "arguments", []) or []:
                        self.check_expression(arg)
                for s in getattr(body, "epilogue", []) or []:
                    self.analyze_statement(s)
            elif isinstance(body, Block):
                self.analyze_block(body, reuse_current_scope=True)
            elif body is not None:
                self.analyze_statement(body)
        finally:
            self._current_return_type = prev_return
            self._exit_scope()
            self._pop_type_parameters()

    def _declare_parameters(self, parameters: Optional[Sequence[Any]]) -> None:
        for param in parameters or ():
            p_line = getattr(param, "line", 1)
            extra = int(getattr(param, "dims", 0) or 0) + (1 if getattr(param, "is_varargs", False) else 0)
            p_type = self._type_to_str(getattr(param, "type_ref", None), extra_dims=extra, register_line=p_line)
            p_name = getattr(param, "name", None)
            if p_name and p_name != "_":
                self._declare_variable(p_name, p_type, p_line, category="parametro")

    # ------------------------------------------------------------------
    # Passo 3: Blocos e instruções (Statements)
    # ------------------------------------------------------------------

    def analyze_block(self, block_node: Block, reuse_current_scope: bool = False) -> None:
        if not reuse_current_scope:
            self._enter_scope()
        try:
            for stmt in getattr(block_node, "statements", []) or []:
                self.analyze_statement(stmt)
        finally:
            if not reuse_current_scope:
                self._exit_scope()

    def analyze_statement(self, stmt: Optional[ASTNode]) -> None:
        if stmt is None or isinstance(stmt, EmptyStatement):
            return

        if isinstance(stmt, Block):
            self.analyze_block(stmt)
        elif isinstance(stmt, (Declaration, LocalVariableDeclaration)):
            self._analyze_local_declaration(stmt)
        elif isinstance(stmt, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration)):
            self._preindex_type_decl(stmt)
            self._analyze_type_declaration(stmt)
        elif isinstance(stmt, ExpressionStatement):
            self.check_expression(stmt.expression)
        elif isinstance(stmt, Assignment):
            self._check_assignment(stmt)
        elif isinstance(stmt, StatementExpressionList):
            for expr in getattr(stmt, "expressions", []) or []:
                self.check_expression(expr)
        elif isinstance(stmt, IfStatement):
            self._analyze_if(stmt)
        elif isinstance(stmt, WhileStatement):
            self._analyze_while(stmt)
        elif isinstance(stmt, DoWhileStatement):
            self._analyze_do_while(stmt)
        elif isinstance(stmt, ForStatement):
            self._analyze_for(stmt)
        elif isinstance(stmt, EnhancedForStatement):
            self._analyze_enhanced_for(stmt)
        elif isinstance(stmt, SwitchStatement):
            self._analyze_switch(stmt)
        elif isinstance(stmt, TryStatement):
            self._analyze_try(stmt)
        elif isinstance(stmt, ReturnStatement):
            self._analyze_return(stmt)
        elif isinstance(stmt, BreakStatement):
            label = getattr(stmt, "label", None)
            if not label and self._loop_depth == 0 and self._switch_depth == 0:
                self._error("Instrução 'break' fora de um laço ou estrutura 'switch'.", getattr(stmt, "line", 1))
        elif isinstance(stmt, ContinueStatement):
            label = getattr(stmt, "label", None)
            if not label and self._loop_depth == 0:
                self._error("Instrução 'continue' fora de um laço de repetição.", getattr(stmt, "line", 1))
        elif isinstance(stmt, ThrowStatement):
            self.check_expression(getattr(stmt, "expression", None))
        elif isinstance(stmt, AssertStatement):
            self._check_boolean_condition(getattr(stmt, "condition", None), "assert", getattr(stmt, "line", 1))
            if getattr(stmt, "message", None) is not None:
                self.check_expression(stmt.message)
        elif isinstance(stmt, SynchronizedStatement):
            self.check_expression(getattr(stmt, "lock", None))
            if getattr(stmt, "body", None) is not None:
                self.analyze_statement(stmt.body)
        elif isinstance(stmt, LabeledStatement):
            lbl = getattr(stmt, "label", None)
            if lbl:
                self._active_labels.add(lbl)
            try:
                self.analyze_statement(getattr(stmt, "statement", None))
            finally:
                if lbl:
                    self._active_labels.discard(lbl)
        elif isinstance(stmt, YieldStatement):
            self.check_expression(getattr(stmt, "expression", None))
        else:
            # Nó sintático reconhecido pela AST sem semântica específica obrigatória
            self.check_expression(stmt)

    def _analyze_local_declaration(self, stmt: ASTNode) -> None:
        line = getattr(stmt, "line", 1)
        declarators = getattr(stmt, "declarators", None)
        if declarators:
            base_ref = getattr(stmt, "type_ref", None) or getattr(stmt, "type_name", None)
            is_var = bool(getattr(stmt, "is_var", False)) or (getattr(base_ref, "name", None) == "var")
            if is_var and hasattr(self.symbols, "register_type"):
                self.symbols.register_type("var", line, category="palavra_reservada")
            for decl in declarators:
                d_id = getattr(decl, "id", None)
                v_name = getattr(d_id, "name", None) if d_id else None
                d_line = getattr(d_id, "line", None) or getattr(decl, "line", None) or line
                dims = int(getattr(d_id, "dims", 0) or 0) + int(getattr(stmt, "dims", 0) or 0)
                init = getattr(decl, "initializer", None)
                if is_var:
                    v_type = self._infer_initializer_type(init)
                else:
                    v_type = self._type_to_str(base_ref, extra_dims=dims, register_line=d_line)
                if v_name and v_name != "_":
                    self._declare_variable(v_name, v_type, d_line, category="variavel")
                if init is not None:
                    self._check_initializer(v_type, init, v_name or "variavel", d_line)
            return

        # Forma compacta didática (Declaration / LocalVariableDeclaration com name/type_name únicos)
        v_name = getattr(stmt, "name", None)
        is_var = bool(getattr(stmt, "is_var", False)) or getattr(stmt, "type_name", None) == "var"
        init = getattr(stmt, "initializer", None)
        if is_var:
            if hasattr(self.symbols, "register_type"):
                self.symbols.register_type("var", line, category="palavra_reservada")
            v_type = self._infer_initializer_type(init)
        else:
            raw_type = getattr(stmt, "type_ref", None) or getattr(stmt, "type_name", None)
            v_type = self._type_to_str(raw_type, extra_dims=int(getattr(stmt, "dims", 0) or 0), register_line=line)
        if v_name and v_name != "_":
            self._declare_variable(v_name, v_type, line, category="variavel")
        if init is not None:
            self._check_initializer(v_type, init, v_name or "variavel", line)

    def _infer_initializer_type(self, init: Optional[ASTNode]) -> str:
        if init is None:
            return UNKNOWN_TYPE
        t = self.infer_type(init)
        return t if t and t != "null" else UNKNOWN_TYPE

    def _check_initializer(self, target_type: str, initializer: ASTNode, target_name: str, line: int) -> None:
        if isinstance(initializer, ArrayInitializer):
            elem_target = target_type[:-2] if target_type.endswith("[]") else UNKNOWN_TYPE
            for elem in getattr(initializer, "elements", []) or []:
                self._check_initializer(elem_target, elem, target_name, getattr(elem, "line", line))
            return
        self.check_expression(initializer)
        if target_type and target_type != UNKNOWN_TYPE and target_type != "var":
            self.check_assignment_type(target_type, initializer, target_name, line)

    def _check_boolean_condition(self, cond: Optional[ASTNode], construct: str, line: int) -> None:
        if cond is None:
            return
        self.check_expression(cond)
        cond_type = self.infer_type(cond)
        if cond_type and cond_type not in ("boolean", "Boolean", UNKNOWN_TYPE, "Object"):
            self._error(
                f"Condição de '{construct}' deve ser do tipo boolean (encontrado '{cond_type}').",
                getattr(cond, "line", line),
            )

    def _collect_pattern_vars_into_scope(self, node: Optional[ASTNode], negated: bool = False) -> None:
        """Extrai variáveis declaradas por Pattern / PatternInstanceOfExpression para o escopo local."""
        if node is None:
            return
        if isinstance(node, UnaryOp) and node.op == "!":
            self._collect_pattern_vars_into_scope(node.operand, negated=not negated)
            return
        if isinstance(node, BinaryOp):
            if (not negated and node.op == "&&") or (negated and node.op == "||"):
                self._collect_pattern_vars_into_scope(node.left, negated=negated)
                self._collect_pattern_vars_into_scope(node.right, negated=negated)
            return
        if negated:
            return
        if isinstance(node, PatternInstanceOfExpression):
            self._collect_pattern_vars_into_scope(getattr(node, "pattern", None))
        elif isinstance(node, InstanceOfExpression) and getattr(node, "pattern", None) is not None:
            self._collect_pattern_vars_into_scope(node.pattern)
        elif isinstance(node, (TypePattern, PatternVariable)):
            p_line = getattr(node, "line", 1)
            p_name = getattr(node, "name", None)
            if not p_name and getattr(node, "variable", None) is not None:
                p_name = getattr(node.variable, "name", None)
            t_ref = getattr(node, "type_ref", None)
            p_type = UNKNOWN_TYPE if getattr(node, "is_var", False) else self._type_to_str(t_ref, register_line=p_line)
            if p_name and p_name != "_" and not getattr(node, "is_unnamed", False):
                self._local_scopes[-1].setdefault(p_name, p_type)
        elif isinstance(node, RecordPattern):
            for comp in getattr(node, "components", []) or []:
                self._collect_pattern_vars_into_scope(comp)
            clist = getattr(node, "component_list", None)
            if clist is not None:
                for comp in getattr(clist, "components", []) or []:
                    self._collect_pattern_vars_into_scope(comp)

    @staticmethod
    def _branch_abruptly_exits(stmt: Optional[ASTNode]) -> bool:
        if stmt is None:
            return False
        if isinstance(stmt, (ReturnStatement, ThrowStatement, BreakStatement, ContinueStatement)):
            return True
        if isinstance(stmt, Block) and getattr(stmt, "statements", None):
            return SemanticAnalyzer._branch_abruptly_exits(stmt.statements[-1])
        return False

    def _analyze_if(self, stmt: IfStatement) -> None:
        self._check_boolean_condition(stmt.condition, "if", getattr(stmt, "line", 1))
        self._enter_scope()
        try:
            self._collect_pattern_vars_into_scope(stmt.condition, negated=False)
            self.analyze_statement(stmt.then_branch)
        finally:
            self._exit_scope()
        if stmt.else_branch is not None:
            self._enter_scope()
            try:
                self._collect_pattern_vars_into_scope(stmt.condition, negated=True)
                self.analyze_statement(stmt.else_branch)
            finally:
                self._exit_scope()
        elif self._branch_abruptly_exits(stmt.then_branch):
            # Padrão if (!(x instanceof T s)) { return; } introduz s no escopo seguinte
            self._collect_pattern_vars_into_scope(stmt.condition, negated=True)

    def _analyze_while(self, stmt: WhileStatement) -> None:
        self._check_boolean_condition(stmt.condition, "while", getattr(stmt, "line", 1))
        self._loop_depth += 1
        try:
            self.analyze_statement(stmt.body)
        finally:
            self._loop_depth -= 1

    def _analyze_do_while(self, stmt: DoWhileStatement) -> None:
        self._loop_depth += 1
        try:
            self.analyze_statement(stmt.body)
        finally:
            self._loop_depth -= 1
        self._check_boolean_condition(stmt.condition, "do-while", getattr(stmt, "line", 1))

    def _analyze_for(self, stmt: ForStatement) -> None:
        self._enter_scope()
        self._loop_depth += 1
        try:
            init = getattr(stmt, "init", None)
            if isinstance(init, list):
                for item in init:
                    self.analyze_statement(item)
            elif init is not None:
                self.analyze_statement(init)
            for item in getattr(stmt, "init_expressions", []) or []:
                self.check_expression(item)

            self._check_boolean_condition(getattr(stmt, "condition", None), "for", getattr(stmt, "line", 1))

            update = getattr(stmt, "update", None)
            if isinstance(update, list):
                for item in update:
                    self.analyze_statement(item)
            elif update is not None:
                self.analyze_statement(update)
            for item in getattr(stmt, "update_expressions", []) or []:
                self.check_expression(item)

            self.analyze_statement(stmt.body)
        finally:
            self._loop_depth -= 1
            self._exit_scope()

    def _analyze_enhanced_for(self, stmt: EnhancedForStatement) -> None:
        self._enter_scope()
        self._loop_depth += 1
        try:
            iter_type = self.infer_type(stmt.iterable) or UNKNOWN_TYPE
            self.check_expression(stmt.iterable)

            var = stmt.variable
            if var is not None:
                v_line = getattr(var, "line", getattr(stmt, "line", 1))
                v_name = getattr(var, "name", None)
                is_var = bool(getattr(var, "is_var", False)) or getattr(var, "type_name", None) == "var"
                if is_var:
                    v_type = iter_type[:-2] if iter_type.endswith("[]") else UNKNOWN_TYPE
                else:
                    v_type = self._type_to_str(
                        getattr(var, "type_ref", None) or getattr(var, "type_name", None),
                        extra_dims=int(getattr(var, "dims", 0) or 0),
                        register_line=v_line,
                    )
                if v_name and v_name != "_":
                    self._declare_variable(v_name, v_type, v_line, category="variavel")

            self.analyze_statement(stmt.body)
        finally:
            self._loop_depth -= 1
            self._exit_scope()

    def _analyze_switch(self, stmt: ASTNode) -> None:
        self.check_expression(getattr(stmt, "expression", None))
        self._switch_depth += 1
        try:
            sw_block = getattr(stmt, "switch_block", None)
            if sw_block is not None:
                entries = getattr(sw_block, "entries", None)
                if entries:
                    for entry in entries:
                        self._analyze_switch_entry(entry)
                else:
                    for grp in getattr(sw_block, "statement_groups", []) or []:
                        self._analyze_switch_entry(grp)
                    for rule in getattr(sw_block, "switch_rules", []) or []:
                        self._analyze_switch_entry(rule)
                return

            for case in getattr(stmt, "cases", []) or []:
                if getattr(case, "value", None) is not None:
                    self.check_expression(case.value)
                for s in getattr(case, "statements", []) or []:
                    self.analyze_statement(s)

            default_block = getattr(stmt, "default_block", None)
            if isinstance(default_block, list):
                for s in default_block:
                    self.analyze_statement(s)
            elif default_block is not None:
                self.analyze_statement(default_block)
        finally:
            self._switch_depth -= 1

    def _analyze_switch_entry(self, entry: ASTNode) -> None:
        self._enter_scope()
        try:
            for lbl in getattr(entry, "labels", []) or []:
                for pat in getattr(lbl, "patterns", []) or []:
                    self._collect_pattern_vars_into_scope(pat)
                raw_consts = list(getattr(lbl, "constants", []) or [])
                if not raw_consts:
                    clist = getattr(lbl, "constant_list", None)
                    if clist is not None:
                        raw_consts.extend(getattr(clist, "constants", []) or [])
                for c in raw_consts:
                    # Em switch sobre enum, case CONST usa identificador simples da constante
                    if not isinstance(c, Identifier):
                        self.check_expression(c)
                guard = getattr(lbl, "guard", None)
                if guard is not None:
                    self._check_boolean_condition(getattr(guard, "expression", None), "when", getattr(guard, "line", 1))

            if isinstance(entry, SwitchRule):
                self.analyze_statement(getattr(entry, "body", None))
            else:
                for s in getattr(entry, "statements", []) or []:
                    self.analyze_statement(s)
        finally:
            self._exit_scope()

    def _analyze_try(self, stmt: TryStatement) -> None:
        res_spec = getattr(stmt, "resource_specification", None)
        if res_spec is not None and getattr(res_spec, "resources", None):
            raw_res = list(res_spec.resources)
        else:
            raw_res = list(getattr(stmt, "resources", []) or [])
        resources: List[ASTNode] = []
        seen_keys: Set[int] = set()
        for r in raw_res:
            key = id(getattr(r, "declaration", None) or r)
            if key not in seen_keys:
                seen_keys.add(key)
                resources.append(r)

        has_res_scope = len(resources) > 0
        if has_res_scope:
            self._enter_scope()
        try:
            for res in resources:
                if getattr(res, "declaration", None) is not None:
                    self._analyze_local_declaration(res.declaration)
                elif getattr(res, "variable_access", None) is not None:
                    self.check_expression(res.variable_access)
                else:
                    self.analyze_statement(res)

            if getattr(stmt, "body", None) is not None:
                self.analyze_statement(stmt.body)
        finally:
            if has_res_scope:
                self._exit_scope()

        for catch in getattr(stmt, "catches", []) or []:
            self._analyze_catch_clause(catch)

        if getattr(stmt, "finally_block", None) is not None:
            self.analyze_statement(stmt.finally_block)

    def _analyze_catch_clause(self, catch: CatchClause) -> None:
        self._enter_scope()
        try:
            param = getattr(catch, "parameter", None)
            if param is not None:
                p_line = getattr(param, "line", getattr(catch, "line", 1))
                p_name = getattr(param, "name", None)
                ctype = getattr(catch, "catch_type", None)
                types_list = getattr(ctype, "types", []) if ctype else []
                if types_list:
                    p_type = self._type_to_str(types_list[0], register_line=p_line)
                    for extra_t in types_list[1:]:
                        self._type_to_str(extra_t, register_line=p_line)
                else:
                    p_type = self._type_to_str(getattr(param, "type_ref", None), register_line=p_line)
                if p_name and p_name != "_":
                    self._declare_variable(p_name, p_type, p_line, category="parametro")
            self.analyze_statement(getattr(catch, "body", None))
        finally:
            self._exit_scope()

    def _analyze_return(self, stmt: ReturnStatement) -> None:
        line = getattr(stmt, "line", 1)
        expr = getattr(stmt, "expression", None)
        expected = self._current_return_type

        if expected is None:
            if expr is not None:
                self.check_expression(expr)
            return

        if expected == "void":
            if expr is not None:
                self.check_expression(expr)
                self._error("Método 'void' não deve retornar valor.", line)
            return

        if expr is None:
            self._error(f"Instrução 'return' deve retornar valor compatível com '{expected}'.", line)
            return

        self.check_expression(expr)
        actual = self.infer_type(expr)
        if actual and actual != UNKNOWN_TYPE and not self.is_assignable(expected, actual):
            self._error(
                f"Tipo de retorno incompatível: não é possível retornar '{actual}' em método do tipo '{expected}'.",
                line,
            )

    # ------------------------------------------------------------------
    # Passo 4: Expressões, inferência e compatibilidade de tipos
    # ------------------------------------------------------------------

    def check_expression(self, node: Optional[ASTNode]) -> None:
        if node is None:
            return
        if isinstance(node, Assignment):
            self._check_assignment(node)
        elif isinstance(node, Identifier):
            self._resolve_identifier_type(node, allow_type_or_pkg=False)
        elif isinstance(node, BinaryOp):
            self._check_binary_op(node)
        elif isinstance(node, UnaryOp):
            self._check_unary_op(node)
        elif isinstance(node, ConditionalExpression):
            self._check_boolean_condition(node.condition, "ternário", getattr(node, "line", 1))
            self._enter_scope()
            try:
                self._collect_pattern_vars_into_scope(node.condition, negated=False)
                self.check_expression(node.then_expr)
            finally:
                self._exit_scope()
            self._enter_scope()
            try:
                self._collect_pattern_vars_into_scope(node.condition, negated=True)
                self.check_expression(node.else_expr)
            finally:
                self._exit_scope()
        elif isinstance(node, MemberAccess):
            self._check_member_access(node)
        elif isinstance(node, ArrayAccess):
            self.check_expression(node.array)
            self.check_expression(node.index)
            idx_type = self.infer_type(node.index)
            if idx_type and idx_type != UNKNOWN_TYPE and idx_type not in self.INTEGRAL_TYPES and idx_type not in ("Integer", "Character", "Byte", "Short"):
                self._error(f"Índice de array deve ser inteiro (encontrado '{idx_type}').", getattr(node, "line", 1))
        elif isinstance(node, ArrayCreationExpression):
            self._type_to_str(getattr(node, "type_ref", None), register_line=getattr(node, "line", 1))
            for dim_expr in getattr(node, "dimensions", []) or []:
                self.check_expression(dim_expr)
            if getattr(node, "initializer", None) is not None:
                self.check_expression(node.initializer)
        elif isinstance(node, ArrayInitializer):
            for elem in getattr(node, "elements", []) or []:
                self.check_expression(elem)
        elif isinstance(node, CastExpression):
            self._type_to_str(getattr(node, "target_type", None), register_line=getattr(node, "line", 1))
            self.check_expression(getattr(node, "expression", None))
        elif isinstance(node, (InstanceOfExpression, PatternInstanceOfExpression)):
            self.check_expression(getattr(node, "expression", None))
            if getattr(node, "target_type", None) is not None:
                self._type_to_str(node.target_type, register_line=getattr(node, "line", 1))
        elif isinstance(node, ObjectCreationExpression):
            self._check_object_creation(node)
        elif isinstance(node, MethodCall):
            self._check_method_call(node)
        elif isinstance(node, LambdaExpression):
            self._check_lambda(node)
        elif isinstance(node, MethodReference):
            target = getattr(node, "target", None)
            if isinstance(target, TypeReference):
                self._type_to_str(target, register_line=getattr(node, "line", 1))
            elif isinstance(target, Identifier):
                self._resolve_identifier_type(target, allow_type_or_pkg=True)
            elif target is not None:
                self.check_expression(target)
        elif isinstance(node, SwitchExpression):
            self._analyze_switch(node)
        elif isinstance(node, ClassLiteral):
            self._type_to_str(getattr(node, "type_ref", None), register_line=getattr(node, "line", 1))
        elif isinstance(node, Annotation):
            self._check_annotation(node)

    def _check_annotation(self, ann: ASTNode) -> None:
        if hasattr(ann, "element_value") and ann.element_value is not None:
            val = getattr(ann.element_value, "value", ann.element_value)
            self.check_expression(val)
        pair_list = getattr(ann, "element_value_pair_list", None)
        if pair_list is not None:
            for pair in getattr(pair_list, "pairs", []) or []:
                val = getattr(pair, "value", None)
                self.check_expression(getattr(val, "value", val))

    def _check_assignment(self, node: Assignment) -> None:
        line = getattr(node, "line", 1)
        op = getattr(node, "operator", "=") or "="
        expr = getattr(node, "expression", None)
        target = getattr(node, "target", None)

        if target is None or isinstance(target, Identifier):
            t_name = getattr(target, "name", None) if target is not None else getattr(node, "name", None)
            if not t_name:
                self.check_expression(expr)
                return
            if t_name == "_":
                self.check_expression(expr)
                return
            t_type = self._lookup_variable_or_field_type(t_name)
            if t_type is None:
                self._error(f"Variável '{t_name}' não foi declarada.", line)
                self.check_expression(expr)
                return
            self.check_expression(expr)
            self.check_assignment_type(t_type, expr, t_name, line, operator=op)
            return

        self.check_expression(target)
        self.check_expression(expr)
        t_type = self.infer_type(target)
        if t_type and t_type != UNKNOWN_TYPE:
            t_label = getattr(target, "member_name", None) or getattr(target, "name", None) or "destino"
            self.check_assignment_type(t_type, expr, t_label, line, operator=op)

    def _check_binary_op(self, node: BinaryOp) -> None:
        if node.op in ("&&", "||"):
            self.check_expression(node.left)
            self._enter_scope()
            try:
                self._collect_pattern_vars_into_scope(node.left, negated=(node.op == "||"))
                self.check_expression(node.right)
            finally:
                self._exit_scope()
            left_t = self.infer_type(node.left) or UNKNOWN_TYPE
            right_t = self.infer_type(node.right) or UNKNOWN_TYPE
            line = getattr(node, "line", 1)
            for side_t in (left_t, right_t):
                if side_t not in (UNKNOWN_TYPE, "boolean", "Boolean"):
                    self._error(f"Operador lógico '{node.op}' exige operandos booleanos (encontrado '{side_t}').", line)
            self._inferred_types[id(node)] = "boolean"
            return

        # Percurso iterativo em pós-ordem para cadeias longas de BinaryOp (evita RecursionError)
        stack: List[Tuple[BinaryOp, bool]] = [(node, False)]
        while stack:
            cur, visited = stack.pop()
            if not visited:
                stack.append((cur, True))
                for child in (cur.right, cur.left):
                    if isinstance(child, BinaryOp) and child.op not in ("&&", "||"):
                        stack.append((child, False))
                    elif child is not None:
                        self.check_expression(child)
                continue

            left_t = self.infer_type(cur.left) or UNKNOWN_TYPE
            right_t = self.infer_type(cur.right) or UNKNOWN_TYPE
            line = getattr(cur, "line", 1)
            op = cur.op
            res_t = UNKNOWN_TYPE

            if op in ("&&", "||"):
                for side_t in (left_t, right_t):
                    if side_t not in (UNKNOWN_TYPE, "boolean", "Boolean"):
                        self._error(f"Operador lógico '{op}' exige operandos booleanos (encontrado '{side_t}').", line)
                res_t = "boolean"
            elif op in ("==", "!=", "<", "<=", ">", ">="):
                res_t = "boolean"
            elif op in ("-", "*", "/", "%"):
                if left_t == "String" or right_t == "String":
                    self._error(
                        f"Operação aritmética '{op}' inválida: tipo 'String' não é suportado em operações aritméticas.",
                        line,
                    )
                else:
                    for side_t in (left_t, right_t):
                        if side_t != UNKNOWN_TYPE and self._unboxed_numeric(side_t) is None:
                            self._error(f"Operação aritmética '{op}' inválida para tipo '{side_t}'.", line)
                            break
                    else:
                        res_t = self._promote_numeric(left_t, right_t) or UNKNOWN_TYPE
            elif op == "+":
                if left_t == "String" or right_t == "String":
                    res_t = "String"
                elif left_t != UNKNOWN_TYPE and right_t != UNKNOWN_TYPE and (
                    self._unboxed_numeric(left_t) is None or self._unboxed_numeric(right_t) is None
                ):
                    self._error(f"Operação '+' inválida entre '{left_t}' e '{right_t}'.", line)
                else:
                    res_t = self._promote_numeric(left_t, right_t) or UNKNOWN_TYPE
            else:
                res_t = self._compute_binary_op_type(op, left_t, right_t)

            self._inferred_types[id(cur)] = res_t

    def _check_unary_op(self, node: UnaryOp) -> None:
        self.check_expression(node.operand)
        t = self.infer_type(node.operand)
        if not t or t == UNKNOWN_TYPE:
            return
        line = getattr(node, "line", 1)
        if node.op == "!":
            if t not in ("boolean", "Boolean"):
                self._error(f"Operador lógico '!' exige tipo boolean (encontrado '{t}').", line)
        elif node.op in ("+", "-", "~", "++", "--"):
            if t == "String" or self._unboxed_numeric(t) is None:
                self._error(f"Operador '{node.op}' inválido para o tipo '{t}'.", line)

    def _check_member_access(self, node: MemberAccess) -> None:
        target = getattr(node, "target", None)
        if isinstance(target, Identifier):
            self._resolve_identifier_type(target, allow_type_or_pkg=True)
        elif target is not None:
            self.check_expression(target)

    def _check_object_creation(self, node: ObjectCreationExpression) -> None:
        line = getattr(node, "line", 1)
        args = getattr(node, "arguments", []) or []
        for arg in args:
            self.check_expression(arg)

        type_ref = getattr(node, "type_ref", None) or getattr(node, "method_name", None)
        t_name = self._type_to_str(type_ref, register_line=line)
        base = self._strip_generics_and_array(t_name)

        info = self._declared_types.get(base)
        if info is not None and not getattr(node, "anonymous_body", None):
            ctors = info.get("constructors", [])
            if ctors:
                if not any(self._arity_matches(sig, len(args)) for sig in ctors):
                    self._error(
                        f"Construtor de '{base}' não aceita {len(args)} argumento(s).",
                        line,
                    )
            elif len(args) > 0 and not info.get("supertypes"):
                self._error(
                    f"Construtor padrão de '{base}' não espera argumentos (recebeu {len(args)}).",
                    line,
                )

        anon = getattr(node, "anonymous_body", None)
        if anon is not None:
            self._current_type_stack.append(base)
            try:
                members = anon if isinstance(anon, list) else getattr(anon, "members", []) or []
                for m in members:
                    self._analyze_class_member(m, owner_kind="classe")
            finally:
                self._current_type_stack.pop()

    def _check_method_call(self, node: MethodCall) -> None:
        line = getattr(node, "line", 1)
        args = getattr(node, "arguments", []) or []
        for arg in args:
            self.check_expression(arg)

        target = getattr(node, "target", None)
        owner_name: Optional[str] = None
        if target is None:
            owner_name = self._current_type_stack[-1] if self._current_type_stack else None
        elif isinstance(target, Identifier):
            t_type = self._resolve_identifier_type(target, allow_type_or_pkg=True)
            if t_type and t_type != UNKNOWN_TYPE:
                owner_name = self._strip_generics_and_array(t_type)
        else:
            self.check_expression(target)
            t_type = self.infer_type(target)
            if t_type and t_type != UNKNOWN_TYPE:
                owner_name = self._strip_generics_and_array(t_type)

        if not owner_name:
            return
        overloads = self._lookup_method_overloads(owner_name, node.method_name)
        if overloads is None:
            if target is None and (node.method_name in self._imported_names or self._has_static_wildcard):
                return
            # Se a classe local não herda de externa e é o próprio alvo local, verifica existência apenas
            # quando o método pertence a uma classe declarada fechada sem supertipos externos
            info = self._declared_types.get(owner_name)
            if info is not None and not self._has_external_supertype(owner_name):
                self._error(f"Método '{node.method_name}' não foi declarado em '{owner_name}'.", line)
            return

        if not any(self._arity_matches(params, len(args)) for params, _ in overloads):
            self._error(
                f"Método '{node.method_name}' de '{owner_name}' não aceita {len(args)} argumento(s).",
                line,
            )

    def _check_lambda(self, node: LambdaExpression) -> None:
        self._enter_scope()
        prev_return = self._current_return_type
        self._current_return_type = None
        try:
            for p in getattr(node, "parameters", []) or []:
                p_name = p if isinstance(p, str) else getattr(p, "name", None)
                p_line = getattr(node, "line", 1) if isinstance(p, str) else getattr(p, "line", getattr(node, "line", 1))
                t_ref = None if isinstance(p, str) else getattr(p, "type_ref", None)
                p_type = self._type_to_str(t_ref, register_line=p_line) if t_ref is not None else UNKNOWN_TYPE
                if p_name and p_name != "_":
                    self._declare_variable(p_name, p_type, p_line, category="parametro")

            body = getattr(node, "body", None)
            if isinstance(body, Block):
                self.analyze_block(body, reuse_current_scope=True)
            elif body is not None:
                self.check_expression(body)
        finally:
            self._current_return_type = prev_return
            self._exit_scope()

    # ------------------------------------------------------------------
    # Resolução de identificadores, campos e métodos locais
    # ------------------------------------------------------------------

    def _lookup_variable_or_field_type(self, name: str) -> Optional[str]:
        local_t = self._lookup_local(name)
        if local_t is not None:
            return local_t
        for cls_name in reversed(self._current_type_stack):
            f_type = self._lookup_field_in_hierarchy(cls_name, name)
            if f_type is not None:
                return f_type
        return None

    def _lookup_field_in_hierarchy(self, cls_name: str, field_name: str, visited: Optional[Set[str]] = None) -> Optional[str]:
        if visited is None:
            visited = set()
        if not cls_name or cls_name in visited:
            return None
        visited.add(cls_name)
        info = self._declared_types.get(cls_name)
        if info is None:
            return None
        if field_name in info["fields"]:
            return info["fields"][field_name]
        for sup in info.get("supertypes", []):
            res = self._lookup_field_in_hierarchy(sup, field_name, visited)
            if res is not None:
                return res
        return None

    def _lookup_method_overloads(
        self, cls_name: str, method_name: str, visited: Optional[Set[str]] = None
    ) -> Optional[List[Tuple[List[Tuple[str, bool]], str]]]:
        if visited is None:
            visited = set()
        if not cls_name or cls_name in visited:
            return None
        visited.add(cls_name)
        info = self._declared_types.get(cls_name)
        if info is None:
            return None
        if method_name in info["methods"]:
            return info["methods"][method_name]
        for sup in info.get("supertypes", []):
            res = self._lookup_method_overloads(sup, method_name, visited)
            if res is not None:
                return res
        return None

    def _has_external_supertype(self, cls_name: str, visited: Optional[Set[str]] = None) -> bool:
        if visited is None:
            visited = set()
        if cls_name in visited:
            return False
        visited.add(cls_name)
        info = self._declared_types.get(cls_name)
        if info is None:
            return True
        for sup in info.get("supertypes", []):
            if sup not in self._declared_types or self._has_external_supertype(sup, visited):
                return True
        return False

    @staticmethod
    def _arity_matches(params: List[Tuple[str, bool]], arg_count: int) -> bool:
        if params and params[-1][1]:  # varargs
            return arg_count >= len(params) - 1
        return arg_count == len(params)

    def _resolve_identifier_type(self, node: Identifier, allow_type_or_pkg: bool = False) -> str:
        name = getattr(node, "name", "")
        if not name:
            return UNKNOWN_TYPE
        if name in ("this", "super"):
            return self._current_type_stack[-1] if self._current_type_stack else UNKNOWN_TYPE

        found = self._lookup_variable_or_field_type(name)
        if found is not None:
            return found

        if name in self._declared_types or name in self.COMMON_EXTERNAL_TYPES or name in self._imported_names:
            return name

        if allow_type_or_pkg and (name[0].isupper() or name in self._package_prefixes):
            return UNKNOWN_TYPE

        self._error(f"Variável '{name}' não foi declarada.", getattr(node, "line", 1))
        return UNKNOWN_TYPE

    # ------------------------------------------------------------------
    # Inferência de tipo e verificação de compatibilidade pública
    # ------------------------------------------------------------------

    def infer_type(self, node: Optional[ASTNode]) -> Optional[str]:
        if node is None:
            return None

        if isinstance(node, Literal):
            kind = getattr(node, "kind", "")
            if kind in ("STRING", "TEXT_BLOCK"):
                return "String"
            if kind == "NULL":
                return "null"
            if kind == "BOOLEAN":
                return "boolean"
            if kind == "CHAR":
                return "char"
            if kind == "LONG":
                return "long"
            if kind == "FLOAT":
                return "float"
            if kind == "DOUBLE":
                return "double"
            if kind in ("NUM", "INT"):
                return "int"
            return UNKNOWN_TYPE

        if isinstance(node, Identifier):
            if node.name in ("this", "super"):
                return self._current_type_stack[-1] if self._current_type_stack else UNKNOWN_TYPE
            found = self._lookup_variable_or_field_type(node.name)
            if found is not None:
                return found
            if node.name in self._declared_types or node.name in self.COMMON_EXTERNAL_TYPES:
                return node.name
            return UNKNOWN_TYPE

        if isinstance(node, Assignment):
            if node.target is None and getattr(node, "name", None):
                return self._lookup_variable_or_field_type(node.name) or UNKNOWN_TYPE
            return self.infer_type(node.target) or self.infer_type(node.expression)

        if isinstance(node, BinaryOp):
            return self._infer_binary_type(node)

        if isinstance(node, UnaryOp):
            if node.op == "!":
                return "boolean"
            op_t = self.infer_type(node.operand)
            if node.op in ("+", "-", "~") and op_t in ("byte", "short", "char"):
                return "int"
            return op_t or UNKNOWN_TYPE

        if isinstance(node, ConditionalExpression):
            t1 = self.infer_type(node.then_expr) or UNKNOWN_TYPE
            t2 = self.infer_type(node.else_expr) or UNKNOWN_TYPE
            if t1 == t2:
                return t1
            if t1 == "null" and t2 not in self.PRIMITIVE_TYPES:
                return t2
            if t2 == "null" and t1 not in self.PRIMITIVE_TYPES:
                return t1
            promoted = self._promote_numeric(t1, t2)
            return promoted or UNKNOWN_TYPE

        if isinstance(node, (InstanceOfExpression, PatternInstanceOfExpression)):
            return "boolean"

        if isinstance(node, CastExpression):
            return self._type_to_str(getattr(node, "target_type", None))

        if isinstance(node, ObjectCreationExpression):
            return self._type_to_str(getattr(node, "type_ref", None) or getattr(node, "method_name", None))

        if isinstance(node, ArrayCreationExpression):
            dims = len(getattr(node, "dimensions", []) or []) or 1
            base = self._type_to_str(getattr(node, "type_ref", None))
            return base if base.endswith("[]") else f"{base}{'[]' * dims}"

        if isinstance(node, ArrayAccess):
            arr_t = self.infer_type(node.array) or UNKNOWN_TYPE
            return arr_t[:-2] if arr_t.endswith("[]") else UNKNOWN_TYPE

        if isinstance(node, MemberAccess):
            target_t = self.infer_type(node.target)
            if target_t and target_t.endswith("[]") and node.member_name == "length":
                return "int"
            if target_t and target_t != UNKNOWN_TYPE:
                base = self._strip_generics_and_array(target_t)
                f_type = self._lookup_field_in_hierarchy(base, node.member_name)
                if f_type is not None:
                    return f_type
            return UNKNOWN_TYPE

        if isinstance(node, MethodCall):
            return self._infer_method_call_type(node)

        if isinstance(node, ClassLiteral):
            return "Class"

        if isinstance(node, (LambdaExpression, MethodReference, SwitchExpression)):
            return UNKNOWN_TYPE

        return UNKNOWN_TYPE

    def _infer_method_call_type(self, node: MethodCall) -> str:
        target = getattr(node, "target", None)
        owner: Optional[str] = None
        if target is None:
            owner = self._current_type_stack[-1] if self._current_type_stack else None
        else:
            t_type = self.infer_type(target)
            if t_type and t_type != UNKNOWN_TYPE:
                owner = self._strip_generics_and_array(t_type)

        if owner == "String" and node.method_name in self.STRING_METHODS:
            return self.STRING_METHODS[node.method_name]
        if owner:
            overloads = self._lookup_method_overloads(owner, node.method_name)
            if overloads:
                argc = len(getattr(node, "arguments", []) or [])
                for params, ret in overloads:
                    if self._arity_matches(params, argc):
                        return ret
                return overloads[0][1]
        return UNKNOWN_TYPE

    def _compute_binary_op_type(self, op: str, left_t: str, right_t: str) -> str:
        if op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||"):
            return "boolean"
        if op == "+" and (left_t == "String" or right_t == "String"):
            return "String"
        promoted = self._promote_numeric(left_t, right_t)
        if promoted is not None:
            return promoted
        if op in ("&", "|", "^") and left_t == "boolean" and right_t == "boolean":
            return "boolean"
        if op in ("<<", ">>", ">>>"):
            u_left = self._unboxed_numeric(left_t)
            if u_left == "long":
                return "long"
            if u_left in self.INTEGRAL_TYPES:
                return "int"
        return UNKNOWN_TYPE

    def _infer_binary_type(self, node: BinaryOp) -> str:
        cached = self._inferred_types.get(id(node))
        if cached is not None:
            return cached
        stack: List[Tuple[BinaryOp, bool]] = [(node, False)]
        while stack:
            cur, visited = stack.pop()
            if id(cur) in self._inferred_types:
                continue
            if not visited:
                stack.append((cur, True))
                for child in (cur.right, cur.left):
                    if isinstance(child, BinaryOp) and id(child) not in self._inferred_types:
                        stack.append((child, False))
                continue
            left_t = (self._inferred_types.get(id(cur.left)) if isinstance(cur.left, BinaryOp) else self.infer_type(cur.left)) or UNKNOWN_TYPE
            right_t = (self._inferred_types.get(id(cur.right)) if isinstance(cur.right, BinaryOp) else self.infer_type(cur.right)) or UNKNOWN_TYPE
            self._inferred_types[id(cur)] = self._compute_binary_op_type(cur.op, left_t, right_t)
        return self._inferred_types.get(id(node), UNKNOWN_TYPE)

    def _unboxed_numeric(self, type_str: Optional[str]) -> Optional[str]:
        if not type_str:
            return None
        clean = self._strip_generics_and_array(type_str) if not type_str.endswith("[]") else ""
        if clean in self.NUMERIC_TYPES:
            return clean
        return self.WRAPPER_TO_PRIMITIVE.get(clean)

    def _promote_numeric(self, left_t: str, right_t: str) -> Optional[str]:
        u_left = self._unboxed_numeric(left_t)
        u_right = self._unboxed_numeric(right_t)
        if u_left is None or u_right is None:
            return None
        for t in self.NUMERIC_PROMOTION_ORDER:
            if u_left == t or u_right == t:
                return t
        return "int"

    def _is_subtype_declared(self, sub_base: str, sup_base: str, visited: Optional[Set[str]] = None) -> bool:
        if sub_base == sup_base:
            return True
        if visited is None:
            visited = set()
        if sub_base in visited:
            return False
        visited.add(sub_base)
        info = self._declared_types.get(sub_base)
        if info is None:
            return False
        for parent in info.get("supertypes", []):
            if self._is_subtype_declared(parent, sup_base, visited):
                return True
        return False

    def is_assignable(self, target_type: str, source_type: str) -> bool:
        """Verifica compatibilidade de atribuição básica (primitivos, widening, boxing, null e tipos locais)."""
        if not target_type or not source_type:
            return True
        if target_type in (UNKNOWN_TYPE, "var") or source_type in (UNKNOWN_TYPE, "var"):
            return True
        if target_type == source_type:
            return True
        if source_type == "void":
            return False
        if target_type == "void":
            return source_type == "void"

        if self._is_active_type_param(target_type) or self._is_active_type_param(source_type):
            return True

        if source_type == "null":
            return target_type not in self.PRIMITIVE_TYPES

        t_dims = self._array_dims(target_type)
        s_dims = self._array_dims(source_type)
        if t_dims > 0 or s_dims > 0:
            if t_dims == 0:
                return self._strip_generics_and_array(target_type) in ("Object", "Cloneable", "Serializable")
            if t_dims != s_dims:
                return False
            t_elem = self._strip_generics_and_array(target_type)
            s_elem = self._strip_generics_and_array(source_type)
            if t_elem in self.PRIMITIVE_TYPES or s_elem in self.PRIMITIVE_TYPES:
                return t_elem == s_elem
            return self.is_assignable(t_elem, s_elem)

        t_base = self._strip_generics_and_array(target_type)
        s_base = self._strip_generics_and_array(source_type)
        if t_base == s_base:
            return True
        if t_base == "Object":
            return True

        t_prim = t_base in self.PRIMITIVE_TYPES
        s_prim = s_base in self.PRIMITIVE_TYPES

        if t_prim and s_prim:
            return t_base in self.WIDENING_PRIMITIVE_TARGETS.get(s_base, set())

        if t_prim and not s_prim:
            unboxed = self.WRAPPER_TO_PRIMITIVE.get(s_base)
            return unboxed is not None and (unboxed == t_base or t_base in self.WIDENING_PRIMITIVE_TARGETS.get(unboxed, set()))

        if not t_prim and s_prim:
            boxed = self.PRIMITIVE_TO_WRAPPER.get(s_base)
            return t_base in (boxed, "Number", "Comparable", "Serializable") if s_base in self.NUMERIC_TYPES else t_base in (boxed, "Comparable", "Serializable")

        if self._is_subtype_declared(s_base, t_base):
            return True

        # Se ambos são tipos fechados/conhecidos localmente (ou String) sem relação, rejeita incompatibilidade clara
        known_closed = set(self._declared_types.keys()) | {"String"}
        if t_base in known_closed and s_base in known_closed:
            return False

        return True

    def check_assignment_type(
        self,
        target_type: str,
        expression: Optional[ASTNode],
        target_name: str,
        line: int,
        operator: str = "=",
    ) -> None:
        """Verifica compatibilidade entre o tipo alvo e a expressão em atribuições simples e compostas."""
        if expression is None:
            return

        if operator == "+=" and target_type == "String":
            return

        if operator != "=" and target_type == "String":
            self._error(
                f"Operação aritmética '{operator}' inválida: tipo 'String' não é suportado em operações aritméticas.",
                line,
            )
            return

        expr_type = self.infer_type(expression) or UNKNOWN_TYPE

        if operator != "=":
            if target_type in (UNKNOWN_TYPE, "var", "Object") or expr_type in (UNKNOWN_TYPE, "var", "Object"):
                return
            if operator in ("<<=", ">>=", ">>>="):
                u_t = self._unboxed_numeric(target_type)
                u_e = self._unboxed_numeric(expr_type)
                if u_t not in self.INTEGRAL_TYPES or u_e not in self.INTEGRAL_TYPES:
                    self._error(
                        f"Atribuição composta '{operator}' exige operandos integrais (encontrado '{target_type}' e '{expr_type}').",
                        line,
                    )
            elif operator in ("&=", "|=", "^="):
                both_bool = target_type in ("boolean", "Boolean") and expr_type in ("boolean", "Boolean")
                both_int = self._unboxed_numeric(target_type) in self.INTEGRAL_TYPES and self._unboxed_numeric(expr_type) in self.INTEGRAL_TYPES
                if not both_bool and not both_int:
                    self._error(
                        f"Atribuição composta '{operator}' exige operandos compatíveis (encontrado '{target_type}' e '{expr_type}').",
                        line,
                    )
            else:
                if self._unboxed_numeric(target_type) is None or self._unboxed_numeric(expr_type) is None:
                    self._error(
                        f"Atribuição aritmética composta '{operator}' inválida entre '{target_type}' e '{expr_type}'.",
                        line,
                    )
            return

        if not self.is_assignable(target_type, expr_type):
            if target_type in ("byte", "short", "char") and isinstance(expression, Literal) and expr_type == "int":
                if self._int_literal_fits(expression.value, target_type):
                    return
            self._error(
                f"Incompatibilidade de tipos: não é possível atribuir {expr_type} a '{target_name}' do tipo {target_type}.",
                line,
            )

    @staticmethod
    def _int_literal_fits(raw_value: Any, target_type: str) -> bool:
        try:
            clean = str(raw_value).replace("_", "")
            val = int(clean, 0)
        except (ValueError, TypeError):
            return False
        if target_type == "byte":
            return -128 <= val <= 127
        if target_type == "short":
            return -32768 <= val <= 32767
        if target_type == "char":
            return 0 <= val <= 65535
        return False
