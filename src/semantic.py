"""
Módulo do Analisador Semântico do Compilador Java (AV3).
Responsável pela validação de escopos, verificação de variáveis e membros declarados,
duplicidade de identificadores e compatibilidade básica de tipos.
Evita falsos erros para membros qualificados externos como System.out.println(...).
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from .ast_nodes import (
    ASTNode, CompilationUnit, PackageDeclaration, ClassDeclaration, InterfaceDeclaration,
    InterfaceConstantDeclaration, InterfaceMethodDeclaration,
    EnumDeclaration, EnumConstant, EnumConstantBody,
    RecordDeclaration, RecordComponent,
    NormalCanonicalConstructor, CompactConstructorDeclaration, NonCanonicalRecordConstructor,
    FieldDeclaration, MethodDeclaration, ConstructorDeclaration,
    Block, ReturnStatement, Declaration, LocalVariableDeclaration, Assignment,
    BinaryOp, UnaryOp, MethodCall, Literal, Identifier, ExpressionStatement,
    EmptyStatement, IfStatement, WhileStatement, DoWhileStatement,
    ForStatement, EnhancedForStatement, SwitchStatement, SwitchCase,
    BreakStatement, ContinueStatement, ThrowStatement, AssertStatement,
    TryStatement, CatchClause, SynchronizedStatement, ConditionalExpression,
    LabeledStatement, StatementExpressionList, SwitchLabel, CaseConstantList,
    CaseLabel, DefaultLabel, SwitchBlockStatementGroup, SwitchRule, SwitchBlock,
    SwitchExpression, YieldStatement, CatchType, Resource, ResourceSpecification,
    MemberAccess, ArrayAccess, ClassLiteral,
    ObjectCreationExpression, ArrayInitializer, ArrayCreationExpression,
    CastExpression, InstanceOfExpression, PatternInstanceOfExpression,
    LambdaExpression, MethodReference,
    ModuleDeclaration, InstanceInitializer, StaticInitializer, ConstructorBody,
    SuperclassConstructorInvocation, AlternateConstructorInvocation,
    TypeReference, WildcardType, Annotation, MarkerAnnotation,
    SingleElementAnnotation, NormalAnnotation, ElementValue, ElementValueList,
    ElementValueArrayInitializer, ElementValuePair, ElementValuePairList,
    AnnotationDefaultValue, AnnotationInterfaceElementDeclaration,
    AnnotationInterfaceBody, AnnotationInterfaceDeclaration,
    ComponentPattern, Pattern, PatternVariable, TypePattern,
    ComponentPatternList, RecordPattern, MatchAllPattern, Guard,
    PatternCaseLabel
)


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
    Analisador semântico para Java (Fases A, B e C e Etapas S1-S4).
    Gerencia escopos hierárquicos e valida a consistência de tipos e símbolos,
    escopos locais em blocos/laços/métodos e previne falsos positivos para símbolos externos.
    """
    FORBIDDEN_RECORD_COMPONENTS = frozenset({
        "clone", "finalize", "getClass", "hashCode",
        "notify", "notifyAll", "toString", "wait",
    })
    FORBIDDEN_ANNOTATION_ELEMENTS = frozenset({
        "clone", "equals", "finalize", "getClass", "hashCode",
        "notify", "notifyAll", "toString", "wait", "annotationType",
    })
    PRIMITIVE_TYPES = frozenset({
        "byte", "short", "int", "long", "float", "double", "boolean", "char",
    })
    NUMERIC_PRIMITIVE_TYPES = frozenset({
        "byte", "short", "char", "int", "long", "float", "double",
    })
    WRAPPER_TO_PRIMITIVE = {
        "Byte": "byte",
        "Short": "short",
        "Character": "char",
        "Integer": "int",
        "Long": "long",
        "Float": "float",
        "Double": "double",
        "Boolean": "boolean",
    }
    BUILTIN_NON_REPEATABLE_ANNOTATIONS = frozenset({
        "Override", "Deprecated", "SuppressWarnings", "Target", "Retention",
        "Documented", "Inherited", "FunctionalInterface", "SafeVarargs", "Repeatable",
    })
    BUILTIN_ANNOTATION_TYPES = BUILTIN_NON_REPEATABLE_ANNOTATIONS | frozenset({
        "Native", "Serial",
    })
    KNOWN_ENUM_TYPES = frozenset({
        "ElementType", "RetentionPolicy",
        "java.lang.annotation.ElementType", "java.lang.annotation.RetentionPolicy",
    })
    DISALLOWED_ANNOTATION_RETURN_TYPES = frozenset({
        "Object", "java.lang.Object",
        "Integer", "Long", "Double", "Float", "Boolean", "Character", "Byte", "Short", "Number",
        "List", "Map", "Set", "Collection", "Optional", "Date", "BigDecimal", "CharSequence",
        "Throwable", "Exception", "Error", "StringBuilder", "Record", "Enum",
    })
    RETENTION_RANK = {"SOURCE": 0, "CLASS": 1, "RUNTIME": 2}
    ACCESS_RANK = {"private": 0, "package": 1, "protected": 2, "public": 3}
    KNOWN_EXCEPTION_PARENTS = {
        "Exception": "Throwable",
        "RuntimeException": "Exception",
        "Error": "Throwable",
        "IOException": "Exception",
        "FileNotFoundException": "IOException",
        "EOFException": "IOException",
        "SQLException": "Exception",
        "IllegalArgumentException": "RuntimeException",
        "IllegalStateException": "RuntimeException",
        "NullPointerException": "RuntimeException",
        "IndexOutOfBoundsException": "RuntimeException",
        "ArrayIndexOutOfBoundsException": "IndexOutOfBoundsException",
        "NumberFormatException": "IllegalArgumentException",
        "ArithmeticException": "RuntimeException",
        "ClassCastException": "RuntimeException",
        "UnsupportedOperationException": "RuntimeException",
        "ClassNotFoundException": "ReflectiveOperationException",
        "ReflectiveOperationException": "Exception",
        "InterruptedException": "Exception",
    }
    BUILTIN_TYPE_SUPERTYPES = {
        "Object": [],
        "String": ["CharSequence", "Comparable", "Serializable", "Object"],
        "StringBuilder": ["CharSequence", "Appendable", "Serializable", "Object"],
        "StringBuffer": ["CharSequence", "Appendable", "Serializable", "Object"],
        "CharSequence": ["Object"],
        "Appendable": ["Object"],
        "Number": ["Serializable", "Object"],
        "Integer": ["Number", "Comparable", "Serializable", "Object"],
        "Long": ["Number", "Comparable", "Serializable", "Object"],
        "Double": ["Number", "Comparable", "Serializable", "Object"],
        "Float": ["Number", "Comparable", "Serializable", "Object"],
        "Byte": ["Number", "Comparable", "Serializable", "Object"],
        "Short": ["Number", "Comparable", "Serializable", "Object"],
        "Boolean": ["Comparable", "Serializable", "Object"],
        "Character": ["Comparable", "Serializable", "Object"],
        "Void": ["Object"],
        "Iterable": ["Object"],
        "Collection": ["Iterable", "Object"],
        "List": ["Collection", "Iterable", "Object"],
        "ArrayList": ["List", "Collection", "Iterable", "Serializable", "Cloneable", "Object"],
        "LinkedList": ["List", "Collection", "Iterable", "Serializable", "Cloneable", "Object"],
        "Set": ["Collection", "Iterable", "Object"],
        "HashSet": ["Set", "Collection", "Iterable", "Serializable", "Cloneable", "Object"],
        "Map": ["Object"],
        "HashMap": ["Map", "Serializable", "Cloneable", "Object"],
        "Optional": ["Object"],
        "Record": ["Object"],
        "Enum": ["Comparable", "Serializable", "Object"],
        "Comparable": ["Object"],
        "Serializable": ["Object"],
        "Cloneable": ["Object"],
        "Runnable": ["Object"],
        "Throwable": ["Serializable", "Object"],
    }
    BUILTIN_FINAL_TYPES = frozenset({
        "String", "Integer", "Long", "Double", "Float", "Byte", "Short", "Boolean", "Character", "Void",
    })
    BUILTIN_CLASS_TYPES = frozenset({
        "Object", "String", "StringBuilder", "StringBuffer", "Number",
        "Integer", "Long", "Double", "Float", "Byte", "Short", "Boolean",
        "Character", "Void", "ArrayList", "LinkedList", "HashSet", "HashMap",
        "Optional", "Record", "Enum", "Throwable", "Exception",
        "RuntimeException", "Error",
    })

    def __init__(self, symbol_table, enable_preview_primitive_patterns: bool = False):
        self.symbols = symbol_table
        self.enable_preview_primitive_patterns = enable_preview_primitive_patterns
        self.errors = []
        self.unresolved_checks: List[str] = []
        self._in_early_construction_context = False
        self._in_compact_constructor = False
        self._compact_component_names: Set[str] = set()
        self._declared_types: Dict[str, Tuple[str, ASTNode]] = {}
        self._annotation_interfaces: Dict[str, AnnotationInterfaceDeclaration] = {}
        self._enums: Dict[str, EnumDeclaration] = {}
        self._static_imports: Set[str] = set()
        self._has_wildcard_static_import: bool = False
        self._validated_ann_targets: Set[int] = set()
        self._loop_depth: int = 0
        self._switch_depth: int = 0
        self._switch_expr_depth: int = 0
        self._callable_kind: str = "top_level"
        self._current_return_type: Optional[str] = None
        self._active_labels: Dict[str, Tuple[bool, int]] = {}
        self._local_var_scopes: List[Dict[str, Dict[str, Any]]] = []
        self._active_pattern_scopes: List[Dict[str, Dict[str, Any]]] = []
        self._local_type_scopes: List[Dict[str, int]] = []
        self._local_declared_type_scopes: List[Dict[str, Tuple[str, ASTNode]]] = []
        self._enclosing_type_names: List[str] = []
        self._current_type_is_local: bool = False

    def _save_exec_context(self) -> Dict[str, Any]:
        return {
            "early": self._in_early_construction_context,
            "compact": self._in_compact_constructor,
            "comp_names": self._compact_component_names,
            "loop": self._loop_depth,
            "switch": self._switch_depth,
            "switch_expr": self._switch_expr_depth,
            "kind": self._callable_kind,
            "ret": self._current_return_type,
            "labels": self._active_labels,
            "var_scopes": self._local_var_scopes,
            "pat_scopes": self._active_pattern_scopes,
            "type_scopes": self._local_type_scopes,
            "decl_type_scopes": self._local_declared_type_scopes,
            "local_type_flag": self._current_type_is_local,
        }

    def _restore_exec_context(self, saved: Dict[str, Any]):
        self._in_early_construction_context = saved["early"]
        self._in_compact_constructor = saved["compact"]
        self._compact_component_names = saved["comp_names"]
        self._loop_depth = saved["loop"]
        self._switch_depth = saved["switch"]
        self._switch_expr_depth = saved["switch_expr"]
        self._callable_kind = saved["kind"]
        self._current_return_type = saved["ret"]
        self._active_labels = saved["labels"]
        self._local_var_scopes = saved["var_scopes"]
        self._active_pattern_scopes = saved["pat_scopes"]
        self._local_type_scopes = saved["type_scopes"]
        self._local_declared_type_scopes = saved["decl_type_scopes"]
        self._current_type_is_local = saved["local_type_flag"]

    def _enter_exec_context(
        self,
        kind: str,
        return_type: Optional[str] = None,
        is_compact: bool = False,
        compact_names: Optional[Set[str]] = None,
        share_locals: bool = False,
        switch_expr_depth: int = 0,
    ) -> Dict[str, Any]:
        saved = self._save_exec_context()
        self._in_early_construction_context = False
        self._in_compact_constructor = is_compact
        self._compact_component_names = compact_names if compact_names is not None else set()
        self._loop_depth = 0
        self._switch_depth = 0
        self._switch_expr_depth = switch_expr_depth
        self._callable_kind = kind
        self._current_return_type = return_type
        self._active_labels = {}
        if not share_locals:
            self._local_var_scopes = [{}] if kind in ("method", "constructor", "initializer") else []
            if not self._current_type_is_local:
                self._active_pattern_scopes = [{}] if kind in ("method", "constructor", "initializer") else []
                self._local_declared_type_scopes = [{}] if kind in ("method", "constructor", "initializer") else []
            else:
                self._active_pattern_scopes = list(self._active_pattern_scopes) + (
                    [{}] if kind in ("method", "constructor", "initializer") else []
                )
                self._local_declared_type_scopes = list(self._local_declared_type_scopes) + (
                    [{}] if kind in ("method", "constructor", "initializer") else []
                )
            self._local_type_scopes = [{}] if kind in ("method", "constructor", "initializer") else []
        return saved

    def analyze(self, program: ASTNode) -> List[SemanticError]:
        """Executa a análise semântica sobre a árvore sintática."""
        self.errors = []
        self.unresolved_checks = []
        self._in_early_construction_context = False
        self._in_compact_constructor = False
        self._compact_component_names = set()
        self._declared_types = {}
        self._annotation_interfaces = {}
        self._enums = {}
        self._static_imports = set()
        self._has_wildcard_static_import = False
        self._validated_ann_targets = set()
        self._loop_depth = 0
        self._switch_depth = 0
        self._switch_expr_depth = 0
        self._callable_kind = "top_level"
        self._current_return_type = None
        self._active_labels = {}
        self._local_var_scopes = []
        self._active_pattern_scopes = []
        self._local_type_scopes = []
        self._local_declared_type_scopes = []
        self._enclosing_type_names = []
        self._current_type_is_local = False
        if not program:
            return self.errors

        # 1. Pré-indexa tipos e imports estáticos e analisa Unidade de Compilação completa
        if isinstance(program, CompilationUnit):
            self._preindex_compilation_unit(program)
            if program.package is not None:
                pkg_annos = [
                    m for m in getattr(program.package, "modifiers", [])
                    if isinstance(m, Annotation)
                ]
                if not pkg_annos and getattr(program.package, "annotations", None):
                    pkg_annos = list(program.package.annotations)
                self._analyze_annotations(pkg_annos, valid_targets={"PACKAGE"})
            for type_decl in program.type_declarations:
                self._analyze_type_declaration(type_decl, is_nested=False, is_local=False)

        # 2. Analisa comandos didáticos de nível superior ou fragmentos
        statements = getattr(program, "statements", [])
        for stmt in statements:
            self.analyze_statement(stmt)

        return self.errors

    def _preindex_compilation_unit(self, unit: CompilationUnit):
        """Pré-indexa classes, interfaces, enums, records e @interfaces declarados na unidade."""
        for imp in getattr(unit, "imports", []):
            if getattr(imp, "is_static", False):
                if getattr(imp, "is_wildcard", False):
                    self._has_wildcard_static_import = True
                elif getattr(imp, "name", None):
                    self._static_imports.add(imp.name.split(".")[-1])

        def visit_type(node: ASTNode):
            if isinstance(node, AnnotationInterfaceDeclaration):
                self._declared_types[node.name] = ("annotation_interface", node)
                self._annotation_interfaces[node.name] = node
                for m in node.members:
                    visit_type(m)
            elif isinstance(node, EnumDeclaration):
                self._declared_types[node.name] = ("enum", node)
                self._enums[node.name] = node
                for m in node.members:
                    visit_type(m)
                for c in node.constants:
                    if isinstance(c.body, EnumConstantBody):
                        for cm in c.body.members:
                            visit_type(cm)
            elif isinstance(node, RecordDeclaration):
                self._declared_types[node.name] = ("record", node)
                for m in node.members:
                    visit_type(m)
            elif isinstance(node, InterfaceDeclaration):
                self._declared_types[node.name] = ("interface", node)
                for m in node.members:
                    visit_type(m)
            elif isinstance(node, ClassDeclaration):
                self._declared_types[node.name] = ("class", node)
                for m in node.members:
                    visit_type(m)

        for tdecl in getattr(unit, "type_declarations", []):
            visit_type(tdecl)

    def _index_local_type_decl(self, node: ASTNode):
        """Registra declarações de tipos locais (inclusive aninhados e enums locais) no escopo de bloco atual."""
        if not self._local_declared_type_scopes:
            self._local_declared_type_scopes.append({})
        target = self._local_declared_type_scopes[-1]

        def visit_local(n: ASTNode):
            if isinstance(n, AnnotationInterfaceDeclaration):
                target.setdefault(n.name, ("annotation_interface", n))
                for m in n.members:
                    visit_local(m)
            elif isinstance(n, EnumDeclaration):
                target.setdefault(n.name, ("enum", n))
                self._enums.setdefault(n.name, n)
                for m in n.members:
                    visit_local(m)
                for c in n.constants:
                    if isinstance(c.body, EnumConstantBody):
                        for cm in c.body.members:
                            visit_local(cm)
            elif isinstance(n, RecordDeclaration):
                target.setdefault(n.name, ("record", n))
                for m in n.members:
                    visit_local(m)
            elif isinstance(n, InterfaceDeclaration):
                target.setdefault(n.name, ("interface", n))
                for m in n.members:
                    visit_local(m)
            elif isinstance(n, ClassDeclaration):
                target.setdefault(n.name, ("class", n))
                for m in n.members:
                    visit_local(m)

        visit_local(node)

    def _analyze_type_declaration(self, type_decl: ASTNode, is_nested: bool = False, is_local: bool = False):
        """Despacha a análise semântica para declarações de tipo (class, interface, enum, record, @interface, module)."""
        tname = getattr(type_decl, "name", None)
        if tname and not isinstance(type_decl, ModuleDeclaration):
            self._enclosing_type_names.append(tname)
        saved_is_local = self._current_type_is_local
        self._current_type_is_local = is_local
        if is_local:
            self._index_local_type_decl(type_decl)
        try:
            if isinstance(type_decl, ClassDeclaration):
                self.analyze_class(type_decl, is_nested=is_nested, is_local=is_local)
            elif isinstance(type_decl, InterfaceDeclaration):
                self.analyze_interface(type_decl, is_nested=is_nested, is_local=is_local)
            elif isinstance(type_decl, EnumDeclaration):
                self.analyze_enum(type_decl, is_nested=is_nested, is_local=is_local)
            elif isinstance(type_decl, RecordDeclaration):
                self.analyze_record(type_decl, is_nested=is_nested, is_local=is_local)
            elif isinstance(type_decl, AnnotationInterfaceDeclaration):
                self.analyze_annotation_interface(type_decl, is_nested=is_nested, is_local=is_local)
            elif isinstance(type_decl, ModuleDeclaration):
                self._analyze_annotations(getattr(type_decl, "annotations", []), valid_targets={"MODULE"})
                self.symbols.declare(type_decl.name, "module", type_decl.line, category="modulo")
        finally:
            self._current_type_is_local = saved_is_local
            if tname and not isinstance(type_decl, ModuleDeclaration):
                self._enclosing_type_names.pop()

    def _effective_access(self, modifiers: List[str]) -> int:
        """Retorna o nível de acesso efetivo segundo a JLS."""
        for m in modifiers:
            if m in self.ACCESS_RANK:
                return self.ACCESS_RANK[m]
        return self.ACCESS_RANK["package"]

    def _check_conflicting_access_modifiers(self, modifiers: List[str], context_label: str, line: int):
        """Verifica se há múltiplos modificadores de acesso incompatíveis na mesma declaração."""
        access_mods = [m for m in modifiers if m in ("public", "protected", "private")]
        if len(access_mods) > 1:
            self.errors.append(
                SemanticError(f"Modificadores de acesso conflitantes ({', '.join(access_mods)}) em {context_label}.", line)
            )

    def _validate_type_modifiers(
        self,
        modifiers: List[str],
        kind: str,
        name: str,
        line: int,
        is_nested: bool = False,
        is_local: bool = False,
    ):
        """Valida modificadores permitidos para interfaces, enums e records (JLS §8.9, §8.10, §9.1)."""
        self._check_conflicting_access_modifiers(modifiers, f"{kind} '{name}'", line)
        mod_set = set(modifiers)

        if is_local:
            for acc in ("public", "protected", "private"):
                if acc in mod_set:
                    self.errors.append(
                        SemanticError(f"Modificador de acesso '{acc}' não é permitido em {kind} local '{name}'.", line)
                    )
            if "static" in mod_set:
                self.errors.append(
                    SemanticError(
                        f"Modificador 'static' explícito não é permitido em {kind} local '{name}' (JLS §14.3).",
                        line,
                    )
                )
            for forbidden_local in ("sealed", "non-sealed"):
                if forbidden_local in mod_set:
                    self.errors.append(
                        SemanticError(
                            f"Modificador '{forbidden_local}' não é permitido em {kind} local '{name}' (JLS §14.3).",
                            line,
                        )
                    )
        elif not is_nested:
            for m in ("private", "protected"):
                if m in mod_set:
                    self.errors.append(
                        SemanticError(f"Modificador '{m}' não é permitido em {kind} de nível superior '{name}'.", line)
                    )
            if "static" in mod_set:
                self.errors.append(
                    SemanticError(f"Modificador 'static' não é permitido em {kind} de nível superior '{name}'.", line)
                )

        if kind == "interface":
            if "final" in mod_set:
                self.errors.append(SemanticError(f"A interface '{name}' não pode ser declarada como 'final' (JLS §9.1.1).", line))
            if "sealed" in mod_set and "non-sealed" in mod_set:
                self.errors.append(SemanticError(f"A interface '{name}' não pode combinar 'sealed' e 'non-sealed'.", line))
        elif kind == "enum":
            for bad in ("abstract", "final", "sealed", "non-sealed"):
                if bad in mod_set:
                    self.errors.append(SemanticError(f"Enum '{name}' não pode possuir modificador '{bad}' (JLS §8.9).", line))
        elif kind == "record":
            for bad in ("abstract", "sealed", "non-sealed"):
                if bad in mod_set:
                    self.errors.append(SemanticError(f"Record '{name}' não pode possuir modificador '{bad}' (JLS §8.10).", line))
        elif kind == "annotation_interface":
            for bad in ("final", "sealed", "non-sealed"):
                if bad in mod_set:
                    self.errors.append(
                        SemanticError(f"Annotation interface '@{name}' não pode possuir modificador '{bad}' (JLS §9.6).", line)
                    )

    def _declare_type_symbol(self, name: str, type_label: str, category: str, dup_label: str, line: int):
        """Declara símbolo de tipo no escopo atual reportando duplicidade no mesmo escopo."""
        prev = self.symbols.lookup(name)
        if not self.symbols.declare(name, type_label, line, category=category):
            prev_line = f" (declarada na linha {prev['line']})" if prev and "line" in prev else ""
            self.errors.append(SemanticError(f"{dup_label} '{name}' declarada novamente{prev_line}.", line))

    def _analyze_field_declaration(
        self,
        member: FieldDeclaration,
        container_label: str = "classe",
        is_interface_constant: bool = False,
    ):
        """Analisa declarações de campo ou constantes de interface, registrando símbolos e validando '_' e inicializadores."""
        self._analyze_annotations(
            getattr(member, "annotations", []),
            valid_targets={"FIELD"},
            adjacent_type_ref=getattr(member, "type_ref", None),
        )
        self._check_type_ref_annotations(getattr(member, "type_ref", None))

        decls = member.declarators if hasattr(member, "declarators") and member.declarators else []
        if getattr(member, "type_ref", None) is not None and getattr(member.type_ref, "name", None) == "var":
            self.errors.append(
                SemanticError("'var' não é permitido em declarações de campo (JLS §8.3 / §14.4).", member.line)
            )
        is_static = True if is_interface_constant else ("static" in member.modifiers)
        is_final = True if is_interface_constant else ("final" in member.modifiers)
        category = "constante_interface" if is_interface_constant else "campo"
        dup_noun = "Constante" if is_interface_constant else "Campo"

        if not decls and hasattr(member, "name"):
            if member.name == "_":
                self.errors.append(
                    SemanticError("O identificador '_' não pode ser utilizado como nome de campo (JLS §8.3 / JEP 456).", member.line)
                )
            else:
                if is_interface_constant and member.initializer is None:
                    self.errors.append(
                        SemanticError(f"Constante de interface '{member.name}' deve possuir inicializador (JLS §9.3).", member.line)
                    )
                eff_type = getattr(member, "effective_type", member.type_ref.full_name)
                is_const = is_final and member.initializer is not None and self._is_compile_time_constant_expr(member.initializer)
                if not self.symbols.declare(
                    member.name, eff_type, member.line, category=category,
                    is_static=is_static, is_final=is_final, is_compile_constant=is_const,
                ):
                    self.errors.append(SemanticError(f"{dup_noun} '{member.name}' declarado novamente na {container_label}.", member.line))
            if member.initializer is not None:
                self.check_expression(member.initializer)
            return

        for decl in decls:
            if hasattr(decl, "id") and getattr(decl.id, "dims_annotations", None):
                for da in decl.id.dims_annotations:
                    self._analyze_annotations(da, valid_targets={"TYPE_USE"})
            if decl.name == "_" or (hasattr(decl, "id") and getattr(decl.id, "is_unnamed", False)):
                self.errors.append(
                    SemanticError("O identificador '_' não pode ser utilizado como nome de campo (JLS §8.3 / JEP 456).", decl.line)
                )
                if decl.initializer is not None:
                    self.check_expression(decl.initializer)
                continue

            if is_interface_constant and decl.initializer is None:
                self.errors.append(
                    SemanticError(f"Constante de interface '{decl.name}' deve possuir inicializador (JLS §9.3).", decl.line)
                )

            eff_type = decl.effective_type
            is_const = is_final and decl.initializer is not None and self._is_compile_time_constant_expr(decl.initializer)
            if not self.symbols.declare(
                decl.name, eff_type, decl.line, category=category,
                is_static=is_static, is_final=is_final, is_compile_constant=is_const,
            ):
                self.errors.append(SemanticError(f"{dup_noun} '{decl.name}' declarado novamente na {container_label}.", decl.line))
            if decl.initializer is not None:
                self.check_expression(decl.initializer)

    def _analyze_method_member(self, member: MethodDeclaration):
        """Registra um método e analisa annotations, type parameters, parâmetros e corpo em escopo isolado."""
        self._analyze_annotations(
            getattr(member, "annotations", []),
            valid_targets={"METHOD"},
            adjacent_type_ref=getattr(member, "return_type", None),
        )
        self._check_type_parameters_annotations(getattr(member, "type_parameters", []))
        self._check_type_ref_annotations(getattr(member, "return_type", None))
        for da in getattr(member, "dims_annotations", []):
            self._analyze_annotations(da, valid_targets={"TYPE_USE"})
        for tt in getattr(member, "throws_types", []):
            self._check_type_ref_annotations(tt)
        recv = getattr(member, "receiver_parameter", None)
        if recv is not None:
            self._analyze_annotations(getattr(recv, "annotations", []), valid_targets={"TYPE_USE"})
            self._check_type_ref_annotations(getattr(recv, "type_ref", None))

        eff_ret_type = member.effective_return_type
        if getattr(member, "return_type", None) is not None and getattr(member.return_type, "name", None) == "var":
            self.errors.append(
                SemanticError("'var' não é permitido como tipo de retorno de método (JLS §8.4 / §14.4).", member.line)
            )
        is_static = "static" in member.modifiers
        self.symbols.declare(member.name, eff_ret_type, member.line, category="metodo", is_static=is_static)
        self.symbols.enter_scope()
        saved_ctx = self._enter_exec_context("method", return_type=eff_ret_type)
        try:
            for p in member.parameters:
                self._analyze_annotations(
                    getattr(p, "annotations", []),
                    valid_targets={"PARAMETER"},
                    adjacent_type_ref=getattr(p, "type_ref", None),
                )
                self._check_type_ref_annotations(getattr(p, "type_ref", None))
                if getattr(p, "type_ref", None) is not None and getattr(p.type_ref, "name", None) == "var":
                    self.errors.append(
                        SemanticError(
                            f"'var' não é permitido em parâmetro formal '{p.name}' (JLS §8.4.1 / §14.4).",
                            getattr(p, "line", member.line),
                        )
                    )
                for ea in getattr(p, "ellipsis_annotations", []):
                    self._analyze_annotations([ea], valid_targets={"TYPE_USE"})
                if p.name != "_":
                    p_type = getattr(p.type_ref, "full_name", p.type_ref.name) if hasattr(p, "type_ref") else "Object"
                    self._register_local_var(
                        p.name,
                        p_type,
                        p.line,
                        is_final=("final" in getattr(p, "modifiers", [])),
                        has_initializer=True,
                        category="parametro",
                    )
            if member.body:
                self.analyze_block(member.body)
        finally:
            self._restore_exec_context(saved_ctx)
        self.symbols.exit_scope()

    def _analyze_constructor_member(
        self,
        member: ConstructorDeclaration,
        expected_name: Optional[str] = None,
        is_enum: bool = False,
        is_compact: bool = False,
        derived_components: Optional[List[RecordComponent]] = None,
    ):
        """Analisa construtor de classe, enum ou record, gerenciando early construction context e regras compactas."""
        if expected_name is not None and member.name != expected_name:
            self.errors.append(
                SemanticError(f"Nome do construtor '{member.name}' não corresponde ao tipo declarador '{expected_name}'.", member.line)
            )

        if is_enum:
            for acc in ("public", "protected"):
                if acc in member.modifiers:
                    self.errors.append(
                        SemanticError(
                            f"Construtor de enum '{expected_name or member.name}' não pode possuir modificador '{acc}'; construtores de enum são implicitamente 'private' (JLS §8.9.2).",
                            member.line,
                        )
                    )

        self._analyze_annotations(getattr(member, "annotations", []), valid_targets={"CONSTRUCTOR"})
        self._check_type_parameters_annotations(getattr(member, "type_parameters", []))
        for tt in getattr(member, "throws_types", []):
            self._check_type_ref_annotations(tt)
        recv = getattr(member, "receiver_parameter", None)
        if recv is not None:
            self._analyze_annotations(getattr(recv, "annotations", []), valid_targets={"TYPE_USE"})
            self._check_type_ref_annotations(getattr(recv, "type_ref", None))

        self.symbols.declare(member.name, member.name, member.line, category="construtor")
        self.symbols.enter_scope()

        derived_names: Set[str] = set()
        if is_compact and derived_components is not None:
            for comp in derived_components:
                if comp.name != "_":
                    derived_names.add(comp.name)

        saved_ctx = self._enter_exec_context(
            "constructor",
            return_type=None,
            is_compact=is_compact,
            compact_names=derived_names if is_compact else set(),
        )
        try:
            if is_compact and derived_components is not None:
                for comp in derived_components:
                    if comp.name != "_":
                        self._register_local_var(
                            comp.name,
                            comp.effective_type,
                            comp.line,
                            has_initializer=True,
                            category="parametro",
                        )
            else:
                for p in member.parameters:
                    self._analyze_annotations(
                        getattr(p, "annotations", []),
                        valid_targets={"PARAMETER"},
                        adjacent_type_ref=getattr(p, "type_ref", None),
                    )
                    self._check_type_ref_annotations(getattr(p, "type_ref", None))
                    if getattr(p, "type_ref", None) is not None and getattr(p.type_ref, "name", None) == "var":
                        self.errors.append(
                            SemanticError(
                                f"'var' não é permitido em parâmetro de construtor '{p.name}' (JLS §8.8.1 / §14.4).",
                                getattr(p, "line", member.line),
                            )
                        )
                    for ea in getattr(p, "ellipsis_annotations", []):
                        self._analyze_annotations([ea], valid_targets={"TYPE_USE"})
                    if p.name != "_":
                        p_type = getattr(p.type_ref, "full_name", p.type_ref.name) if hasattr(p, "type_ref") else "Object"
                        self._register_local_var(
                            p.name,
                            p_type,
                            p.line,
                            is_final=("final" in getattr(p, "modifiers", [])),
                            has_initializer=True,
                            category="parametro",
                        )

            if member.body:
                if isinstance(member.body, ConstructorBody):
                    inv = member.body.constructor_invocation
                    if is_enum and isinstance(inv, SuperclassConstructorInvocation):
                        self.errors.append(
                            SemanticError(f"Construtor de enum '{expected_name or member.name}' não pode conter invocação explícita 'super(...)' (JLS §8.9.2).", inv.line)
                        )
                    if inv is not None:
                        # 1. Prólogo (Early Construction Context - JLS §8.8.7 / JEP 513)
                        self._in_early_construction_context = True
                        try:
                            for s in member.body.prologue:
                                self.analyze_statement(s)
                        finally:
                            self._in_early_construction_context = False

                        # 2. Invocação explícita de construtor (argumentos no Early Construction Context)
                        self._in_early_construction_context = True
                        try:
                            for arg in inv.arguments:
                                self.check_expression(arg)
                        finally:
                            self._in_early_construction_context = False

                        # 3. Epílogo (contexto normal com superclasse já inicializada)
                        for s in member.body.epilogue:
                            self.analyze_statement(s)
                    else:
                        for s in member.body.prologue:
                            self.analyze_statement(s)
                        for s in member.body.epilogue:
                            self.analyze_statement(s)
                elif isinstance(member.body, Block):
                    self.analyze_block(member.body)
        finally:
            self._restore_exec_context(saved_ctx)

        self.symbols.exit_scope()

    def _analyze_class_like_members(
        self,
        members: List[ASTNode],
        container_label: str,
        enclosing_name: str,
        allow_constructor: bool = True,
        is_enum: bool = False,
    ):
        """Analisa membros comuns de classes, enums e corpos de constantes de enum."""
        for member in members:
            if isinstance(member, EmptyStatement):
                continue
            elif isinstance(member, FieldDeclaration):
                self._analyze_field_declaration(member, container_label=container_label)
            elif isinstance(member, MethodDeclaration):
                self._analyze_method_member(member)
            elif isinstance(member, ConstructorDeclaration):
                if not allow_constructor:
                    self.errors.append(
                        SemanticError(f"Corpo específico de constante de enum '{enclosing_name}' não pode declarar construtores (JLS §8.9.1).", member.line)
                    )
                else:
                    self._analyze_constructor_member(
                        member,
                        expected_name=enclosing_name if is_enum else None,
                        is_enum=is_enum,
                    )
            elif isinstance(member, (InstanceInitializer, StaticInitializer)):
                if member.block:
                    saved_ctx = self._enter_exec_context("initializer", return_type=None)
                    try:
                        self.analyze_block(member.block)
                    finally:
                        self._restore_exec_context(saved_ctx)
            elif isinstance(member, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
                self._analyze_type_declaration(member, is_nested=True, is_local=False)

    def _register_local_type_conflict(self, name: str, kind_label: str, line: int, is_local: bool):
        """Verifica duplicidade de declarações de tipos locais e colisão com tipo envolvente (JLS §14.3)."""
        if not is_local:
            return
        # _analyze_type_declaration já empilhou `name` no topo de _enclosing_type_names; verifica apenas ancestrais
        if name in self._enclosing_type_names[:-1]:
            self.errors.append(
                SemanticError(
                    f"{kind_label} '{name}' não pode possuir o mesmo nome de um tipo envolvente (JLS §8.1 / §14.3).",
                    line,
                )
            )
            return
        if not self._local_type_scopes:
            return
        for scope in reversed(self._local_type_scopes):
            if name in scope:
                self.errors.append(
                    SemanticError(
                        f"{kind_label} '{name}' declarada novamente no mesmo escopo local ou escopo envolvente (linha {scope[name]}).",
                        line,
                    )
                )
                return
        self._local_type_scopes[-1][name] = line

    def analyze_class(self, cls_node: ClassDeclaration, is_nested: bool = False, is_local: bool = False):
        """Registra a classe e seus membros (campos, métodos, construtores e tipos aninhados)."""
        self._register_local_type_conflict(cls_node.name, "Classe local", cls_node.line, is_local)
        self._declare_type_symbol(cls_node.name, "classe", "classe", "Classe", cls_node.line)
        self._validate_type_modifiers(
            cls_node.modifiers,
            "classe",
            cls_node.name,
            cls_node.line,
            is_nested=is_nested,
            is_local=is_local,
        )
        self._analyze_annotations(getattr(cls_node, "annotations", []), valid_targets={"TYPE"})
        self._check_type_parameters_annotations(getattr(cls_node, "type_parameters", []))
        if getattr(cls_node, "extends_type", None) is not None:
            self._check_type_ref_annotations(cls_node.extends_type)
        for itype in getattr(cls_node, "implements_types", []):
            self._check_type_ref_annotations(itype)
        for ptype in getattr(cls_node, "permits_types", []):
            self._check_type_ref_annotations(ptype)

        self.symbols.enter_scope()
        saved_ctx = self._enter_exec_context("type_body", return_type=None)
        try:
            self._analyze_class_like_members(
                cls_node.members,
                container_label="classe",
                enclosing_name=cls_node.name,
                allow_constructor=True,
                is_enum=False,
            )
        finally:
            self._restore_exec_context(saved_ctx)
        self.symbols.exit_scope()

    def analyze_interface(self, iface_node: InterfaceDeclaration, is_nested: bool = False, is_local: bool = False):
        """Valida declarações e membros de interface segundo JLS §9.1–§9.5."""
        self._register_local_type_conflict(iface_node.name, "Interface local", iface_node.line, is_local)
        self._declare_type_symbol(iface_node.name, "interface", "interface", "Interface", iface_node.line)
        self._validate_type_modifiers(iface_node.modifiers, "interface", iface_node.name, iface_node.line, is_nested=is_nested, is_local=is_local)
        self._analyze_annotations(getattr(iface_node, "annotations", []), valid_targets={"TYPE"})
        self._check_type_parameters_annotations(getattr(iface_node, "type_parameters", []))
        for etype in getattr(iface_node, "extends_types", []):
            self._check_type_ref_annotations(etype)
        for ptype in getattr(iface_node, "permits_types", []):
            self._check_type_ref_annotations(ptype)
        self.symbols.enter_scope()
        saved_ctx = self._enter_exec_context("type_body", return_type=None)
        try:
            allowed_const_mods = {"public", "static", "final"}
            forbidden_method_mods = {"protected", "final", "synchronized", "native"}

            for member in iface_node.members:
                if isinstance(member, EmptyStatement):
                    continue

                elif isinstance(member, (InterfaceConstantDeclaration, FieldDeclaration)):
                    for mod in member.modifiers:
                        if mod not in allowed_const_mods:
                            self.errors.append(
                                SemanticError(f"Modificador '{mod}' inválido em constante da interface '{iface_node.name}' (JLS §9.3).", member.line)
                            )
                    self._analyze_field_declaration(member, container_label="interface", is_interface_constant=True)

                elif isinstance(member, (InterfaceMethodDeclaration, MethodDeclaration)):
                    mset = set(member.modifiers)
                    self._check_conflicting_access_modifiers(member.modifiers, f"método '{member.name}' de interface", member.line)
                    for bad in member.modifiers:
                        if bad in forbidden_method_mods:
                            self.errors.append(
                                SemanticError(f"Modificador '{bad}' não é permitido em método de interface '{member.name}' (JLS §9.4).", member.line)
                            )
                    if "default" in mset and "static" in mset:
                        self.errors.append(SemanticError(f"Método de interface '{member.name}' não pode combinar 'default' e 'static' (JLS §9.4).", member.line))
                    if "default" in mset and "abstract" in mset:
                        self.errors.append(SemanticError(f"Método de interface '{member.name}' não pode combinar 'default' e 'abstract' (JLS §9.4).", member.line))
                    if "static" in mset and "abstract" in mset:
                        self.errors.append(SemanticError(f"Método de interface '{member.name}' não pode combinar 'static' e 'abstract' (JLS §9.4).", member.line))
                    if "private" in mset:
                        for clash in ("default", "abstract"):
                            if clash in mset:
                                self.errors.append(SemanticError(f"Método 'private' em interface '{member.name}' não pode ser '{clash}' (JLS §9.4).", member.line))

                    if "abstract" in mset and member.body is not None:
                        self.errors.append(SemanticError(f"Método 'abstract' em interface '{member.name}' não pode possuir corpo (JLS §9.4).", member.line))
                    if any(m in mset for m in ("default", "static", "private")) and member.body is None:
                        self.errors.append(SemanticError(f"Método '{member.name}' ('default', 'static' ou 'private') em interface deve possuir corpo (JLS §9.4).", member.line))

                    self._analyze_method_member(member)

                elif isinstance(member, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
                    self._analyze_type_declaration(member, is_nested=True, is_local=False)

                elif isinstance(member, (ConstructorDeclaration, InstanceInitializer, StaticInitializer)):
                    self.errors.append(
                        SemanticError(f"Interface '{iface_node.name}' não pode declarar construtores ou blocos inicializadores (JLS §9.1.4).", member.line)
                    )
        finally:
            self._restore_exec_context(saved_ctx)

        self.symbols.exit_scope()

    def analyze_enum(self, enum_node: EnumDeclaration, is_nested: bool = False, is_local: bool = False):
        """Valida declarações de enum, constantes, corpos de constantes, métodos abstratos e membros (JLS §8.9)."""
        self._register_local_type_conflict(enum_node.name, "Enum local", enum_node.line, is_local)
        self._enums[enum_node.name] = enum_node
        self._declare_type_symbol(enum_node.name, "enum", "enum", "Enum", enum_node.line)
        self._validate_type_modifiers(enum_node.modifiers, "enum", enum_node.name, enum_node.line, is_nested=is_nested, is_local=is_local)
        self._analyze_annotations(getattr(enum_node, "annotations", []), valid_targets={"TYPE"})
        for itype in getattr(enum_node, "implements_types", []):
            self._check_type_ref_annotations(itype)
        self.symbols.enter_scope()
        saved_ctx = self._enter_exec_context("type_body", return_type=None)
        try:
            # Métodos abstratos declarados diretamente no corpo do enum (JLS §8.9.1)
            abstract_methods = [
                m for m in enum_node.members
                if isinstance(m, MethodDeclaration) and "abstract" in getattr(m, "modifiers", [])
            ]
            if abstract_methods and not enum_node.constants:
                for am in abstract_methods:
                    self.errors.append(
                        SemanticError(
                            f"Enum '{enum_node.name}' declara método abstrato '{am.name}' mas não possui constantes que o implementem (JLS §8.9).",
                            am.line,
                        )
                    )

            for const in enum_node.constants:
                self._analyze_annotations(getattr(const, "annotations", []), valid_targets={"FIELD"})
                if const.name == "_":
                    self.errors.append(SemanticError("O identificador '_' não pode ser utilizado como nome de constante de enum.", const.line))
                elif not self.symbols.declare(const.name, enum_node.name, const.line, category="constante_enum", is_static=True, is_final=True, is_compile_constant=True):
                    self.errors.append(SemanticError(f"Constante de enum '{const.name}' declarada novamente em '{enum_node.name}'.", const.line))

                for arg in const.arguments:
                    self.check_expression(arg)

                const_impl_sigs: Set[Tuple[str, int]] = set()
                if isinstance(const.body, EnumConstantBody):
                    for cm in const.body.members:
                        if isinstance(cm, MethodDeclaration) and "abstract" not in getattr(cm, "modifiers", []) and cm.body is not None:
                            const_impl_sigs.add((cm.name, len(cm.parameters)))
                    self.symbols.enter_scope()
                    self._analyze_class_like_members(
                        const.body.members,
                        container_label="corpo de constante de enum",
                        enclosing_name=const.name,
                        allow_constructor=False,
                        is_enum=False,
                    )
                    self.symbols.exit_scope()

                for am in abstract_methods:
                    if (am.name, len(am.parameters)) not in const_impl_sigs:
                        self.errors.append(
                            SemanticError(
                                f"Constante de enum '{const.name}' em '{enum_node.name}' deve implementar o método abstrato '{am.name}' (JLS §8.9).",
                                const.line,
                            )
                        )

            self._analyze_class_like_members(
                enum_node.members,
                container_label="enum",
                enclosing_name=enum_node.name,
                allow_constructor=True,
                is_enum=True,
            )
        finally:
            self._restore_exec_context(saved_ctx)
        self.symbols.exit_scope()

    def analyze_record(self, rec_node: RecordDeclaration, is_nested: bool = False, is_local: bool = False):
        """Valida declarações de records, componentes, assessores explícitos e construtores (JLS §8.10)."""
        self._register_local_type_conflict(rec_node.name, "Record local", rec_node.line, is_local)
        self._declare_type_symbol(rec_node.name, "record", "record", "Record", rec_node.line)
        self._validate_type_modifiers(rec_node.modifiers, "record", rec_node.name, rec_node.line, is_nested=is_nested, is_local=is_local)
        self._analyze_annotations(getattr(rec_node, "annotations", []), valid_targets={"TYPE"})
        self._check_type_parameters_annotations(getattr(rec_node, "type_parameters", []))
        for itype in getattr(rec_node, "implements_types", []):
            self._check_type_ref_annotations(itype)
        self.symbols.enter_scope()
        saved_ctx = self._enter_exec_context("type_body", return_type=None)
        try:
            seen_components: Set[str] = set()
            comp_by_name: Dict[str, RecordComponent] = {}
            for comp in rec_node.components:
                self._analyze_annotations(
                    getattr(comp, "annotations", []),
                    valid_targets={"RECORD_COMPONENT", "FIELD", "METHOD", "PARAMETER"},
                    adjacent_type_ref=getattr(comp, "type_ref", None),
                )
                self._check_type_ref_annotations(getattr(comp, "type_ref", None))
                if getattr(comp, "type_ref", None) is not None and getattr(comp.type_ref, "name", None) == "var":
                    self.errors.append(
                        SemanticError(f"'var' não é permitido em componente de record '{comp.name}' (JLS §8.10.1 / §14.4).", comp.line)
                    )
                for ea in getattr(comp, "ellipsis_annotations", []):
                    self._analyze_annotations([ea], valid_targets={"TYPE_USE"})
                if comp.name == "_":
                    self.errors.append(
                        SemanticError("O identificador '_' não pode ser utilizado como nome de componente de record (JLS §8.10.1).", comp.line)
                    )
                elif comp.name in self.FORBIDDEN_RECORD_COMPONENTS:
                    self.errors.append(
                        SemanticError(f"Nome de componente de record inválido: '{comp.name}' conflita com método reservado de java.lang.Object (JLS §8.10.1).", comp.line)
                    )
                elif comp.name in seen_components:
                    self.errors.append(
                        SemanticError(f"Componente de record '{comp.name}' declarado novamente em '{rec_node.name}' (JLS §8.10.1).", comp.line)
                    )
                else:
                    seen_components.add(comp.name)
                    comp_by_name[comp.name] = comp
                    self.symbols.declare(comp.name, comp.effective_type, comp.line, category="componente_record")

            rec_access = self._effective_access(rec_node.modifiers)
            canonical_ctors = 0

            for member in rec_node.members:
                if isinstance(member, EmptyStatement):
                    continue

                elif isinstance(member, FieldDeclaration):
                    if "static" not in member.modifiers:
                        self.errors.append(
                            SemanticError(f"Records não podem declarar campos de instância; apenas campos 'static' são permitidos em '{rec_node.name}' (JLS §8.10.2).", member.line)
                        )
                    self._analyze_field_declaration(member, container_label="record")

                elif isinstance(member, InstanceInitializer):
                    self.errors.append(
                        SemanticError(f"Records não podem declarar inicializadores de instância em '{rec_node.name}' (JLS §8.10.2).", member.line)
                    )
                    if member.block:
                        init_ctx = self._enter_exec_context("initializer", return_type=None)
                        try:
                            self.analyze_block(member.block)
                        finally:
                            self._restore_exec_context(init_ctx)

                elif isinstance(member, StaticInitializer):
                    if member.block:
                        init_ctx = self._enter_exec_context("initializer", return_type=None)
                        try:
                            self.analyze_block(member.block)
                        finally:
                            self._restore_exec_context(init_ctx)

                elif isinstance(member, MethodDeclaration):
                    for bad in ("abstract", "native"):
                        if bad in member.modifiers:
                            self.errors.append(
                                SemanticError(f"Método '{member.name}' do record '{rec_node.name}' não pode possuir modificador '{bad}' (JLS §8.10.2).", member.line)
                            )
                    if member.body is None and not any(m in member.modifiers for m in ("abstract", "native")):
                        self.errors.append(
                            SemanticError(f"Método '{member.name}' do record '{rec_node.name}' deve possuir corpo.", member.line)
                        )
                    if member.name in comp_by_name and len(member.parameters) == 0:
                        comp = comp_by_name[member.name]
                        if "static" in member.modifiers:
                            self.errors.append(
                                SemanticError(f"Método acessor explícito '{member.name}()' do record '{rec_node.name}' não pode ser 'static' (JLS §8.10.3).", member.line)
                            )
                        if "public" not in member.modifiers:
                            self.errors.append(
                                SemanticError(f"Método acessor explícito '{member.name}()' do record '{rec_node.name}' deve ser declarado como 'public' (JLS §8.10.3).", member.line)
                            )
                        if getattr(member, "type_parameters", None):
                            self.errors.append(
                                SemanticError(f"Método acessor explícito '{member.name}()' do record '{rec_node.name}' não pode declarar parâmetros de tipo genérico (JLS §8.10.3).", member.line)
                            )
                        if getattr(member, "throws_types", None):
                            self.errors.append(
                                SemanticError(f"Método acessor explícito '{member.name}()' do record '{rec_node.name}' não pode possuir cláusula 'throws' (JLS §8.10.3).", member.line)
                            )
                        expected_ret = comp.effective_type.replace("...", "[]")
                        if member.effective_return_type != expected_ret:
                            self.errors.append(
                                SemanticError(
                                    f"Método acessor explícito '{member.name}()' do record '{rec_node.name}' deve retornar '{expected_ret}' (encontrado '{member.effective_return_type}' — JLS §8.10.3).",
                                    member.line,
                                )
                            )
                    self._analyze_method_member(member)

                elif isinstance(member, CompactConstructorDeclaration):
                    canonical_ctors += 1
                    if canonical_ctors > 1:
                        self.errors.append(
                            SemanticError(f"Record '{rec_node.name}' possui múltiplos construtores canônicos declarados (JLS §8.10.4).", member.line)
                        )
                    if self._effective_access(member.modifiers) < rec_access:
                        self.errors.append(
                            SemanticError(f"Construtor canônico compacto de '{rec_node.name}' não pode possuir visibilidade mais restrita que a do record (JLS §8.10.4).", member.line)
                        )
                    if getattr(member, "type_parameters", None):
                        self.errors.append(SemanticError("Construtor compacto de record não pode declarar type parameters (JLS §8.10.4.2).", member.line))
                    if getattr(member, "throws_types", None):
                        self.errors.append(SemanticError("Construtor compacto de record não pode possuir cláusula 'throws' (JLS §8.10.4.2).", member.line))
                    if isinstance(member.body, ConstructorBody) and member.body.constructor_invocation is not None:
                        inv_line = getattr(member.body.constructor_invocation, "line", member.line)
                        self.errors.append(
                            SemanticError("Construtor compacto de record não pode conter invocação explícita 'this(...)' ou 'super(...)' (JLS §8.10.4.2).", inv_line)
                        )
                    self._analyze_constructor_member(
                        member,
                        expected_name=rec_node.name,
                        is_compact=True,
                        derived_components=rec_node.components,
                    )

                elif isinstance(member, NormalCanonicalConstructor):
                    canonical_ctors += 1
                    if canonical_ctors > 1:
                        self.errors.append(
                            SemanticError(f"Record '{rec_node.name}' possui múltiplos construtores canônicos declarados (JLS §8.10.4).", member.line)
                        )
                    if self._effective_access(member.modifiers) < rec_access:
                        self.errors.append(
                            SemanticError(f"Construtor canônico normal de '{rec_node.name}' não pode possuir visibilidade mais restrita que a do record (JLS §8.10.4).", member.line)
                        )
                    if getattr(member, "type_parameters", None):
                        self.errors.append(SemanticError("Construtor canônico de record não pode declarar type parameters (JLS §8.10.4.1).", member.line))
                    if getattr(member, "throws_types", None):
                        self.errors.append(SemanticError("Construtor canônico de record não pode possuir cláusula 'throws' (JLS §8.10.4.1).", member.line))
                    if getattr(member, "receiver_parameter", None):
                        self.errors.append(SemanticError("Construtor canônico de record não pode declarar receiver parameter (JLS §8.10.4.1).", member.line))
                    if isinstance(member.body, ConstructorBody) and member.body.constructor_invocation is not None:
                        inv_line = getattr(member.body.constructor_invocation, "line", member.line)
                        self.errors.append(
                            SemanticError("Construtor canônico normal de record não pode conter invocação explícita 'this(...)' ou 'super(...)' (JLS §8.10.4.1).", inv_line)
                        )
                    if len(member.parameters) == len(rec_node.components):
                        for param, comp in zip(member.parameters, rec_node.components):
                            if param.name != comp.name:
                                self.errors.append(
                                    SemanticError(
                                        f"Parâmetro '{param.name}' do construtor canônico deve possuir o mesmo nome do componente '{comp.name}' do record '{rec_node.name}' (JLS §8.10.4.1).",
                                        param.line,
                                    )
                                )
                    self._analyze_constructor_member(member, expected_name=rec_node.name, is_compact=False)

                elif isinstance(member, NonCanonicalRecordConstructor):
                    inv = member.body.constructor_invocation if isinstance(member.body, ConstructorBody) else None
                    if isinstance(inv, SuperclassConstructorInvocation):
                        self.errors.append(
                            SemanticError(f"Construtor não canônico do record '{rec_node.name}' não pode invocar 'super(...)'; deve delegar via 'this(...)' (JLS §8.10.4).", inv.line)
                        )
                    elif not isinstance(inv, AlternateConstructorInvocation):
                        self.errors.append(
                            SemanticError(
                                f"Construtor não canônico do record '{rec_node.name}' deve iniciar com invocação explícita 'this(...)' (ou corresponder exatamente aos componentes e varargs do record — JLS §8.10.4).",
                                member.line,
                            )
                        )
                    self._analyze_constructor_member(member, expected_name=rec_node.name, is_compact=False)

                elif isinstance(member, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
                    self._analyze_type_declaration(member, is_nested=True, is_local=False)
        finally:
            self._restore_exec_context(saved_ctx)

        self.symbols.exit_scope()

    # =========================================================================
    # ANOTAÇÕES E ANNOTATION INTERFACES (ETAPA S5 — JLS §9.6, §9.7)
    # =========================================================================
    def analyze_annotation_interface(
        self,
        ann_node: AnnotationInterfaceDeclaration,
        is_nested: bool = False,
        is_local: bool = False,
    ):
        """Valida declaração de @interface, elementos, valores default e meta-anotações (JLS §9.6)."""
        if is_local:
            self.errors.append(
                SemanticError(
                    f"Annotation interface '@{ann_node.name}' não pode ser declarada localmente dentro de bloco ou método (JLS §9.6 / §14.3).",
                    ann_node.line,
                )
            )
            return

        self._declare_type_symbol(
            ann_node.name, "annotation_interface", "annotation_interface", "Annotation interface", ann_node.line
        )
        self._validate_type_modifiers(
            ann_node.modifiers,
            "annotation_interface",
            ann_node.name,
            ann_node.line,
            is_nested=is_nested,
            is_local=is_local,
        )

        if getattr(ann_node, "type_parameters", None):
            self.errors.append(
                SemanticError(
                    f"Annotation interface '@{ann_node.name}' não pode declarar parâmetros de tipo genérico (JLS §9.6).",
                    ann_node.line,
                )
            )
        if getattr(ann_node, "extends_types", None):
            self.errors.append(
                SemanticError(
                    f"Annotation interface '@{ann_node.name}' não pode possuir cláusula 'extends' (JLS §9.6).",
                    ann_node.line,
                )
            )
        if getattr(ann_node, "permits_types", None):
            self.errors.append(
                SemanticError(
                    f"Annotation interface '@{ann_node.name}' não pode possuir cláusula 'permits' (JLS §9.6).",
                    ann_node.line,
                )
            )

        self._analyze_annotations(
            getattr(ann_node, "annotations", []),
            valid_targets={"ANNOTATION_TYPE", "TYPE"},
        )
        self._validate_repeatable_declaration(ann_node)

        self.symbols.enter_scope()
        allowed_const_mods = {"public", "static", "final"}
        allowed_elem_mods = {"public", "abstract"}
        seen_elements: Set[str] = set()

        for member in ann_node.members:
            if isinstance(member, EmptyStatement):
                continue

            elif isinstance(member, AnnotationInterfaceElementDeclaration):
                self._analyze_annotations(
                    getattr(member, "annotations", []),
                    valid_targets={"METHOD"},
                    adjacent_type_ref=member.effective_return_type_ref,
                )
                self._check_type_ref_annotations(member.return_type)
                for da in getattr(member, "dims_annotations", []):
                    self._analyze_annotations(da, valid_targets={"TYPE_USE"})

                self._check_conflicting_access_modifiers(
                    member.modifiers, f"elemento '{member.name}' de '@{ann_node.name}'", member.line
                )
                for mod in member.modifiers:
                    if mod not in allowed_elem_mods:
                        self.errors.append(
                            SemanticError(
                                f"Modificador '{mod}' não é permitido em elemento de '@interface' ('{member.name}' em '@{ann_node.name}' — JLS §9.6.1).",
                                member.line,
                            )
                        )
                if getattr(member, "parameters", None):
                    self.errors.append(
                        SemanticError(
                            f"Elemento '{member.name}' de '@{ann_node.name}' não pode possuir parâmetros formais (JLS §9.6.1).",
                            member.line,
                        )
                    )
                if getattr(member, "throws_types", None):
                    self.errors.append(
                        SemanticError(
                            f"Elemento '{member.name}' de '@{ann_node.name}' não pode declarar 'throws' (JLS §9.6.1).",
                            member.line,
                        )
                    )
                if getattr(member, "body", None) is not None:
                    self.errors.append(
                        SemanticError(
                            f"Elemento '{member.name}' de '@{ann_node.name}' não pode possuir corpo de implementação (JLS §9.6.1).",
                            member.line,
                        )
                    )
                if member.name in self.FORBIDDEN_ANNOTATION_ELEMENTS:
                    self.errors.append(
                        SemanticError(
                            f"Nome de elemento inválido em '@{ann_node.name}': '{member.name}' conflita com método de java.lang.Object ou Annotation (JLS §9.6.1).",
                            member.line,
                        )
                    )
                if member.name in seen_elements:
                    self.errors.append(
                        SemanticError(
                            f"Elemento '{member.name}' declarado novamente na annotation interface '@{ann_node.name}'.",
                            member.line,
                        )
                    )
                else:
                    seen_elements.add(member.name)

                self._validate_annotation_element_return_type(member, ann_node.name)
                self.symbols.declare(
                    member.name,
                    member.effective_return_type,
                    member.line,
                    category="elemento_anotacao",
                )

                if member.default_value is not None:
                    ev = member.default_value.value
                    self._validate_element_value(
                        ev,
                        expected_type=member.effective_return_type,
                        owner_desc=f"valor default de '{member.name}' em '@{ann_node.name}'",
                    )

            elif isinstance(member, (InterfaceConstantDeclaration, FieldDeclaration)):
                for mod in member.modifiers:
                    if mod not in allowed_const_mods:
                        self.errors.append(
                            SemanticError(
                                f"Modificador '{mod}' inválido em constante da annotation interface '@{ann_node.name}' (JLS §9.6.1).",
                                member.line,
                            )
                        )
                self._analyze_field_declaration(
                    member, container_label="annotation interface", is_interface_constant=True
                )

            elif isinstance(member, MethodDeclaration):
                self.errors.append(
                    SemanticError(
                        f"Declaração de método '{member.name}' com parâmetros ou corpo não é permitida em '@{ann_node.name}' (JLS §9.6.1).",
                        member.line,
                    )
                )

            elif isinstance(
                member,
                (
                    ClassDeclaration,
                    InterfaceDeclaration,
                    EnumDeclaration,
                    RecordDeclaration,
                    AnnotationInterfaceDeclaration,
                ),
            ):
                self._analyze_type_declaration(member, is_nested=True, is_local=False)

            elif isinstance(member, (ConstructorDeclaration, InstanceInitializer, StaticInitializer)):
                self.errors.append(
                    SemanticError(
                        f"Annotation interface '@{ann_node.name}' não pode declarar construtores ou inicializadores (JLS §9.6.1).",
                        member.line,
                    )
                )

        self.symbols.exit_scope()

    def _validate_annotation_element_return_type(
        self,
        elem: AnnotationInterfaceElementDeclaration,
        owner_ann_name: str,
    ):
        """Valida tipos permitidos de elementos de annotation interface e ciclos (JLS §9.6.1)."""
        ret_ref = elem.effective_return_type_ref
        eff_str = elem.effective_return_type
        dims = ret_ref.array_dimensions
        raw_name = ret_ref.name
        base_name = raw_name.split(".")[-1]

        if dims > 1:
            self.errors.append(
                SemanticError(
                    f"Tipo de retorno '{eff_str}' inválido em elemento '{elem.name}' de '@{owner_ann_name}': arrays multidimensionais são proibidos (JLS §9.6.1).",
                    elem.line,
                )
            )
            return

        if raw_name == "void":
            self.errors.append(
                SemanticError(
                    f"Tipo de retorno 'void' não é permitido no elemento '{elem.name}' de '@{owner_ann_name}' (JLS §9.6.1).",
                    elem.line,
                )
            )
            return

        if ret_ref.type_arguments and base_name != "Class":
            self.errors.append(
                SemanticError(
                    f"Tipo parametrizado '{ret_ref.pretty()}' não é permitido no elemento '{elem.name}' de '@{owner_ann_name}'; apenas 'Class<...>' aceita argumentos de tipo (JLS §9.6.1).",
                    elem.line,
                )
            )
            return

        if base_name == owner_ann_name:
            self.errors.append(
                SemanticError(
                    f"Referência cíclica proibida: elemento '{elem.name}' de '@{owner_ann_name}' referencia a própria annotation interface (JLS §9.6.1).",
                    elem.line,
                )
            )
            return

        if base_name in self._annotation_interfaces:
            if self._has_annotation_cycle(base_name, owner_ann_name, set()):
                self.errors.append(
                    SemanticError(
                        f"Referência cíclica indireta proibida entre '@{owner_ann_name}' e '@{base_name}' (JLS §9.6.1).",
                        elem.line,
                    )
                )
            return

        if raw_name in self.PRIMITIVE_TYPES or raw_name in ("String", "java.lang.String", "Class", "java.lang.Class"):
            return

        if raw_name in self.KNOWN_ENUM_TYPES or base_name in self._enums or base_name in self.BUILTIN_ANNOTATION_TYPES:
            return

        if base_name in self.DISALLOWED_ANNOTATION_RETURN_TYPES or raw_name in self.DISALLOWED_ANNOTATION_RETURN_TYPES:
            self.errors.append(
                SemanticError(
                    f"Tipo '{eff_str}' não é permitido para elemento '{elem.name}' de '@{owner_ann_name}' (apenas primitivos, String, Class, enum, annotation ou array unidimensional — JLS §9.6.1).",
                    elem.line,
                )
            )
            return

        if base_name in self._declared_types:
            kind, _ = self._declared_types[base_name]
            if kind in ("class", "interface", "record"):
                self.errors.append(
                    SemanticError(
                        f"Tipo '{eff_str}' ({kind}) não é permitido para elemento '{elem.name}' de '@{owner_ann_name}' (JLS §9.6.1).",
                        elem.line,
                    )
                )

    def _has_annotation_cycle(self, current_name: str, target_name: str, visited: Set[str]) -> bool:
        """Verifica se há ciclo de dependência entre annotation interfaces via seus elementos."""
        if current_name in visited:
            return False
        visited.add(current_name)
        ann_decl = self._annotation_interfaces.get(current_name)
        if not ann_decl:
            return False
        for el in ann_decl.elements:
            dep_base = el.return_type.name.split(".")[-1]
            if dep_base == target_name:
                return True
            if dep_base in self._annotation_interfaces and self._has_annotation_cycle(dep_base, target_name, visited):
                return True
        return False

    def _extract_target_elements(self, defn: AnnotationInterfaceDeclaration) -> Optional[Set[str]]:
        """Extrai o conjunto de ElementType declarados em @Target(...) ou None se ausente."""
        for ann in getattr(defn, "annotations", []):
            if ann.name.split(".")[-1] == "Target":
                vals: List[ElementValue] = []
                if isinstance(ann, SingleElementAnnotation) and ann.element_value is not None:
                    vals = [ann.element_value]
                elif isinstance(ann, NormalAnnotation):
                    for p in ann.pairs:
                        if p.name == "value":
                            vals = [p.value]
                            break
                if not vals:
                    return set()
                v0 = vals[0]
                items = v0.value.elements if isinstance(v0.value, ArrayInitializer) else [v0]
                targets: Set[str] = set()
                for item in items:
                    inner = item.value if isinstance(item, ElementValue) else item
                    if isinstance(inner, MemberAccess):
                        targets.add(inner.member_name)
                    elif isinstance(inner, Identifier):
                        targets.add(inner.name.split(".")[-1])
                return targets
        return None

    def _extract_retention_policy(self, defn: AnnotationInterfaceDeclaration) -> str:
        """Extrai a política de @Retention(...) (SOURCE, CLASS ou RUNTIME; padrão CLASS)."""
        for ann in getattr(defn, "annotations", []):
            if ann.name.split(".")[-1] == "Retention":
                val = None
                if isinstance(ann, SingleElementAnnotation):
                    val = ann.element_value
                elif isinstance(ann, NormalAnnotation):
                    for p in ann.pairs:
                        if p.name == "value":
                            val = p.value
                            break
                if val is not None:
                    inner = val.value if isinstance(val, ElementValue) else val
                    if isinstance(inner, MemberAccess):
                        return inner.member_name
                    if isinstance(inner, Identifier):
                        return inner.name.split(".")[-1]
        return "CLASS"

    def _extract_repeatable_container_name(self, defn: AnnotationInterfaceDeclaration) -> Optional[Tuple[str, int]]:
        """Retorna (NomeContainer, linha) se @interface possuir @Repeatable(Container.class)."""
        for ann in getattr(defn, "annotations", []):
            if ann.name.split(".")[-1] == "Repeatable":
                val = None
                if isinstance(ann, SingleElementAnnotation):
                    val = ann.element_value
                elif isinstance(ann, NormalAnnotation):
                    for p in ann.pairs:
                        if p.name == "value":
                            val = p.value
                            break
                if val is not None:
                    inner = val.value if isinstance(val, ElementValue) else val
                    if isinstance(inner, ClassLiteral):
                        return inner.type_ref.name.split(".")[-1], ann.line
                    return "", ann.line
        return None

    def _validate_repeatable_declaration(self, ann_node: AnnotationInterfaceDeclaration):
        """Valida meta-anotação @Repeatable e seu container segundo JLS §9.6.3."""
        rep = self._extract_repeatable_container_name(ann_node)
        if rep is None:
            return
        container_name, rep_line = rep
        if not container_name:
            self.errors.append(
                SemanticError(
                    f"@Repeatable em '@{ann_node.name}' requer literal de classe de uma annotation interface container (ex: Containers.class — JLS §9.6.3).",
                    rep_line,
                )
            )
            return

        if container_name in self._declared_types:
            kind, _ = self._declared_types[container_name]
            if kind != "annotation_interface":
                self.errors.append(
                    SemanticError(
                        f"Tipo container '{container_name}' de '@Repeatable' em '@{ann_node.name}' deve ser uma '@interface' (encontrado {kind} — JLS §9.6.3).",
                        rep_line,
                    )
                )
                return

        container = self._annotation_interfaces.get(container_name)
        if container is None:
            return

        elem_map = {e.name: e for e in container.elements}
        if "value" not in elem_map:
            self.errors.append(
                SemanticError(
                    f"Annotation container '@{container_name}' de '@{ann_node.name}' deve declarar elemento obrigatório 'value()' retornando '{ann_node.name}[]' (JLS §9.6.3).",
                    rep_line,
                )
            )
        else:
            val_el = elem_map["value"]
            val_ret = val_el.effective_return_type
            expected_arr = f"{ann_node.name}[]"
            if val_ret != expected_arr and val_ret.split(".")[-1] != expected_arr:
                self.errors.append(
                    SemanticError(
                        f"Elemento 'value()' do container '@{container_name}' deve retornar '{expected_arr}' (encontrado '{val_ret}' — JLS §9.6.3).",
                        val_el.line,
                    )
                )

        for el in container.elements:
            if el.name != "value" and el.default_value is None:
                self.errors.append(
                    SemanticError(
                        f"Elemento extra '{el.name}' do container '@{container_name}' deve possuir valor 'default' obrigatório para @Repeatable (JLS §9.6.3).",
                        el.line,
                    )
                )

        t_ret_policy = self._extract_retention_policy(ann_node)
        c_ret_policy = self._extract_retention_policy(container)
        if self.RETENTION_RANK.get(c_ret_policy, 1) < self.RETENTION_RANK.get(t_ret_policy, 1):
            self.errors.append(
                SemanticError(
                    f"Retenção '{c_ret_policy}' do container '@{container_name}' não pode ser menor que a retenção '{t_ret_policy}' de '@{ann_node.name}' (JLS §9.6.3).",
                    rep_line,
                )
            )

        t_targets = self._extract_target_elements(ann_node)
        c_targets = self._extract_target_elements(container)
        if t_targets is not None and c_targets is not None:
            allowed_for_container = set(t_targets)
            if "TYPE_USE" in allowed_for_container:
                allowed_for_container.update({"TYPE", "TYPE_PARAMETER"})
            if "TYPE" in allowed_for_container:
                allowed_for_container.add("ANNOTATION_TYPE")
            invalid_c_targets = c_targets - allowed_for_container
            if invalid_c_targets:
                self.errors.append(
                    SemanticError(
                        f"@Target do container '@{container_name}' ({sorted(invalid_c_targets)}) excede o @Target permitido pela anotação repetível '@{ann_node.name}' (JLS §9.6.3).",
                        rep_line,
                    )
                )

    def _check_type_parameters_annotations(self, type_params: List[ASTNode]):
        """Valida annotations em TypeParameters e seus bounds (JLS §4.4, §9.7.4)."""
        for tp in type_params or []:
            self._analyze_annotations(getattr(tp, "annotations", []), valid_targets={"TYPE_PARAMETER", "TYPE_USE"})
            for b in getattr(tp, "bounds", []):
                self._check_type_ref_annotations(b)

    def _check_type_ref_annotations(self, type_ref: Optional[ASTNode]):
        """Valida recursivamente type annotations em tipos, segmentos qualificados, dimensões e generics."""
        if type_ref is None:
            return
        if isinstance(type_ref, WildcardType):
            self._analyze_annotations(getattr(type_ref, "annotations", []), valid_targets={"TYPE_USE"})
            bound_t = getattr(type_ref, "bound_type", None)
            if bound_t is not None:
                self._check_type_ref_annotations(bound_t)
            return

        annos = getattr(type_ref, "annotations", [])
        is_void = getattr(type_ref, "name", "") == "void" and getattr(type_ref, "array_dimensions", 0) == 0
        if annos and not is_void:
            self._analyze_annotations(annos, valid_targets={"TYPE_USE"})

        for seg_annos in getattr(type_ref, "segment_annotations", []):
            if seg_annos:
                self._analyze_annotations(seg_annos, valid_targets={"TYPE_USE"})

        for da in getattr(type_ref, "dims_annotations", []):
            if da:
                self._analyze_annotations(da, valid_targets={"TYPE_USE"})

        for ea in getattr(type_ref, "ellipsis_annotations", []):
            self._analyze_annotations([ea], valid_targets={"TYPE_USE"})

        self._check_type_parameters_annotations(getattr(type_ref, "type_parameters", []))
        for targ in getattr(type_ref, "type_arguments", []):
            self._check_type_ref_annotations(targ)

    def _analyze_annotations(
        self,
        annos: List[ASTNode],
        valid_targets: Set[str],
        adjacent_type_ref: Optional[TypeReference] = None,
    ):
        """
        Valida uso de lista de annotations em uma posição alvo:
        - Repetibilidade (@Repeatable) e mistura proibida container + repetível
        - Aplicabilidade via @Target
        - Presença de elementos obrigatórios, desconhecimento/duplicidade de chaves e constância/tipo dos valores
        """
        if not annos:
            return

        grouped: Dict[str, List[Annotation]] = {}
        adj_annos = set(id(a) for a in getattr(adjacent_type_ref, "annotations", [])) if adjacent_type_ref is not None else set()
        adj_is_void = (
            adjacent_type_ref is not None
            and getattr(adjacent_type_ref, "name", "") == "void"
            and getattr(adjacent_type_ref, "array_dimensions", 0) == 0
        )

        for ann in annos:
            if not isinstance(ann, Annotation):
                continue
            simple_name = ann.name.split(".")[-1]
            grouped.setdefault(simple_name, []).append(ann)

            ann_id = id(ann)
            first_visit = ann_id not in self._validated_ann_targets
            self._validated_ann_targets.add(ann_id)

            effective_targets = set(valid_targets)
            if ann_id in adj_annos and not adj_is_void:
                effective_targets.add("TYPE_USE")

            defn = self._annotation_interfaces.get(simple_name)

            # 1. Validação de @Target quando @interface foi declarada na unidade e há contexto-alvo (anotações aninhadas em ElementValue têm effective_targets vazio)
            if effective_targets and first_visit and defn is not None:
                allowed = self._extract_target_elements(defn)
                if allowed is not None:
                    expanded_allowed = set(allowed)
                    if "TYPE_USE" in expanded_allowed:
                        expanded_allowed.update({"TYPE", "TYPE_PARAMETER"})
                    if "TYPE" in expanded_allowed:
                        expanded_allowed.add("ANNOTATION_TYPE")
                    if not (effective_targets & expanded_allowed):
                        self.errors.append(
                            SemanticError(
                                f"Anotação '@{ann.name}' não é aplicável ao alvo {sorted(effective_targets)} (permitido pelo @Target: {sorted(allowed)} — JLS §9.6.4.1).",
                                ann.line,
                            )
                        )

            # 2. Validação estrutural e semântica de argumentos da anotação (sem duplicar no par decl/type_ref)
            if not first_visit:
                continue

            elem_map = {e.name: e for e in defn.elements} if defn is not None else None
            provided_keys: Set[str] = set()

            if isinstance(ann, SingleElementAnnotation):
                if ann.element_value is not None:
                    expected_t = None
                    if elem_map is not None:
                        if "value" not in elem_map:
                            self.errors.append(
                                SemanticError(
                                    f"Anotação '@{ann.name}' não declara o elemento 'value' para uso abreviado (JLS §9.7.3).",
                                    ann.line,
                                )
                            )
                        else:
                            expected_t = elem_map["value"].effective_return_type
                            provided_keys.add("value")
                    self._validate_element_value(
                        ann.element_value,
                        expected_type=expected_t,
                        owner_desc=f"anotação '@{ann.name}'",
                    )
            elif isinstance(ann, NormalAnnotation):
                seen_pair_keys: Set[str] = set()
                for pair in ann.pairs:
                    if pair.name in seen_pair_keys:
                        self.errors.append(
                            SemanticError(
                                f"Elemento duplicado '{pair.name}' na anotação '@{ann.name}' (JLS §9.7.1).",
                                pair.line,
                            )
                        )
                    else:
                        seen_pair_keys.add(pair.name)

                    expected_t = None
                    if elem_map is not None:
                        if pair.name not in elem_map:
                            self.errors.append(
                                SemanticError(
                                    f"Elemento desconhecido '{pair.name}' na anotação '@{ann.name}' (JLS §9.7.1).",
                                    pair.line,
                                )
                            )
                        else:
                            expected_t = elem_map[pair.name].effective_return_type
                            provided_keys.add(pair.name)

                    self._validate_element_value(
                        pair.value,
                        expected_type=expected_t,
                        owner_desc=f"elemento '{pair.name}' de '@{ann.name}'",
                    )

            # 3. Elementos obrigatórios (sem default) ausentes
            if elem_map is not None:
                for el_name, el_decl in elem_map.items():
                    if el_decl.is_required and el_name not in provided_keys:
                        self.errors.append(
                            SemanticError(
                                f"Elemento obrigatório '{el_name}' ausente na anotação '@{ann.name}' (JLS §9.7).",
                                ann.line,
                            )
                        )

        # 4. Validação de repetibilidade (@Repeatable) no mesmo local
        for name, group in grouped.items():
            defn = self._annotation_interfaces.get(name)
            rep = self._extract_repeatable_container_name(defn) if defn is not None else None
            if len(group) > 1:
                if name in self.BUILTIN_NON_REPEATABLE_ANNOTATIONS:
                    self.errors.append(
                        SemanticError(
                            f"Anotação '@{name}' não é repetível (@Repeatable) e não pode aparecer múltiplas vezes no mesmo local (JLS §9.7.5).",
                            group[1].line,
                        )
                    )
                elif defn is not None and rep is None:
                    self.errors.append(
                        SemanticError(
                            f"Anotação duplicada '@{name}' requer meta-anotação '@Repeatable' para ser repetida (JLS §9.6.3 / §9.7.5).",
                            group[1].line,
                        )
                    )
            if rep is not None and rep[0] and rep[0] in grouped:
                self.errors.append(
                    SemanticError(
                        f"Não é permitido misturar a anotação repetível '@{name}' e seu container '@{rep[0]}' diretamente no mesmo local (JLS §9.7.5).",
                        grouped[rep[0]][0].line,
                    )
                )

    def _validate_element_value(
        self,
        ev: ElementValue,
        expected_type: Optional[str] = None,
        owner_desc: str = "anotação",
    ):
        """Valida constância em tempo de compilação e compatibilidade de tipos de um ElementValue."""
        if ev is None:
            return
        val = ev.value if isinstance(ev, ElementValue) else ev

        # 1. Anotação aninhada
        if isinstance(val, Annotation):
            self._analyze_annotations([val], valid_targets=set())
            if expected_type is not None:
                self._validate_element_value_compatible(val, expected_type, owner_desc, getattr(val, "line", ev.line))
            return

        # 2. Inicializador de array ({...})
        if isinstance(val, ArrayInitializer):
            for elem in val.elements:
                inner = elem.value if isinstance(elem, ElementValue) else elem
                if isinstance(inner, ArrayInitializer):
                    self.errors.append(
                        SemanticError(
                            f"Inicializadores de array aninhados '{{{{ ... }}}}' não são permitidos em {owner_desc} (JLS §9.7.1).",
                            getattr(elem, "line", ev.line),
                        )
                    )
                else:
                    sub_ev = elem if isinstance(elem, ElementValue) else ElementValue(value=elem, line=getattr(elem, "line", ev.line), column=1)
                    self._validate_element_value(sub_ev, expected_type=None, owner_desc=owner_desc)

            if expected_type is not None:
                self._validate_element_value_compatible(val, expected_type, owner_desc, ev.line)
            return

        # 3. Expressão condicional: não permite null, chamadas de método, new, atribuições, lambdas ou não-constantes
        self._check_annotation_constant_expr(val, owner_desc, ev.line)
        if expected_type is not None:
            self._validate_element_value_compatible(val, expected_type, owner_desc, ev.line)

    def _is_compile_time_constant_expr(self, expr: Optional[ASTNode]) -> bool:
        """Verifica de forma conservadora se uma expressão de inicialização é constante em tempo de compilação."""
        if expr is None:
            return False
        if isinstance(expr, Literal):
            return expr.kind != "NULL" and str(expr.value) != "null"
        if isinstance(expr, ClassLiteral):
            return True
        if isinstance(expr, UnaryOp):
            return self._is_compile_time_constant_expr(expr.operand)
        if isinstance(expr, BinaryOp):
            return self._is_compile_time_constant_expr(expr.left) and self._is_compile_time_constant_expr(expr.right)
        if isinstance(expr, ConditionalExpression):
            return (
                self._is_compile_time_constant_expr(expr.condition)
                and self._is_compile_time_constant_expr(expr.then_expr)
                and self._is_compile_time_constant_expr(expr.else_expr)
            )
        if isinstance(expr, CastExpression):
            return self._is_compile_time_constant_expr(expr.expression)
        if isinstance(expr, Identifier):
            sym = self.symbols.lookup(expr.name)
            if sym is not None:
                return bool(sym.get("is_compile_constant", False)) or sym.get("category") in ("constante_enum", "constante_interface")
            return expr.name.split(".")[0][:1].isupper()
        if isinstance(expr, MemberAccess):
            if isinstance(expr.target, Identifier) and expr.target.name in self._enums:
                return True
            if isinstance(expr.target, Identifier) and expr.target.name[:1].isupper():
                return True
            return False
        if isinstance(expr, ArrayInitializer):
            return all(self._is_compile_time_constant_expr(e) for e in expr.elements)
        return False

    def _check_annotation_constant_expr(self, node: Optional[ASTNode], owner_desc: str, fallback_line: int):
        """Valida que uma expressão dentro de ElementValue não contenha construções não-constantes."""
        if node is None:
            return
        line = getattr(node, "line", fallback_line)

        if isinstance(node, Literal):
            if node.kind == "NULL" or str(node.value) == "null":
                self.errors.append(
                    SemanticError(
                        f"Valor 'null' não é permitido em {owner_desc} (JLS §9.7.1).",
                        line,
                    )
                )
            return

        if isinstance(node, ClassLiteral):
            return

        if isinstance(node, ObjectCreationExpression):
            self.errors.append(
                SemanticError(
                    f"Instanciação 'new' não é expressão constante válida para {owner_desc} (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, MethodCall):
            self.errors.append(
                SemanticError(
                    f"Chamada de método '{node.method_name}(...)' não é expressão constante válida para {owner_desc} (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, ArrayCreationExpression):
            self.errors.append(
                SemanticError(
                    f"Criação explícita de array 'new ...[]' não é permitida em {owner_desc}; use inicializador '{{...}}' (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, ArrayInitializer):
            self.errors.append(
                SemanticError(
                    f"Inicializador de array '{{...}}' inválido em {owner_desc} (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, (Assignment, LambdaExpression, MethodReference)):
            self.errors.append(
                SemanticError(
                    f"Expressão não constante inválida em {owner_desc} (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, Identifier):
            sym = self.symbols.lookup(node.name)
            if sym is not None:
                cat = sym.get("category")
                if cat in ("constante_enum", "constante_interface"):
                    return
                if sym.get("is_compile_constant", False):
                    return
                self.errors.append(
                    SemanticError(
                        f"Valor não constante '{node.name}' ({cat}) não pode ser usado em {owner_desc} (JLS §9.7.1).",
                        line,
                    )
                )
                return
            if node.name in self._static_imports or self._has_wildcard_static_import:
                return
            self.errors.append(
                SemanticError(
                    f"Identificador não declarado ou não constante '{node.name}' em {owner_desc} (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, MemberAccess):
            if isinstance(node.target, Identifier):
                tname = node.target.name
                sym = self.symbols.lookup(tname)
                if sym is not None and sym.get("category") in ("variavel", "parametro", "componente_record", "campo"):
                    if not sym.get("is_compile_constant", False):
                        self.errors.append(
                            SemanticError(
                                f"Acesso a membro de instância ou variável '{tname}.{node.member_name}' não é expressão constante para {owner_desc} (JLS §9.7.1).",
                                line,
                            )
                        )
                        return
                enum_decl = self._enums.get(tname)
                if enum_decl is not None:
                    const_names = {c.name for c in enum_decl.constants}
                    if node.member_name not in const_names:
                        self.errors.append(
                            SemanticError(
                                f"Constante '{node.member_name}' não existe no enum '{tname}' em {owner_desc}.",
                                line,
                            )
                        )
                elif not tname[:1].isupper() and sym is None:
                    self.errors.append(
                        SemanticError(
                            f"Acesso '{tname}.{node.member_name}' não é constante em tempo de compilação válida para {owner_desc} (JLS §9.7.1).",
                            line,
                        )
                    )
            else:
                self._check_annotation_constant_expr(node.target, owner_desc, line)
            return

        if isinstance(node, UnaryOp):
            self._check_annotation_constant_expr(node.operand, owner_desc, line)
            return

        if isinstance(node, BinaryOp):
            self._check_annotation_constant_expr(node.left, owner_desc, line)
            self._check_annotation_constant_expr(node.right, owner_desc, line)
            return

        if isinstance(node, ConditionalExpression):
            self._check_annotation_constant_expr(node.condition, owner_desc, line)
            self._check_annotation_constant_expr(node.then_expr, owner_desc, line)
            self._check_annotation_constant_expr(node.else_expr, owner_desc, line)
            return

        if isinstance(node, CastExpression):
            self._check_annotation_constant_expr(node.expression, owner_desc, line)
            return

    def _validate_element_value_compatible(
        self,
        val: ASTNode,
        expected_type: str,
        owner_desc: str,
        line: int,
    ):
        """Valida compatibilidade estática entre um valor de anotação e o tipo esperado pelo elemento."""
        exp_clean = expected_type.strip()
        exp_no_gen_parts = []
        depth = 0
        for ch in exp_clean:
            if ch == "<":
                depth += 1
            elif ch == ">":
                if depth > 0:
                    depth -= 1
            elif depth == 0:
                exp_no_gen_parts.append(ch)
        exp_no_gen = "".join(exp_no_gen_parts).strip()

        # Shorthand de elemento único para tipo array unidimensional (JLS §9.7.5)
        if exp_no_gen.endswith("[]") and not isinstance(val, ArrayInitializer):
            self._validate_element_value_compatible(val, exp_clean[:-2], owner_desc, line)
            return

        if isinstance(val, ArrayInitializer):
            if not exp_no_gen.endswith("[]"):
                self.errors.append(
                    SemanticError(
                        f"Inicializador de array '{{...}}' incompatível com o tipo '{expected_type}' esperado em {owner_desc}.",
                        line,
                    )
                )
                return
            item_expected = exp_clean[:-2]
            for elem in val.elements:
                inner = elem.value if isinstance(elem, ElementValue) else elem
                if not isinstance(inner, ArrayInitializer):
                    self._validate_element_value_compatible(inner, item_expected, owner_desc, getattr(elem, "line", line))
            return

        exp_base = exp_no_gen.split(".")[-1]

        if isinstance(val, Annotation):
            ann_simple = val.name.split(".")[-1]
            if exp_base != ann_simple:
                self.errors.append(
                    SemanticError(
                        f"Anotação '@{val.name}' incompatível com o tipo esperado '{expected_type}' em {owner_desc}.",
                        getattr(val, "line", line),
                    )
                )
            return

        if exp_base in self._annotation_interfaces or exp_base in self.BUILTIN_ANNOTATION_TYPES:
            self.errors.append(
                SemanticError(
                    f"Era esperada uma anotação '@{exp_base}' compatível com '{expected_type}' em {owner_desc}.",
                    line,
                )
            )
            return

        if exp_base == "Class":
            if not isinstance(val, ClassLiteral):
                self.errors.append(
                    SemanticError(
                        f"Era esperado um literal de classe ('.class') compatível com '{expected_type}' em {owner_desc}.",
                        line,
                    )
                )
                return
            if "<" in exp_clean and ">" in exp_clean:
                inner_gen = exp_clean[exp_clean.find("<") + 1 : exp_clean.rfind(">")].strip()
                lit_name = val.type_ref.full_name
                if inner_gen.startswith("? extends "):
                    bound_type = inner_gen[len("? extends "):].strip().split(".")[-1]
                    if bound_type == "Number":
                        allowed_nums = {"Number", "Integer", "Long", "Double", "Float", "Short", "Byte", "BigDecimal", "BigInteger"}
                        if lit_name.split(".")[-1] not in allowed_nums or lit_name in self.PRIMITIVE_TYPES or lit_name == "void":
                            self.errors.append(
                                SemanticError(
                                    f"Literal de classe '{lit_name}.class' incompatível com '{expected_type}' em {owner_desc}.",
                                    line,
                                )
                            )
                elif inner_gen != "?" and not inner_gen.startswith("? "):
                    exact_t = inner_gen.split(".")[-1]
                    if lit_name.split(".")[-1] != exact_t and lit_name != inner_gen:
                        self.errors.append(
                            SemanticError(
                                f"Literal de classe '{lit_name}.class' incompatível com '{expected_type}' em {owner_desc}.",
                                line,
                            )
                        )
            return

        if exp_base in self._enums:
            if isinstance(val, MemberAccess) and isinstance(val.target, Identifier):
                t_enum = val.target.name.split(".")[-1]
                if t_enum != exp_base:
                    self.errors.append(
                        SemanticError(
                            f"Enum '{val.target.name}' incompatível com o tipo esperado '{expected_type}' em {owner_desc}.",
                            line,
                        )
                    )
            elif isinstance(val, Identifier) and (val.name in self._static_imports or self._has_wildcard_static_import):
                pass
            else:
                self.errors.append(
                    SemanticError(
                        f"Valor incompatível com o enum '{expected_type}' em {owner_desc}.",
                        line,
                    )
                )
            return

        inferred = self.infer_type(val)
        if not inferred:
            return

        if exp_base == "String":
            if inferred != "String":
                self.errors.append(
                    SemanticError(
                        f"Incompatibilidade de tipo em {owner_desc}: esperado 'String', encontrado '{inferred}'.",
                        line,
                    )
                )
            return

        if exp_base == "boolean":
            if inferred != "boolean":
                self.errors.append(
                    SemanticError(
                        f"Incompatibilidade de tipo em {owner_desc}: esperado 'boolean', encontrado '{inferred}'.",
                        line,
                    )
                )
            return

        if exp_base in ("byte", "short", "int", "long", "float", "double", "char"):
            # Conversão estreitante constante válida em Java para byte/short/char a partir de literal int
            if exp_base in ("byte", "short", "char") and isinstance(val, Literal) and inferred == "int":
                try:
                    n = int(str(val.value), 0)
                    bounds = {"byte": (-128, 127), "short": (-32768, 32767), "char": (0, 65535)}
                    lo, hi = bounds[exp_base]
                    if lo <= n <= hi:
                        return
                except ValueError:
                    pass
            if not self.is_assignable(exp_base, inferred):
                self.errors.append(
                    SemanticError(
                        f"Incompatibilidade de tipo em {owner_desc}: esperado '{expected_type}', encontrado '{inferred}'.",
                        line,
                    )
                )

    def _register_local_var(
        self,
        name: str,
        var_type: str,
        line: int,
        is_final: bool = False,
        has_initializer: bool = True,
        category: str = "variavel",
        is_compile_constant: bool = False,
    ) -> bool:
        """Registra variável/parâmetro local verificando conflito em escopos locais e de patterns envolventes (JLS §6.3 / §6.4.1 / §14.4.2)."""
        if name == "_":
            return False
        for pscope in reversed(self._active_pattern_scopes):
            if name in pscope:
                prev = pscope[name]
                self.errors.append(
                    SemanticError(
                        f"Variável '{name}' declarada novamente (já declarada como variável de pattern na linha {prev['line']}).",
                        line,
                    )
                )
                return False
        if self._local_var_scopes:
            for scope in reversed(self._local_var_scopes):
                if name in scope:
                    prev = scope[name]
                    self.errors.append(
                        SemanticError(
                            f"Variável '{name}' declarada novamente (já declarada na linha {prev['line']}).",
                            line,
                        )
                    )
                    return False
            self._local_var_scopes[-1][name] = {
                "type": var_type,
                "line": line,
                "is_final": is_final,
                "reassigned": False,
                "category": category,
                "has_initializer": has_initializer,
            }
            self.symbols.declare(
                name,
                var_type,
                line,
                category=category,
                is_final=is_final,
                is_compile_constant=is_compile_constant,
            )
            return True

        prev_sym = self.symbols.lookup(name)
        if not self.symbols.declare(
            name,
            var_type,
            line,
            category=category,
            is_final=is_final,
            is_compile_constant=is_compile_constant,
        ):
            prev_line = f" (declarada na linha {prev_sym['line']})" if prev_sym and "line" in prev_sym else ""
            self.errors.append(
                SemanticError(f"Variável '{name}' declarada novamente{prev_line}.", line)
            )
            return False
        return True

    def _find_local_var_info(self, name: str) -> Optional[Dict[str, Any]]:
        for scope in reversed(self._active_pattern_scopes):
            if name in scope:
                return scope[name]
        for scope in reversed(self._local_var_scopes):
            if name in scope:
                return scope[name]
        return None

    def _lookup_var_symbol(self, name: str) -> Optional[Dict[str, Any]]:
        """Busca variável em escopos de pattern ativos primeiro e depois na tabela de símbolos."""
        for pscope in reversed(self._active_pattern_scopes):
            if name in pscope:
                info = pscope[name]
                return {
                    "type": info.get("type", "Object"),
                    "line": info.get("line", 1),
                    "category": info.get("category", "variavel"),
                    "is_final": info.get("is_final", False),
                    "is_compile_constant": False,
                    "is_pattern_var": True,
                }
        return self.symbols.lookup(name)

    def _mark_local_var_reassigned(self, name: str):
        if not name:
            return
        for scope in reversed(self._active_pattern_scopes):
            if name in scope:
                info = scope[name]
                if info.get("has_initializer", True):
                    info["reassigned"] = True
                else:
                    info["has_initializer"] = True
                return
        for scope in reversed(self._local_var_scopes):
            if name in scope:
                info = scope[name]
                if info.get("has_initializer", True):
                    info["reassigned"] = True
                else:
                    info["has_initializer"] = True
                return

    def _expr_contains_identifier(self, node: Optional[ASTNode], target_name: str) -> bool:
        """Verifica se uma expressão referencia o identificador alvo (usado para detectar autorreferência em 'var')."""
        if node is None or isinstance(node, (TypeReference, Annotation)):
            return False
        if isinstance(node, Identifier):
            return node.name == target_name or node.name.startswith(f"{target_name}.")
        if isinstance(node, MemberAccess):
            return self._expr_contains_identifier(node.target, target_name)
        if isinstance(node, MethodCall):
            if self._expr_contains_identifier(node.target, target_name):
                return True
            return any(self._expr_contains_identifier(arg, target_name) for arg in node.arguments)
        if isinstance(node, MethodReference):
            return self._expr_contains_identifier(node.target, target_name)
        if isinstance(node, (list, tuple)):
            return any(self._expr_contains_identifier(item, target_name) for item in node)
        if isinstance(node, ASTNode) and hasattr(node, "__dict__"):
            for val in node.__dict__.values():
                if isinstance(val, (ASTNode, list, tuple)):
                    if self._expr_contains_identifier(val, target_name):
                        return True
        return False

    def _check_boolean_condition(self, cond: Optional[ASTNode], context_label: str, line: int) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """Valida expressão de condição booleana e retorna (true_vars, false_vars) para escopo de patterns (JLS §6.3)."""
        if cond is None:
            return {}, {}
        flow = self._check_expression_flow(cond)
        inferred = self.infer_type(cond)
        if inferred is not None and inferred not in ("boolean", "Boolean", "Object", "desconhecido", "var"):
            self.errors.append(
                SemanticError(
                    f"Condição de '{context_label}' deve possuir tipo 'boolean' (encontrado '{inferred}').",
                    line,
                )
            )
        return flow.true_vars, flow.false_vars

    def _collect_all_enum_constant_names(self) -> Set[str]:
        """Coleta nomes de constantes de todos os enums pré-indexados na unidade."""
        names: Set[str] = set()
        for enum_decl in self._enums.values():
            for c in getattr(enum_decl, "constants", []):
                if getattr(c, "name", None):
                    names.add(c.name)
        return names

    def _switch_label_constant_key(self, const_expr: ASTNode) -> Any:
        """Normaliza constante de label 'case' para detecção de duplicidade."""
        if isinstance(const_expr, Literal):
            kind = getattr(const_expr, "kind", "")
            val = getattr(const_expr, "value", None)
            if kind in ("NUM", "INT"):
                val_s = str(val)
                if val_s.lower().endswith("l"):
                    try:
                        return ("long", int(val_s[:-1].replace("_", ""), 0))
                    except ValueError:
                        return ("lit", val_s)
                try:
                    return ("int", int(val_s.replace("_", ""), 0))
                except ValueError:
                    return ("lit", val_s)
            if kind in ("FLOAT", "DOUBLE", "CHAR", "STRING", "TEXT_BLOCK", "BOOLEAN", "NULL"):
                return ("lit", kind, str(val))
            return ("lit", kind, str(val))
        if isinstance(const_expr, Identifier):
            return ("id", const_expr.name)
        if isinstance(const_expr, MemberAccess) and isinstance(const_expr.target, Identifier):
            return ("member", const_expr.target.name, const_expr.member_name)
        if isinstance(const_expr, UnaryOp) and const_expr.op in ("+", "-") and isinstance(const_expr.operand, Literal):
            val_s = str(const_expr.operand.value)
            if val_s.lower().endswith("l"):
                try:
                    num = int(val_s[:-1].replace("_", ""), 0)
                    return ("long", -num if const_expr.op == "-" else num)
                except ValueError:
                    return None
            try:
                num = int(val_s.replace("_", ""), 0)
                return ("int", -num if const_expr.op == "-" else num)
            except ValueError:
                return None
        return None

    def _check_switch_constant_expr(self, const_expr: ASTNode, lb_line: int, enum_const_names: Set[str]):
        """Valida que constante de case é literal, constante de enum ou constante em tempo de compilação."""
        if isinstance(const_expr, Literal):
            kind = getattr(const_expr, "kind", "")
            val_s = str(getattr(const_expr, "value", ""))
            err_line = getattr(const_expr, "line", lb_line)
            if kind in ("FLOAT", "DOUBLE") and not self.enable_preview_primitive_patterns:
                self.errors.append(
                    SemanticError(
                        "Tipo de ponto flutuante em constante de 'case' requer recurso preview (JEP 530) no modo padrão Java SE 26 (JLS §14.11.1).",
                        err_line,
                    )
                )
            elif kind == "BOOLEAN" and not self.enable_preview_primitive_patterns:
                self.errors.append(
                    SemanticError(
                        "Constante booleana em 'case' requer recurso preview (JEP 530) e está desabilitada no modo padrão Java SE 26 (JLS §14.11.1).",
                        err_line,
                    )
                )
            elif kind in ("NUM", "INT") and val_s.lower().endswith("l") and not self.enable_preview_primitive_patterns:
                self.errors.append(
                    SemanticError(
                        "Constante do tipo 'long' em 'case' requer recurso preview (JEP 530) e está desabilitada no modo padrão Java SE 26 (JLS §14.11.1).",
                        err_line,
                    )
                )
            return
        if isinstance(const_expr, Identifier):
            sym = self._lookup_var_symbol(const_expr.name)
            if sym is not None and sym.get("is_pattern_var", False):
                self.errors.append(
                    SemanticError(
                        f"Expressão de 'case' deve ser constante em tempo de compilação; '{const_expr.name}' é variável de pattern (JLS §14.11.1).",
                        getattr(const_expr, "line", lb_line),
                    )
                )
                return
            if const_expr.name in enum_const_names or const_expr.name in self._static_imports or self._has_wildcard_static_import:
                return
            if sym is None:
                self.errors.append(
                    SemanticError(
                        f"Constante de 'case' inválida ou não declarada: '{const_expr.name}' (JLS §14.11.1).",
                        getattr(const_expr, "line", lb_line),
                    )
                )
            elif sym.get("category") not in ("constante_enum", "constante_interface") and not sym.get("is_compile_constant", False):
                self.errors.append(
                    SemanticError(
                        f"Expressão de 'case' deve ser constante em tempo de compilação; '{const_expr.name}' não é constante (JLS §14.11.1 / §15.29).",
                        getattr(const_expr, "line", lb_line),
                    )
                )
            return
        if isinstance(const_expr, MemberAccess) and isinstance(const_expr.target, Identifier):
            t_name = const_expr.target.name
            if t_name in self._enums:
                enum_decl = self._enums[t_name]
                valid_c = {c.name for c in getattr(enum_decl, "constants", [])}
                if const_expr.member_name not in valid_c:
                    self.errors.append(
                        SemanticError(
                            f"Constante '{const_expr.member_name}' não pertence ao enum '{t_name}' (JLS §14.11.1).",
                            getattr(const_expr, "line", lb_line),
                        )
                    )
            return
        if isinstance(const_expr, UnaryOp) and const_expr.op in ("+", "-", "~"):
            self._check_switch_constant_expr(const_expr.operand, lb_line, enum_const_names)
            return
        self.check_expression(const_expr)

    def _is_statement_expression(self, expr: ASTNode) -> bool:
        if isinstance(expr, ExpressionStatement):
            expr = expr.expression
        if isinstance(expr, (Assignment, MethodCall, ObjectCreationExpression)):
            return True
        if isinstance(expr, UnaryOp) and expr.op in ("++", "--", "post++", "post--"):
            return True
        return False

    def _record_unresolved(self, msg: str):
        """Registra verificação semântica parcial/adiada por ausência de tipos externos ou classpath."""
        if msg not in self.unresolved_checks:
            self.unresolved_checks.append(msg)

    @staticmethod
    def _split_type_dims(type_str: str) -> Tuple[str, int]:
        """Separa dimensões '[]' finais de uma string de tipo, retornando (base, dims)."""
        s = (type_str or "").strip()
        dims = 0
        while s.endswith("[]"):
            dims += 1
            s = s[:-2].strip()
        return s, dims

    @staticmethod
    def _strip_generics(type_str: Optional[str]) -> Optional[str]:
        """Remove argumentos genéricos <...> preservando sufixos de array []."""
        if not type_str:
            return type_str
        base, dims = SemanticAnalyzer._split_type_dims(type_str)
        out: List[str] = []
        depth = 0
        for ch in base:
            if ch == "<":
                depth += 1
            elif ch == ">":
                if depth > 0:
                    depth -= 1
            elif depth == 0:
                out.append(ch)
        cleaned = "".join(out).strip()
        if dims > 0:
            return cleaned + ("[]" * dims)
        return cleaned

    @staticmethod
    def _extract_generic_args(type_str: Optional[str]) -> Tuple[Optional[str], List[str], int]:
        """Retorna (nome_base_sem_generics, lista_args_genericos, dims)."""
        if not type_str:
            return None, [], 0
        s, dims = SemanticAnalyzer._split_type_dims(type_str)
        lt = s.find("<")
        if lt == -1 or not s.endswith(">"):
            return s, [], dims
        base = s[:lt].strip()
        inner = s[lt + 1:-1]
        args: List[str] = []
        cur: List[str] = []
        depth = 0
        for ch in inner:
            if ch == "<":
                depth += 1
                cur.append(ch)
            elif ch == ">":
                depth = max(0, depth - 1)
                cur.append(ch)
            elif ch == "," and depth == 0:
                part = "".join(cur).strip()
                if part:
                    args.append(part)
                cur = []
            else:
                cur.append(ch)
        tail = "".join(cur).strip()
        if tail:
            args.append(tail)
        return base, args, dims

    def _normalize_type_str(self, tref: Any) -> Optional[str]:
        """Normaliza TypeReference ou string para representação textual consistente."""
        if tref is None:
            return None
        if isinstance(tref, str):
            return tref.strip() or None
        if isinstance(tref, WildcardType):
            if tref.bound_kind == "extends" and tref.bound_type is not None:
                return self._normalize_type_str(tref.bound_type) or "Object"
            return "Object"
        if isinstance(tref, TypeReference):
            if getattr(tref, "full_name", None):
                return tref.full_name
            name = getattr(tref, "name", "")
            dims = getattr(tref, "dimensions", 0) or 0
            return f"{name}{'[]' * dims}" if name else None
        if hasattr(tref, "pretty"):
            return tref.pretty()
        return str(tref)

    def _simple_base_name(self, type_str: Optional[str]) -> Optional[str]:
        """Extrai o nome simples sem generics e sem qualificador de pacote."""
        if not type_str:
            return None
        stripped = self._strip_generics(type_str)
        if not stripped:
            return None
        base, dims = self._split_type_dims(stripped)
        simple = base.split(".")[-1]
        return simple + ("[]" * dims if dims > 0 else "")

    def _lookup_type_decl(self, type_name: Optional[str]) -> Optional[Tuple[str, ASTNode]]:
        """Busca declaração de tipo em escopos locais e na unidade de compilação."""
        if not type_name:
            return None
        stripped = self._strip_generics(type_name)
        if not stripped:
            return None
        base, dims = self._split_type_dims(stripped)
        if dims > 0 or base in self.PRIMITIVE_TYPES:
            return None
        simple = base.split(".")[-1]
        for lscope in reversed(self._local_declared_type_scopes):
            if base in lscope:
                return lscope[base]
            if simple in lscope:
                return lscope[simple]
        if base in self._declared_types:
            return self._declared_types[base]
        if simple in self._declared_types:
            return self._declared_types[simple]
        return None

    def _direct_supertypes(self, type_name: str) -> Tuple[List[str], bool]:
        """Retorna (supertipos_diretos, possui_supertipo_ou_tipo_externo)."""
        stripped = self._strip_generics(type_name) or ""
        base, dims = self._split_type_dims(stripped)
        if dims > 0:
            elem_base = base
            elem_full = f"{elem_base}{'[]' * (dims - 1)}"
            supers = ["Object", "Cloneable", "Serializable"]
            if elem_base not in self.PRIMITIVE_TYPES and elem_base != "Object":
                p_supers, ext = self._direct_supertypes(elem_base)
                for ps in p_supers:
                    supers.append(f"{ps}{'[]' * dims}")
                return supers, ext
            return supers, False

        simple = base.split(".")[-1]
        if simple == "Object":
            return [], False

        tdecl = self._lookup_type_decl(simple)
        if tdecl is not None:
            tkind, node = tdecl
            supers: List[str] = []
            if tkind == "class":
                ext = getattr(node, "extends_type", None)
                if ext is not None:
                    ext_s = self._normalize_type_str(ext)
                    if ext_s:
                        supers.append(ext_s)
                else:
                    supers.append("Object")
                for impl in getattr(node, "implements_types", []):
                    impl_s = self._normalize_type_str(impl)
                    if impl_s:
                        supers.append(impl_s)
            elif tkind == "interface":
                exts = getattr(node, "extends_types", [])
                for e in exts:
                    e_s = self._normalize_type_str(e)
                    if e_s:
                        supers.append(e_s)
                supers.append("Object")
            elif tkind == "record":
                supers.append("Record")
                for impl in getattr(node, "implements_types", []):
                    impl_s = self._normalize_type_str(impl)
                    if impl_s:
                        supers.append(impl_s)
                supers.append("Object")
            elif tkind == "enum":
                supers.append("Enum")
                for impl in getattr(node, "implements_types", []):
                    impl_s = self._normalize_type_str(impl)
                    if impl_s:
                        supers.append(impl_s)
                supers.append("Object")
            elif tkind == "annotation_interface":
                supers.extend(["Annotation", "Object"])
            return supers, False

        if simple in self.BUILTIN_TYPE_SUPERTYPES:
            return list(self.BUILTIN_TYPE_SUPERTYPES[simple]), False
        if simple in self.KNOWN_EXCEPTION_PARENTS:
            return [self.KNOWN_EXCEPTION_PARENTS[simple], "Object"], False
        return ["Object"], True

    def _is_known_type(self, type_name: Optional[str]) -> bool:
        """Indica se o tipo está declarado na unidade ou pertence ao núcleo embutido conhecido."""
        if not type_name:
            return False
        s = self._simple_base_name(type_name)
        if not s:
            return False
        base, dims = self._split_type_dims(s)
        if base in self.PRIMITIVE_TYPES:
            return True
        if base in self.BUILTIN_TYPE_SUPERTYPES or base in self.KNOWN_EXCEPTION_PARENTS:
            return True
        return self._lookup_type_decl(base) is not None

    def _is_final_or_closed_leaf(self, type_name: Optional[str]) -> bool:
        """Indica se um tipo não admite subtipos desconhecidos (final, record, enum ou array de final/primitivo)."""
        if not type_name:
            return False
        s = self._simple_base_name(type_name)
        if not s:
            return False
        base, dims = self._split_type_dims(s)
        if dims > 0:
            return base in self.PRIMITIVE_TYPES or self._is_final_or_closed_leaf(base)
        if base in self.PRIMITIVE_TYPES or base in self.BUILTIN_FINAL_TYPES:
            return True
        tdecl = self._lookup_type_decl(base)
        if tdecl is not None:
            tkind, node = tdecl
            if tkind in ("record", "enum"):
                return True
            if tkind == "class" and "final" in getattr(node, "modifiers", []):
                return True
        return False

    def _is_class_kind(self, type_name: Optional[str]) -> Optional[bool]:
        """Retorna True se é class/record/enum, False se é interface, None se desconhecido."""
        if not type_name:
            return None
        s = self._simple_base_name(type_name)
        if not s or s.endswith("[]"):
            return None
        tdecl = self._lookup_type_decl(s)
        if tdecl is not None:
            tkind, _ = tdecl
            return tkind in ("class", "record", "enum")
        if s in self.BUILTIN_CLASS_TYPES or s in self.KNOWN_EXCEPTION_PARENTS:
            return True
        if s in ("CharSequence", "Appendable", "Iterable", "Collection", "List", "Set", "Map", "Comparable", "Serializable", "Cloneable", "Runnable"):
            return False
        return None

    def _generic_args_compatible(self, sub_full: str, sup_full: str) -> Optional[bool]:
        """Verifica compatibilidade básica entre argumentos genéricos quando ambos são parametrizados no mesmo tipo base."""
        _, sub_args, sub_dims = self._extract_generic_args(sub_full)
        _, sup_args, sup_dims = self._extract_generic_args(sup_full)
        if sub_dims != sup_dims:
            return False
        if not sub_args or not sup_args:
            return True
        if len(sub_args) != len(sup_args):
            return False
        for sa, sb in zip(sub_args, sup_args):
            sa_s = sa.strip()
            sb_s = sb.strip()
            if sb_s == "?" or sa_s == sb_s:
                continue
            if sb_s.startswith("? extends "):
                bound = sb_s[len("? extends "):].strip()
                res = self._is_subtype(sa_s, bound)
                if res is False:
                    return False
                continue
            if sb_s.startswith("? super "):
                bound = sb_s[len("? super "):].strip()
                res = self._is_subtype(bound, sa_s)
                if res is False:
                    return False
                continue
            sa_simple = self._simple_base_name(sa_s)
            sb_simple = self._simple_base_name(sb_s)
            if sa_simple != sb_simple:
                return False
        return True

    def _is_subtype(self, sub: Optional[str], sup: Optional[str]) -> Optional[bool]:
        """Retorna True se sub <: sup, False se provadamente não, ou None se envolver hierarquia externa não resolvida."""
        if not sub or not sup:
            return None
        sub_s = self._simple_base_name(sub)
        sup_s = self._simple_base_name(sup)
        if not sub_s or not sup_s:
            return None
        if sub_s == "var" or sup_s == "var" or sub_s == "desconhecido" or sup_s == "desconhecido":
            return None
        if sub_s == "null":
            return sup_s not in self.PRIMITIVE_TYPES
        if sub_s in self.PRIMITIVE_TYPES or sup_s in self.PRIMITIVE_TYPES:
            return sub_s == sup_s
        if sub_s == sup_s:
            return self._generic_args_compatible(sub, sup)
        if sup_s == "Object":
            return True

        sub_base, sub_dims = self._split_type_dims(sub_s)
        sup_base, sup_dims = self._split_type_dims(sup_s)
        if sub_dims > 0 and sup_dims == 0:
            return sup_base in ("Object", "Cloneable", "Serializable")
        if sub_dims != sup_dims:
            return False
        if sub_dims > 0 and sup_dims > 0:
            if sub_base in self.PRIMITIVE_TYPES or sup_base in self.PRIMITIVE_TYPES:
                return sub_base == sup_base
            return self._is_subtype(sub_base, sup_base)

        queue: List[str] = [sub]
        visited: Set[str] = set()
        saw_external = False
        while queue:
            cur = queue.pop(0)
            cur_simple = self._simple_base_name(cur) or ""
            if cur_simple in visited:
                continue
            visited.add(cur_simple)
            if cur_simple == sup_s:
                return self._generic_args_compatible(cur, sup)
            supers, is_ext = self._direct_supertypes(cur)
            if is_ext:
                saw_external = True
            for s in supers:
                s_simple = self._simple_base_name(s) or ""
                if s_simple == sup_s:
                    # Verifica compatibilidade genérica caso haja argumentos no supertipo direto
                    _, cur_gen_args, _ = self._extract_generic_args(s)
                    _, sup_gen_args, _ = self._extract_generic_args(sup)
                    if cur_gen_args and sup_gen_args:
                        return self._generic_args_compatible(s, sup)
                    return True
                if s_simple not in visited:
                    queue.append(s)

        if saw_external:
            return None
        return False

    def _get_sealed_permitted_types(self, type_name: str) -> List[str]:
        """Obtém os subtipos permitidos de um tipo 'sealed' (explícitos via 'permits' ou implícitos na unidade)."""
        tdecl = self._lookup_type_decl(type_name)
        if tdecl is None:
            return []
        tkind, node = tdecl
        if "sealed" not in getattr(node, "modifiers", []):
            return []
        permits = getattr(node, "permits_types", [])
        if permits:
            res: List[str] = []
            for p in permits:
                ps = self._normalize_type_str(p)
                if ps:
                    res.append(ps)
            return res

        target_simple = self._simple_base_name(type_name)
        implicit: List[str] = []
        seen: Set[str] = set()

        def check_candidate(cname: str, ckind: str, cnode: ASTNode):
            if cname in seen or cname == target_simple:
                return
            refs: List[ASTNode] = []
            if ckind == "class":
                if getattr(cnode, "extends_type", None) is not None:
                    refs.append(cnode.extends_type)
                refs.extend(getattr(cnode, "implements_types", []))
            elif ckind == "interface":
                refs.extend(getattr(cnode, "extends_types", []))
            elif ckind in ("record", "enum"):
                refs.extend(getattr(cnode, "implements_types", []))
            for r in refs:
                r_simple = self._simple_base_name(self._normalize_type_str(r))
                if r_simple == target_simple:
                    seen.add(cname)
                    implicit.append(cname)
                    break

        for scope in self._local_declared_type_scopes:
            for cname, (ckind, cnode) in scope.items():
                check_candidate(cname, ckind, cnode)
        for cname, (ckind, cnode) in self._declared_types.items():
            check_candidate(cname, ckind, cnode)
        return implicit

    def _are_preview_primitive_types_disjoint(self, s1: str, s2: str) -> Optional[bool]:
        """Verifica disjunção parcial para modo preview JEP 530 entre tipos primitivos e referências."""
        if s1 in self.PRIMITIVE_TYPES and s2 in self.PRIMITIVE_TYPES:
            if s1 == s2:
                return False
            if s1 == "boolean" or s2 == "boolean":
                return True
            return False

        prim, ref = (s1, s2) if s1 in self.PRIMITIVE_TYPES else (s2, s1)
        ref_base, ref_dims = self._split_type_dims(ref)
        if ref_dims > 0:
            return True
        if ref_base in ("Object", "Serializable", "Comparable"):
            return False
        if ref_base == "Number":
            return prim == "boolean"
        if ref_base in self.WRAPPER_TO_PRIMITIVE:
            wp = self.WRAPPER_TO_PRIMITIVE[ref_base]
            if prim == "boolean" or wp == "boolean":
                return prim != wp
            return False
        if not self._is_known_type(ref_base):
            return None
        return True

    def _are_types_disjoint(self, t1: Optional[str], t2: Optional[str]) -> Optional[bool]:
        """Retorna True se dois tipos são provadamente disjuntos (pattern inaplicável/incompatível), False ou None."""
        if not t1 or not t2:
            return None
        s1 = self._simple_base_name(t1)
        s2 = self._simple_base_name(t2)
        if not s1 or not s2 or "Object" in (s1, s2) or "var" in (s1, s2) or "desconhecido" in (s1, s2):
            return False
        if s1 in self.PRIMITIVE_TYPES or s2 in self.PRIMITIVE_TYPES:
            if not self.enable_preview_primitive_patterns:
                return s1 != s2
            return self._are_preview_primitive_types_disjoint(s1, s2)
        sub12 = self._is_subtype(t1, t2)
        sub21 = self._is_subtype(t2, t1)
        if sub12 is True or sub21 is True:
            return False

        b1, d1 = self._split_type_dims(s1)
        b2, d2 = self._split_type_dims(s2)
        if (d1 > 0 or d2 > 0) and d1 != d2:
            return True
        if d1 > 0 and d2 > 0:
            return self._are_types_disjoint(b1, b2)

        if self._is_final_or_closed_leaf(t1) or self._is_final_or_closed_leaf(t2):
            if sub12 is False and sub21 is False:
                return True

        k1 = self._is_class_kind(t1)
        k2 = self._is_class_kind(t2)
        if k1 is True and k2 is True and sub12 is False and sub21 is False:
            return True

        # Verifica hierarquia sealed fechada de t1 contra t2 e vice-versa
        for sealed_t, other_t in ((t1, t2), (t2, t1)):
            permits = self._get_sealed_permitted_types(sealed_t)
            if permits:
                all_disjoint = True
                for pt in permits:
                    d_res = self._are_types_disjoint(pt, other_t)
                    if d_res is not True:
                        all_disjoint = False
                        break
                if all_disjoint:
                    return True

        if not self._is_known_type(t1) or not self._is_known_type(t2):
            return None
        return False

    def _substitute_type_str(self, type_str: str, subst: Dict[str, str]) -> str:
        """Substitui parâmetros genéricos em um tipo de componente de record usando o mapa subst."""
        if not subst or not type_str:
            return type_str
        base, args, dims = self._extract_generic_args(type_str)
        if base in subst and not args:
            return subst[base] + ("[]" * dims)
        if args:
            new_args = [self._substitute_type_str(a, subst) for a in args]
            return f"{base}<{', '.join(new_args)}>{'[]' * dims}"
        return type_str

    def _get_record_component_types(
        self,
        rec_type_ref_or_name: Any,
        seen_records: Optional[Set[str]] = None,
    ) -> Optional[List[str]]:
        """Retorna os tipos (com substituição genérica quando possível) dos componentes de um record."""
        r_str = self._normalize_type_str(rec_type_ref_or_name)
        if not r_str:
            return None
        tdecl = self._lookup_type_decl(r_str)
        if tdecl is None or tdecl[0] != "record" or not isinstance(tdecl[1], RecordDeclaration):
            return None
        rnode = tdecl[1]
        subst: Dict[str, str] = {}
        _, gargs, _ = self._extract_generic_args(r_str)
        tparams = getattr(rnode, "type_parameters", []) or []
        if gargs and tparams:
            for tp, ga in zip(tparams, gargs):
                tp_name = getattr(tp, "name", None) or str(tp)
                if ga.strip() == "?":
                    subst[tp_name] = "Object"
                elif ga.strip().startswith("? extends "):
                    subst[tp_name] = ga.strip()[len("? extends "):].strip()
                elif ga.strip().startswith("? super "):
                    subst[tp_name] = "Object"
                else:
                    subst[tp_name] = ga.strip()
        elif tparams and not gargs:
            # Record bruto (raw): parâmetros genéricos substituem para Object
            for tp in tparams:
                tp_name = getattr(tp, "name", None) or str(tp)
                subst[tp_name] = "Object"

        comp_types: List[str] = []
        for comp in getattr(rnode, "components", []):
            ct = getattr(comp, "effective_type", None) or self._normalize_type_str(getattr(comp, "type_ref", None)) or "Object"
            comp_types.append(self._substitute_type_str(ct, subst))
        return comp_types

    def _check_pattern_type_compatibility(self, source_type: Optional[str], pat_type: Optional[str], line: int, is_component: bool):
        """Verifica aplicabilidade/compatibilidade entre o tipo alvo/seletor e o tipo de um pattern."""
        if not source_type or not pat_type or pat_type == "var":
            return
        disjoint = self._are_types_disjoint(source_type, pat_type)
        if disjoint is True:
            ctx = "componente de record" if is_component else "expressão/seletor"
            self.errors.append(
                SemanticError(
                    f"Tipos incompatíveis: {ctx} do tipo '{source_type}' não pode casar com pattern de tipo '{pat_type}' (JLS §14.30.3 / §15.20.2).",
                    line,
                )
            )
        elif disjoint is None and (not self._is_known_type(source_type) or not self._is_known_type(pat_type)):
            self._record_unresolved(
                f"Compatibilidade entre '{source_type}' e pattern '{pat_type}' envolve tipo externo não declarado na unidade."
            )

    def _analyze_pattern(
        self,
        pattern: Optional[ASTNode],
        selector_type: Optional[str] = None,
        is_component: bool = False,
        expected_comp_type: Optional[str] = None,
        seen_pattern_vars: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Valida sintaxe contextual, variáveis, record arity, generics e preview rules de um pattern (JLS §14.30)."""
        collected: Dict[str, Dict[str, Any]] = {}
        if pattern is None:
            return collected
        if seen_pattern_vars is None:
            seen_pattern_vars = {}

        if isinstance(pattern, MatchAllPattern):
            if not is_component:
                self.errors.append(
                    SemanticError(
                        "Pattern irrestrito '_' (match-all) só é permitido como componente dentro de um record pattern (JLS §14.30.1).",
                        getattr(pattern, "line", 1),
                    )
                )
            return collected

        if isinstance(pattern, TypePattern):
            p_line = getattr(pattern, "line", 1)
            tref = getattr(pattern, "type_ref", None)
            is_var = getattr(pattern, "is_var", False) or (tref is not None and getattr(tref, "name", "") == "var")
            is_unnamed = getattr(pattern, "is_unnamed", False) or getattr(pattern, "name", "") == "_"
            mods = getattr(pattern, "modifiers", []) or []
            is_final = getattr(pattern, "is_final", False) or ("final" in mods)
            for mod in mods:
                if mod != "final":
                    self.errors.append(
                        SemanticError(
                            f"Modificador '{mod}' não é permitido em TypePattern; apenas 'final' e anotações são válidos (JLS §14.30.1).",
                            p_line,
                        )
                    )
            self._analyze_annotations(
                getattr(pattern, "annotations", []),
                valid_targets={"LOCAL_VARIABLE"},
                adjacent_type_ref=tref,
            )
            if tref is not None and not is_var:
                self._check_type_ref_annotations(tref)

            if is_var and not is_component:
                self.errors.append(
                    SemanticError(
                        "Inferência de tipo 'var' em pattern só é permitida para componentes dentro de record pattern (JLS §14.30.1).",
                        p_line,
                    )
                )

            raw_type = self._normalize_type_str(tref) or getattr(pattern, "type_name", None)
            if raw_type == "void":
                self.errors.append(
                    SemanticError("O tipo 'void' não é permitido em pattern (JLS §14.30.1).", p_line)
                )

            target_source_type = expected_comp_type if is_component else selector_type
            resolved_var_type = (expected_comp_type or "Object") if is_var else (raw_type or "Object")

            raw_base, raw_dims = self._split_type_dims(self._strip_generics(raw_type) or "")
            if (not is_var) and raw_dims == 0 and raw_base in self.PRIMITIVE_TYPES:
                if not self.enable_preview_primitive_patterns:
                    ctx_msg = "componente de RecordPattern" if is_component else "nível superior"
                    self.errors.append(
                        SemanticError(
                            f"Pattern com tipo primitivo '{raw_type}' em {ctx_msg} pertence ao recurso preview (JEP 530) e está desabilitado no modo padrão Java SE 26 (JLS §14.30.1).",
                            p_line,
                        )
                    )
                elif target_source_type:
                    self._check_pattern_type_compatibility(target_source_type, raw_type, p_line, is_component=is_component)
            else:
                if not is_component and target_source_type:
                    src_base, src_dims = self._split_type_dims(self._strip_generics(target_source_type) or "")
                    if src_dims == 0 and src_base in self.PRIMITIVE_TYPES and not self.enable_preview_primitive_patterns:
                        self.errors.append(
                            SemanticError(
                                f"Expressão/seletor de tipo primitivo '{target_source_type}' não suporta pattern matching no modo padrão Java SE 26 (JLS §14.30.3 / §15.20.2).",
                                p_line,
                            )
                        )
                    else:
                        self._check_pattern_type_compatibility(target_source_type, raw_type, p_line, is_component=False)
                elif is_component and not is_var and target_source_type:
                    self._check_pattern_type_compatibility(target_source_type, raw_type, p_line, is_component=True)

            vname = getattr(pattern, "name", None)
            if not is_unnamed and vname:
                if vname in seen_pattern_vars:
                    self.errors.append(
                        SemanticError(
                            f"Variável de pattern '{vname}' declarada novamente no mesmo pattern (linha {seen_pattern_vars[vname]} — JLS §14.30.1).",
                            p_line,
                        )
                    )
                else:
                    conflict = self._find_local_var_info(vname)
                    if conflict is not None:
                        self.errors.append(
                            SemanticError(
                                f"Variável de pattern '{vname}' conflita com variável ou parâmetro já em escopo na linha {conflict['line']} (JLS §6.3 / §6.4.1).",
                                p_line,
                            )
                        )
                    seen_pattern_vars[vname] = p_line
                    collected[vname] = {
                        "type": resolved_var_type,
                        "line": p_line,
                        "is_final": is_final,
                        "reassigned": False,
                        "has_initializer": True,
                        "category": "variavel",
                    }
            return collected

        if isinstance(pattern, RecordPattern):
            p_line = getattr(pattern, "line", 1)
            tref = getattr(pattern, "type_ref", None)
            if tref is not None and getattr(tref, "annotations", None):
                self.errors.append(
                    SemanticError(
                        "Anotações não são permitidas diretamente sobre o ReferenceType de um RecordPattern (JLS §14.30.1).",
                        p_line,
                    )
                )
            if tref is not None:
                for ta in getattr(tref, "type_arguments", []):
                    self._check_type_ref_annotations(ta)

            r_type = self._normalize_type_str(tref) or getattr(pattern, "type_name", None) or ""
            target_source_type = expected_comp_type if is_component else selector_type
            if target_source_type:
                src_base, src_dims = self._split_type_dims(self._strip_generics(target_source_type) or "")
                if src_dims == 0 and src_base in self.PRIMITIVE_TYPES and not self.enable_preview_primitive_patterns:
                    self.errors.append(
                        SemanticError(
                            f"Expressão/seletor de tipo primitivo '{target_source_type}' não pode casar com record pattern '{r_type}' (JLS §14.30.1).",
                            p_line,
                        )
                    )
                else:
                    self._check_pattern_type_compatibility(target_source_type, r_type, p_line, is_component=is_component)

            tdecl = self._lookup_type_decl(r_type)
            comps = getattr(pattern, "components", []) or []
            if tdecl is not None:
                tkind, rnode = tdecl
                if tkind != "record" or not isinstance(rnode, RecordDeclaration):
                    self.errors.append(
                        SemanticError(
                            f"Tipo '{r_type}' é '{tkind}' e não um 'record'; record pattern inválido (JLS §14.30.1).",
                            p_line,
                        )
                    )
                    for cp in comps:
                        collected.update(
                            self._analyze_pattern(cp, is_component=True, expected_comp_type=None, seen_pattern_vars=seen_pattern_vars)
                        )
                    return collected

                expected_comps = getattr(rnode, "components", []) or []
                if len(comps) != len(expected_comps):
                    self.errors.append(
                        SemanticError(
                            f"Record pattern '{r_type}' espera {len(expected_comps)} componente(s), mas recebeu {len(comps)} (JLS §14.30.1).",
                            p_line,
                        )
                    )
                g_tparams = getattr(rnode, "type_parameters", []) or []
                _, g_args, _ = self._extract_generic_args(r_type)
                if g_args and g_tparams and len(g_args) != len(g_tparams):
                    self.errors.append(
                        SemanticError(
                            f"Número de argumentos genéricos incompatível em record pattern '{r_type}' (esperado {len(g_tparams)}, encontrado {len(g_args)}).",
                            p_line,
                        )
                    )
                comp_types = self._get_record_component_types(tref or r_type) or []
                for idx, cp in enumerate(comps):
                    exp_ct = comp_types[idx] if idx < len(comp_types) else None
                    collected.update(
                        self._analyze_pattern(
                            cp,
                            is_component=True,
                            expected_comp_type=exp_ct,
                            seen_pattern_vars=seen_pattern_vars,
                        )
                    )
            else:
                self._record_unresolved(
                    f"Record externo '{r_type}' não declarado na unidade atual: natureza de record, aridade e tipos dos componentes não puderam ser validados completamente."
                )
                for cp in comps:
                    collected.update(
                        self._analyze_pattern(cp, is_component=True, expected_comp_type=None, seen_pattern_vars=seen_pattern_vars)
                    )
            return collected

        return collected

    def _push_pattern_scope(self, pvars: Dict[str, Dict[str, Any]]):
        """Empilha um escopo temporário de variáveis de pattern."""
        self._active_pattern_scopes.append(dict(pvars))

    def _pop_pattern_scope(self):
        """Desempilha o escopo temporário de variáveis de pattern."""
        if self._active_pattern_scopes:
            self._active_pattern_scopes.pop()

    def _inject_pattern_vars_into_enclosing_block(self, pvars: Dict[str, Dict[str, Any]]):
        """Injeta variáveis de pattern válidas no escopo do bloco imediatamente envolvente (JLS §6.3.2)."""
        if not pvars:
            return
        if not self._active_pattern_scopes:
            self._active_pattern_scopes.append({})
        target = self._active_pattern_scopes[-1]
        for vname, vinfo in pvars.items():
            if vname == "_":
                continue
            existing_pat = None
            for pscope in reversed(self._active_pattern_scopes):
                if vname in pscope:
                    existing_pat = pscope[vname]
                    break
            existing_loc = None
            for lscope in reversed(self._local_var_scopes):
                if vname in lscope:
                    existing_loc = lscope[vname]
                    break
            if existing_pat is not None:
                self.errors.append(
                    SemanticError(
                        f"Variável de pattern '{vname}' já está em escopo neste bloco (linha {existing_pat['line']} — JLS §6.3).",
                        vinfo.get("line", 1),
                    )
                )
            elif existing_loc is not None:
                self.errors.append(
                    SemanticError(
                        f"Variável de pattern '{vname}' conflita com variável local na linha {existing_loc['line']} (JLS §6.3).",
                        vinfo.get("line", 1),
                    )
                )
            else:
                target[vname] = dict(vinfo)

    def _pattern_has_named_vars(self, pattern: Optional[ASTNode]) -> bool:
        """Retorna True se o pattern ou seus componentes declararem alguma variável nomeada (não '_')."""
        if isinstance(pattern, TypePattern):
            is_unnamed = getattr(pattern, "is_unnamed", False) or getattr(pattern, "name", "") == "_"
            return (not is_unnamed) and bool(getattr(pattern, "name", None))
        if isinstance(pattern, RecordPattern):
            return any(self._pattern_has_named_vars(c) for c in getattr(pattern, "components", []))
        return False

    def _eval_constant_boolean(self, expr: Optional[ASTNode]) -> Optional[bool]:
        """Avalia expressões booleanas constantes simples em tempo de compilação (usado em guards e laços)."""
        if expr is None:
            return None
        if isinstance(expr, Literal) and getattr(expr, "kind", "") == "BOOLEAN":
            return str(expr.value).lower() == "true"
        if isinstance(expr, UnaryOp) and expr.op == "!":
            v = self._eval_constant_boolean(expr.operand)
            return (not v) if v is not None else None
        if isinstance(expr, BinaryOp):
            if expr.op == "&&":
                lv = self._eval_constant_boolean(expr.left)
                if lv is False:
                    return False
                rv = self._eval_constant_boolean(expr.right)
                if rv is False:
                    return False
                if lv is True and rv is True:
                    return True
                return None
            if expr.op == "||":
                lv = self._eval_constant_boolean(expr.left)
                if lv is True:
                    return True
                rv = self._eval_constant_boolean(expr.right)
                if rv is True:
                    return True
                if lv is False and rv is False:
                    return False
                return None
            if expr.op in ("==", "!=", "<", "<=", ">", ">="):
                lv = self._eval_constant_scalar(expr.left)
                rv = self._eval_constant_scalar(expr.right)
                if lv is not None and rv is not None and type(lv) is type(rv):
                    try:
                        if expr.op == "==":
                            return lv == rv
                        if expr.op == "!=":
                            return lv != rv
                        if not isinstance(lv, bool):
                            if expr.op == "<":
                                return lv < rv
                            if expr.op == "<=":
                                return lv <= rv
                            if expr.op == ">":
                                return lv > rv
                            if expr.op == ">=":
                                return lv >= rv
                    except TypeError:
                        return None
        return None

    def _eval_constant_scalar(self, expr: Optional[ASTNode]) -> Any:
        """Avalia literal escalar constante simples (boolean, int, String)."""
        if isinstance(expr, Literal):
            k = getattr(expr, "kind", "")
            if k == "BOOLEAN":
                return str(expr.value).lower() == "true"
            if k in ("NUM", "INT"):
                try:
                    return int(str(expr.value).replace("_", ""), 0)
                except ValueError:
                    return None
            if k in ("STRING", "TEXT_BLOCK"):
                return str(expr.value)
        if isinstance(expr, UnaryOp) and expr.op in ("+", "-"):
            inner = self._eval_constant_scalar(expr.operand)
            if isinstance(inner, int) and not isinstance(inner, bool):
                return -inner if expr.op == "-" else inner
        return None

    def _stmt_completes_normally(self, stmt: Optional[ASTNode]) -> bool:
        """Estimativa conservadora de conclusão normal de instruções segundo JLS §14.22 (para escopo JLS §6.3)."""
        if stmt is None or isinstance(stmt, EmptyStatement):
            return True
        if isinstance(stmt, (ReturnStatement, ThrowStatement, YieldStatement, BreakStatement, ContinueStatement)):
            return False
        if isinstance(stmt, Block):
            for s in stmt.statements:
                if not self._stmt_completes_normally(s):
                    return False
            return True
        if isinstance(stmt, LabeledStatement):
            inner_norm = self._stmt_completes_normally(stmt.statement)
            return inner_norm or self._contains_break_targeting(stmt.statement, target_label=stmt.label)
        if isinstance(stmt, IfStatement):
            c_val = self._eval_constant_boolean(stmt.condition)
            if stmt.else_branch is None:
                if c_val is True:
                    return self._stmt_completes_normally(stmt.then_branch)
                return True
            if c_val is True:
                return self._stmt_completes_normally(stmt.then_branch)
            if c_val is False:
                return self._stmt_completes_normally(stmt.else_branch)
            return self._stmt_completes_normally(stmt.then_branch) or self._stmt_completes_normally(stmt.else_branch)
        if isinstance(stmt, WhileStatement):
            c_val = self._eval_constant_boolean(stmt.condition)
            if c_val is True:
                return self._contains_break_targeting(stmt.body, target_label=None)
            return True
        if isinstance(stmt, DoWhileStatement):
            c_val = self._eval_constant_boolean(stmt.condition)
            if c_val is True:
                return self._contains_break_targeting(stmt.body, target_label=None)
            return self._stmt_completes_normally(stmt.body) or self._contains_continue_to_current_loop(stmt.body) or self._contains_break_targeting(stmt.body, target_label=None)
        if isinstance(stmt, ForStatement):
            if stmt.condition is None or self._eval_constant_boolean(stmt.condition) is True:
                return self._contains_break_targeting(stmt.body, target_label=None)
            return True
        if isinstance(stmt, TryStatement):
            if stmt.finally_block is not None and not self._stmt_completes_normally(stmt.finally_block):
                return False
            if self._stmt_completes_normally(stmt.try_block):
                return True
            return any(self._stmt_completes_normally(c.body) for c in getattr(stmt, "catch_clauses", []))
        if isinstance(stmt, SynchronizedStatement):
            return self._stmt_completes_normally(stmt.body)
        return True

    def _contains_break_targeting(
        self,
        node: Optional[ASTNode],
        target_label: Optional[str] = None,
        extra_labels: Optional[Set[str]] = None,
        in_nested_loop_or_switch: bool = False,
    ) -> bool:
        """Verifica se há BreakStatement direcionado ao laço/label alvo."""
        if node is None:
            return False
        if isinstance(node, BreakStatement):
            if node.label is None:
                return (target_label is None) and (not in_nested_loop_or_switch)
            if target_label is not None and node.label == target_label:
                return True
            if extra_labels and node.label in extra_labels:
                return True
            return False
        if isinstance(node, (LambdaExpression, ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
            return False
        if isinstance(node, (WhileStatement, DoWhileStatement, ForStatement, EnhancedForStatement, SwitchStatement, SwitchExpression)):
            in_nested_loop_or_switch = True
        if hasattr(node, "__dict__"):
            for val in node.__dict__.values():
                if isinstance(val, ASTNode):
                    if self._contains_break_targeting(val, target_label, extra_labels, in_nested_loop_or_switch):
                        return True
                elif isinstance(val, (list, tuple)):
                    for item in val:
                        if isinstance(item, ASTNode) and self._contains_break_targeting(item, target_label, extra_labels, in_nested_loop_or_switch):
                            return True
        return False

    def _contains_continue_to_current_loop(self, node: Optional[ASTNode], in_nested_loop: bool = False) -> bool:
        """Verifica se há ContinueStatement não rotulado direcionado ao laço atual."""
        if node is None:
            return False
        if isinstance(node, ContinueStatement):
            return (node.label is None) and (not in_nested_loop)
        if isinstance(node, (LambdaExpression, ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
            return False
        if isinstance(node, (WhileStatement, DoWhileStatement, ForStatement, EnhancedForStatement)):
            in_nested_loop = True
        if hasattr(node, "__dict__"):
            for val in node.__dict__.values():
                if isinstance(val, ASTNode) and self._contains_continue_to_current_loop(val, in_nested_loop):
                    return True
                elif isinstance(val, (list, tuple)):
                    for item in val:
                        if isinstance(item, ASTNode) and self._contains_continue_to_current_loop(item, in_nested_loop):
                            return True
        return False

    def _is_pattern_unconditional(self, pattern: Optional[ASTNode], target_type: Optional[str]) -> Optional[bool]:
        """Indica se um pattern casa incondicionalmente com qualquer valor não nulo de target_type (JLS §14.30.3)."""
        if pattern is None:
            return False
        if isinstance(pattern, MatchAllPattern):
            return True
        if isinstance(pattern, TypePattern):
            if getattr(pattern, "is_var", False) or (getattr(pattern, "type_ref", None) and getattr(pattern.type_ref, "name", "") == "var"):
                return True
            p_type = self._normalize_type_str(getattr(pattern, "type_ref", None)) or getattr(pattern, "type_name", None)
            if not target_type:
                return p_type == "Object"
            return self._is_subtype(target_type, p_type)
        if isinstance(pattern, RecordPattern):
            r_type = self._normalize_type_str(getattr(pattern, "type_ref", None)) or getattr(pattern, "type_name", None)
            if not target_type:
                return False
            sub = self._is_subtype(target_type, r_type)
            if sub is not True:
                return sub
            comp_types = self._get_record_component_types(getattr(pattern, "type_ref", None) or r_type)
            if comp_types is None or len(comp_types) != len(getattr(pattern, "components", [])):
                return None
            all_true = True
            for cp, ct in zip(pattern.components, comp_types):
                c_uncond = self._is_pattern_unconditional(cp, ct)
                if c_uncond is False:
                    return False
                if c_uncond is None:
                    all_true = False
            return True if all_true else None
        return False

    def _pattern_dominates(
        self,
        p1: Optional[ASTNode],
        p2: Optional[ASTNode],
        target_type: Optional[str] = None,
    ) -> Tuple[Optional[bool], bool]:
        """Verifica se p1 domina p2 segundo JLS §14.30.3. Retorna (domina_ou_None, houve_externo)."""
        if p1 is None or p2 is None:
            return False, False
        if isinstance(p1, MatchAllPattern):
            return True, False
        if isinstance(p1, TypePattern):
            if getattr(p1, "is_var", False) or (getattr(p1, "type_ref", None) and getattr(p1.type_ref, "name", "") == "var"):
                return True, False
            t1 = self._normalize_type_str(getattr(p1, "type_ref", None)) or getattr(p1, "type_name", None)
            if isinstance(p2, MatchAllPattern):
                if not target_type:
                    return (True, False) if self._simple_base_name(t1) == "Object" else (None, True)
                sub = self._is_subtype(target_type, t1)
                return sub, (sub is None)
            if isinstance(p2, TypePattern):
                is_var2 = getattr(p2, "is_var", False) or (getattr(p2, "type_ref", None) and getattr(p2.type_ref, "name", "") == "var")
                t2 = (target_type or "Object") if is_var2 else (self._normalize_type_str(getattr(p2, "type_ref", None)) or getattr(p2, "type_name", None))
                if self.enable_preview_primitive_patterns and t1 == "Object" and t2 in self.PRIMITIVE_TYPES:
                    return True, False
                sub = self._is_subtype(t2, t1)
                return sub, (sub is None)
            if isinstance(p2, RecordPattern):
                t2 = self._normalize_type_str(getattr(p2, "type_ref", None)) or getattr(p2, "type_name", None)
                sub = self._is_subtype(t2, t1)
                return sub, (sub is None)
            return False, False

        if isinstance(p1, RecordPattern):
            r1 = self._normalize_type_str(getattr(p1, "type_ref", None)) or getattr(p1, "type_name", None)
            c1 = getattr(p1, "components", []) or []
            if isinstance(p2, MatchAllPattern):
                if not target_type:
                    return False, False
                uncond = self._is_pattern_unconditional(p1, target_type)
                return uncond, (uncond is None)
            if isinstance(p2, TypePattern):
                is_var2 = getattr(p2, "is_var", False) or (getattr(p2, "type_ref", None) and getattr(p2.type_ref, "name", "") == "var")
                t2 = target_type if is_var2 else (self._normalize_type_str(getattr(p2, "type_ref", None)) or getattr(p2, "type_name", None))
                if not t2:
                    return False, False
                uncond = self._is_pattern_unconditional(p1, t2)
                return uncond, (uncond is None)
            if isinstance(p2, RecordPattern):
                r2 = self._normalize_type_str(getattr(p2, "type_ref", None)) or getattr(p2, "type_name", None)
                c2 = getattr(p2, "components", []) or []
                sub = self._is_subtype(r2, r1)
                if sub is False:
                    return False, False
                if sub is None:
                    return None, True
                if len(c1) != len(c2):
                    return False, False
                comp_types = self._get_record_component_types(getattr(p2, "type_ref", None) or r2)
                saw_unres = False
                for idx, (sub_p1, sub_p2) in enumerate(zip(c1, c2)):
                    ct = comp_types[idx] if comp_types and idx < len(comp_types) else None
                    dom, unres = self._pattern_dominates(sub_p1, sub_p2, ct)
                    if unres:
                        saw_unres = True
                    if dom is False:
                        return False, saw_unres
                    if dom is None:
                        return None, True
                return True, False
        return False, False

    def _switch_constant_type(self, const_expr: ASTNode, selector_type: Optional[str] = None) -> Optional[str]:
        """Infere o tipo de uma constante de 'case' para verificação de dominância (JLS §14.11.1)."""
        if isinstance(const_expr, Literal):
            kind = getattr(const_expr, "kind", "")
            val_s = str(getattr(const_expr, "value", ""))
            if kind in ("STRING", "TEXT_BLOCK"):
                return "String"
            if kind in ("NUM", "INT"):
                if val_s.lower().endswith("l"):
                    return "Long" if selector_type not in self.PRIMITIVE_TYPES else "long"
                return "Integer" if selector_type not in self.PRIMITIVE_TYPES else "int"
            if kind == "FLOAT":
                return "Float" if selector_type not in self.PRIMITIVE_TYPES else "float"
            if kind == "DOUBLE":
                return "Double" if selector_type not in self.PRIMITIVE_TYPES else "double"
            if kind == "CHAR":
                return "Character" if selector_type not in self.PRIMITIVE_TYPES else "char"
            if kind == "BOOLEAN":
                return "Boolean" if selector_type not in self.PRIMITIVE_TYPES else "boolean"
            if kind == "NULL":
                return "null"
        if isinstance(const_expr, Identifier):
            if selector_type and self._simple_base_name(selector_type) in self._enums:
                ename = self._simple_base_name(selector_type)
                econsts = {c.name for c in getattr(self._enums[ename], "constants", [])}
                if const_expr.name in econsts:
                    return ename
            for ename, edecl in self._enums.items():
                if const_expr.name in {c.name for c in getattr(edecl, "constants", [])}:
                    return ename
            sym = self._lookup_var_symbol(const_expr.name)
            if sym and "type" in sym:
                t = sym["type"]
                return self._boxed_type(t) if (t in self.PRIMITIVE_TYPES and selector_type not in self.PRIMITIVE_TYPES) else t
        if isinstance(const_expr, MemberAccess) and isinstance(const_expr.target, Identifier):
            return const_expr.target.name
        if isinstance(const_expr, UnaryOp):
            return self._switch_constant_type(const_expr.operand, selector_type)
        return None

    @staticmethod
    def _boxed_type(prim: str) -> str:
        return {
            "byte": "Byte",
            "short": "Short",
            "int": "Integer",
            "long": "Long",
            "float": "Float",
            "double": "Double",
            "char": "Character",
            "boolean": "Boolean",
        }.get(prim, prim)

    def _pattern_dominates_constant(self, pattern: ASTNode, const_type: Optional[str]) -> Optional[bool]:
        """Indica se um pattern incondicional domina uma constante de tipo const_type."""
        if not const_type or const_type == "null":
            return False
        if isinstance(pattern, MatchAllPattern):
            return True
        if isinstance(pattern, TypePattern):
            p_type = self._normalize_type_str(getattr(pattern, "type_ref", None)) or getattr(pattern, "type_name", None)
            if not p_type:
                return False
            sub = self._is_subtype(const_type, p_type)
            if sub is None and const_type in self.PRIMITIVE_TYPES:
                return self._is_subtype(self._boxed_type(const_type), p_type)
            return sub
        return False

    def _max_pattern_depth(self, pat: Optional[ASTNode]) -> int:
        if not isinstance(pat, RecordPattern):
            return 0
        comps = getattr(pat, "components", []) or []
        if not comps:
            return 1
        return 1 + max(self._max_pattern_depth(c) for c in comps)

    def _is_vector_covered(
        self,
        types: List[str],
        matrix: List[List[ASTNode]],
        max_rec_depth: int,
        depth: int = 0,
    ) -> Tuple[bool, bool]:
        """
        Verifica cobertura/exaustividade de uma tupla de tipos `types` contra uma matriz de patterns
        (inclui tipos sealed, enums, booleans e records aninhados/recursivos — JLS §14.11.1.1).
        Retorna (coberto, encontrou_tipo_externo_nao_resolvido).
        """
        if not types:
            return (len(matrix) > 0), False
        if not matrix:
            return False, not self._is_known_type(types[0])

        t0 = types[0]
        rest_types = types[1:]
        t0_simple = self._simple_base_name(t0) or ""

        # Caso 1: Qualquer linha cujo pattern 0 seja incondicional para t0 e cubra rest_types garante cobertura se sufixos cobrirem
        # Primeiro separa as linhas wildcard/incondicionais para t0:
        uncond_suffixes: List[List[ASTNode]] = []
        for row in matrix:
            p0 = row[0]
            if self._is_pattern_unconditional(p0, t0) is True:
                uncond_suffixes.append(row[1:])
        if uncond_suffixes:
            cov_rest, unres_rest = self._is_vector_covered(rest_types, uncond_suffixes, max_rec_depth, depth)
            if cov_rest:
                return True, unres_rest

        # Caso 2: t0 é tipo sealed declarado na unidade -> precisa cobrir TODOS os subtipos permitidos
        tdecl = self._lookup_type_decl(t0_simple)
        if tdecl is not None and "sealed" in getattr(tdecl[1], "modifiers", []):
            permits = self._get_sealed_permitted_types(t0)
            if not permits:
                self._record_unresolved(
                    f"Tipo sealed '{t0}' não possui subtipos permitidos visíveis nesta unidade de compilação."
                )
                return False, True
            saw_unres = False
            for pt in permits:
                # Reutiliza matrix original: subtipo pt herda cobertura de patterns supertipo (p0 >= pt ou RecordPattern pt)
                sub_cov, sub_unres = self._is_vector_covered([pt] + rest_types, matrix, max_rec_depth, depth)
                if sub_unres:
                    saw_unres = True
                if not sub_cov:
                    return False, saw_unres
            return True, saw_unres

        # Caso 3: t0 é um record declarado -> desconstruir componentes [C1..Ck] apenas até max_rec_depth
        if tdecl is not None and tdecl[0] == "record" and isinstance(tdecl[1], RecordDeclaration) and depth < max_rec_depth + 1:
            comp_types = self._get_record_component_types(t0) or []
            k = len(comp_types)
            rec_matrix: List[List[ASTNode]] = []
            for row in matrix:
                p0 = row[0]
                if isinstance(p0, RecordPattern):
                    pr_name = self._normalize_type_str(getattr(p0, "type_ref", None)) or getattr(p0, "type_name", None)
                    if self._is_subtype(t0, pr_name) is True and len(getattr(p0, "components", [])) == k:
                        rec_matrix.append(list(p0.components) + row[1:])
                elif self._is_pattern_unconditional(p0, t0) is True:
                    rec_matrix.append([MatchAllPattern() for _ in range(k)] + row[1:])
            if rec_matrix:
                return self._is_vector_covered(comp_types + rest_types, rec_matrix, max_rec_depth, depth + 1)
            return False, False

        # Caso 4: Enum ou boolean em coluna interna de record não tem constante em pattern (só TypePattern/var/_),
        # mas se houve padrão incondicional já teria retornado no Caso 1.
        is_known = self._is_known_type(t0)
        return False, (not is_known)

    def _analyze_switch_block(self, switch_node: ASTNode, is_expression: bool = False):
        """Valida SwitchStatement e SwitchExpression (patterns, guards, dominância, escopo e exaustividade)."""
        self.check_expression(switch_node.expression)
        sb = getattr(switch_node, "switch_block", None)
        selector_type = self.infer_type(switch_node.expression)
        selector_base = self._strip_generics(selector_type) if selector_type else None
        if selector_base in ("boolean", "long", "float", "double") and not self.enable_preview_primitive_patterns:
            self.errors.append(
                SemanticError(
                    f"Seletor de tipo '{selector_type}' em 'switch' requer recurso preview (JEP 530) e está desabilitado no modo padrão Java SE 26 (JLS §14.11).",
                    getattr(switch_node, "line", 1),
                )
            )

        self.symbols.enter_scope()
        if self._local_var_scopes is not None:
            self._local_var_scopes.append({})
        self._local_type_scopes.append({})
        self._local_declared_type_scopes.append({})
        self._active_pattern_scopes.append({})
        if not is_expression:
            self._switch_depth += 1

        enum_const_names = self._collect_all_enum_constant_names()
        seen_default_pos: Optional[Tuple[int, bool]] = None  # (line, is_null_default)
        seen_null_line: Optional[int] = None
        seen_constants: Dict[Any, int] = {}
        seen_enum_case_names: Set[str] = set()
        seen_boolean_literals: Set[bool] = set()
        seen_patterns_for_dominance: List[Tuple[ASTNode, bool, int]] = []
        unconditional_top_patterns: List[ASTNode] = []
        has_pattern_labels = False

        def validate_label_and_collect_vars(lb: ASTNode) -> Dict[str, Dict[str, Any]]:
            nonlocal seen_default_pos, seen_null_line, has_pattern_labels
            lb_line = getattr(lb, "line", getattr(switch_node, "line", 1))
            label_pvars: Dict[str, Dict[str, Any]] = {}

            if isinstance(lb, DefaultLabel):
                if seen_default_pos is not None:
                    self.errors.append(SemanticError("Múltiplos labels 'default' no mesmo switch (JLS §14.11.1).", lb_line))
                seen_default_pos = (lb_line, False)
                for prev_p, prev_uncond, prev_line in seen_patterns_for_dominance:
                    if prev_uncond and self._is_pattern_unconditional(prev_p, selector_type) is True:
                        self.errors.append(
                            SemanticError(
                                f"Label 'default' é dominado pelo pattern incondicional anterior na linha {prev_line} (JLS §14.11.1).",
                                lb_line,
                            )
                        )
                        break
                return label_pvars

            if isinstance(lb, CaseLabel):
                patterns = list(getattr(lb, "patterns", []) or [])
                guard = getattr(lb, "guard", None)
                if patterns:
                    has_pattern_labels = True

                # Verificações de ordenação relativas a 'default' e 'case null, default' anteriores
                if seen_default_pos is not None and not (lb.has_default and len(patterns) == 0 and len(lb.constants) == 0):
                    def_line, def_is_null_default = seen_default_pos
                    if def_is_null_default:
                        self.errors.append(
                            SemanticError(
                                f"Label 'case' na linha {lb_line} não pode aparecer após 'case null, default' (linha {def_line} — JLS §14.11.1).",
                                lb_line,
                            )
                        )
                    elif patterns or lb.is_null:
                        self.errors.append(
                            SemanticError(
                                f"Label com pattern ou 'case null' não pode aparecer após 'default' (linha {def_line} — JLS §14.11.1).",
                                lb_line,
                            )
                        )

                if lb.is_null:
                    if selector_base in self.PRIMITIVE_TYPES:
                        self.errors.append(
                            SemanticError(
                                f"'case null' não é permitido para seletor de tipo primitivo '{selector_type}' (JLS §14.11.1).",
                                lb_line,
                            )
                        )
                    if seen_null_line is not None:
                        self.errors.append(SemanticError("Múltiplos labels 'case null' no mesmo switch (JLS §14.11.1).", lb_line))
                    seen_null_line = lb_line

                if lb.has_default:
                    if seen_default_pos is not None:
                        self.errors.append(SemanticError("Múltiplos labels 'default' no mesmo switch (JLS §14.11.1).", lb_line))
                    seen_default_pos = (lb_line, bool(lb.is_null))
                    for prev_p, prev_uncond, prev_line in seen_patterns_for_dominance:
                        if prev_uncond and self._is_pattern_unconditional(prev_p, selector_type) is True:
                            self.errors.append(
                                SemanticError(
                                    f"Label 'case null, default' não pode coexistir após pattern incondicional na linha {prev_line} (JLS §14.11.1).",
                                    lb_line,
                                )
                            )
                            break

                # Regra JLS §14.11.1: múltiplos patterns no mesmo label não podem declarar variáveis nomeadas
                if len(patterns) > 1:
                    for p in patterns:
                        if self._pattern_has_named_vars(p):
                            self.errors.append(
                                SemanticError(
                                    "Múltiplos patterns no mesmo label 'case' não podem declarar variáveis de pattern nomeadas (JLS §14.11.1).",
                                    getattr(p, "line", lb_line),
                                )
                            )
                            break

                # Constantes em 'case'
                for c in lb.constants:
                    if lb.is_null and isinstance(c, Literal) and getattr(c, "kind", "") == "NULL":
                        continue
                    self._check_switch_constant_expr(c, lb_line, enum_const_names)
                    c_line = getattr(c, "line", lb_line)
                    c_type = self._switch_constant_type(c, selector_type)
                    for prev_p, prev_uncond, prev_line in seen_patterns_for_dominance:
                        if not prev_uncond:
                            continue
                        if self._pattern_dominates_constant(prev_p, c_type) is True:
                            self.errors.append(
                                SemanticError(
                                    f"Constante de 'case' é dominada pelo pattern anterior na linha {prev_line} (JLS §14.11.1).",
                                    c_line,
                                )
                            )
                            break
                    key = self._switch_label_constant_key(c)
                    if key is not None:
                        if key in seen_constants:
                            self.errors.append(
                                SemanticError(
                                    f"Constante de 'case' duplicada no switch (já definida na linha {seen_constants[key]} — JLS §14.11.1).",
                                    c_line,
                                )
                            )
                        else:
                            seen_constants[key] = c_line
                    if isinstance(c, Identifier):
                        seen_enum_case_names.add(c.name)
                    elif isinstance(c, MemberAccess):
                        seen_enum_case_names.add(c.member_name)
                    elif isinstance(c, Literal) and getattr(c, "kind", "") == "BOOLEAN":
                        seen_boolean_literals.add(str(c.value).lower() == "true")

                # Patterns + dominância entre patterns + análise do guard 'when'
                if patterns:
                    is_uncond_guard = True
                    if guard is not None:
                        g_const = self._eval_constant_boolean(guard.expression)
                        is_uncond_guard = (g_const is True)

                    guard_true_vars: Dict[str, Dict[str, Any]] = {}
                    for p in patterns:
                        p_line = getattr(p, "line", lb_line)
                        p_vars = self._analyze_pattern(p, selector_type=selector_type, is_component=False)
                        for vn, vi in p_vars.items():
                            if vn in label_pvars:
                                self.errors.append(
                                    SemanticError(
                                        f"Variável de pattern '{vn}' declarada em duplicidade no mesmo label de switch (JLS §14.11.1).",
                                        vi.get("line", p_line),
                                    )
                                )
                            else:
                                label_pvars[vn] = vi

                        for prev_p, prev_uncond, prev_line in seen_patterns_for_dominance:
                            if not prev_uncond:
                                continue
                            dom, unres = self._pattern_dominates(prev_p, p, selector_type)
                            if dom is True:
                                self.errors.append(
                                    SemanticError(
                                        f"Label de case é dominado pelo pattern anterior na linha {prev_line} (JLS §14.11.1 / §14.30.3).",
                                        p_line,
                                    )
                                )
                                break
                            if unres:
                                self._record_unresolved(
                                    f"Verificação parcial de dominância entre patterns nas linhas {prev_line} e {p_line} envolve tipo externo não resolvido."
                                )

                        seen_patterns_for_dominance.append((p, is_uncond_guard, p_line))
                        if is_uncond_guard:
                            unconditional_top_patterns.append(p)

                    if guard is not None:
                        g_line = getattr(guard, "line", lb_line)
                        self._push_pattern_scope(label_pvars)
                        try:
                            g_flow = self._check_expression_flow(guard.expression)
                            g_type = self.infer_type(guard.expression)
                            if g_type is not None and g_type not in ("boolean", "Boolean", "Object", "desconhecido", "var"):
                                self.errors.append(
                                    SemanticError(
                                        f"Condição do guard 'when' deve possuir tipo 'boolean' (encontrado '{g_type}' — JLS §14.11.1).",
                                        g_line,
                                    )
                                )
                            guard_true_vars = dict(g_flow.true_vars)
                        finally:
                            self._pop_pattern_scope()
                        for gvn, gvi in guard_true_vars.items():
                            if gvn not in label_pvars:
                                label_pvars[gvn] = gvi

            return label_pvars

        try:
            if sb is not None:
                if sb.is_rule_based:
                    for rule in sb.switch_rules:
                        rule_pvars: Dict[str, Dict[str, Any]] = {}
                        for lb in rule.labels:
                            lb_vars = validate_label_and_collect_vars(lb)
                            rule_pvars.update(lb_vars)
                        self.symbols.enter_scope()
                        self._local_var_scopes.append({})
                        self._local_type_scopes.append({})
                        self._local_declared_type_scopes.append({})
                        self._push_pattern_scope(rule_pvars)
                        try:
                            if rule.is_throw:
                                self.analyze_statement(rule.body)
                            elif rule.is_block and isinstance(rule.body, Block):
                                self.analyze_block(rule.body)
                            elif rule.body is not None:
                                rule_inner = rule.body.expression if isinstance(rule.body, ExpressionStatement) else rule.body
                                if not is_expression and not self._is_statement_expression(rule_inner):
                                    self.errors.append(
                                        SemanticError(
                                            "Em switch statement com '->', o corpo deve ser bloco, 'throw' ou statement expression (JLS §14.11.1).",
                                            getattr(rule, "line", 1),
                                        )
                                    )
                                self._check_expression_flow(rule_inner)
                        finally:
                            self._pop_pattern_scope()
                            self._local_declared_type_scopes.pop()
                            self._local_type_scopes.pop()
                            self._local_var_scopes.pop()
                            self.symbols.exit_scope()
                else:
                    prev_grp_completes_normally = False
                    for grp in sb.statement_groups:
                        grp_pvars: Dict[str, Dict[str, Any]] = {}
                        has_named_pat_in_grp = False
                        grp_labels = list(getattr(grp, "labels", []) or [])
                        for lb in grp_labels:
                            lb_vars = validate_label_and_collect_vars(lb)
                            if any(
                                self._pattern_has_named_vars(p)
                                for p in (getattr(lb, "patterns", []) or [])
                            ):
                                has_named_pat_in_grp = True
                            for vn, vi in lb_vars.items():
                                if vn in grp_pvars:
                                    self.errors.append(
                                        SemanticError(
                                            f"Variável de pattern '{vn}' declarada em múltiplos labels do mesmo grupo de switch (JLS §14.11.1).",
                                            vi.get("line", getattr(lb, "line", 1)),
                                        )
                                    )
                                grp_pvars[vn] = vi

                        if len(grp_labels) > 1 and has_named_pat_in_grp:
                            self.errors.append(
                                SemanticError(
                                    "Múltiplos labels 'case' agrupados antes de um bloco não podem introduzir variáveis de pattern nomeadas (JLS §14.11.1).",
                                    getattr(grp_labels[-1], "line", getattr(grp, "line", 1)),
                                )
                            )
                        if prev_grp_completes_normally and has_named_pat_in_grp:
                            self.errors.append(
                                SemanticError(
                                    "Não é permitido fall-through de um grupo 'case' anterior para um label que declara variável de pattern (JLS §14.11.1).",
                                    getattr(grp_labels[0], "line", getattr(grp, "line", 1)) if grp_labels else getattr(grp, "line", 1),
                                )
                            )

                        self._push_pattern_scope(grp_pvars)
                        try:
                            stmts = list(getattr(grp, "statements", []) or [])
                            self._check_stmt_list_with_flow(stmts)
                        finally:
                            self._pop_pattern_scope()

                        if grp.statements:
                            last_completes = True
                            for s in grp.statements:
                                if not self._stmt_completes_normally(s):
                                    last_completes = False
                                    break
                            prev_grp_completes_normally = last_completes
                        else:
                            prev_grp_completes_normally = False
            else:
                for case_clause in getattr(switch_node, "cases", []):
                    if isinstance(case_clause, SwitchCase):
                        if case_clause.value is not None:
                            self._check_switch_constant_expr(case_clause.value, getattr(case_clause, "line", 1), enum_const_names)
                        for case_stmt in case_clause.statements:
                            self.analyze_statement(case_stmt)
                def_block = getattr(switch_node, "default_block", None)
                if def_block is not None:
                    seen_default_pos = (getattr(def_block, "line", 1), False)
                    if isinstance(def_block, Block):
                        for def_stmt in def_block.statements:
                            self.analyze_statement(def_stmt)
                    else:
                        self.analyze_statement(def_block)

            # Regras de exaustividade (JLS §14.11.1.1 / §14.11.2 / §15.28.1)
            needs_exhaustiveness = is_expression or has_pattern_labels or (seen_null_line is not None)
            if needs_exhaustiveness:
                is_exhaustive, unresolved_exhaust = self._check_switch_exhaustiveness(
                    selector_type=selector_type,
                    has_default=(seen_default_pos is not None),
                    unconditional_patterns=unconditional_top_patterns,
                    seen_enum_case_names=seen_enum_case_names,
                    seen_boolean_literals=seen_boolean_literals,
                )
                if not is_exhaustive:
                    if unresolved_exhaust and has_pattern_labels and selector_type and not self._is_known_type(selector_type):
                        self._record_unresolved(
                            f"Exaustividade completa do switch sobre tipo externo '{selector_type}' não pôde ser verificada sem classpath completo."
                        )
                    elif is_expression:
                        self.errors.append(
                            SemanticError(
                                "Switch expression não é exaustiva: adicione 'default' ou cubra todos os casos possíveis (JLS §15.28.1).",
                                getattr(switch_node, "line", 1),
                            )
                        )
                    elif seen_null_line is not None and not has_pattern_labels:
                        self.errors.append(
                            SemanticError(
                                "Switch aprimorado com 'case null' requer exaustividade ('default' ou cobertura completa dos casos — JLS §14.11.2).",
                                getattr(switch_node, "line", 1),
                            )
                        )
                    else:
                        self.errors.append(
                            SemanticError(
                                "Switch statement com patterns requer exaustividade: adicione 'default' ou cubra todos os subtipos/componentes possíveis (JLS §14.11.2).",
                                getattr(switch_node, "line", 1),
                            )
                        )
        finally:
            if not is_expression:
                self._switch_depth -= 1
            self._pop_pattern_scope()
            self._local_declared_type_scopes.pop()
            self._local_type_scopes.pop()
            self._local_var_scopes.pop()
            self.symbols.exit_scope()

    def _check_switch_exhaustiveness(
        self,
        selector_type: Optional[str],
        has_default: bool,
        unconditional_patterns: List[ASTNode],
        seen_enum_case_names: Set[str],
        seen_boolean_literals: Set[bool],
    ) -> Tuple[bool, bool]:
        """Verifica se o conjunto de labels incondicionais do switch cobre exaustivamente selector_type."""
        if has_default:
            return True, False

        sel_simple = self._simple_base_name(selector_type) if selector_type else None
        # 1. Verifica cobertura por patterns incondicionais sobre selector_type (incluindo sealed + record)
        if unconditional_patterns:
            target_t = selector_type or "Object"
            # Enum pode combinar constantes de enum com patterns de subtipo/enum
            if sel_simple and sel_simple in self._enums:
                enum_decl = self._enums[sel_simple]
                all_consts = {c.name for c in getattr(enum_decl, "constants", [])}
                if all_consts and all_consts.issubset(seen_enum_case_names):
                    return True, False
            # Boolean pode combinar constantes true/false em preview (JEP 530) ou pattern Boolean
            if (
                self.enable_preview_primitive_patterns
                and sel_simple in ("boolean", "Boolean")
                and seen_boolean_literals == {True, False}
            ):
                return True, False

            max_depth = max((self._max_pattern_depth(p) for p in unconditional_patterns), default=0)
            matrix = [[p] for p in unconditional_patterns]
            cov, unres = self._is_vector_covered([target_t], matrix, max_rec_depth=max_depth)
            if cov:
                return True, unres
            return False, unres

        # 2. Switch sem patterns incondicionais: enum completo ou boolean completo
        if sel_simple and sel_simple in self._enums:
            enum_decl = self._enums[sel_simple]
            all_consts = {c.name for c in getattr(enum_decl, "constants", [])}
            if all_consts and all_consts.issubset(seen_enum_case_names):
                return True, False
            return False, False

        if self.enable_preview_primitive_patterns and sel_simple in ("boolean", "Boolean"):
            if seen_boolean_literals == {True, False}:
                return True, False
            return False, False

        is_known = self._is_known_type(selector_type) if selector_type else True
        return False, (not is_known)

    def _is_exception_subtype(self, sub_name: str, super_name: str) -> bool:
        """Verifica relação de subtipo conhecida entre exceções padrão para multicatch/catch."""
        sub_simple = sub_name.split(".")[-1]
        sup_simple = super_name.split(".")[-1]
        cur = sub_simple
        visited: Set[str] = set()
        while cur in self.KNOWN_EXCEPTION_PARENTS and cur not in visited:
            visited.add(cur)
            parent = self.KNOWN_EXCEPTION_PARENTS[cur]
            if parent == sup_simple:
                return True
            cur = parent
        return False

    def _analyze_local_variable_declaration(self, stmt: LocalVariableDeclaration, is_resource: bool = False):
        """Analisa declaração de variável local ou recurso, validando 'var', '_', modificadores e múltiplos declaradores."""
        l_annos = getattr(stmt, "annotations", [])
        l_tref = getattr(stmt, "type_ref", None)
        if l_annos:
            self._analyze_annotations(l_annos, valid_targets={"LOCAL_VARIABLE"}, adjacent_type_ref=l_tref)
        if l_tref is not None:
            self._check_type_ref_annotations(l_tref)
        for ldecl in getattr(stmt, "declarators", []):
            if hasattr(ldecl, "id") and getattr(ldecl.id, "dims_annotations", None):
                for da in ldecl.id.dims_annotations:
                    self._analyze_annotations(da, valid_targets={"TYPE_USE"})

        mods = getattr(stmt, "modifiers", [])
        for mod in mods:
            if mod != "final":
                self.errors.append(
                    SemanticError(f"Modificador '{mod}' não é permitido em declaração de variável local (JLS §14.4).", stmt.line)
                )

        is_final = ("final" in mods) or is_resource
        is_var = getattr(stmt, "is_var", False) or (l_tref is not None and getattr(l_tref, "name", None) == "var")

        raw_decls = getattr(stmt, "declarators", [])
        items: List[Tuple[str, Optional[ASTNode], int, int, Optional[str]]] = []
        if raw_decls:
            for ldecl in raw_decls:
                d_id = getattr(ldecl, "id", None)
                d_name = getattr(ldecl, "name", getattr(d_id, "name", stmt.name))
                d_init = getattr(ldecl, "initializer", None)
                d_dims = getattr(ldecl, "dims", getattr(d_id, "dims", 0))
                d_line = getattr(ldecl, "line", stmt.line)
                d_eff = getattr(ldecl, "effective_type", None)
                items.append((d_name, d_init, d_dims, d_line, d_eff))
        else:
            items.append((stmt.name, stmt.initializer, getattr(stmt, "dims", 0), stmt.line, None))

        if is_var:
            if l_tref is not None and getattr(l_tref, "type_arguments", None):
                self.errors.append(
                    SemanticError("'var' não pode possuir argumentos de tipo genérico (JLS §14.4.1).", stmt.line)
                )
            if l_tref is not None and getattr(l_tref, "dims", 0) > 0:
                self.errors.append(
                    SemanticError("'var' não pode ser combinado com colchetes de array 'var[]' (JLS §14.4.1).", stmt.line)
                )
            if len(items) > 1:
                self.errors.append(
                    SemanticError("'var' não é permitido em declarações com múltiplos declaradores (JLS §14.4.1).", stmt.line)
                )
            for d_name, d_init, d_dims, d_line, _ in items:
                if d_dims > 0:
                    self.errors.append(
                        SemanticError(
                            f"'var' não é permitido com dimensões '[]' no declarador '{d_name}' (JLS §14.4.1).",
                            d_line,
                        )
                    )
                if d_init is None:
                    self.errors.append(
                        SemanticError(
                            f"Variável '{d_name}' declarada com 'var' exige obrigatoriamente um inicializador (JLS §14.4.1).",
                            d_line,
                        )
                    )
                else:
                    if isinstance(d_init, ArrayInitializer):
                        self.errors.append(
                            SemanticError(
                                f"Inicializador de array '{{...}}' não é permitido diretamente com 'var' em '{d_name}' (JLS §14.4.1).",
                                d_line,
                            )
                        )
                    elif isinstance(d_init, Literal) and getattr(d_init, "kind", "") == "NULL":
                        self.errors.append(
                            SemanticError(
                                f"Não é possível inferir o tipo de 'var {d_name}' a partir do literal 'null' (JLS §14.4.1).",
                                d_line,
                            )
                        )
                    elif isinstance(d_init, (LambdaExpression, MethodReference)):
                        self.errors.append(
                            SemanticError(
                                f"Não é possível inferir o tipo de 'var {d_name}' a partir de lambda ou method reference sem tipo alvo explícito (JLS §14.4.1).",
                                d_line,
                            )
                        )
                    if d_name != "_" and self._expr_contains_identifier(d_init, d_name):
                        self.errors.append(
                            SemanticError(
                                f"Autorreferência à variável '{d_name}' não é permitida no inicializador de 'var' (JLS §14.4.1).",
                                d_line,
                            )
                        )
                    self.check_expression(d_init)
                inferred = self.infer_type(d_init) if d_init is not None else None
                eff_type = inferred if inferred else "var"
                self._register_local_var(
                    d_name,
                    eff_type,
                    d_line,
                    is_final=is_final,
                    has_initializer=(d_init is not None),
                    category="variavel",
                )
            return

        base_type = getattr(l_tref, "full_name", stmt.type_name) if l_tref is not None else stmt.type_name
        if base_type == "void":
            self.errors.append(
                SemanticError("O tipo 'void' não é válido para declaração de variável local (JLS §14.4).", stmt.line)
            )
        if is_resource and len(items) > 1:
            self.errors.append(
                SemanticError("Declaração de recurso em try-with-resources aceita apenas um declarador (JLS §14.20.3).", stmt.line)
            )

        for d_name, d_init, d_dims, d_line, d_eff in items:
            eff_type = d_eff if d_eff else (base_type + ("[]" * d_dims if d_dims else ""))
            if is_resource and d_init is None:
                self.errors.append(
                    SemanticError(
                        f"Recurso '{d_name}' em try-with-resources deve possuir inicializador (JLS §14.20.3).",
                        d_line,
                    )
                )
            if d_init is not None:
                self.check_expression(d_init)
                self.check_assignment_type(eff_type, d_init, d_name, d_line)
            is_const = is_final and d_init is not None and self._is_compile_time_constant_expr(d_init)
            self._register_local_var(
                d_name,
                eff_type,
                d_line,
                is_final=is_final,
                has_initializer=(d_init is not None),
                category="variavel",
                is_compile_constant=is_const,
            )

    def _check_stmt_list_with_flow(self, stmts: List[ASTNode]):
        """Analisa sequência de instruções propagando variáveis de pattern introduzidas no bloco (JLS §6.3.2)."""
        for stmt in stmts:
            post_vars = self._analyze_statement_with_flow(stmt)
            if post_vars:
                self._inject_pattern_vars_into_enclosing_block(post_vars)

    def _analyze_statement_with_flow(
        self,
        stmt: ASTNode,
        enclosing_labels: Optional[Set[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Analisa uma instrução e retorna variáveis de pattern introduzidas no escopo imediatamente posterior."""
        if stmt is None:
            return {}

        if isinstance(stmt, LabeledStatement):
            line = getattr(stmt, "line", 1)
            next_labels = set(enclosing_labels or ())
            next_labels.add(stmt.label)
            if stmt.label in self._active_labels:
                prev_line = self._active_labels[stmt.label][1]
                self.errors.append(
                    SemanticError(
                        f"Label '{stmt.label}' declarado novamente no mesmo escopo envolvente (linha {prev_line} — JLS §14.7).",
                        line,
                    )
                )
                return self._analyze_statement_with_flow(stmt.statement, enclosing_labels=next_labels)
            target = stmt.statement
            while isinstance(target, LabeledStatement):
                target = target.statement
            is_iterative = isinstance(target, (WhileStatement, DoWhileStatement, ForStatement, EnhancedForStatement))
            self._active_labels[stmt.label] = (is_iterative, line)
            try:
                post_vars = self._analyze_statement_with_flow(stmt.statement, enclosing_labels=next_labels)
            finally:
                self._active_labels.pop(stmt.label, None)
            if self._contains_break_targeting(stmt.statement, target_label=stmt.label):
                return {}
            return post_vars

        if isinstance(stmt, IfStatement):
            true_vars, false_vars = self._check_boolean_condition(stmt.condition, "if", getattr(stmt, "line", 1))
            self._push_pattern_scope(true_vars)
            try:
                self.analyze_statement(stmt.then_branch)
            finally:
                self._pop_pattern_scope()

            if stmt.else_branch is not None:
                self._push_pattern_scope(false_vars)
                try:
                    self.analyze_statement(stmt.else_branch)
                finally:
                    self._pop_pattern_scope()
                then_norm = self._stmt_completes_normally(stmt.then_branch)
                else_norm = self._stmt_completes_normally(stmt.else_branch)
                if not then_norm and else_norm:
                    return dict(false_vars)
                if then_norm and not else_norm:
                    return dict(true_vars)
                return {}

            if not self._stmt_completes_normally(stmt.then_branch):
                return dict(false_vars)
            return {}

        if isinstance(stmt, WhileStatement):
            true_vars, false_vars = self._check_boolean_condition(stmt.condition, "while", getattr(stmt, "line", 1))
            self._loop_depth += 1
            self._push_pattern_scope(true_vars)
            try:
                self.analyze_statement(stmt.body)
            finally:
                self._pop_pattern_scope()
                self._loop_depth -= 1
            if false_vars and not self._contains_break_targeting(stmt.body, target_label=None, extra_labels=enclosing_labels):
                return dict(false_vars)
            return {}

        if isinstance(stmt, ForStatement):
            self.symbols.enter_scope()
            push_local = bool(self._local_var_scopes)
            if push_local:
                self._local_var_scopes.append({})
            self._active_pattern_scopes.append({})
            self._loop_depth += 1
            false_vars: Dict[str, Dict[str, Any]] = {}
            try:
                if stmt.init is not None:
                    self.analyze_statement(stmt.init)
                true_vars: Dict[str, Dict[str, Any]] = {}
                if stmt.condition is not None:
                    true_vars, false_vars = self._check_boolean_condition(stmt.condition, "for", getattr(stmt, "line", 1))
                self._push_pattern_scope(true_vars)
                try:
                    if stmt.update is not None:
                        if isinstance(stmt.update, StatementExpressionList):
                            for uexpr in stmt.update.expressions:
                                self.check_expression(uexpr)
                        else:
                            self.check_expression(stmt.update)
                    if stmt.body is not None:
                        self.analyze_statement(stmt.body)
                finally:
                    self._pop_pattern_scope()
            finally:
                self._loop_depth -= 1
                self._pop_pattern_scope()
                if push_local:
                    self._local_var_scopes.pop()
                self.symbols.exit_scope()
            if false_vars and not self._contains_break_targeting(stmt.body, target_label=None, extra_labels=enclosing_labels):
                return dict(false_vars)
            return {}

        self.analyze_statement(stmt)
        return {}

    def analyze_block(self, block_node: Block):
        """Analisa instruções dentro de um bloco de código com controle de escopo local e flow-scoping S7."""
        if not block_node or not hasattr(block_node, "statements"):
            return
        self.symbols.enter_scope()
        push_local = bool(self._local_var_scopes)
        if push_local:
            self._local_var_scopes.append({})
        self._active_pattern_scopes.append({})
        self._local_type_scopes.append({})
        self._local_declared_type_scopes.append({})
        for stmt in block_node.statements:
            if isinstance(stmt, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
                self._index_local_type_decl(stmt)
        try:
            self._check_stmt_list_with_flow(block_node.statements)
        finally:
            self._local_declared_type_scopes.pop()
            self._local_type_scopes.pop()
            self._pop_pattern_scope()
            if push_local:
                self._local_var_scopes.pop()
            self.symbols.exit_scope()

    def analyze_statement(self, stmt: ASTNode):
        """Analisa uma declaração ou instrução isolada com validações contextuais completas (S6/S7)."""
        if stmt is None:
            return

        if isinstance(stmt, (Declaration, LocalVariableDeclaration)):
            self._analyze_local_variable_declaration(stmt, is_resource=False)

        elif isinstance(stmt, StatementExpressionList):
            for expr in stmt.expressions:
                self.check_expression(expr)

        elif isinstance(stmt, Assignment):
            self._check_assignment(stmt)

        elif isinstance(stmt, LabeledStatement):
            self._analyze_statement_with_flow(stmt)

        elif isinstance(stmt, ReturnStatement):
            line = getattr(stmt, "line", 1)
            if self._in_compact_constructor:
                self.errors.append(
                    SemanticError("Instrução 'return' não é permitida dentro de um construtor compacto de record (JLS §8.10.4.2).", line)
                )
            elif self._callable_kind == "initializer":
                self.errors.append(
                    SemanticError("Instrução 'return' não é permitida dentro de um bloco inicializador (JLS §8.6 / §8.7 / §14.17).", line)
                )
            elif self._switch_expr_depth > 0:
                self.errors.append(
                    SemanticError("Instrução 'return' não é permitida dentro de uma switch expression (JLS §14.17).", line)
                )
            elif self._callable_kind == "constructor":
                if stmt.expression is not None:
                    self.errors.append(
                        SemanticError("Construtor não pode retornar valor com expressão em 'return' (JLS §8.8.4 / §14.17).", line)
                    )
            elif self._callable_kind == "method":
                if self._current_return_type == "void" and stmt.expression is not None:
                    self.errors.append(
                        SemanticError("Método 'void' não pode retornar valor em 'return' (JLS §14.17).", line)
                    )
                elif self._current_return_type not in (None, "void") and stmt.expression is None:
                    self.errors.append(
                        SemanticError(
                            f"Método com tipo de retorno '{self._current_return_type}' deve retornar valor em 'return' (JLS §14.17).",
                            line,
                        )
                    )
            if stmt.expression is not None:
                self.check_expression(stmt.expression)

        elif isinstance(stmt, YieldStatement):
            line = getattr(stmt, "line", 1)
            if self._switch_expr_depth <= 0:
                self.errors.append(
                    SemanticError("Instrução 'yield' só é permitida dentro de uma switch expression (JLS §14.21).", line)
                )
            self.check_expression(stmt.expression)

        elif isinstance(stmt, BreakStatement):
            line = getattr(stmt, "line", 1)
            if stmt.label:
                if stmt.label not in self._active_labels:
                    self.errors.append(
                        SemanticError(
                            f"Label '{stmt.label}' não encontrado ou fora de alcance para 'break' (JLS §14.15).",
                            line,
                        )
                    )
            elif self._loop_depth <= 0 and self._switch_depth <= 0:
                self.errors.append(
                    SemanticError("Instrução 'break' fora de laço ou switch (JLS §14.15).", line)
                )

        elif isinstance(stmt, ContinueStatement):
            line = getattr(stmt, "line", 1)
            if stmt.label:
                if stmt.label not in self._active_labels:
                    self.errors.append(
                        SemanticError(
                            f"Label '{stmt.label}' não encontrado ou fora de alcance para 'continue' (JLS §14.16).",
                            line,
                        )
                    )
                elif not self._active_labels[stmt.label][0]:
                    self.errors.append(
                        SemanticError(
                            f"Instrução 'continue {stmt.label}' só pode referenciar um laço iterativo (JLS §14.16).",
                            line,
                        )
                    )
            elif self._loop_depth <= 0:
                self.errors.append(
                    SemanticError("Instrução 'continue' fora de laço (JLS §14.16).", line)
                )

        elif isinstance(stmt, (IfStatement, WhileStatement, ForStatement)):
            self._analyze_statement_with_flow(stmt)

        elif isinstance(stmt, DoWhileStatement):
            self._loop_depth += 1
            try:
                self.analyze_statement(stmt.body)
            finally:
                self._loop_depth -= 1
            self._check_boolean_condition(stmt.condition, "do-while", getattr(stmt, "line", 1))

        elif isinstance(stmt, EnhancedForStatement):
            self.symbols.enter_scope()
            push_local = bool(self._local_var_scopes)
            if push_local:
                self._local_var_scopes.append({})
            self._loop_depth += 1
            try:
                # Avalia expressão iterável antes de registrar a variável do cabeçalho
                self.check_expression(stmt.iterable)
                var = stmt.variable
                v_annos = getattr(var, "annotations", [])
                v_tref = getattr(var, "type_ref", None)
                self._analyze_annotations(
                    v_annos,
                    valid_targets={"LOCAL_VARIABLE"},
                    adjacent_type_ref=v_tref,
                )
                self._check_type_ref_annotations(v_tref)
                for vm in getattr(var, "modifiers", []):
                    if vm != "final":
                        self.errors.append(
                            SemanticError(f"Modificador '{vm}' inválido em variável de for-each (JLS §14.14.2).", getattr(var, "line", stmt.line))
                        )
                v_is_var = getattr(var, "is_var", False) or (v_tref is not None and getattr(v_tref, "name", None) == "var")
                v_dims = getattr(var, "dims", 0)
                if v_is_var and (v_dims > 0 or (v_tref is not None and getattr(v_tref, "dims", 0) > 0)):
                    self.errors.append(
                        SemanticError("'var' não pode ser combinado com colchetes de array '[]' em for-each (JLS §14.14.2).", getattr(var, "line", stmt.line))
                    )
                if hasattr(var, "name") and var.name != "_":
                    t_name = "var" if v_is_var else getattr(var, "effective_type", getattr(var, "type_name", "Object"))
                    self._register_local_var(
                        var.name,
                        t_name,
                        getattr(var, "line", stmt.line),
                        is_final=("final" in getattr(var, "modifiers", [])),
                        has_initializer=True,
                        category="variavel",
                    )
                if stmt.body is not None:
                    self.analyze_statement(stmt.body)
            finally:
                self._loop_depth -= 1
                if push_local:
                    self._local_var_scopes.pop()
                self.symbols.exit_scope()

        elif isinstance(stmt, SwitchStatement):
            self._analyze_switch_block(stmt, is_expression=False)

        elif isinstance(stmt, TryStatement):
            res_spec = getattr(stmt, "resource_specification", None)
            res_nodes = res_spec.resources if res_spec is not None else stmt.resources
            has_resources = bool(res_nodes)
            if has_resources:
                self.symbols.enter_scope()
                push_res = bool(self._local_var_scopes)
                if push_res:
                    self._local_var_scopes.append({})
                try:
                    for res in res_nodes:
                        if isinstance(res, Resource):
                            if res.is_reference:
                                self.check_expression(res.variable_access)
                                if isinstance(res.variable_access, Identifier):
                                    rname = res.variable_access.name
                                    linfo = self._find_local_var_info(rname)
                                    sym = self.symbols.lookup(rname)
                                    if linfo is not None and not linfo.get("is_final", False) and linfo.get("reassigned", False):
                                        self.errors.append(
                                            SemanticError(
                                                f"Recurso '{rname}' em try-with-resources deve ser 'final' ou efetivamente final (JLS §14.20.3).",
                                                getattr(res, "line", stmt.line),
                                            )
                                        )
                                    elif sym is not None and sym.get("category") == "campo" and not sym.get("is_final", False):
                                        self.errors.append(
                                            SemanticError(
                                                f"Campo '{rname}' referenciado em try-with-resources deve ser 'final' ou efetivamente final (JLS §14.20.3).",
                                                getattr(res, "line", stmt.line),
                                            )
                                        )
                                elif isinstance(res.variable_access, MemberAccess) and isinstance(res.variable_access.target, Identifier) and res.variable_access.target.name == "this":
                                    sym = self.symbols.lookup(res.variable_access.member_name)
                                    if sym is not None and sym.get("category") == "campo" and not sym.get("is_final", False):
                                        self.errors.append(
                                            SemanticError(
                                                f"Campo 'this.{res.variable_access.member_name}' em try-with-resources deve ser 'final' (JLS §14.20.3).",
                                                getattr(res, "line", stmt.line),
                                            )
                                        )
                            elif res.declaration is not None:
                                self._analyze_local_variable_declaration(res.declaration, is_resource=True)
                        else:
                            self._analyze_local_variable_declaration(res, is_resource=True)
                    if stmt.body is not None:
                        self.analyze_block(stmt.body)
                finally:
                    if push_res:
                        self._local_var_scopes.pop()
                    self.symbols.exit_scope()
            else:
                if stmt.body is not None:
                    self.analyze_block(stmt.body)

            caught_exceptions: List[Tuple[str, int]] = []
            for catch_c in stmt.catches:
                self.symbols.enter_scope()
                push_catch = bool(self._local_var_scopes)
                if push_catch:
                    self._local_var_scopes.append({})
                try:
                    c_param = catch_c.parameter
                    c_types = catch_c.catch_types
                    if c_param is not None:
                        self._analyze_annotations(
                            getattr(c_param, "annotations", []),
                            valid_targets={"PARAMETER"},
                            adjacent_type_ref=getattr(c_param, "type_ref", None),
                        )
                        for cm in getattr(c_param, "modifiers", []):
                            if cm != "final":
                                self.errors.append(
                                    SemanticError(f"Modificador '{cm}' inválido em parâmetro de catch (JLS §14.20).", getattr(c_param, "line", catch_c.line))
                                )
                    for ct in c_types:
                        self._check_type_ref_annotations(ct)
                        if getattr(ct, "name", None) == "var":
                            self.errors.append(
                                SemanticError("'var' não é permitido como tipo de parâmetro de catch (JLS §14.20).", getattr(ct, "line", catch_c.line))
                            )
                    if len(c_types) > 1:
                        for idx_a in range(len(c_types)):
                            for idx_b in range(idx_a + 1, len(c_types)):
                                na = c_types[idx_a].full_name
                                nb = c_types[idx_b].full_name
                                if na.split(".")[-1] == nb.split(".")[-1] or self._is_exception_subtype(na, nb) or self._is_exception_subtype(nb, na):
                                    self.errors.append(
                                        SemanticError(
                                            f"Alternativas incompatíveis em multicatch: '{na}' e '{nb}' possuem relação de subtipo ou são idênticas (JLS §14.20).",
                                            getattr(c_types[idx_b], "line", catch_c.line),
                                        )
                                    )
                    for ct in c_types:
                        ct_name = ct.full_name
                        ct_line = getattr(ct, "line", catch_c.line)
                        for prev_ex, prev_line in caught_exceptions:
                            if ct_name.split(".")[-1] == prev_ex.split(".")[-1] or self._is_exception_subtype(ct_name, prev_ex):
                                self.errors.append(
                                    SemanticError(
                                        f"Cláusula catch inalcançável para '{ct_name}': exceção já capturada anteriormente na linha {prev_line} (JLS §14.20).",
                                        ct_line,
                                    )
                                )
                                break
                        caught_exceptions.append((ct_name, ct_line))

                    if c_param is not None and c_param.name != "_":
                        is_catch_final = ("final" in getattr(c_param, "modifiers", [])) or (len(c_types) > 1)
                        catch_type_label = " | ".join(t.full_name for t in c_types) if c_types else (
                            c_param.type_ref.name if getattr(c_param, "type_ref", None) else "Throwable"
                        )
                        self._register_local_var(
                            c_param.name,
                            catch_type_label,
                            getattr(c_param, "line", catch_c.line),
                            is_final=is_catch_final,
                            has_initializer=True,
                            category="parametro",
                        )
                    if catch_c.body is not None:
                        self.analyze_block(catch_c.body)
                finally:
                    if push_catch:
                        self._local_var_scopes.pop()
                    self.symbols.exit_scope()

            if stmt.finally_block is not None:
                self.analyze_block(stmt.finally_block)

        elif isinstance(stmt, SynchronizedStatement):
            self.check_expression(stmt.lock)
            if stmt.body is not None:
                self.analyze_block(stmt.body)

        elif isinstance(stmt, ThrowStatement):
            self.check_expression(stmt.expression)

        elif isinstance(stmt, AssertStatement):
            self._check_boolean_condition(stmt.condition, "assert", getattr(stmt, "line", 1))
            if stmt.message is not None:
                self.check_expression(stmt.message)

        elif isinstance(stmt, ExpressionStatement):
            self.check_expression(stmt.expression)

        elif isinstance(stmt, Block):
            self.analyze_block(stmt)

        elif isinstance(stmt, EmptyStatement):
            pass

        elif isinstance(stmt, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
            saved_compact = self._in_compact_constructor
            self._in_compact_constructor = False
            try:
                self._analyze_type_declaration(stmt, is_nested=True, is_local=True)
            finally:
                self._in_compact_constructor = saved_compact

    def _check_early_target_ref(self, target_name: str, line: int, context_detail: str = "") -> bool:
        """Verifica se há uso inválido de 'this' ou 'super' durante o early construction context (JLS §8.8.7 / JEP 513)."""
        if not self._in_early_construction_context:
            return False
        for kw in ("this", "super"):
            if target_name == kw or target_name.startswith(f"{kw}."):
                msg = (
                    f"{context_detail} antes da invocação explícita do construtor (early construction context — JLS §8.8.7 / JEP 513)."
                    if context_detail
                    else f"Uso inválido de '{kw}' antes da invocação explícita do construtor (early construction context — JLS §8.8.7 / JEP 513)."
                )
                self.errors.append(SemanticError(msg, line))
                return True
        return False

    def _check_assignment(self, node: Assignment):
        """Valida uma atribuição (instrução ou expressão), incluindo regras do early construction context e construtores compactos."""
        line = getattr(node, "line", 1)
        is_this_member_assign = (
            (node.name and node.name.startswith("this."))
            or (
                isinstance(node.target, MemberAccess)
                and isinstance(node.target.target, Identifier)
                and node.target.target.name == "this"
            )
        )
        if self._in_compact_constructor and is_this_member_assign:
            self.errors.append(
                SemanticError(
                    "Construtor compacto de record não pode atribuir campos de instância diretamente usando 'this.' (JLS §8.10.4.2).",
                    line,
                )
            )
            self.check_expression(node.expression)
            return

        if node.target is not None and not isinstance(node.target, Identifier):
            self.check_expression(node.target)
            self.check_expression(node.expression)
            return

        if node.name and (node.name.startswith(("this.", "super.")) or node.name in ("this", "super")):
            self._check_early_target_ref(node.name, line)
            self.check_expression(node.expression)
            return

        if node.name and "." in node.name:
            if node.target is not None:
                self.check_expression(node.target)
            self.check_expression(node.expression)
            return

        symbol = self._lookup_var_symbol(node.name)
        if self._in_early_construction_context and symbol is not None and symbol.get("category") == "campo" and not symbol.get("is_static", False):
            self.errors.append(
                SemanticError(f"Acesso inválido ao campo de instância '{node.name}' antes da invocação explícita do construtor (early construction context — JLS §8.8.7 / JEP 513).", line)
            )
        if symbol is not None and symbol.get("category") in ("constante_interface", "constante_enum", "componente_record"):
            self.errors.append(
                SemanticError(f"Não é possível atribuir valor a '{node.name}' ({symbol.get('category')} é implicitamente final).", line)
            )
        elif symbol is None or symbol.get("category") not in ("variavel", "parametro", "campo"):
            self.errors.append(
                SemanticError(f"Variável '{node.name}' não foi declarada.", line)
            )
        else:
            local_info = self._find_local_var_info(node.name)
            if local_info is not None:
                if local_info.get("is_final", False) and local_info.get("has_initializer", True):
                    self.errors.append(
                        SemanticError(f"Não é possível atribuir valor à variável 'final' '{node.name}'.", line)
                    )
                self._mark_local_var_reassigned(node.name)
        self.check_expression(node.expression)
        if symbol is not None and "type" in symbol:
            self.check_assignment_type(
                symbol["type"],
                node.expression,
                node.name,
                line,
                operator=getattr(node, "operator", "="),
            )

    class _FlowResult:
        """Armazena conjuntos de variáveis de pattern introduzidas quando booleano verdadeiro vs falso (JLS §6.3.1)."""
        __slots__ = ("true_vars", "false_vars")

        def __init__(
            self,
            true_vars: Optional[Dict[str, Dict[str, Any]]] = None,
            false_vars: Optional[Dict[str, Dict[str, Any]]] = None,
        ):
            self.true_vars: Dict[str, Dict[str, Any]] = true_vars if true_vars is not None else {}
            self.false_vars: Dict[str, Dict[str, Any]] = false_vars if false_vars is not None else {}

    def check_expression(self, node: Optional[ASTNode]):
        """Verifica expressões, prevenindo falsos positivos para símbolos externos e métodos."""
        if node is None:
            return
        self._check_expression_flow(node)

    def _check_expression_flow(self, node: Optional[ASTNode]) -> "_FlowResult":
        """Verifica uma expressão e computa variáveis de pattern em escopo nos ramos true/false (JLS §6.3.1)."""
        empty = self._FlowResult()
        if node is None:
            return empty

        if isinstance(node, Identifier):
            line = getattr(node, "line", 1)
            if self._check_early_target_ref(node.name, line):
                return empty

            # Identificadores com ponto (ex: System.out.println), 'this' ou 'super' não geram falso erro
            if node.name in ("this", "super") or node.name.startswith(("this.", "super.")) or "." in node.name:
                return empty

            symbol = self._lookup_var_symbol(node.name)
            if self._in_early_construction_context and symbol is not None and symbol.get("category") == "campo" and not symbol.get("is_static", False):
                self.errors.append(
                    SemanticError(f"Acesso inválido ao campo de instância '{node.name}' antes da invocação explícita do construtor (early construction context — JLS §8.8.7 / JEP 513).", line)
                )

            if symbol is None or symbol.get("category") not in ("variavel", "parametro", "campo", "tipo", "constante_enum", "constante_interface", "componente_record"):
                self.errors.append(
                    SemanticError(f"Variável '{node.name}' não foi declarada.", line)
                )
            return empty

        if isinstance(node, ObjectCreationExpression):
            self._check_type_ref_annotations(getattr(node, "type_ref", None))
            if node.target is not None:
                self._check_expression_flow(node.target)
            for arg in node.arguments:
                self._check_expression_flow(arg)
            return empty

        if isinstance(node, MethodCall):
            line = getattr(node, "line", 1)
            if node.target is not None:
                if isinstance(node.target, Identifier) and node.target.name in ("this", "super"):
                    self._check_early_target_ref(
                        node.target.name,
                        line,
                        f"Invocação inválida de método via '{node.target.name}' ('{node.target.name}.{node.method_name}(...)')"
                    )
                if isinstance(node.target, Identifier) and (node.target.name in ("this", "super") or node.target.name[0].isupper()):
                    pass
                else:
                    self._check_expression_flow(node.target)
            else:
                if self._in_early_construction_context:
                    sym = self.symbols.lookup(node.method_name)
                    if sym is not None and sym.get("category") == "metodo" and not sym.get("is_static", False):
                        self.errors.append(
                            SemanticError(f"Invocação inválida de método de instância '{node.method_name}(...)' antes da invocação explícita do construtor (early construction context — JLS §8.8.7 / JEP 513).", line)
                        )
            for arg in node.arguments:
                self._check_expression_flow(arg)
            return empty

        if isinstance(node, MemberAccess):
            line = getattr(node, "line", 1)
            if isinstance(node.target, Identifier) and node.target.name in ("this", "super"):
                self._check_early_target_ref(
                    node.target.name,
                    line,
                    f"Acesso inválido a membro via '{node.target.name}' ('{node.target.name}.{node.member_name}')"
                )
            if isinstance(node.target, Identifier) and (node.target.name in ("this", "super") or node.target.name[0].isupper()):
                pass
            else:
                self._check_expression_flow(node.target)
            return empty

        if isinstance(node, MethodReference):
            line = getattr(node, "line", 1)
            if isinstance(node.target, Identifier) and node.target.name in ("this", "super"):
                self._check_early_target_ref(
                    node.target.name,
                    line,
                    f"Referência inválida a método via '{node.target.name}' ('{node.target.name}::{node.method_name}')"
                )
            if isinstance(node.target, Identifier) and (node.target.name in ("this", "super") or node.target.name[0].isupper()):
                pass
            else:
                self._check_expression_flow(node.target)
            return empty

        if isinstance(node, ArrayAccess):
            self._check_expression_flow(node.array)
            self._check_expression_flow(node.index)
            return empty

        if isinstance(node, ConditionalExpression):
            fc = self._check_expression_flow(node.condition)
            self._push_pattern_scope(fc.true_vars)
            try:
                ft = self._check_expression_flow(node.then_expr)
            finally:
                self._pop_pattern_scope()

            self._push_pattern_scope(fc.false_vars)
            try:
                fe = self._check_expression_flow(node.else_expr)
            finally:
                self._pop_pattern_scope()

            # JLS §6.3.1.3: variável é introduzida quando (true em c|then) e (false em c ou true em else)
            left_true = {**fc.true_vars, **ft.true_vars}
            right_true = {**fc.false_vars, **fe.true_vars}
            out_true = {k: v for k, v in left_true.items() if k in right_true}
            left_false = {**fc.true_vars, **ft.false_vars}
            right_false = {**fc.false_vars, **fe.false_vars}
            out_false = {k: v for k, v in left_false.items() if k in right_false}
            return self._FlowResult(out_true, out_false)

        if isinstance(node, ArrayCreationExpression):
            self._check_type_ref_annotations(getattr(node, "type_ref", None))
            for dim in node.dimensions:
                if dim is not None:
                    self._check_expression_flow(dim)
            if node.initializer is not None:
                self._check_expression_flow(node.initializer)
            return empty

        if isinstance(node, ArrayInitializer):
            for elem in node.elements:
                self._check_expression_flow(elem)
            return empty

        if isinstance(node, CastExpression):
            self._check_type_ref_annotations(getattr(node, "target_type", None))
            self._check_expression_flow(node.expression)
            return empty

        if isinstance(node, InstanceOfExpression):
            line = getattr(node, "line", 1)
            self._check_expression_flow(node.expression)
            src_type = self.infer_type(node.expression)
            pat = getattr(node, "pattern", None)
            if getattr(node, "is_pattern", False) or pat is not None:
                pvars = self._analyze_pattern(pat, selector_type=src_type, is_component=False)
                return self._FlowResult(true_vars=pvars, false_vars={})

            tref = getattr(node, "target_type", None)
            self._check_type_ref_annotations(tref)
            t_str = self._normalize_type_str(tref)
            if t_str:
                t_base, t_dims = self._split_type_dims(self._strip_generics(t_str) or "")
                src_base, src_dims = (
                    self._split_type_dims(self._strip_generics(src_type) or "")
                    if src_type
                    else ("", 0)
                )
                if t_dims == 0 and t_base in self.PRIMITIVE_TYPES and not self.enable_preview_primitive_patterns:
                    self.errors.append(
                        SemanticError(
                            f"Tipo primitivo '{t_str}' em 'instanceof' pertence ao recurso preview (JEP 530) e está desabilitado no modo padrão Java SE 26 (JLS §15.20.2).",
                            line,
                        )
                    )
                elif src_type and src_dims == 0 and src_base in self.PRIMITIVE_TYPES and not self.enable_preview_primitive_patterns:
                    self.errors.append(
                        SemanticError(
                            f"Operador 'instanceof' exige expressão de tipo referência no modo padrão Java SE 26 (encontrado '{src_type}' — JLS §15.20.2).",
                            line,
                        )
                    )
                elif src_type and self._are_types_disjoint(src_type, t_str) is True:
                    self.errors.append(
                        SemanticError(
                            f"Tipos incompatíveis em 'instanceof': '{src_type}' não pode ser instância de '{t_str}' (JLS §15.20.2).",
                            line,
                        )
                    )
            return empty

        if isinstance(node, ClassLiteral):
            return empty

        if isinstance(node, LambdaExpression):
            self.symbols.enter_scope()
            self._local_var_scopes.append({})
            self._active_pattern_scopes.append({})
            self._local_type_scopes.append({})
            self._local_declared_type_scopes.append({})
            saved_ctx = self._enter_exec_context("lambda", return_type=None, share_locals=True)
            try:
                for p in node.parameters:
                    if p != "_":
                        self._register_local_var(
                            p,
                            "Object",
                            getattr(node, "line", 1),
                            has_initializer=True,
                            category="parametro",
                        )
                if node.is_block_body and isinstance(node.body, Block):
                    self.analyze_block(node.body)
                elif node.body is not None:
                    self._check_expression_flow(node.body)
            finally:
                self._restore_exec_context(saved_ctx)
                self._local_declared_type_scopes.pop()
                self._local_type_scopes.pop()
                self._pop_pattern_scope()
                self._local_var_scopes.pop()
            self.symbols.exit_scope()
            return empty

        if isinstance(node, SwitchExpression):
            saved_ctx = self._enter_exec_context(
                "switch_expression",
                return_type=self._current_return_type,
                share_locals=True,
                switch_expr_depth=self._switch_expr_depth + 1,
            )
            try:
                self._analyze_switch_block(node, is_expression=True)
            finally:
                self._restore_exec_context(saved_ctx)
            return empty

        if isinstance(node, Assignment):
            self._check_assignment(node)
            return empty

        if isinstance(node, UnaryOp):
            if node.op == "!":
                sub = self._check_expression_flow(node.operand)
                return self._FlowResult(true_vars=dict(sub.false_vars), false_vars=dict(sub.true_vars))
            self._check_expression_flow(node.operand)
            if node.op in ("++", "--", "post++", "post--") and isinstance(node.operand, Identifier):
                op_name = node.operand.name
                linfo = self._find_local_var_info(op_name)
                if linfo is not None:
                    if linfo.get("is_final", False) and linfo.get("has_initializer", True):
                        self.errors.append(
                            SemanticError(
                                f"Não é possível modificar variável 'final' '{op_name}' com '{node.op}'.",
                                getattr(node, "line", 1),
                            )
                        )
                    self._mark_local_var_reassigned(op_name)
            return empty

        if isinstance(node, BinaryOp):
            if node.op == "&&":
                fl = self._check_expression_flow(node.left)
                self._push_pattern_scope(fl.true_vars)
                try:
                    fr = self._check_expression_flow(node.right)
                finally:
                    self._pop_pattern_scope()
                merged_true = dict(fl.true_vars)
                merged_true.update(fr.true_vars)
                return self._FlowResult(true_vars=merged_true, false_vars={})

            if node.op == "||":
                fl = self._check_expression_flow(node.left)
                self._push_pattern_scope(fl.false_vars)
                try:
                    fr = self._check_expression_flow(node.right)
                finally:
                    self._pop_pattern_scope()
                merged_false = dict(fl.false_vars)
                merged_false.update(fr.false_vars)
                return self._FlowResult(true_vars={}, false_vars=merged_false)

            self._check_expression_flow(node.left)
            self._check_expression_flow(node.right)
            if node.op in ("+", "-", "*", "/", "%"):
                left_type = self.infer_type(node.left)
                right_type = self.infer_type(node.right)
                line = getattr(node, "line", 1)

                # 1. Regra do Java para '+': se pelo menos um operando for String,
                #    trata-se de concatenação válida e o tipo resultante é String.
                if node.op == "+" and (left_type == "String" or right_type == "String"):
                    return empty

                # Demais operadores aritméticos (-, *, /, %) não suportam String
                if left_type == "String" or right_type == "String":
                    self.errors.append(
                        SemanticError(
                            f"Operação aritmética '{node.op}' inválida: tipo 'String' não é suportado em operações aritméticas.",
                            line,
                        )
                    )
                else:
                    numeric_types = {"int", "double", "float", "long", "short", "byte", "char"}
                    if (
                        left_type
                        and right_type
                        and left_type not in ("Object", "desconhecido")
                        and right_type not in ("Object", "desconhecido")
                        and not (left_type in numeric_types and right_type in numeric_types)
                    ):
                        self.errors.append(
                            SemanticError(
                                f"Operação aritmética '{node.op}' inválida entre tipos '{left_type}' e '{right_type}'.",
                                line,
                            )
                        )
            return empty

        return empty

    def is_assignable(self, target_type: str, source_type: str) -> bool:
        """
        Verifica compatibilidade de atribuição entre o tipo alvo e o da expressão,
        suportando as regras de promoção implícita (widening primitive conversion) do Java:
        byte -> short -> int -> long -> float -> double
        char -> int
        """
        if not target_type or not source_type:
            return True
        if target_type == source_type:
            return True
        widening_map = {
            "double": {"int", "float", "long", "short", "byte", "char"},
            "float": {"int", "long", "short", "byte", "char"},
            "long": {"int", "short", "byte", "char"},
            "int": {"short", "byte", "char"},
            "short": {"byte"},
        }
        if target_type in widening_map and source_type in widening_map[target_type]:
            return True
        if target_type in ("Object", "desconhecido", "var") or source_type in ("Object", "desconhecido", "var"):
            return True
        if source_type == "null":
            return target_type not in self.PRIMITIVE_TYPES
        if self._is_subtype(source_type, target_type) is True:
            return True
        if (not self._is_known_type(target_type) or not self._is_known_type(source_type)) and target_type not in self.PRIMITIVE_TYPES and source_type not in self.PRIMITIVE_TYPES:
            return True
        return False

    def infer_type(self, node: Optional[ASTNode]) -> Optional[str]:
        """Inferência simples de tipos para expressões primitivas com suporte a widening."""
        if node is None:
            return None
        if isinstance(node, Literal):
            if node.kind in ("STRING", "TEXT_BLOCK"):
                return "String"
            if node.kind == "NULL":
                return "null"
            if node.kind == "BOOLEAN":
                return "boolean"
            if node.kind == "CHAR":
                return "char"
            if node.kind == "DOUBLE":
                return "double"
            if node.kind == "FLOAT":
                return "float"
            if node.kind in ("NUM", "INT"):
                val_str = str(node.value)
                # Hexadecimais inteiros (ex: 0x0F, 0xFF) são int e não devem ser
                # classificados como float apenas por terminarem em 'F'/'f' ou 'D'/'d'.
                if val_str.startswith(("0x", "0X")) and not any(c in val_str for c in ('p', 'P', '.')):
                    return "int"
                if "." in val_str or "e" in val_str.lower() or val_str.endswith(("f", "F", "d", "D")):
                    if val_str.endswith(("f", "F")):
                        return "float"
                    return "double"
                return "int"
            return "int"
        if isinstance(node, ClassLiteral):
            return "Class"
        if isinstance(node, MemberAccess) and isinstance(node.target, Identifier):
            if node.target.name in self._enums:
                return node.target.name
            return None
        if isinstance(node, Identifier):
            symbol = self._lookup_var_symbol(node.name)
            return symbol["type"] if symbol and "type" in symbol else None
        if isinstance(node, ObjectCreationExpression):
            return self._normalize_type_str(getattr(node, "type_ref", None)) or getattr(node, "class_name", None)
        if isinstance(node, InstanceOfExpression):
            return "boolean"
        if isinstance(node, CastExpression):
            return self._normalize_type_str(getattr(node, "target_type", None)) or str(node.target_type)
        if isinstance(node, ConditionalExpression):
            then_t = self.infer_type(node.then_expr)
            else_t = self.infer_type(node.else_expr)
            if then_t and else_t:
                if then_t == else_t:
                    return then_t
                if "double" in (then_t, else_t):
                    return "double"
                if "float" in (then_t, else_t):
                    return "float"
            return then_t if then_t else else_t
        if isinstance(node, UnaryOp):
            if node.op == "!":
                return "boolean"
            return self.infer_type(node.operand)
        if isinstance(node, Assignment):
            if node.name and "." not in node.name and not node.name.startswith("this."):
                symbol = self._lookup_var_symbol(node.name)
                if symbol and "type" in symbol:
                    return symbol["type"]
            return self.infer_type(node.expression)
        if isinstance(node, BinaryOp):
            if node.op in ("&&", "||", "==", "!=", "<", ">", "<=", ">="):
                return "boolean"
            left = self.infer_type(node.left)
            right = self.infer_type(node.right)
            if node.op == "+" and (left == "String" or right == "String"):
                return "String"
            if left and right:
                # Promoção binária aritmética oficial do Java (widening)
                if "double" in (left, right):
                    return "double"
                if "float" in (left, right):
                    return "float"
                if "long" in (left, right):
                    return "long"
                if left == "int" and right == "int":
                    return "int"
                numeric_int_types = {"int", "short", "byte", "char"}
                if left in numeric_int_types and right in numeric_int_types:
                    return "int"
            return left or right or None
        return None

    def check_assignment_type(
        self,
        target_type: str,
        expression: ASTNode,
        target_name: str,
        line: int,
        operator: str = "=",
    ):
        """
        Verifica compatibilidade entre o tipo alvo e o da expressão com suporte a
        promoção por alargamento e concatenação composta (+= quando o destino for String).
        """
        if operator == "+=" and target_type == "String":
            return

        if operator != "=" and target_type == "String":
            self.errors.append(
                SemanticError(
                    f"Operação aritmética '{operator}' inválida: tipo 'String' não é suportado em operações aritméticas.",
                    line,
                )
            )
            return

        expr_type = self.infer_type(expression)
        if expr_type and not self.is_assignable(target_type, expr_type):
            self.errors.append(
                SemanticError(
                    f"Incompatibilidade de tipos: não é possível atribuir {expr_type} a '{target_name}' do tipo {target_type}.",
                    line,
                )
            )
