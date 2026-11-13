"""
Módulo de Análise de Acesso a Membros, Herança e Sobrescrita conforme a JLS
(§§6.6, 8.1, 8.3, 8.4, 8.8, 9.1, 9.4, 9.6.4.4).

Centraliza:
- Registro multi-unidade de pacotes, imports e metadados de tipos;
- Controle de acesso (public, protected, package-private, private e nestmates);
- Regras de hierarquia (classes final, abstract, ciclos, extends/implements);
- Sobrescrita e ocultação de métodos, retorno covariante, visibilidade e @Override;
- Conflitos de métodos default/abstract em múltiplas interfaces e classe abstrata;
- Regras de modificadores de construtores e ciclos de invocação recursiva 'this(...)'.
"""

from typing import Any, Dict, List, Optional, Set, Tuple


class InheritanceAccessAnalyzer:
    """Analisador centralizado de controle de acesso, herança e sobrescrita."""

    BUILTIN_PACKAGES = {
        "Object": "java.lang",
        "String": "java.lang",
        "StringBuilder": "java.lang",
        "StringBuffer": "java.lang",
        "CharSequence": "java.lang",
        "Appendable": "java.lang",
        "Number": "java.lang",
        "Integer": "java.lang",
        "Long": "java.lang",
        "Double": "java.lang",
        "Float": "java.lang",
        "Byte": "java.lang",
        "Short": "java.lang",
        "Boolean": "java.lang",
        "Character": "java.lang",
        "Void": "java.lang",
        "Class": "java.lang",
        "System": "java.lang",
        "Math": "java.lang",
        "Thread": "java.lang",
        "Runnable": "java.lang",
        "AutoCloseable": "java.lang",
        "Comparable": "java.lang",
        "Cloneable": "java.lang",
        "Iterable": "java.lang",
        "Record": "java.lang",
        "Enum": "java.lang",
        "Throwable": "java.lang",
        "Exception": "java.lang",
        "RuntimeException": "java.lang",
        "Error": "java.lang",
        "IllegalArgumentException": "java.lang",
        "IllegalStateException": "java.lang",
        "NullPointerException": "java.lang",
        "IndexOutOfBoundsException": "java.lang",
        "ArrayIndexOutOfBoundsException": "java.lang",
        "NumberFormatException": "java.lang",
        "ArithmeticException": "java.lang",
        "ClassCastException": "java.lang",
        "UnsupportedOperationException": "java.lang",
        "InterruptedException": "java.lang",
        "CloneNotSupportedException": "java.lang",
        "ReflectiveOperationException": "java.lang",
        "ClassNotFoundException": "java.lang",
        "Closeable": "java.io",
        "InputStream": "java.io",
        "OutputStream": "java.io",
        "FileInputStream": "java.io",
        "FileOutputStream": "java.io",
        "Reader": "java.io",
        "InputStreamReader": "java.io",
        "FileReader": "java.io",
        "BufferedReader": "java.io",
        "Writer": "java.io",
        "FileWriter": "java.io",
        "File": "java.io",
        "PrintStream": "java.io",
        "Serializable": "java.io",
        "IOException": "java.io",
        "FileNotFoundException": "java.io",
        "EOFException": "java.io",
        "Collection": "java.util",
        "List": "java.util",
        "ArrayList": "java.util",
        "LinkedList": "java.util",
        "Set": "java.util",
        "HashSet": "java.util",
        "Map": "java.util",
        "HashMap": "java.util",
        "Iterator": "java.util",
        "ListIterator": "java.util",
        "Comparator": "java.util",
        "Optional": "java.util",
        "Collections": "java.util",
        "Arrays": "java.util",
        "Objects": "java.util",
        "Callable": "java.util.concurrent",
        "SQLException": "java.sql",
    }

    ACCESS_NAMES = ("private", "package", "protected", "public")

    def __init__(self, host: Any):
        self.host = host
        self._type_meta: Dict[str, Dict[str, Any]] = {}
        self._simple_to_keys: Dict[str, List[str]] = {}
        self._node_to_key: Dict[int, str] = {}
        self._current_unit: Optional[Any] = None
        self._current_unit_package: str = ""
        self._enclosing_type_keys: List[str] = []

    def reset(self) -> None:
        self._type_meta = {}
        self._simple_to_keys = {}
        self._node_to_key = {}
        self._current_unit = None
        self._current_unit_package = ""
        self._enclosing_type_keys = []

    def _err(self, msg: str, line: int) -> Any:
        from .semantic import SemanticError
        return SemanticError(msg, line)

    # -------------------------------------------------------------------------
    # Registro de Pacotes, Unidades de Compilação e Resolução de Tipos
    # -------------------------------------------------------------------------
    def set_current_unit(self, unit: Optional[Any]) -> None:
        self._current_unit = unit
        pkg_node = getattr(unit, "package", None) if unit is not None else None
        self._current_unit_package = (getattr(pkg_node, "name", None) or "") if pkg_node is not None else ""

    def push_enclosing_type(self, type_node: Any) -> Optional[str]:
        key = self._node_to_key.get(id(type_node))
        if not key:
            tname = getattr(type_node, "name", None)
            if tname:
                key = f"{self._current_unit_package}.{tname}" if self._current_unit_package else tname
        if key:
            self._enclosing_type_keys.append(key)
        return key

    def pop_enclosing_type(self, pushed_key: Optional[str]) -> None:
        if pushed_key and self._enclosing_type_keys:
            self._enclosing_type_keys.pop()

    def register_unit_types(self, unit: Any) -> None:
        """Registra tipos top-level e aninhados de uma CompilationUnit com pacote e metadados."""
        from .ast_nodes import (
            AnnotationInterfaceDeclaration,
            ClassDeclaration,
            EnumConstantBody,
            EnumDeclaration,
            InterfaceDeclaration,
            RecordDeclaration,
        )

        pkg_node = getattr(unit, "package", None)
        pkg = (getattr(pkg_node, "name", None) or "") if pkg_node is not None else ""

        def register_type(node: Any, parent_key: Optional[str], top_key: Optional[str], parent_kind: Optional[str]):
            kind = None
            if isinstance(node, AnnotationInterfaceDeclaration):
                kind = "annotation_interface"
            elif isinstance(node, EnumDeclaration):
                kind = "enum"
            elif isinstance(node, RecordDeclaration):
                kind = "record"
            elif isinstance(node, InterfaceDeclaration):
                kind = "interface"
            elif isinstance(node, ClassDeclaration):
                kind = "class"
            if kind is None or not getattr(node, "name", None):
                return

            if parent_key:
                fqn = f"{parent_key}.{node.name}"
                eff_top = top_key or parent_key
            else:
                fqn = f"{pkg}.{node.name}" if pkg else node.name
                eff_top = fqn

            mods = list(getattr(node, "modifiers", []) or [])
            acc = self.effective_access(mods, owner_kind=parent_kind or "package", member_kind="tipo")
            meta = {
                "key": fqn,
                "name": node.name,
                "fqn": fqn,
                "package": pkg,
                "kind": kind,
                "node": node,
                "modifiers": mods,
                "access": acc,
                "is_nested": parent_key is not None,
                "enclosing_key": parent_key,
                "top_level_key": eff_top,
                "unit": unit,
            }
            self._type_meta[fqn] = meta
            self._node_to_key[id(node)] = fqn
            self._simple_to_keys.setdefault(node.name, [])
            if fqn not in self._simple_to_keys[node.name]:
                self._simple_to_keys[node.name].append(fqn)

            self.host._declared_types[fqn] = (kind, node)
            self.host._declared_types.setdefault(node.name, (kind, node))

            for m in getattr(node, "members", []):
                register_type(m, fqn, eff_top, kind)
            if isinstance(node, EnumDeclaration):
                for c in getattr(node, "constants", []):
                    if isinstance(getattr(c, "body", None), EnumConstantBody):
                        for cm in c.body.members:
                            register_type(cm, fqn, eff_top, "class")

        for tdecl in getattr(unit, "type_declarations", []):
            register_type(tdecl, None, None, None)

    def register_local_type(self, node: Any, kind: str) -> str:
        """Registra classe/interface/enum/record local no mapa de metadados vinculando ao nest atual."""
        name = getattr(node, "name", "")
        top_key = self.current_top_level_key()
        parent_key = self._enclosing_type_keys[-1] if self._enclosing_type_keys else None
        pkg = self._current_unit_package
        fqn = f"{parent_key}.{name}" if parent_key else (f"{pkg}.{name}" if pkg else name)
        eff_top = top_key or fqn
        mods = list(getattr(node, "modifiers", []) or [])
        meta = {
            "key": fqn,
            "name": name,
            "fqn": fqn,
            "package": pkg,
            "kind": kind,
            "node": node,
            "modifiers": mods,
            "access": "package",
            "is_nested": False,
            "is_local": True,
            "enclosing_key": parent_key,
            "top_level_key": eff_top,
            "unit": self._current_unit,
        }
        self._type_meta[fqn] = meta
        self._node_to_key[id(node)] = fqn
        return fqn

    def current_top_level_key(self) -> Optional[str]:
        if not self._enclosing_type_keys:
            return None
        inner = self._enclosing_type_keys[-1]
        meta = self._type_meta.get(inner)
        if meta is not None:
            return meta.get("top_level_key") or inner
        return self._enclosing_type_keys[0]

    def current_enclosing_key(self) -> Optional[str]:
        if self._enclosing_type_keys:
            return self._enclosing_type_keys[-1]
        return self.host._current_enclosing_type()

    def get_type_meta(self, type_name: Optional[str], context_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not type_name:
            return None
        key = self.resolve_type_key(type_name, context_type=context_type)
        if key and key in self._type_meta:
            return self._type_meta[key]
        return None

    def resolve_type_key(
        self,
        type_name: Optional[str],
        context_type: Optional[str] = None,
    ) -> Optional[str]:
        """Resolve nome simples ou qualificado para chave canônica respeitando pacote e imports."""
        if not type_name:
            return None
        clean = self.host._strip_leading_type_annotations(type_name) or type_name
        stripped = self.host._strip_generics(clean)
        if not stripped:
            return None
        base, dims = self.host._split_type_dims(stripped)
        if dims > 0 or base in self.host.PRIMITIVE_TYPES:
            return None

        if base in self._type_meta:
            return base

        # Verifica escopos locais primeiro
        simple = base.split(".")[-1]
        for lscope in reversed(self.host._local_declared_type_scopes):
            if base in lscope or simple in lscope:
                node_info = lscope.get(base) or lscope.get(simple)
                if node_info is not None:
                    nkey = self._node_to_key.get(id(node_info[1]))
                    if nkey:
                        return nkey

        # Tipos aninhados dentro da hierarquia envolvente atual
        for enc_key in reversed(self._enclosing_type_keys):
            candidate_nested = f"{enc_key}.{base}"
            if candidate_nested in self._type_meta:
                return candidate_nested
            emeta = self._type_meta.get(enc_key)
            if emeta and emeta["name"] == base:
                return enc_key

        ctx_unit = self._current_unit
        ctx_pkg = self._current_unit_package
        if context_type:
            cmeta = self._type_meta.get(context_type)
            if cmeta is not None:
                ctx_unit = cmeta.get("unit")
                ctx_pkg = cmeta.get("package", "")
                cand = f"{context_type}.{base}"
                if cand in self._type_meta:
                    return cand

        if ctx_unit is not None:
            imports = getattr(ctx_unit, "imports", []) or []
            # 1. Import explícito de tipo único (import pkg.X;)
            for imp in imports:
                if not getattr(imp, "is_static", False) and not getattr(imp, "is_wildcard", False):
                    iname = getattr(imp, "name", "")
                    if iname and iname.split(".")[-1] == base:
                        if iname in self._type_meta:
                            return iname
                        return iname

            # 2. Mesmo pacote
            same_pkg_key = f"{ctx_pkg}.{base}" if ctx_pkg else base
            if same_pkg_key in self._type_meta:
                return same_pkg_key

            # 3. Import sob demanda (import pkg.*;)
            for imp in imports:
                if not getattr(imp, "is_static", False) and getattr(imp, "is_wildcard", False):
                    iname = getattr(imp, "name", "")
                    cand = f"{iname}.{base}" if iname else base
                    if cand in self._type_meta:
                        return cand

            # Se existe exatamente no mapa em outro pacote mas não foi importado, NÃO vaza silenciosamente
            if base in self._simple_to_keys:
                return None

        keys = self._simple_to_keys.get(base, [])
        if len(keys) == 1:
            return keys[0]
        if base in self.host._declared_types:
            return base
        return None

    def get_type_package(self, type_name: Optional[str]) -> str:
        if not type_name:
            return self._current_unit_package
        clean = self.host._strip_generics(self.host._strip_leading_type_annotations(type_name) or type_name) or ""
        base, _ = self.host._split_type_dims(clean)
        meta = self._type_meta.get(base) or self.get_type_meta(base)
        if meta is not None:
            return meta.get("package", "")
        if hasattr(self.host, "_resolve_external_type"):
            ext = self.host._resolve_external_type(base)
            if ext is not None:
                return ext.package
        simple = base.split(".")[-1]
        if "." in base and base.rsplit(".", 1)[0]:
            if simple in self.BUILTIN_PACKAGES and base.startswith(self.BUILTIN_PACKAGES[simple] + "."):
                return self.BUILTIN_PACKAGES[simple]
            return base.rsplit(".", 1)[0]
        if simple in self.BUILTIN_PACKAGES:
            return self.BUILTIN_PACKAGES[simple]
        return self._current_unit_package

    def get_top_level_key(self, type_name: Optional[str]) -> Optional[str]:
        if not type_name:
            return None
        meta = self._type_meta.get(type_name) or self.get_type_meta(type_name)
        if meta is not None:
            return meta.get("top_level_key") or meta["key"]
        if hasattr(self.host, "_resolve_external_type"):
            ext = self.host._resolve_external_type(type_name)
            if ext is not None:
                return ext.top_level_fqn or ext.fqn
        return self.host._simple_base_name(type_name) or type_name

    # -------------------------------------------------------------------------
    # Matriz de Acesso (JLS §6.6.1 e §6.6.2)
    # -------------------------------------------------------------------------
    @staticmethod
    def effective_access(modifiers: List[str], owner_kind: str = "class", member_kind: str = "metodo") -> str:
        """Determina o modificador de acesso efetivo ('public', 'protected', 'package', 'private')."""
        mset = set(modifiers or [])
        if owner_kind == "interface" and member_kind in ("metodo", "campo", "constante_interface", "tipo"):
            return "private" if "private" in mset else "public"
        if owner_kind == "enum" and member_kind == "construtor":
            return "private"
        for mod in ("public", "protected", "private"):
            if mod in mset:
                return mod
        return "package"

    def is_type_accessible(self, target_key_or_name: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Verifica se um tipo (top-level ou aninhado) é acessível a partir do contexto atual."""
        if not target_key_or_name:
            return True, None
        meta = self._type_meta.get(target_key_or_name) or self.get_type_meta(target_key_or_name)
        if meta is None:
            ext = self.host._resolve_external_type(target_key_or_name) if hasattr(self.host, "_resolve_external_type") else None
            if ext is None:
                return True, None
            if ext.is_nested and ext.enclosing_fqn:
                return self.is_member_accessible(
                    decl_owner=ext.enclosing_fqn,
                    access=ext.access,
                    is_static=("static" in ext.modifiers),
                    member_kind="tipo",
                    member_name=ext.simple_name,
                    receiver_type=None,
                    via_super=True,
                )
            if ext.access == "public" or self._current_unit_package == ext.package:
                return True, None
            return (
                False,
                f"O tipo '{ext.fqn}' não é público em '{ext.package or '<padrão>'}'; não pode ser acessado fora do pacote (JLS §6.6.1).",
            )
        if meta.get("is_local", False):
            return True, None
        if meta.get("is_nested", False) and meta.get("enclosing_key"):
            ok, reason = self.is_member_accessible(
                decl_owner=meta["enclosing_key"],
                access=meta["access"],
                is_static=("static" in meta.get("modifiers", [])),
                member_kind="tipo",
                member_name=meta["name"],
                receiver_type=None,
                via_super=True,
            )
            return ok, reason
        acc = meta.get("access", "package")
        if acc == "public":
            return True, None
        decl_pkg = meta.get("package", "")
        if self._current_unit_package == decl_pkg:
            return True, None
        return (
            False,
            f"O tipo '{meta['fqn']}' não é público em '{decl_pkg or '<padrão>'}'; não pode ser acessado fora do pacote (JLS §6.6.1).",
        )

    def check_type_access(self, type_name: Optional[str], line: int, context_desc: str = "") -> bool:
        """Verifica existência em outro pacote e visibilidade de tipo referenciado."""
        if not type_name:
            return True
        clean = self.host._strip_leading_type_annotations(type_name) or type_name
        stripped = self.host._strip_generics(clean) or ""
        base, _ = self.host._split_type_dims(stripped)
        if not base or base in self.host.PRIMITIVE_TYPES or base in ("void", "var"):
            return True

        resolved = self.resolve_type_key(base)
        if resolved is None and "." not in base and base in self._simple_to_keys and self._current_unit is not None:
            # Tipo declarado em outro pacote sem import no arquivo atual
            if not self.host._is_known_type_ignoring_other_pkgs(base):
                self.host.errors.append(
                    self._err(
                        f"Tipo '{base}' não foi encontrado no pacote atual ou importado para {context_desc or 'esta referência'} (JLS §6.5.5).",
                        line,
                    )
                )
                return False
        if resolved:
            ok, msg = self.is_type_accessible(resolved)
            if not ok and msg:
                self.host.errors.append(self._err(msg, line))
                return False
        elif hasattr(self.host, "_resolve_external_type"):
            ext_t = self.host._resolve_external_type(base)
            if ext_t is not None:
                ok, msg = self.is_type_accessible(ext_t.fqn)
                if not ok and msg:
                    self.host.errors.append(self._err(msg, line))
                    return False
        return True

    def is_member_accessible(
        self,
        decl_owner: Optional[str],
        access: str,
        is_static: bool,
        member_kind: str,
        member_name: str,
        receiver_type: Optional[str] = None,
        via_super: bool = False,
        is_anon_ctor: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """Aplica matriz completa JLS §6.6.1 / §6.6.2 (public, protected, package-private, private e nestmates)."""
        if self.host._flow_suppress_errors:
            return True, None
        if not decl_owner or access == "public":
            return True, None

        decl_meta = self._type_meta.get(decl_owner) or self.get_type_meta(decl_owner)
        decl_label = decl_meta["name"] if decl_meta else (self.host._simple_base_name(decl_owner) or decl_owner)
        decl_pkg = decl_meta.get("package", "") if decl_meta else self.get_type_package(decl_owner)
        decl_top = (decl_meta.get("top_level_key") or decl_meta["key"]) if decl_meta else self.get_top_level_key(decl_owner)

        cur_pkg = self._current_unit_package
        cur_top = self.current_top_level_key()

        if access == "private":
            if cur_top is not None and decl_top is not None and cur_top == decl_top:
                return True, None
            return (
                False,
                f"{member_kind.capitalize()} '{member_name}' possui acesso 'private' em '{decl_label}' (JLS §6.6.1).",
            )

        if access == "package":
            if cur_pkg == decl_pkg:
                return True, None
            return (
                False,
                f"{member_kind.capitalize()} '{member_name}' não é público em '{decl_label}' (pacote '{decl_pkg or '<padrão>'}'); não pode ser acessado fora do pacote (JLS §6.6.1).",
            )

        if access == "protected":
            if cur_pkg == decl_pkg:
                return True, None

            # Pacotes diferentes: precisa estar dentro de subclasse S de decl_owner (JLS §6.6.2)
            enclosing_subclasses: List[str] = []
            for enc_k in reversed(self._enclosing_type_keys):
                if enc_k == decl_owner or self.host._is_subtype(enc_k, decl_owner) is True:
                    enclosing_subclasses.append(enc_k)
            if not enclosing_subclasses:
                return (
                    False,
                    f"{member_kind.capitalize()} '{member_name}' possui acesso 'protected' em '{decl_label}' e não é acessível a partir do pacote '{cur_pkg or '<padrão>'}' (JLS §6.6.2).",
                )

            if is_static:
                return True, None

            if member_kind == "construtor":
                if via_super or is_anon_ctor:
                    return True, None
                return (
                    False,
                    f"Construtor 'protected' '{member_name}(...)' de '{decl_label}' não pode ser invocado com 'new' fora do pacote de declaração sem corpo de subclasse anônima (JLS §6.6.2).",
                )

            # Membro de instância protected em pacote diferente:
            # o tipo do receptor Q deve ser subtipo de alguma subclasse envolvente S <: decl_owner (JLS §6.6.2.1)
            if via_super or not receiver_type:
                return True, None
            q_resolved = self.resolve_type_key(receiver_type) or receiver_type
            for sub_s in enclosing_subclasses:
                if q_resolved == sub_s or self.host._is_subtype(q_resolved, sub_s) is True:
                    return True, None
            q_label = self.host._simple_base_name(receiver_type) or receiver_type
            s_label = self.host._simple_base_name(enclosing_subclasses[0]) or enclosing_subclasses[0]
            return (
                False,
                f"{member_kind.capitalize()} 'protected' '{member_name}' declarado em '{decl_label}' não pode ser acessado através de referência do tipo '{q_label}' dentro da subclasse '{s_label}' em outro pacote (JLS §6.6.2).",
            )

        return True, None

    def check_member_access(
        self,
        decl_owner: Optional[str],
        access: str,
        is_static: bool,
        member_kind: str,
        member_name: str,
        line: int,
        receiver_type: Optional[str] = None,
        via_super: bool = False,
        is_anon_ctor: bool = False,
    ) -> bool:
        ok, msg = self.is_member_accessible(
            decl_owner=decl_owner,
            access=access,
            is_static=is_static,
            member_kind=member_kind,
            member_name=member_name,
            receiver_type=receiver_type,
            via_super=via_super,
            is_anon_ctor=is_anon_ctor,
        )
        if not ok and msg:
            self.host.errors.append(self._err(msg, line))
        return ok

    # -------------------------------------------------------------------------
    # Validação de Hierarquia de Tipos (final, abstract, ciclos, extends/implements)
    # -------------------------------------------------------------------------
    def validate_type_hierarchy(self, type_decl: Any, owner_key: Optional[str]) -> None:
        """Valida regras de herança de classe, interface, record e enum (JLS §§8.1.1, 8.1.4, 8.1.5, 9.1.3)."""
        from .ast_nodes import ClassDeclaration, EnumDeclaration, InterfaceDeclaration, RecordDeclaration

        line = getattr(type_decl, "line", 1)
        tname = getattr(type_decl, "name", "")
        mods = set(getattr(type_decl, "modifiers", []) or [])

        if isinstance(type_decl, ClassDeclaration):
            if "abstract" in mods and "final" in mods:
                self.host.errors.append(
                    self._err(f"Classe '{tname}' não pode combinar modificadores 'abstract' e 'final' (JLS §8.1.1.2).", line)
                )

            ext = getattr(type_decl, "extends_type", None)
            if ext is not None:
                ext_line = getattr(ext, "line", line)
                ext_raw = self.host._normalize_type_str(ext)
                if ext_raw:
                    self.check_type_access(ext_raw, ext_line, f"cláusula 'extends' de '{tname}'")
                    ext_key = self.resolve_type_key(ext_raw)
                    ext_simple = self.host._simple_base_name(ext_raw) or ext_raw
                    ext_meta = self._type_meta.get(ext_key) if ext_key else None
                    if ext_meta is not None:
                        ekind = ext_meta["kind"]
                        emods = set(ext_meta.get("modifiers", []))
                        if ekind == "interface" or ekind == "annotation_interface":
                            self.host.errors.append(
                                self._err(f"Classe '{tname}' não pode estender a interface '{ext_simple}'; use 'implements' (JLS §8.1.4).", ext_line)
                            )
                        elif ekind in ("enum", "record"):
                            self.host.errors.append(
                                self._err(f"Classe '{tname}' não pode herdar de {ekind} '{ext_simple}' (JLS §8.9 / §8.10).", ext_line)
                            )
                        elif "final" in emods:
                            self.host.errors.append(
                                self._err(f"Classe '{tname}' não pode herdar da classe 'final' '{ext_simple}' (JLS §8.1.1.2).", ext_line)
                            )
                    else:
                        ext_info = self.host._resolve_external_type(ext_raw) if hasattr(self.host, "_resolve_external_type") else None
                        if ext_info is not None:
                            if ext_info.kind in ("interface", "annotation_interface"):
                                self.host.errors.append(
                                    self._err(f"Classe '{tname}' não pode estender a interface '{ext_simple}'; use 'implements' (JLS §8.1.4).", ext_line)
                                )
                            elif ext_info.kind in ("enum", "record"):
                                self.host.errors.append(
                                    self._err(f"Classe '{tname}' não pode herdar de {ext_info.kind} '{ext_simple}' (JLS §8.9 / §8.10).", ext_line)
                                )
                            elif ext_info.is_final:
                                self.host.errors.append(
                                    self._err(f"Classe '{tname}' não pode herdar da classe 'final' '{ext_simple}' (JLS §8.1.1.2).", ext_line)
                                )
                        elif ext_simple in self.host.BUILTIN_FINAL_TYPES:
                            self.host.errors.append(
                                self._err(f"Classe '{tname}' não pode herdar da classe 'final' '{ext_simple}' (JLS §8.1.1.2).", ext_line)
                            )
                        elif ext_simple in self.host.BUILTIN_INTERFACE_TYPES:
                            self.host.errors.append(
                                self._err(f"Classe '{tname}' não pode estender a interface '{ext_simple}'; use 'implements' (JLS §8.1.4).", ext_line)
                            )

                    # Detecção de ciclo na cadeia 'extends'
                    if owner_key:
                        self._check_inheritance_cycle(owner_key, tname, line, interface_only=False)

        if isinstance(type_decl, (ClassDeclaration, EnumDeclaration, RecordDeclaration)):
            seen_impls: Set[str] = set()
            for itype in getattr(type_decl, "implements_types", []) or []:
                iline = getattr(itype, "line", line)
                iraw = self.host._normalize_type_str(itype)
                if not iraw:
                    continue
                self.check_type_access(iraw, iline, f"cláusula 'implements' de '{tname}'")
                ikey = self.resolve_type_key(iraw)
                ext_ifc = (self.host._resolve_external_type(iraw) if hasattr(self.host, "_resolve_external_type") else None) if not ikey else None
                isimple = self.host._simple_base_name(iraw) or iraw
                canon = ikey or (ext_ifc.fqn if ext_ifc is not None else isimple)
                if canon in seen_impls:
                    self.host.errors.append(
                        self._err(f"Interface duplicada '{isimple}' na cláusula 'implements' de '{tname}' (JLS §8.1.5).", iline)
                    )
                seen_impls.add(canon)
                imeta = self._type_meta.get(ikey) if ikey else None
                if imeta is not None and imeta["kind"] not in ("interface",):
                    self.host.errors.append(
                        self._err(f"Tipo '{isimple}' em 'implements' de '{tname}' não é uma interface (JLS §8.1.5).", iline)
                    )
                elif ext_ifc is not None and ext_ifc.kind != "interface":
                    self.host.errors.append(
                        self._err(f"Tipo '{isimple}' em 'implements' de '{tname}' não é uma interface (JLS §8.1.5).", iline)
                    )
                elif imeta is None and ext_ifc is None and (isimple in self.host.BUILTIN_CLASS_TYPES or isimple in self.host.KNOWN_EXCEPTION_PARENTS):
                    self.host.errors.append(
                        self._err(f"Tipo '{isimple}' em 'implements' de '{tname}' não é uma interface (JLS §8.1.5).", iline)
                    )

        if isinstance(type_decl, InterfaceDeclaration):
            seen_exts: Set[str] = set()
            for etype in getattr(type_decl, "extends_types", []) or []:
                eline = getattr(etype, "line", line)
                eraw = self.host._normalize_type_str(etype)
                if not eraw:
                    continue
                self.check_type_access(eraw, eline, f"cláusula 'extends' da interface '{tname}'")
                ekey = self.resolve_type_key(eraw)
                ext_sup = (self.host._resolve_external_type(eraw) if hasattr(self.host, "_resolve_external_type") else None) if not ekey else None
                esimple = self.host._simple_base_name(eraw) or eraw
                canon = ekey or (ext_sup.fqn if ext_sup is not None else esimple)
                if canon in seen_exts:
                    self.host.errors.append(
                        self._err(f"Superinterface duplicada '{esimple}' na interface '{tname}' (JLS §9.1.3).", eline)
                    )
                seen_exts.add(canon)
                emeta = self._type_meta.get(ekey) if ekey else None
                if emeta is not None and emeta["kind"] != "interface":
                    self.host.errors.append(
                        self._err(f"Interface '{tname}' não pode estender o tipo não-interface '{esimple}' (JLS §9.1.3).", eline)
                    )
                elif ext_sup is not None and ext_sup.kind != "interface":
                    self.host.errors.append(
                        self._err(f"Interface '{tname}' não pode estender o tipo não-interface '{esimple}' (JLS §9.1.3).", eline)
                    )
                elif emeta is None and ext_sup is None and (esimple in self.host.BUILTIN_CLASS_TYPES or esimple in self.host.KNOWN_EXCEPTION_PARENTS):
                    self.host.errors.append(
                        self._err(f"Interface '{tname}' não pode estender a classe '{esimple}' (JLS §9.1.3).", eline)
                    )
            if owner_key:
                self._check_inheritance_cycle(owner_key, tname, line, interface_only=True)

    def _check_inheritance_cycle(self, start_key: str, display_name: str, line: int, interface_only: bool) -> None:
        visited: Set[str] = set()
        stack: List[str] = []
        meta = self._type_meta.get(start_key)
        if meta is None:
            return

        if interface_only:
            for e in getattr(meta["node"], "extends_types", []) or []:
                ek = self.resolve_type_key(self.host._normalize_type_str(e), context_type=start_key)
                if ek:
                    stack.append(ek)
        else:
            ext = getattr(meta["node"], "extends_type", None)
            if ext is not None:
                ek = self.resolve_type_key(self.host._normalize_type_str(ext), context_type=start_key)
                if ek:
                    stack.append(ek)

        while stack:
            cur = stack.pop()
            if cur == start_key:
                self.host.errors.append(
                    self._err(f"Herança cíclica envolvendo '{display_name}' (JLS §8.1.4 / §9.1.3).", line)
                )
                return
            if cur in visited:
                continue
            visited.add(cur)
            cmeta = self._type_meta.get(cur)
            if cmeta is None:
                continue
            if interface_only:
                if cmeta["kind"] == "interface":
                    for e in getattr(cmeta["node"], "extends_types", []) or []:
                        ek = self.resolve_type_key(self.host._normalize_type_str(e), context_type=cur)
                        if ek:
                            stack.append(ek)
            else:
                if cmeta["kind"] == "class":
                    ext = getattr(cmeta["node"], "extends_type", None)
                    if ext is not None:
                        ek = self.resolve_type_key(self.host._normalize_type_str(ext), context_type=cur)
                        if ek:
                            stack.append(ek)

    # -------------------------------------------------------------------------
    # Coleta de Métodos de Supertipos com Visibilidade de Herança (JLS §8.4.8.1)
    # -------------------------------------------------------------------------
    def _method_sig_key(self, name: str, params: List[str]) -> Tuple[str, Tuple[str, ...]]:
        """Chave canônica baseada em erasure simples dos parâmetros para casar sobrescritas."""
        erased: List[str] = []
        for p in params:
            clean = (self.host._strip_leading_type_annotations(p) or p).strip()
            no_gen = self.host._strip_generics(clean) or clean
            base, dims = self.host._split_type_dims(no_gen)
            simple = base.split(".")[-1]
            erased.append(f"{simple}{'[]' * dims}")
        return (name, tuple(erased))

    def _params_override_equivalent(self, sig1: Dict[str, Any], sig2: Dict[str, Any]) -> bool:
        p1 = sig1.get("params", [])
        p2 = sig2.get("params", [])
        if len(p1) != len(p2):
            return False
        for a, b in zip(p1, p2):
            ca = (self.host._strip_leading_type_annotations(a) or a).strip()
            cb = (self.host._strip_leading_type_annotations(b) or b).strip()
            if ca == cb:
                continue
            ea = self.host._strip_generics(ca) or ca
            eb = self.host._strip_generics(cb) or cb
            if (self.host._simple_base_name(ea) or ea) == (self.host._simple_base_name(eb) or eb):
                continue
            if self.host._is_type_variable(cb) or self.host._is_type_variable(ca):
                continue
            return False
        return True

    def _is_supertype_method_inherited_by(
        self,
        child_key: str,
        parent_sig: Dict[str, Any],
        class_ancestors: List[str],
        direct_super_sigs_map: Dict[str, List[Dict[str, Any]]],
    ) -> bool:
        """Determina se parent_sig é herdado/sobrescrito por child_key (JLS §8.4.8.1)."""
        p_access = parent_sig.get("access", "public")
        if p_access == "private":
            return False
        if p_access in ("public", "protected"):
            return True

        # package-private: herdado apenas no mesmo pacote OU via ponte transitiva (JLS §8.4.8.1(3))
        p_owner = parent_sig.get("owner_key") or parent_sig.get("owner")
        p_pkg = self.get_type_package(p_owner)
        c_pkg = self.get_type_package(child_key)
        if p_pkg == c_pkg:
            return True

        # Verifica cadeia de classes intermediárias entre child_key e p_owner
        if p_owner not in class_ancestors:
            return False
        p_idx = class_ancestors.index(p_owner)
        for mid_key in class_ancestors[:p_idx]:
            mid_pkg = self.get_type_package(mid_key)
            if mid_pkg == p_pkg:
                # Se alguma superclasse intermediária no pacote de p_owner já o sobrescreveu com protected/public
                for msig in direct_super_sigs_map.get(mid_key, []):
                    if self._params_override_equivalent(msig, parent_sig) and msig.get("access") in ("public", "protected"):
                        return True
        return False

    def _collect_hierarchy_methods(
        self,
        owner_key: str,
        method_name: Optional[str] = None,
        include_owner: bool = False,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Coleta assinaturas de métodos nos supertipos (sem estáticos de interfaces), retornando (sigs, tem_externo)."""
        collected: List[Dict[str, Any]] = []
        visited: Set[str] = set()
        has_external = False

        owner_meta = self._type_meta.get(owner_key)
        tvar_root = self.host._type_var_mapping_for_type(owner_key)

        if include_owner:
            queue: List[str] = [owner_key]
        else:
            visited.add(owner_key)
            supers, ext_flag = self.host._direct_supertypes(owner_key)
            if ext_flag:
                has_external = True
            queue = [self.host._substitute_type_vars(s, tvar_root) or s for s in supers]

        class_ancestors: List[str] = []
        direct_sigs_by_owner: Dict[str, List[Dict[str, Any]]] = {}

        while queue:
            cur = queue.pop(0)
            cur_base = self.host._strip_generics(cur) or cur
            cur_simple = self.host._simple_base_name(cur) or cur
            resolved_int = (
                self.host._lookup_internal_type_key(cur_base, context_type=owner_key)
                if hasattr(self.host, "_lookup_internal_type_key")
                else self.resolve_type_key(cur_base, context_type=owner_key)
            )
            cur_ext = (self.host._resolve_external_type(cur_base) if hasattr(self.host, "_resolve_external_type") else None) if resolved_int is None else None
            resolved = resolved_int or (cur_ext.fqn if cur_ext is not None else cur_simple)
            visit_id = resolved
            if not visit_id or visit_id in visited:
                continue
            visited.add(visit_id)

            tvar_map = self.host._type_var_mapping_for_type(cur)
            tmeta = self._type_meta.get(resolved)
            cur_is_interface = False

            if tmeta is not None:
                tkind, tnode = tmeta["kind"], tmeta["node"]
                cur_is_interface = (tkind == "interface")
                if tkind in ("class", "record", "enum"):
                    class_ancestors.append(resolved)
                sigs_here: List[Dict[str, Any]] = []
                for m in getattr(tnode, "members", []):
                    mname = getattr(m, "name", None)
                    if method_name is not None and mname != method_name:
                        continue
                    if not (hasattr(m, "parameters") and hasattr(m, "return_type")):
                        continue
                    sig = self.host._extract_method_sig(m, cur_simple, tvar_map)
                    sig["name"] = mname
                    sig["owner_key"] = resolved
                    sig["owner_kind"] = tkind
                    # Métodos estáticos de interface NUNCA são herdados (JLS §9.2 / §8.4.8)
                    if cur_is_interface and sig.get("static", False):
                        continue
                    sigs_here.append(sig)
                    collected.append(sig)
                direct_sigs_by_owner[resolved] = sigs_here
            else:
                sigs_here = []
                seen_here: Set[Tuple[str, Tuple[str, ...], bool]] = set()
                if cur_ext is not None:
                    cur_is_interface = (cur_ext.kind == "interface")
                    if cur_ext.kind in ("class", "record", "enum"):
                        class_ancestors.append(cur_ext.fqn)
                    mnames = [method_name] if method_name is not None else list(cur_ext.methods.keys())
                    for mn in mnames:
                        for minfo in cur_ext.methods.get(mn, []):
                            if cur_is_interface and minfo.static:
                                continue
                            sig = self.host._ext_method_to_sig(minfo, cur_ext, tvar_map)
                            p_key, va_key = self.host._sig_dedup_key(sig["params"], sig["varargs"])
                            skey = (mn, p_key, va_key)
                            if skey not in seen_here:
                                seen_here.add(skey)
                                sigs_here.append(sig)
                                collected.append(sig)
                if cur_simple in self.host.BUILTIN_METHODS and (cur_ext is None or self.host._is_partial_external_stdlib(cur_ext)):
                    cur_is_interface = (cur_simple in self.host.BUILTIN_INTERFACE_TYPES)
                    if not cur_is_interface and cur_ext is None:
                        class_ancestors.append(cur_simple)
                    mnames = [method_name] if method_name is not None else list(self.host.BUILTIN_METHODS[cur_simple].keys())
                    for mn in mnames:
                        for bsig in self.host.BUILTIN_METHODS[cur_simple].get(mn, []):
                            if cur_is_interface and bsig.get("static", False):
                                continue
                            bparams = [
                                self.host._substitute_type_vars(bp[:-3] if bp.endswith("...") else bp, tvar_map)
                                or (bp[:-3] if bp.endswith("...") else bp)
                                for bp in bsig["params"]
                            ]
                            bret = self.host._substitute_type_vars(bsig["ret"], tvar_map) or bsig["ret"]
                            bthrows = [self.host._substitute_type_vars(bt, tvar_map) or bt for bt in bsig.get("throws", [])]
                            is_def = bool(bsig.get("is_default", False))
                            is_abs = bool(bsig.get("is_abstract", cur_is_interface and not bsig.get("static", False) and not is_def))
                            is_va = bool(bsig.get("varargs", False))
                            p_key, va_key = self.host._sig_dedup_key(bparams, is_va)
                            skey = (mn, p_key, va_key)
                            if skey in seen_here:
                                continue
                            seen_here.add(skey)
                            sig = {
                                "name": mn,
                                "params": bparams,
                                "ret": bret,
                                "static": bsig.get("static", False),
                                "varargs": is_va,
                                "tparams": list(bsig.get("tparams", [])),
                                "throws": bthrows,
                                "owner": cur_simple,
                                "owner_key": cur_ext.fqn if cur_ext is not None else cur_simple,
                                "owner_kind": "interface" if cur_is_interface else "class",
                                "access": bsig.get("access", "public"),
                                "is_final": bool(bsig.get("is_final", False)),
                                "is_abstract": is_abs,
                                "is_default": is_def,
                            }
                            sigs_here.append(sig)
                            collected.append(sig)
                elif cur_ext is None and cur_simple not in self.host.BUILTIN_TYPE_SUPERTYPES and cur_simple not in self.host.KNOWN_EXCEPTION_PARENTS:
                    has_external = True
                if sigs_here:
                    direct_sigs_by_owner[resolved] = sigs_here

            supers, ext_flag = self.host._direct_supertypes(resolved if (tmeta is not None or cur_ext is not None) else cur)
            if ext_flag:
                has_external = True
            for s in supers:
                sub_s = self.host._substitute_type_vars(s, tvar_map) or s
                queue.append(sub_s)

        # Marca em cada sig se ela é efetivamente herdada por owner_key (excluindo private e pkg-private cruzado)
        out: List[Dict[str, Any]] = []
        for sig in collected:
            if sig.get("owner_key") == owner_key and include_owner:
                out.append(sig)
                continue
            if self._is_supertype_method_inherited_by(owner_key, sig, class_ancestors, direct_sigs_by_owner):
                out.append(sig)
        return out, has_external

    # -------------------------------------------------------------------------
    # Validação de Modificadores de Método, Sobrescrita, Retorno e @Override
    # -------------------------------------------------------------------------
    def _is_return_compatible(self, child_ret: str, parent_ret: str) -> Optional[bool]:
        """Verifica compatibilidade de retorno na sobrescrita/ocultação (JLS §8.4.5)."""
        cr = (self.host._strip_leading_type_annotations(child_ret) or child_ret).strip()
        pr = (self.host._strip_leading_type_annotations(parent_ret) or parent_ret).strip()
        if cr == pr:
            return True
        if cr == "void" or pr == "void":
            return False
        if cr in self.host.PRIMITIVE_TYPES or pr in self.host.PRIMITIVE_TYPES:
            return cr == pr
        if self.host._is_type_variable(cr) or self.host._is_type_variable(pr):
            return True
        return self.host._is_subtype(cr, pr)

    def validate_method_declaration(
        self,
        owner_key: str,
        member: Any,
        sig: Dict[str, Any],
        is_anonymous: bool = False,
        owner_kind: str = "class",
        owner_modifiers: Optional[List[str]] = None,
    ) -> None:
        """Valida modificadores abstract/corpo, sobrescrita/ocultação, covariância, visibilidade e @Override."""
        line = getattr(member, "line", 1)
        mname = getattr(member, "name", "")
        mods = set(getattr(member, "modifiers", []) or [])
        omods = set(owner_modifiers or [])

        # 1. Regras de modificadores abstract / corpo em classes, enums e records (interfaces já validadas em analyze_interface)
        if owner_kind in ("class", "enum", "record"):
            if "abstract" in mods:
                if owner_kind == "class" and "abstract" not in omods and not is_anonymous:
                    self.host.errors.append(
                        self._err(f"Classe concreta '{self.host._simple_base_name(owner_key) or owner_key}' não pode declarar método abstrato '{mname}(...)' (JLS §8.1.1.1).", line)
                    )
                elif owner_kind == "record":
                    self.host.errors.append(
                        self._err(f"Record '{self.host._simple_base_name(owner_key) or owner_key}' não pode declarar método abstrato '{mname}(...)' (JLS §8.10).", line)
                    )
                for bad in ("private", "static", "final", "synchronized", "native", "strictfp"):
                    if bad in mods:
                        self.host.errors.append(
                            self._err(f"Método abstrato '{mname}' não pode possuir o modificador '{bad}' (JLS §8.4.3.1).", line)
                        )
                if getattr(member, "body", None) is not None:
                    self.host.errors.append(
                        self._err(f"Método abstrato '{mname}' não pode possuir corpo (JLS §8.4.7).", line)
                    )
            elif "native" in mods:
                if getattr(member, "body", None) is not None:
                    self.host.errors.append(
                        self._err(f"Método 'native' '{mname}' não pode possuir corpo (JLS §8.4.7).", line)
                    )
            elif getattr(member, "body", None) is None:
                self.host.errors.append(
                    self._err(f"Método '{mname}' precisa possuir corpo ou ser declarado como 'abstract' (JLS §8.4.7).", line)
                )

        # 2. Busca métodos herdados de mesmo nome nos supertipos
        has_override = any(
            getattr(a, "name", "").split(".")[-1] == "Override"
            for a in (getattr(member, "annotations", []) or [])
        )
        super_methods, has_external = self._collect_hierarchy_methods(
            owner_key,
            method_name=mname,
            include_owner=is_anonymous,
        )
        matching_parents = [ps for ps in super_methods if self._params_override_equivalent(sig, ps)]

        # Métodos privados nunca sobrescrevem nem ocultam métodos herdados (JLS §8.4.8.1)
        if "private" in mods:
            if has_override:
                self.host.errors.append(
                    self._err(f"Método 'private' '{mname}' não pode ser anotado com '@Override' (JLS §9.6.4.4).", line)
                )
            return

        # Interface 'default' não pode sobrescrever método de java.lang.Object (JLS §9.4.1.2)
        if owner_kind == "interface" and "default" in mods:
            if any((ps.get("owner") == "Object") for ps in matching_parents):
                self.host.errors.append(
                    self._err(f"Método 'default' '{mname}' na interface não pode sobrescrever método de 'java.lang.Object' (JLS §9.4.1.2).", line)
                )

        if has_override:
            if sig.get("static", False):
                self.host.errors.append(
                    self._err(f"Método estático '{mname}' não pode ser anotado com '@Override' (JLS §9.6.4.4).", line)
                )
            else:
                instance_matches = [ps for ps in matching_parents if not ps.get("static", False)]
                # Em interface, @Override é válido para métodos públicos de Object mesmo sem supertipo explícito;
                # em record, @Override é válido no acessor explícito de componente (JLS §8.10.3 / §9.6.4.4)
                object_pub_match = (
                    owner_kind == "interface"
                    and self.host._is_object_public_method_sig(mname, sig)
                )
                record_comp_match = False
                if owner_kind == "record" and not sig.get("params"):
                    rmeta = self.get_type_meta(owner_key)
                    if rmeta is not None:
                        record_comp_match = any(
                            getattr(c, "name", None) == mname
                            for c in getattr(rmeta["node"], "components", [])
                        )
                if not instance_matches and not object_pub_match and not record_comp_match:
                    if has_external:
                        self.host._record_unresolved(
                            f"Validação de '@Override' em '{mname}' adiada devido a supertipo externo não resolvido."
                        )
                    else:
                        self.host.errors.append(
                            self._err(
                                f"O método '{mname}(...)' anotado com '@Override' não sobrescreve nem implementa nenhum método de um supertipo (JLS §9.6.4.4).",
                                line,
                            )
                        )

        child_is_static = bool(sig.get("static", False))
        child_access = sig.get("access", "package")
        child_rank = self.host.ACCESS_RANK.get(child_access, 1)

        for ps in matching_parents:
            p_owner = ps.get("owner") or "supertipo"
            p_static = bool(ps.get("static", False))
            # JLS §8.4.8.2: static vs instância
            if child_is_static and not p_static:
                self.host.errors.append(
                    self._err(f"O método estático '{mname}(...)' não pode ocultar o método de instância de '{p_owner}' (JLS §8.4.8.2).", line)
                )
                continue
            if not child_is_static and p_static:
                self.host.errors.append(
                    self._err(f"O método de instância '{mname}(...)' não pode sobrescrever o método estático de '{p_owner}' (JLS §8.4.8.2).", line)
                )
                continue

            # JLS §8.4.3.3: método final não pode ser sobrescrito ou ocultado
            if ps.get("is_final", False):
                self.host.errors.append(
                    self._err(f"Não é possível sobrescrever o método 'final' '{mname}(...)' declarado em '{p_owner}' (JLS §8.4.3.3).", line)
                )

            # JLS §8.4.8.3: visibilidade não pode ser reduzida
            p_access = ps.get("access", "public")
            p_rank = self.host.ACCESS_RANK.get(p_access, 1)
            if child_rank < p_rank:
                self.host.errors.append(
                    self._err(
                        f"'{mname}(...)' não pode atribuir privilégios de acesso mais fracos ('{child_access}'); era '{p_access}' em '{p_owner}' (JLS §8.4.8.3).",
                        line,
                    )
                )

            # JLS §8.4.5: compatibilidade de retorno (idêntico ou covariante)
            ret_ok = self._is_return_compatible(sig.get("ret", "void"), ps.get("ret", "void"))
            if ret_ok is False:
                self.host.errors.append(
                    self._err(
                        f"Tipo de retorno '{sig.get('ret')}' em '{mname}(...)' é incompatível com '{ps.get('ret')}' de '{p_owner}' (JLS §8.4.5 / §8.4.8.3).",
                        line,
                    )
                )

    # -------------------------------------------------------------------------
    # Validação de Implementação de Abstratos e Conflitos Default em Interfaces
    # -------------------------------------------------------------------------
    def validate_type_inherited_methods(
        self,
        owner_key: str,
        owner_kind: str,
        owner_modifiers: List[str],
        members: List[Any],
        line: int,
        is_anonymous: bool = False,
        enum_const_impls: Optional[List[Tuple[str, Set[Tuple[str, int]]]]] = None,
    ) -> None:
        """
        Verifica:
        1. Conflitos de métodos 'default' / 'abstract' herdados de interfaces (JLS §8.4.8.4, §9.4.1.3);
        2. Implementação obrigatória de métodos abstratos em classes concretas, enums, records e anônimas (JLS §8.1.1.1);
        3. Visibilidade/retorno de método concreto herdado que implementa método de interface.
        """
        omods = set(owner_modifiers or [])
        is_concrete_class = (
            owner_kind == "record"
            or is_anonymous
            or (owner_kind == "class" and "abstract" not in omods)
        )
        owner_simple = self.host._simple_base_name(owner_key) or owner_key

        tvar_root = self.host._type_var_mapping_for_type(owner_key)
        own_instance_sigs: Dict[Tuple[str, Tuple[str, ...]], Dict[str, Any]] = {}
        for m in members:
            if hasattr(m, "parameters") and hasattr(m, "return_type"):
                mods = set(getattr(m, "modifiers", []) or [])
                if "static" in mods or "private" in mods:
                    continue
                msig = self.host._extract_method_sig(m, owner_simple, tvar_root)
                msig["name"] = getattr(m, "name", "")
                msig["owner_key"] = owner_key
                msig["owner_kind"] = owner_kind
                own_instance_sigs[self._method_sig_key(msig["name"], msig["params"])] = msig

        if is_anonymous:
            inherited, has_external = self._collect_hierarchy_methods(owner_key, include_owner=True)
        else:
            inherited, has_external = self._collect_hierarchy_methods(owner_key, include_owner=False)

        # Agrupa métodos herdados de instância por chave de assinatura erasa
        groups: Dict[Tuple[str, Tuple[str, ...]], List[Dict[str, Any]]] = {}
        for isig in inherited:
            if isig.get("static", False) or isig.get("access") == "private":
                continue
            sk = self._method_sig_key(isig["name"], isig["params"])
            groups.setdefault(sk, []).append(isig)

        # Se for concrete class sem herança de tipos declarados abstratos nem interfaces, evita trabalho desnecessário
        if owner_kind == "enum" and not own_instance_sigs:
            pass

        for sk, group in groups.items():
            mname, eparams = sk
            own_sig = own_instance_sigs.get(sk)

            class_sigs = [g for g in group if g.get("owner_kind") != "interface"]
            iface_sigs = [g for g in group if g.get("owner_kind") == "interface"]

            # Classe declarada mais específica (BFS visita subclasse antes da superclasse)
            best_class_sig = class_sigs[0] if class_sigs else None

            # Filtra métodos de interface dominados por subinterface mais específica
            maximal_iface_sigs: List[Dict[str, Any]] = []
            for isig in iface_sigs:
                i_owner = isig.get("owner_key") or isig.get("owner")
                dominated = False
                for other in iface_sigs:
                    o_owner = other.get("owner_key") or other.get("owner")
                    if o_owner != i_owner and self.host._is_subtype(o_owner, i_owner) is True:
                        dominated = True
                        break
                if not dominated:
                    maximal_iface_sigs.append(isig)

            # Deduplica pela chave de dono para evitar falsos conflitos pela mesma interface via múltiplos caminhos
            dedup_iface: List[Dict[str, Any]] = []
            seen_i_owners: Set[str] = set()
            for isig in maximal_iface_sigs:
                io = isig.get("owner_key") or isig.get("owner") or ""
                if io not in seen_i_owners:
                    seen_i_owners.add(io)
                    dedup_iface.append(isig)
            maximal_iface_sigs = dedup_iface

            # A. Conflito entre métodos herdados de interfaces sem declaração local nem método de classe concreto (JLS §8.4.8.4 / §9.4.1.3)
            class_wins_concrete = best_class_sig is not None and not best_class_sig.get("is_abstract", False)
            if own_sig is None and not class_wins_concrete and len(maximal_iface_sigs) > 1:
                defaults = [g for g in maximal_iface_sigs if g.get("is_default", False)]
                abstracts = [g for g in maximal_iface_sigs if g.get("is_abstract", False)]
                if len(defaults) >= 2:
                    owners_str = " e ".join(f"'{g.get('owner')}'" for g in defaults[:2])
                    self.host.errors.append(
                        self._err(
                            f"Tipo '{owner_simple}' herda métodos 'default' conflitantes para '{mname}({', '.join(eparams)})' das interfaces {owners_str} (JLS §8.4.8.4).",
                            line,
                        )
                    )
                    continue
                if len(defaults) >= 1 and len(abstracts) >= 1:
                    self.host.errors.append(
                        self._err(
                            f"Conflito em '{owner_simple}' entre método 'default' de '{defaults[0].get('owner')}' e método 'abstract' de '{abstracts[0].get('owner')}' para '{mname}({', '.join(eparams)})' (JLS §9.4.1.3).",
                            line,
                        )
                    )
                    continue

            # B. Se classe concreta herdada implementa interface, ela deve ser 'public' (JLS §8.4.8.3)
            if own_sig is None and class_wins_concrete and maximal_iface_sigs:
                c_acc = best_class_sig.get("access", "package")
                if self.host.ACCESS_RANK.get(c_acc, 1) < self.host.ACCESS_RANK["public"]:
                    self.host.errors.append(
                        self._err(
                            f"Método herdado '{best_class_sig.get('owner')}.{mname}(...)' possui acesso '{c_acc}' e não pode implementar método 'public' da interface '{maximal_iface_sigs[0].get('owner')}' em '{owner_simple}' (JLS §8.4.8.3).",
                            line,
                        )
                    )

            # C. Verifica se algum método abstrato ficou sem implementação concreta em tipo concreto
            if own_sig is not None:
                continue
            if class_wins_concrete:
                continue
            if any(g.get("is_default", False) for g in maximal_iface_sigs):
                # Default único vencedor de interface implementa o contrato
                continue

            unimplemented_source = None
            if best_class_sig is not None and best_class_sig.get("is_abstract", False):
                unimplemented_source = best_class_sig
            elif maximal_iface_sigs:
                abs_ifaces = [g for g in maximal_iface_sigs if g.get("is_abstract", False)]
                if abs_ifaces:
                    unimplemented_source = abs_ifaces[0]

            if unimplemented_source is None:
                continue

            src_owner = unimplemented_source.get("owner") or "supertipo"
            if owner_kind == "enum":
                # Em enum, constantes individuais devem implementar se o enum em si não implementou
                if enum_const_impls is None:
                    continue
                if len(enum_const_impls) == 0:
                    self.host.errors.append(
                        self._err(
                            f"Enum '{owner_simple}' não é abstrato e deve implementar o método abstrato '{mname}(...)' herdado de '{src_owner}' (JLS §8.9).",
                            line,
                        )
                    )
                    continue
                for cname, cimpls in enum_const_impls:
                    if (mname, len(eparams)) not in cimpls:
                        self.host.errors.append(
                            self._err(
                                f"Constante de enum '{cname}' em '{owner_simple}' deve implementar o método abstrato '{mname}(...)' herdado de '{src_owner}' (JLS §8.9).",
                                line,
                            )
                        )
                continue

            if is_concrete_class and not has_external:
                self.host.errors.append(
                    self._err(
                        f"'{owner_simple}' não é abstrato e não sobrescreve o método abstrato '{mname}({', '.join(eparams)})' em '{src_owner}' (JLS §8.1.1.1).",
                        line,
                    )
                )

    # -------------------------------------------------------------------------
    # Validação de Construtores (Modificadores e Ciclos this(...))
    # -------------------------------------------------------------------------
    def validate_constructor_modifiers(self, ctor_member: Any) -> None:
        """Valida que o construtor possui apenas modificadores de acesso permitidos (JLS §8.8.3)."""
        allowed = {"public", "protected", "private"}
        for mod in getattr(ctor_member, "modifiers", []) or []:
            if mod not in allowed:
                self.host.errors.append(
                    self._err(
                        f"Modificador '{mod}' não é permitido em declaração de construtor '{ctor_member.name}' (JLS §8.8.3).",
                        getattr(ctor_member, "line", 1),
                    )
                )

    def validate_constructor_cycles(self, owner_name: str, ctor_members: List[Any]) -> None:
        """Detecta ciclos recursivos em invocações 'this(...)' entre construtores da classe (JLS §8.8.7)."""
        from .ast_nodes import AlternateConstructorInvocation, ConstructorBody

        if len(ctor_members) == 0:
            return
        sigs = [self.host._extract_method_sig(cm, owner_name) for cm in ctor_members]
        edges: Dict[int, int] = {}

        for idx, cm in enumerate(ctor_members):
            body = getattr(cm, "body", None)
            inv = getattr(body, "constructor_invocation", None) if isinstance(body, ConstructorBody) else None
            if not isinstance(inv, AlternateConstructorInvocation):
                continue
            args = list(getattr(inv, "arguments", []) or [])
            # Mapeia primeiro por aridade/compatibilidade para outros construtores da mesma classe
            arg_types = [self.host.infer_type(a) for a in args]
            for j, target_sig in enumerate(sigs):
                tp = target_sig.get("params", [])
                if len(tp) == len(args):
                    ok = True
                    for pt, at in zip(tp, arg_types):
                        if at and not self.host.is_assignable(pt, at):
                            ok = False
                            break
                    if ok:
                        edges[idx] = j
                        break

        state: Dict[int, int] = {}  # 0=unvisited, 1=visiting, 2=done
        reported: Set[int] = set()
        for start in range(len(ctor_members)):
            cur = start
            path: List[int] = []
            while cur is not None and state.get(cur, 0) == 0:
                state[cur] = 1
                path.append(cur)
                nxt = edges.get(cur)
                if nxt is not None and state.get(nxt, 0) == 1:
                    if nxt not in reported:
                        reported.add(nxt)
                        self.host.errors.append(
                            self._err(
                                f"Invocação recursiva de construtor detectada via 'this(...)' em '{owner_name}' (JLS §8.8.7).",
                                getattr(ctor_members[nxt], "line", 1),
                            )
                        )
                    break
                cur = nxt
            for node_idx in path:
                state[node_idx] = 2

    def validate_interface_super_call(self, iface_name: str, method_name: str, line: int) -> Optional[Dict[str, Any]]:
        """Valida chamada 'Interface.super.metodo(...)' verificando herança direta e existência de default (JLS §15.12.1)."""
        cur_key = self.current_enclosing_key()
        iface_key = self.resolve_type_key(iface_name) or iface_name
        if cur_key:
            supers, _ = self.host._direct_supertypes(cur_key)
            super_keys = {self.resolve_type_key(s, context_type=cur_key) or (self.host._simple_base_name(s) or s) for s in supers}
            iface_simple = self.host._simple_base_name(iface_name) or iface_name
            if iface_key not in super_keys and iface_simple not in super_keys:
                self.host.errors.append(
                    self._err(
                        f"'{iface_name}' não é uma superinterface direta de '{self.host._simple_base_name(cur_key) or cur_key}' em '{iface_name}.super.{method_name}(...)' (JLS §15.12.1).",
                        line,
                    )
                )
        methods, is_known, _ = self.host._collect_type_methods(iface_key, method_name)
        if methods:
            inst_methods = [m for m in methods if not m.get("static", False)]
            if inst_methods and all(m.get("is_abstract", False) and not m.get("is_default", False) for m in inst_methods):
                self.host.errors.append(
                    self._err(
                        f"Método abstrato '{iface_name}.{method_name}(...)' não pode ser acessado diretamente via '{iface_name}.super' (JLS §15.12.1).",
                        line,
                    )
                )
        elif is_known:
            self.host.errors.append(
                self._err(f"Método '{method_name}' não encontrado na superinterface '{iface_name}'.", line)
            )
        return None
