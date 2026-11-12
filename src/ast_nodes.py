"""
Módulo de Definição dos Nós da Árvore Sintática Abstrata (AST) do Compilador Java (AV3).
Contém as representações estruturais para:
- Unidades de compilação, pacotes e imports (Fase B);
- Declarações de tipos: classes, interfaces, enums (Fase B);
- Membros: campos, métodos, construtores e parâmetros (Fase B);
- Estruturas de controle e comandos: blocos, if/else, while, do/while, for (tradicional e aprimorado),
  break, continue, return, throw, assert, try/catch/finally e synchronized (Fase C);
- Expressões e nós didáticos de etapas anteriores.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


def _format_children(title: str, children: list) -> str:
    """
    Função auxiliar para formatação em árvore hierárquica legível (pretty).
    Gera branches com ├── e └── e indenta nós filhos recursivamente.
    """
    valid_children = [c for c in children if c is not None]
    if not valid_children:
        return title
    lines = [title]
    for i, child in enumerate(valid_children):
        is_last = (i == len(valid_children) - 1)
        branch = "└── " if is_last else "├── "
        prefix = "    " if is_last else "│   "
        if hasattr(child, "pretty"):
            c_lines = child.pretty().splitlines()
        else:
            c_lines = [str(child)]
        if not c_lines:
            c_lines = ["<vazio>"]
        lines.append(branch + c_lines[0])
        lines.extend(prefix + line for line in c_lines[1:])
    return "\n".join(lines)


# =============================================================================
# SEÇÃO 1: NÓ BASE DA AST
# =============================================================================
class ASTNode:
    """Classe base para todos os nós da árvore sintática abstrata."""
    parenthesized: bool = False

    def pretty(self) -> str:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """Representação em dicionário para inspeção e testes estruturais."""
        res = {"node": self.__class__.__name__}
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            if isinstance(v, ASTNode):
                res[k] = v.to_dict()
            elif isinstance(v, list):
                res[k] = [item.to_dict() if isinstance(item, ASTNode) else item for item in v]
            else:
                res[k] = v
        return res


class BlockStatement(ASTNode):
    """Marcador normativo para elementos ordenados dentro de um Block (JLS §14.2)."""


class LocalClassOrInterfaceDeclaration(BlockStatement):
    """Marcador normativo para declarações locais de classes, interfaces, enums e records (JLS §14.3)."""


class Statement(BlockStatement):
    """Marcador normativo base para instruções executáveis Java (JLS §14.5)."""


# =============================================================================
# SEÇÃO 2: PROGRAMA E UNIDADE DE COMPILAÇÃO JAVA (COMPILATION UNIT)
# =============================================================================
@dataclass
class Program(ASTNode):
    """
    Representação de nível superior de comandos e programas didáticos.
    Mantido para compatibilidade total com os testes das etapas anteriores.
    """
    statements: list = field(default_factory=list)

    def pretty(self) -> str:
        if not self.statements:
            return "Program"
        return _format_children("Program", self.statements)


@dataclass
class CompilationUnit(Program):
    """
    Classe base para Unidades de Compilação Java (JLS §7.3).
    """
    package: Optional['PackageDeclaration'] = None
    imports: List['ImportDeclaration'] = field(default_factory=list)
    type_declarations: List[ASTNode] = field(default_factory=list)
    statements: list = field(default_factory=list)
    module_declaration: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    @property
    def package_decl(self) -> Optional['PackageDeclaration']:
        """Alias para self.package."""
        return self.package

    @property
    def is_modular(self) -> bool:
        return isinstance(self, ModularCompilationUnit) or self.module_declaration is not None

    @property
    def is_compact(self) -> bool:
        return isinstance(self, CompactCompilationUnit)

    @property
    def is_ordinary(self) -> bool:
        return not self.is_modular and not self.is_compact

    def pretty(self) -> str:
        # Se for arquivo completamente vazio, retorna "Program" para compatibilidade com test_23
        if not self.package and not self.imports and not self.type_declarations and not self.statements and not self.module_declaration:
            return "Program"

        # Se for um fragmento antigo (apenas comandos, sem pacote/imports/tipos/modulo)
        if not self.package and not self.imports and not self.type_declarations and not self.module_declaration:
            return _format_children("Program", self.statements)

        children = []
        if self.package:
            children.append(self.package)
        children.extend(self.imports)
        if self.module_declaration:
            children.append(self.module_declaration)
        children.extend(self.type_declarations)
        children.extend(self.statements)

        return _format_children("CompilationUnit", children)


# =============================================================================
# SEÇÃO 3: DECLARAÇÃO DE PACOTE E IMPORTAÇÕES
# =============================================================================
@dataclass
class PackageDeclaration(ASTNode):
    """Representa a cláusula de pacote: [annotations] package nome.do.pacote;"""
    name: str
    line: int = 1
    column: int = 1
    modifiers: List[ASTNode] = field(default_factory=list)

    @property
    def annotations(self) -> List[ASTNode]:
        """Alias para self.modifiers."""
        return self.modifiers

    def pretty(self) -> str:
        mods_str = (" ".join(m.pretty() for m in self.modifiers) + " ") if self.modifiers else ""
        header = f"PackageDeclaration: {mods_str}{self.name}".strip()
        if self.modifiers:
            return _format_children(header, [self.name])
        return _format_children("PackageDeclaration", [self.name])


@dataclass
class ImportDeclaration(ASTNode):
    """Representa uma importação Java: import [static | module] caminho.[*];"""
    name: str
    is_static: bool = False
    is_wildcard: bool = False
    is_module: bool = False
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        tag = ""
        if self.is_static and self.is_wildcard:
            tag = " (static on-demand)"
        elif self.is_static:
            tag = " (static)"
        elif self.is_module:
            tag = " (module)"
        elif self.is_wildcard:
            tag = " (on-demand)"
        return f"ImportDeclaration{tag}: {self.name}"


@dataclass
class SingleTypeImport(ImportDeclaration):
    """import TypeName;"""
    pass


@dataclass
class TypeImportOnDemand(ImportDeclaration):
    """import PackageOrTypeName.*;"""
    def __init__(self, name: str, line: int = 1, column: int = 1):
        super().__init__(name=name, is_static=False, is_wildcard=True, is_module=False, line=line, column=column)


@dataclass
class SingleStaticImport(ImportDeclaration):
    """import static TypeName.Identifier;"""
    def __init__(self, name: str, line: int = 1, column: int = 1):
        super().__init__(name=name, is_static=True, is_wildcard=False, is_module=False, line=line, column=column)


@dataclass
class StaticImportOnDemand(ImportDeclaration):
    """import static TypeName.*;"""
    def __init__(self, name: str, line: int = 1, column: int = 1):
        super().__init__(name=name, is_static=True, is_wildcard=True, is_module=False, line=line, column=column)


@dataclass
class SingleModuleImport(ImportDeclaration):
    """import module ModuleName;"""
    def __init__(self, name: str, line: int = 1, column: int = 1):
        super().__init__(name=name, is_static=False, is_wildcard=False, is_module=True, line=line, column=column)


# =============================================================================
# SEÇÃO 4: REFERÊNCIAS DE TIPO (PRIMITIVOS, CLASSES, ARRAYS, GENERICS)
# =============================================================================
@dataclass
class ElementValue(ASTNode):
    """
    Representa um valor de elemento de anotação (JLS §9.7.1):
    ElementValue ::= ConditionalExpression | ElementValueArrayInitializer | Annotation
    """
    value: ASTNode
    line: int = 1
    column: int = 1

    @property
    def is_annotation(self) -> bool:
        return isinstance(self.value, Annotation)

    @property
    def is_array_initializer(self) -> bool:
        return isinstance(self.value, ArrayInitializer)

    @property
    def is_expression(self) -> bool:
        return not self.is_annotation and not self.is_array_initializer

    def to_dict(self) -> Dict[str, Any]:
        val_dict = self.value.to_dict() if hasattr(self.value, "to_dict") else self.value.pretty()
        return {
            "node": "ElementValue",
            "value": val_dict,
            "is_annotation": self.is_annotation,
            "is_array_initializer": self.is_array_initializer,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return self.value.pretty() if hasattr(self.value, "pretty") else str(self.value)


@dataclass
class ElementValueList(ASTNode):
    """Lista de valores de elemento separada por vírgulas (JLS §9.7.1)."""
    values: List[ElementValue] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ElementValueList",
            "values": [v.to_dict() for v in self.values],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return ", ".join(v.pretty() for v in self.values)


@dataclass
class ElementValuePair(ASTNode):
    """Par nome = valor em uma anotação normal (JLS §9.7.1)."""
    name: str
    value: ElementValue
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ElementValuePair",
            "name": self.name,
            "value": self.value.to_dict(),
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return f"{self.name} = {self.value.pretty()}"


@dataclass
class ElementValuePairList(ASTNode):
    """Lista de pares nome-valor de uma NormalAnnotation (JLS §9.7.1)."""
    pairs: List[ElementValuePair] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ElementValuePairList",
            "pairs": [p.to_dict() for p in self.pairs],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return ", ".join(p.pretty() for p in self.pairs)


@dataclass
class Annotation(ASTNode):
    """Representa uma anotação Java (classe base): Marker, SingleElement ou Normal."""
    name: str
    arguments: Any = None
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        args_repr = None
        if isinstance(self.arguments, ASTNode):
            args_repr = self.arguments.to_dict() if hasattr(self.arguments, "to_dict") else self.arguments.pretty()
        elif isinstance(self.arguments, list):
            args_repr = [a.to_dict() if hasattr(a, "to_dict") else str(a) for a in self.arguments]
        elif self.arguments is not None:
            args_repr = str(self.arguments)
        return {
            "node": self.__class__.__name__,
            "name": self.name,
            "arguments": args_repr,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        if self.arguments is not None:
            return f"@{self.name}(...)"
        return f"@{self.name}"


@dataclass
class MarkerAnnotation(Annotation):
    """Anotação marcadora sem parênteses (JLS §9.7.2): @TypeName."""

    def __post_init__(self):
        self.arguments = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "MarkerAnnotation",
            "name": self.name,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return f"@{self.name}"


@dataclass
class SingleElementAnnotation(Annotation):
    """Anotação de elemento único abreviada (JLS §9.7.3): @TypeName(ElementValue)."""
    element_value: Optional[ElementValue] = None

    def __post_init__(self):
        if self.element_value is None and isinstance(self.arguments, ElementValue):
            self.element_value = self.arguments
        elif self.element_value is not None and self.arguments is None:
            self.arguments = self.element_value

    @property
    def value(self) -> Optional[ElementValue]:
        return self.element_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "SingleElementAnnotation",
            "name": self.name,
            "element_value": self.element_value.to_dict() if self.element_value else None,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        val_str = self.element_value.pretty() if self.element_value is not None else ""
        return f"@{self.name}({val_str})"


@dataclass
class NormalAnnotation(Annotation):
    """Anotação normal (JLS §9.7.1): @TypeName([ElementValuePairList])."""
    element_value_pair_list: Optional[ElementValuePairList] = None
    has_parentheses: bool = True

    def __post_init__(self):
        if self.element_value_pair_list is None:
            if isinstance(self.arguments, ElementValuePairList):
                self.element_value_pair_list = self.arguments
            elif isinstance(self.arguments, list):
                self.element_value_pair_list = ElementValuePairList(
                    pairs=self.arguments,
                    line=self.line,
                    column=self.column,
                )
            else:
                self.element_value_pair_list = ElementValuePairList(
                    pairs=[],
                    line=self.line,
                    column=self.column,
                )
        if self.arguments is None:
            self.arguments = self.element_value_pair_list

    @property
    def pairs(self) -> List[ElementValuePair]:
        return self.element_value_pair_list.pairs if self.element_value_pair_list else []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "NormalAnnotation",
            "name": self.name,
            "element_value_pair_list": self.element_value_pair_list.to_dict() if self.element_value_pair_list else None,
            "has_parentheses": self.has_parentheses,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        pairs_str = self.element_value_pair_list.pretty() if self.element_value_pair_list else ""
        return f"@{self.name}({pairs_str})"


@dataclass
class WildcardType(ASTNode):
    """Representa um tipo curinga (wildcard) em generics: ?, ? extends T, ? super T."""
    bound_kind: Optional[str] = None # 'extends', 'super' ou None
    bound_type: Optional[ASTNode] = None
    annotations: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        anno_str = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        if self.bound_kind and self.bound_type:
            b_str = self.bound_type.pretty() if hasattr(self.bound_type, "pretty") else str(self.bound_type)
            return f"{anno_str}? {self.bound_kind} {b_str}"
        return f"{anno_str}?"


@dataclass
class TypeParameter(ASTNode):
    """Representa a declaração de parâmetro genérico: T, T extends Number & Comparable<T>."""
    name: str
    bounds: List[ASTNode] = field(default_factory=list)
    annotations: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.name == other
        if isinstance(other, TypeParameter):
            return (
                self.name == other.name
                and self.bounds == other.bounds
                and self.annotations == other.annotations
            )
        return False

    def pretty(self) -> str:
        anno_str = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        if self.bounds:
            bounds_str = " & ".join(b.pretty() if hasattr(b, "pretty") else str(b) for b in self.bounds)
            return f"{anno_str}{self.name} extends {bounds_str}"
        return f"{anno_str}{self.name}"


@dataclass
class TypeReference(ASTNode):
    """
    Representa o nome de um tipo Java (primitivo ou de referência).
    Suporta arrays (ex: int[]), generics simples e aninhados (ex: List<T>, Map<K, List<V>>),
    wildcards (?, ? extends T), annotations de tipo e varargs (...).
    """
    name: str
    array_dimensions: int = 0
    type_arguments: List[ASTNode] = field(default_factory=list)
    is_varargs: bool = False
    line: int = 1
    column: int = 1
    annotations: List[ASTNode] = field(default_factory=list)
    type_parameters: List[TypeParameter] = field(default_factory=list)
    dims_annotations: List[List[ASTNode]] = field(default_factory=list)

    def get_effective_type(self, extra_dims: int = 0) -> str:
        """Retorna a representação do tipo com suas dimensões normais acrescidas de extra_dims (JLS §10.2)."""
        total_dims = self.array_dimensions + extra_dims
        base_str = self.name
        if self.type_parameters:
            params_str = ", ".join(p.pretty() for p in self.type_parameters)
            base_str += f"<{params_str}>"
        elif self.type_arguments:
            args_str = ", ".join(arg.pretty() if hasattr(arg, "pretty") else str(arg) for arg in self.type_arguments)
            base_str += f"<{args_str}>"
        if self.is_varargs:
            return f"{base_str}{'[]' * total_dims}..."
        return f"{base_str}{'[]' * total_dims}"

    def get_effective_type_ref(self, extra_dims: int = 0) -> "TypeReference":
        """Retorna uma nova instância de TypeReference com as dimensões combinadas."""
        return TypeReference(
            name=self.name,
            array_dimensions=self.array_dimensions + extra_dims,
            type_arguments=list(self.type_arguments),
            is_varargs=self.is_varargs,
            line=self.line,
            column=self.column,
            annotations=list(self.annotations),
            type_parameters=list(self.type_parameters),
            dims_annotations=list(self.dims_annotations),
        )

    segment_annotations: List[List[ASTNode]] = field(default_factory=list)
    ellipsis_annotations: List[ASTNode] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Nome completo do tipo incluindo suas dimensões de array."""
        return self.get_effective_type(0)

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "node": "TypeReference",
            "name": self.name,
            "array_dimensions": self.array_dimensions,
            "full_name": self.full_name,
            "is_varargs": self.is_varargs,
            "line": self.line,
            "column": self.column,
        }
        if self.annotations:
            res["annotations"] = [a.pretty() for a in self.annotations]
        if any(self.dims_annotations):
            res["dims_annotations"] = [
                [a.pretty() for a in dim_annos] for dim_annos in self.dims_annotations
            ]
        seg_annos = getattr(self, "segment_annotations", None)
        if seg_annos and any(seg_annos):
            res["segment_annotations"] = [
                [a.pretty() for a in sa] for sa in seg_annos
            ]
        return res

    def pretty(self) -> str:
        seg_annos = getattr(self, "segment_annotations", None)
        parts = self.name.split(".")
        if seg_annos and len(seg_annos) == len(parts) and any(seg_annos[1:]):
            formatted_parts = []
            for idx, (part, sa) in enumerate(zip(parts, seg_annos)):
                annos_for_seg = sa if sa else (self.annotations if idx == 0 else [])
                prefix = (" ".join(a.pretty() for a in annos_for_seg) + " ") if annos_for_seg else ""
                formatted_parts.append(f"{prefix}{part}")
            res = ".".join(formatted_parts)
        else:
            anno_str = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
            res = f"{anno_str}{self.name}"
        if self.type_parameters:
            params_str = ", ".join(p.pretty() for p in self.type_parameters)
            base_str = f"<{params_str}>"
            res += base_str
        elif self.type_arguments:
            args_str = ", ".join(arg.pretty() if hasattr(arg, "pretty") else str(arg) for arg in self.type_arguments)
            res += f"<{args_str}>"
        if self.array_dimensions > 0:
            if len(self.dims_annotations) == self.array_dimensions and any(self.dims_annotations):
                dim_parts = []
                for dim_annos in self.dims_annotations:
                    if dim_annos:
                        dim_parts.append(" ".join(a.pretty() for a in dim_annos) + " []")
                    else:
                        dim_parts.append("[]")
                res += " " + " ".join(dim_parts)
            else:
                res += "[]" * self.array_dimensions
        if self.is_varargs:
            el_annos = getattr(self, "ellipsis_annotations", None)
            if el_annos:
                res += " " + " ".join(a.pretty() for a in el_annos) + " ..."
            else:
                res += "..."
        return res


# =============================================================================
# SEÇÃO 5: DECLARAÇÃO DE CLASSES, INTERFACES E ENUMS
# =============================================================================
@dataclass
class ClassDeclaration(LocalClassOrInterfaceDeclaration):
    """
    Representa a declaração de uma classe Java:
    [modificadores] class Nome [<T>] [extends Base] [implements I1, I2] [permits P1, P2] { membros }
    """
    name: str
    modifiers: List[str] = field(default_factory=list)
    extends_type: Optional[TypeReference] = None
    implements_types: List[TypeReference] = field(default_factory=list)
    members: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1
    type_parameters: List[TypeParameter] = field(default_factory=list)
    permits_types: List[TypeReference] = field(default_factory=list)
    annotations: List[ASTNode] = field(default_factory=list)
    is_local: bool = False

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        tparams = f"<{', '.join(p.pretty() for p in self.type_parameters)}>" if self.type_parameters else ""
        ext = f" extends {self.extends_type.pretty()}" if self.extends_type else ""
        impl = f" implements {', '.join(t.pretty() for t in self.implements_types)}" if self.implements_types else ""
        perm = f" permits {', '.join(t.pretty() for t in self.permits_types)}" if self.permits_types else ""
        header = f"ClassDeclaration: {mods}{self.name}{tparams}{ext}{impl}{perm}".strip()
        if not self.members:
            return header
        return _format_children(header, self.members)


@dataclass
class InterfaceExtends(ASTNode):
    """Cláusula extends de uma interface (JLS §9.1.3): extends InterfaceType {, InterfaceType}."""
    types: List[TypeReference] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "InterfaceExtends",
            "types": [t.pretty() for t in self.types],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return f"InterfaceExtends: extends {', '.join(t.pretty() for t in self.types)}"


@dataclass
class InterfacePermits(ASTNode):
    """Cláusula permits de uma interface sealed (JLS §9.1.4): permits TypeName {, TypeName}."""
    types: List[TypeReference] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "InterfacePermits",
            "types": [t.pretty() for t in self.types],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return f"InterfacePermits: permits {', '.join(t.pretty() for t in self.types)}"


@dataclass
class InterfaceBody(ASTNode):
    """Corpo de uma declaração de interface (JLS §9.1.5): { {InterfaceMemberDeclaration} }."""
    members: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "InterfaceBody",
            "members": [m.to_dict() if hasattr(m, "to_dict") else m.pretty() for m in self.members],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        if not self.members:
            return "InterfaceBody"
        return _format_children("InterfaceBody", self.members)


class InterfaceMemberDeclaration(ASTNode):
    """Classe base para declarações de membros de interface (JLS §9.1.5)."""
    pass


class AnnotationInterfaceMemberDeclaration(ASTNode):
    """Classe base para declarações de membros de annotation interface (JLS §9.6.1)."""
    pass


@dataclass
class InterfaceDeclaration(LocalClassOrInterfaceDeclaration):
    """
    Representa a declaração de uma interface normal Java (JLS §9.1):
    [modificadores] interface Nome [<T>] [extends I1, I2] [permits P1, P2] { membros }
    """
    name: str
    modifiers: List[str] = field(default_factory=list)
    type_parameters: List[Any] = field(default_factory=list)
    extends_types: List[TypeReference] = field(default_factory=list)
    members: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1
    permits_types: List[TypeReference] = field(default_factory=list)
    annotations: List[ASTNode] = field(default_factory=list)
    body: Optional[InterfaceBody] = None
    is_local: bool = False

    def __post_init__(self):
        if self.body is None:
            self.body = InterfaceBody(members=self.members, line=self.line, column=self.column)
        elif not self.members and self.body.members:
            self.members = self.body.members

    @property
    def extends_clause(self) -> Optional[InterfaceExtends]:
        if self.extends_types:
            return InterfaceExtends(types=list(self.extends_types), line=self.line, column=self.column)
        return None

    @property
    def permits_clause(self) -> Optional[InterfacePermits]:
        if self.permits_types:
            return InterfacePermits(types=list(self.permits_types), line=self.line, column=self.column)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "InterfaceDeclaration",
            "name": self.name,
            "modifiers": list(self.modifiers),
            "annotations": [a.pretty() for a in self.annotations],
            "type_parameters": [p.pretty() if hasattr(p, "pretty") else str(p) for p in self.type_parameters],
            "extends_types": [t.pretty() for t in self.extends_types],
            "permits_types": [t.pretty() for t in self.permits_types],
            "body": self.body.to_dict() if self.body else None,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        tparams = ""
        if self.type_parameters:
            tparams = f"<{', '.join(p.pretty() if hasattr(p, 'pretty') else str(p) for p in self.type_parameters)}>"
        ext = f" extends {', '.join(t.pretty() for t in self.extends_types)}" if self.extends_types else ""
        perm = f" permits {', '.join(t.pretty() for t in self.permits_types)}" if self.permits_types else ""
        header = f"InterfaceDeclaration: {annos}{mods}{self.name}{tparams}{ext}{perm}".strip()
        if not self.members:
            return header
        return _format_children(header, self.members)


@dataclass
class EnumConstantBody(ASTNode):
    """Corpo específico (classe anônima) de uma constante de enum (JLS §8.9.1)."""
    members: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "EnumConstantBody",
            "members": [m.to_dict() if hasattr(m, "to_dict") else m.pretty() for m in self.members],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        if not self.members:
            return "EnumConstantBody"
        return _format_children("EnumConstantBody", self.members)


@dataclass
class EnumConstant(ASTNode):
    """
    Representa uma constante dentro de um enum (JLS §8.9.1):
    {EnumConstantModifier} Identifier [ ( [ArgumentList] ) ] [ClassBody]
    """
    name: str
    arguments: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1
    annotations: List[ASTNode] = field(default_factory=list)
    body: Optional[EnumConstantBody] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "EnumConstant",
            "name": self.name,
            "annotations": [a.pretty() for a in self.annotations],
            "arguments": [a.pretty() if hasattr(a, "pretty") else str(a) for a in self.arguments],
            "body": self.body.to_dict() if self.body else None,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        args = f"({', '.join(a.pretty() if hasattr(a, 'pretty') else str(a) for a in self.arguments)})" if self.arguments else ""
        header = f"EnumConstant: {annos}{self.name}{args}".strip()
        if self.body is not None:
            return _format_children(header, [self.body])
        return header


@dataclass
class EnumConstantList(ASTNode):
    """Lista de constantes de um enum (JLS §8.9.1): EnumConstant { , EnumConstant }."""
    constants: List[EnumConstant] = field(default_factory=list)
    has_trailing_comma: bool = False
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "EnumConstantList",
            "constants": [c.to_dict() for c in self.constants],
            "has_trailing_comma": self.has_trailing_comma,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        if not self.constants:
            return "EnumConstantList (vazia)"
        return _format_children("EnumConstantList", self.constants)


@dataclass
class EnumBodyDeclarations(ASTNode):
    """Declarações de membros após ';' em um enum (JLS §8.9.2): ; {ClassBodyDeclaration}."""
    members: List[ASTNode] = field(default_factory=list)
    has_semicolon: bool = True
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "EnumBodyDeclarations",
            "members": [m.to_dict() if hasattr(m, "to_dict") else m.pretty() for m in self.members],
            "has_semicolon": self.has_semicolon,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        if not self.members:
            return "EnumBodyDeclarations"
        return _format_children("EnumBodyDeclarations", self.members)


@dataclass
class EnumBody(ASTNode):
    """Corpo de um enum (JLS §8.9): { [EnumConstantList] [,] [EnumBodyDeclarations] }."""
    constant_list: Optional[EnumConstantList] = None
    body_declarations: Optional[EnumBodyDeclarations] = None
    line: int = 1
    column: int = 1

    @property
    def constants(self) -> List[EnumConstant]:
        return self.constant_list.constants if self.constant_list else []

    @property
    def members(self) -> List[ASTNode]:
        return self.body_declarations.members if self.body_declarations else []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "EnumBody",
            "constant_list": self.constant_list.to_dict() if self.constant_list else None,
            "body_declarations": self.body_declarations.to_dict() if self.body_declarations else None,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        children = []
        if self.constant_list and self.constant_list.constants:
            children.extend(self.constant_list.constants)
        if self.body_declarations and self.body_declarations.members:
            children.extend(self.body_declarations.members)
        if not children:
            return "EnumBody"
        return _format_children("EnumBody", children)


@dataclass
class EnumDeclaration(LocalClassOrInterfaceDeclaration):
    """
    Representa a declaração de um enum Java (JLS §8.9):
    [modificadores] enum Nome [implements I1] { CONSTANTES... [; membros] }
    """
    name: str
    modifiers: List[str] = field(default_factory=list)
    implements_types: List[TypeReference] = field(default_factory=list)
    constants: List[EnumConstant] = field(default_factory=list)
    members: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1
    annotations: List[ASTNode] = field(default_factory=list)
    body: Optional[EnumBody] = None
    has_trailing_comma: bool = False
    has_semicolon: bool = False
    is_local: bool = False

    def __post_init__(self):
        if self.body is None:
            clist = EnumConstantList(constants=self.constants, has_trailing_comma=self.has_trailing_comma, line=self.line, column=self.column)
            bdecl = EnumBodyDeclarations(members=self.members, has_semicolon=self.has_semicolon, line=self.line, column=self.column) if (self.has_semicolon or self.members) else None
            self.body = EnumBody(constant_list=clist, body_declarations=bdecl, line=self.line, column=self.column)
        else:
            if not self.constants and self.body.constant_list:
                self.constants = self.body.constant_list.constants
            if not self.members and self.body.body_declarations:
                self.members = self.body.body_declarations.members

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "EnumDeclaration",
            "name": self.name,
            "modifiers": list(self.modifiers),
            "annotations": [a.pretty() for a in self.annotations],
            "implements_types": [t.pretty() for t in self.implements_types],
            "body": self.body.to_dict() if self.body else None,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        impl = f" implements {', '.join(t.pretty() for t in self.implements_types)}" if self.implements_types else ""
        header = f"EnumDeclaration: {annos}{mods}{self.name}{impl}".strip()
        all_children = list(self.constants) + list(self.members)
        if not all_children:
            return header
        return _format_children(header, all_children)


# =============================================================================
# SEÇÃO 5.1: SUBCLASSES DE UNIDADE DE COMPILAÇÃO (JAVA SE 26 / JLS §7.3)
# =============================================================================
@dataclass
class OrdinaryCompilationUnit(CompilationUnit):
    """
    Representa uma unidade de compilação ordinária (JLS §7.3):
    [PackageDeclaration] {ImportDeclaration} {TopLevelClassOrInterfaceDeclaration}
    """
    def pretty(self) -> str:
        if not self.package and not self.imports and not self.type_declarations and not self.statements:
            return "Program"
        if not self.package and not self.imports and not self.type_declarations:
            return _format_children("Program", self.statements)
        children = []
        if self.package:
            children.append(self.package)
        children.extend(self.imports)
        children.extend(self.type_declarations)
        children.extend(self.statements)
        return _format_children("OrdinaryCompilationUnit", children)


@dataclass
class ModularCompilationUnit(CompilationUnit):
    """
    Representa uma unidade de compilação modular (JLS §7.3 / §7.7):
    {ImportDeclaration} ModuleDeclaration
    """
    def __init__(self, imports: List[ImportDeclaration] = None, module_declaration: 'ModuleDeclaration' = None, line: int = 1, column: int = 1):
        super().__init__(
            package=None,
            imports=imports or [],
            type_declarations=[module_declaration] if module_declaration else [],
            statements=[],
            module_declaration=module_declaration,
            line=line,
            column=column
        )

    def pretty(self) -> str:
        children = []
        children.extend(self.imports)
        if self.module_declaration:
            children.append(self.module_declaration)
        return _format_children("ModularCompilationUnit", children)


@dataclass
class CompactCompilationUnit(CompilationUnit):
    """
    Representa uma unidade de compilação compacta com classe declarada implicitamente (JLS §7.3):
    {ImportDeclaration} {ClassBodyDeclaration}
    """
    class_members: List[ASTNode] = field(default_factory=list)
    implicit_class: Optional[ClassDeclaration] = None

    def __init__(self, imports: List[ImportDeclaration] = None, class_members: List[ASTNode] = None, line: int = 1, column: int = 1):
        members = class_members or []
        imp_class = ClassDeclaration(
            name="Unnamed",
            modifiers=[],
            members=members,
            line=line,
            column=column
        )
        super().__init__(
            package=None,
            imports=imports or [],
            type_declarations=[imp_class],
            statements=[],
            line=line,
            column=column
        )
        self.class_members = members
        self.implicit_class = imp_class

    def pretty(self) -> str:
        children = []
        children.extend(self.imports)
        children.extend(self.class_members)
        return _format_children("CompactCompilationUnit", children)


# =============================================================================
# SEÇÃO 5.2: DIRETIVAS E DECLARAÇÃO DE MÓDULOS (JAVA SE 26 / JLS §7.7)
# =============================================================================
@dataclass
class ModuleDirective(ASTNode):
    """Classe base para diretivas de um módulo Java (JLS §7.7)."""
    pass


@dataclass
class RequiresDirective(ModuleDirective):
    """
    Directiva: requires {RequiresModifier} ModuleName ;
    Modifiers: 'transitive', 'static'
    """
    module_name: str
    is_transitive: bool = False
    is_static: bool = False
    line: int = 1
    column: int = 1

    @property
    def modifiers(self) -> List[str]:
        mods = []
        if self.is_transitive:
            mods.append("transitive")
        if self.is_static:
            mods.append("static")
        return mods

    def pretty(self) -> str:
        flags = []
        if self.is_transitive:
            flags.append("transitive")
        if self.is_static:
            flags.append("static")
        mods_str = (" " + " ".join(flags)) if flags else ""
        return f"RequiresDirective{mods_str}: {self.module_name}"


@dataclass
class ExportsDirective(ModuleDirective):
    """Directiva: exports PackageName [to ModuleName {, ModuleName}] ;"""
    package_name: str
    to_modules: List[str] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        to_str = f" to {', '.join(self.to_modules)}" if self.to_modules else ""
        return f"ExportsDirective: {self.package_name}{to_str}"


@dataclass
class OpensDirective(ModuleDirective):
    """Directiva: opens PackageName [to ModuleName {, ModuleName}] ;"""
    package_name: str
    to_modules: List[str] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        to_str = f" to {', '.join(self.to_modules)}" if self.to_modules else ""
        return f"OpensDirective: {self.package_name}{to_str}"


@dataclass
class UsesDirective(ModuleDirective):
    """Directiva: uses TypeName ;"""
    service_type: TypeReference
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return f"UsesDirective: {self.service_type.pretty()}"


@dataclass
class ProvidesDirective(ModuleDirective):
    """Directiva: provides TypeName with TypeName {, TypeName} ;"""
    service_type: TypeReference
    with_types: List[TypeReference] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        impls = ", ".join(t.pretty() for t in self.with_types)
        return f"ProvidesDirective: {self.service_type.pretty()} with {impls}"


@dataclass
class ModuleDeclaration(ASTNode):
    """
    Representa a declaração de módulo (Java 9+ / JLS §7.7):
    {Annotation} [open] module Identifier {. Identifier} { {ModuleDirective} }
    """
    name: str
    is_open: bool = False
    directives: List[ModuleDirective] = field(default_factory=list)
    annotations: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        open_str = "open " if self.is_open else ""
        header = f"ModuleDeclaration: {annos}{open_str}{self.name}".strip()
        if not self.directives:
            return header
        return _format_children(header, self.directives)


# =============================================================================
# SEÇÃO 6: PARÂMETROS, CAMPOS, MÉTODOS, CONSTRUTORES E INICIALIZADORES (ETAPA S3)
# =============================================================================
@dataclass
class VariableDeclaratorId(ASTNode):
    """
    Identificador de variável com dimensões de array opcionais (JLS §8.3):
    (Identifier | _) [Dims]
    """
    name: str
    dims: int = 0
    line: int = 1
    column: int = 1
    dims_annotations: List[List[ASTNode]] = field(default_factory=list)

    @property
    def is_unnamed(self) -> bool:
        return self.name == "_"

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "node": "VariableDeclaratorId",
            "name": self.name,
            "dims": self.dims,
            "is_unnamed": self.is_unnamed,
            "line": self.line,
            "column": self.column,
        }
        if any(self.dims_annotations):
            d["dims_annotations"] = [
                [a.pretty() for a in da] for da in self.dims_annotations
            ]
        return d

    def pretty(self) -> str:
        if len(self.dims_annotations) == self.dims and any(self.dims_annotations):
            dim_parts = []
            for da in self.dims_annotations:
                if da:
                    dim_parts.append(" ".join(a.pretty() for a in da) + " []")
                else:
                    dim_parts.append("[]")
            return f"{self.name} " + " ".join(dim_parts)
        dims_str = "[]" * self.dims
        return f"{self.name}{dims_str}"


@dataclass
class VariableDeclarator(ASTNode):
    """
    Declarador individual de variável (JLS §8.3):
    VariableDeclaratorId [= VariableInitializer]
    """
    id: VariableDeclaratorId
    initializer: Optional[ASTNode] = None
    line: int = 1
    column: int = 1
    base_type: Optional[TypeReference] = None

    @property
    def name(self) -> str:
        return self.id.name

    @property
    def dims(self) -> int:
        return self.id.dims

    @property
    def effective_type(self) -> str:
        """Tipo efetivo do campo combinando o tipo base da declaração e as dimensões do declarador (JLS §8.3 e §10.2)."""
        if self.base_type is not None:
            return self.base_type.get_effective_type(self.dims)
        return f"{'[]' * self.dims}"

    @property
    def effective_type_ref(self) -> Optional[TypeReference]:
        if self.base_type is not None:
            return self.base_type.get_effective_type_ref(self.dims)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "VariableDeclarator",
            "name": self.name,
            "dims": self.dims,
            "effective_type": self.effective_type,
            "initializer": self.initializer.to_dict() if self.initializer and hasattr(self.initializer, "to_dict") else (self.initializer.pretty() if self.initializer else None),
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        s = self.id.pretty()
        if self.initializer is not None:
            init_str = self.initializer.pretty() if hasattr(self.initializer, "pretty") else str(self.initializer)
            s += f" = {init_str}"
        return s


@dataclass
class ReceiverParameter(ASTNode):
    """
    Parâmetro receptor explícito (JLS §8.4.1):
    {Annotation} UnannType [Identifier .] this
    """
    type_ref: TypeReference
    name: str = "this"
    qualifier: Optional[str] = None
    annotations: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        qual = f"{self.qualifier}." if self.qualifier else ""
        return f"ReceiverParameter: {annos}{self.type_ref.pretty()} {qual}this"


@dataclass
class Parameter(ASTNode):
    """Representa um parâmetro formal em método ou construtor: Tipo nome."""
    type_ref: TypeReference
    name: str
    is_varargs: bool = False
    line: int = 1
    column: int = 1
    modifiers: List[str] = field(default_factory=list)
    annotations: List[ASTNode] = field(default_factory=list)
    dims: int = 0

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        var = "..." if self.is_varargs else ""
        dims_str = "[]" * self.dims
        return f"Parametro {annos}{mods}({self.type_ref.pretty()}{var}) {self.name}{dims_str}".strip()


@dataclass
class FormalParameter(Parameter):
    """Parâmetro formal tradicional (JLS §8.4.1)."""
    pass


@dataclass
class VariableArityParameter(Parameter):
    """Parâmetro de aridade variável / varargs (JLS §8.4.1): {VariableModifier} UnannType {Annotation} ... VariableDeclaratorId."""
    def __init__(
        self,
        type_ref: TypeReference,
        name: str,
        line: int = 1,
        column: int = 1,
        modifiers: List[str] = None,
        annotations: List[ASTNode] = None,
        ellipsis_annotations: List[ASTNode] = None,
    ):
        super().__init__(
            type_ref=type_ref,
            name=name,
            is_varargs=True,
            line=line,
            column=column,
            modifiers=modifiers or [],
            annotations=annotations or [],
        )
        self.ellipsis_annotations: List[ASTNode] = list(ellipsis_annotations or [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "VariableArityParameter",
            "name": self.name,
            "type": self.type_ref.pretty() if self.type_ref else None,
            "modifiers": list(self.modifiers),
            "annotations": [a.pretty() for a in self.annotations],
            "ellipsis_annotations": [a.pretty() for a in self.ellipsis_annotations],
            "is_varargs": True,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        e_annos = (" ".join(a.pretty() for a in self.ellipsis_annotations) + " ") if self.ellipsis_annotations else ""
        t_str = self.type_ref.pretty() if self.type_ref else ""
        if t_str.endswith("..."):
            t_str = t_str[:-3]
        return f"{annos}{mods}{t_str} {e_annos}... {self.name}".strip()


@dataclass
class Block(Statement):
    """Representa um bloco de comandos delimitado por chaves: { ... }."""
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    @property
    def block_statements(self) -> List[ASTNode]:
        """Alias ordenado dos elementos do bloco (JLS §14.2)."""
        return self.statements

    def pretty(self) -> str:
        if not self.statements:
            return "Block"
        return _format_children("Block", self.statements)


@dataclass
class InstanceInitializer(ASTNode):
    """Inicializador de instância (JLS §8.6): { ... }."""
    block: Block
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("InstanceInitializer", [self.block])


@dataclass
class StaticInitializer(ASTNode):
    """Inicializador estático (JLS §8.7): static { ... }."""
    block: Block
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("StaticInitializer", [self.block])


@dataclass
class FieldDeclaration(ASTNode):
    """
    Representa a declaração de um campo (atributo) em uma classe/interface (JLS §8.3):
    {FieldModifier} UnannType VariableDeclaratorList ;
    """
    type_ref: TypeReference
    declarators: List[VariableDeclarator] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    line: int = 1
    column: int = 1
    annotations: List[ASTNode] = field(default_factory=list)

    def __init__(
        self,
        type_ref: TypeReference,
        name_or_declarators: Any = None,
        modifiers: List[str] = None,
        initializer: Optional[ASTNode] = None,
        line: int = 1,
        column: int = 1,
        annotations: List[ASTNode] = None,
        declarators: List[VariableDeclarator] = None,
        name: Optional[str] = None,
    ):
        super().__init__()
        self.type_ref = type_ref
        self.modifiers = modifiers or []
        self.line = line
        self.column = column
        self.annotations = annotations or []

        if name is not None:
            name_or_declarators = name

        if declarators is not None:
            self.declarators = declarators
        elif isinstance(name_or_declarators, list):
            self.declarators = name_or_declarators
        elif isinstance(name_or_declarators, str):
            decl_id = VariableDeclaratorId(name=name_or_declarators, dims=0, line=line, column=column)
            self.declarators = [VariableDeclarator(id=decl_id, initializer=initializer, line=line, column=column)]
        else:
            self.declarators = []

        # Vincula o tipo base da declaração aos declaradores individuais (JLS §8.3 e §10.2)
        for d in self.declarators:
            if hasattr(d, "base_type"):
                d.base_type = self.type_ref

    @property
    def name(self) -> str:
        return self.declarators[0].name if self.declarators else ""

    @property
    def initializer(self) -> Optional[ASTNode]:
        return self.declarators[0].initializer if self.declarators else None

    def get_effective_type(self, declarator_or_name_or_index: Any) -> str:
        """Consulta o tipo efetivo de um declarador específico por objeto, nome ou índice."""
        if isinstance(declarator_or_name_or_index, int):
            if 0 <= declarator_or_name_or_index < len(self.declarators):
                return self.declarators[declarator_or_name_or_index].effective_type
        elif isinstance(declarator_or_name_or_index, str):
            for d in self.declarators:
                if d.name == declarator_or_name_or_index:
                    return d.effective_type
        elif isinstance(declarator_or_name_or_index, VariableDeclarator):
            return declarator_or_name_or_index.effective_type
        return self.type_ref.full_name

    @property
    def effective_types(self) -> List[str]:
        """Lista com os tipos efetivos de todos os declaradores da declaração."""
        return [d.effective_type for d in self.declarators]

    @property
    def effective_type(self) -> str:
        """Tipo efetivo do primeiro declarador (mantido para retrocompatibilidade)."""
        if self.declarators:
            return self.declarators[0].effective_type
        return self.type_ref.full_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "FieldDeclaration",
            "type": self.type_ref.pretty(),
            "modifiers": list(self.modifiers),
            "declarators": [d.to_dict() for d in self.declarators],
            "effective_types": self.effective_types,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        decls_str = ", ".join(d.pretty() for d in self.declarators)
        header = f"FieldDeclaration: {annos}{mods}{self.type_ref.pretty()} {decls_str}".strip()
        inits = [d.initializer for d in self.declarators if d.initializer is not None]
        if inits:
            return _format_children(header, inits)
        return header


@dataclass
class MethodDeclaration(ASTNode):
    """
    Representa a declaração de um método (JLS §8.4):
    {MethodModifier} [TypeParameters] Result MethodDeclarator [Throws] MethodBody
    """
    name: str
    return_type: TypeReference
    parameters: List[Parameter] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    throws_types: List[TypeReference] = field(default_factory=list)
    body: Optional[Block] = None
    line: int = 1
    column: int = 1
    type_parameters: List[TypeParameter] = field(default_factory=list)
    annotations: List[ASTNode] = field(default_factory=list)
    receiver_parameter: Optional[ReceiverParameter] = None
    dims: int = 0
    dims_annotations: List[List[ASTNode]] = field(default_factory=list)

    @property
    def effective_return_type(self) -> str:
        """Tipo efetivo de retorno combinando Result e dimensões posteriores ao declarador (JLS §8.4.5 e §10.2)."""
        if self.return_type is None:
            return ""
        return self.return_type.get_effective_type(self.dims)

    @property
    def effective_return_type_ref(self) -> TypeReference:
        if self.return_type is None:
            return TypeReference(name="void", line=self.line, column=self.column)
        return self.return_type.get_effective_type_ref(self.dims)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "node": "MethodDeclaration",
            "name": self.name,
            "return_type": self.return_type.pretty() if self.return_type else None,
            "dims": self.dims,
            "effective_return_type": self.effective_return_type,
            "modifiers": list(self.modifiers),
            "parameters": [p.to_dict() if hasattr(p, "to_dict") else str(p) for p in self.parameters],
            "throws_types": [t.pretty() for t in self.throws_types],
            "line": self.line,
            "column": self.column,
        }
        if any(self.dims_annotations):
            d["dims_annotations"] = [
                [a.pretty() for a in da] for da in self.dims_annotations
            ]
        return d

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        tparams = f"<{', '.join(p.pretty() for p in self.type_parameters)}> " if self.type_parameters else ""
        all_params_repr = []
        if self.receiver_parameter:
            all_params_repr.append(self.receiver_parameter.pretty())
        all_params_repr.extend(p.pretty() for p in self.parameters)
        params_str = ", ".join(all_params_repr)
        thr_str = f" throws {', '.join(t.pretty() for t in self.throws_types)}" if self.throws_types else ""
        if len(self.dims_annotations) == self.dims and any(self.dims_annotations):
            dims_str = " " + " ".join(
                (" ".join(a.pretty() for a in da) + " []") if da else "[]"
                for da in self.dims_annotations
            )
        else:
            dims_str = "[]" * self.dims
        header = f"MethodDeclaration: {annos}{mods}{tparams}{self.return_type.pretty()} {self.name}({params_str}){dims_str}{thr_str}".strip()
        if self.body is not None:
            return _format_children(header, [self.body])
        return header + " (abstrato / sem corpo)"


@dataclass
class ExplicitConstructorInvocation(ASTNode):
    """
    Invocação explícita de construtor (JLS §8.8.7.1):
    [TypeArguments] this ( [ArgumentList] ) ;
    [TypeArguments] super ( [ArgumentList] ) ;
    Expression . [TypeArguments] super ( [ArgumentList] ) ;
    """
    kind: str  # "this" ou "super"
    arguments: List[ASTNode] = field(default_factory=list)
    type_arguments: List[TypeReference] = field(default_factory=list)
    qualifier: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        targs = f"<{', '.join(t.pretty() for t in self.type_arguments)}>" if self.type_arguments else ""
        qual = f"{self.qualifier.pretty()}." if self.qualifier else ""
        header = f"ExplicitConstructorInvocation: {qual}{targs}{self.kind}"
        if self.arguments:
            return _format_children(header, self.arguments)
        return header + "()"


@dataclass
class AlternateConstructorInvocation(ExplicitConstructorInvocation):
    """Invocação explícita de construtor alternativo: this(...) (JLS §8.8.7.1)."""
    def __init__(self, arguments: List[ASTNode] = None, type_arguments: List[TypeReference] = None, line: int = 1, column: int = 1):
        super().__init__(kind="this", arguments=arguments or [], type_arguments=type_arguments or [], qualifier=None, line=line, column=column)


@dataclass
class SuperclassConstructorInvocation(ExplicitConstructorInvocation):
    """Invocação explícita de construtor da superclasse: [qualifier.]super(...) (JLS §8.8.7.1)."""
    def __init__(self, arguments: List[ASTNode] = None, type_arguments: List[TypeReference] = None, qualifier: Optional[ASTNode] = None, line: int = 1, column: int = 1):
        super().__init__(kind="super", arguments=arguments or [], type_arguments=type_arguments or [], qualifier=qualifier, line=line, column=column)


@dataclass
class ConstructorBody(ASTNode):
    """
    Corpo de construtor com suporte a Flexible Constructor Bodies (JEP 513 / JLS §8.8.7):
    { [BlockStatements] ConstructorInvocation [BlockStatements] }
    { [BlockStatements] }
    """
    prologue: List[ASTNode] = field(default_factory=list)
    constructor_invocation: Optional[ExplicitConstructorInvocation] = None
    epilogue: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    @property
    def statements(self) -> List[ASTNode]:
        res = list(self.prologue)
        if self.constructor_invocation is not None:
            res.append(self.constructor_invocation)
        res.extend(self.epilogue)
        return res

    def pretty(self) -> str:
        children = []
        if self.prologue:
            children.append(_format_children("Prologue", self.prologue))
        if self.constructor_invocation:
            children.append(self.constructor_invocation)
        if self.epilogue:
            children.append(_format_children("Epilogue", self.epilogue))
        if not children:
            return "ConstructorBody"
        return _format_children("ConstructorBody", children)


@dataclass
class ConstructorDeclaration(ASTNode):
    """
    Declaração de construtor (JLS §8.8):
    {ConstructorModifier} [TypeParameters] SimpleTypeName ( [FormalParameterList] ) [Throws] ConstructorBody
    """
    name: str
    parameters: List[Parameter] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    throws_types: List[TypeReference] = field(default_factory=list)
    body: Optional[ASTNode] = None
    line: int = 1
    column: int = 1
    receiver_parameter: Optional[ReceiverParameter] = None
    type_parameters: List[TypeParameter] = field(default_factory=list)
    annotations: List[ASTNode] = field(default_factory=list)

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        tparams = f"<{', '.join(p.pretty() for p in self.type_parameters)}> " if self.type_parameters else ""
        all_params_repr = []
        if self.receiver_parameter:
            all_params_repr.append(self.receiver_parameter.pretty())
        all_params_repr.extend(p.pretty() for p in self.parameters)
        params_str = ", ".join(all_params_repr)
        thr_str = f" throws {', '.join(t.pretty() for t in self.throws_types)}" if self.throws_types else ""
        header = f"ConstructorDeclaration: {annos}{mods}{tparams}{self.name}({params_str}){thr_str}".strip()
        if self.body is not None:
            return _format_children(header, [self.body])
        return header


# =============================================================================
# SEÇÃO 6.1: MEMBROS DE INTERFACE E ESTRUTURAS DE RECORDS (ETAPA S4 / JLS §8.10, §9)
# =============================================================================
class InterfaceConstantDeclaration(FieldDeclaration, InterfaceMemberDeclaration, AnnotationInterfaceMemberDeclaration):
    """
    Declaração de constante em interface (JLS §9.3):
    {ConstantModifier} UnannType VariableDeclaratorList ;
    Implicitamente public static final.
    """
    @property
    def implicit_modifiers(self) -> List[str]:
        return ["public", "static", "final"]

    @property
    def effective_modifiers(self) -> List[str]:
        seen = []
        for m in list(self.modifiers) + self.implicit_modifiers:
            if m not in seen:
                seen.append(m)
        return seen

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["node"] = "InterfaceConstantDeclaration"
        d["implicit_modifiers"] = self.implicit_modifiers
        d["effective_modifiers"] = self.effective_modifiers
        return d

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        decls_str = ", ".join(d.pretty() for d in self.declarators)
        header = f"InterfaceConstantDeclaration: {annos}{mods}{self.type_ref.pretty()} {decls_str}".strip()
        inits = [d.initializer for d in self.declarators if d.initializer is not None]
        if inits:
            return _format_children(header, inits)
        return header


@dataclass
class AnnotationInterfaceElementModifier(ASTNode):
    """Modificador explícito de elemento de annotation interface (JLS §9.6.1): public | abstract."""
    name: str
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "AnnotationInterfaceElementModifier",
            "name": self.name,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return self.name


@dataclass
class AnnotationDefaultValue(ASTNode):
    """Cláusula default de elemento de annotation interface (JLS §9.6.2): default ElementValue."""
    value: ElementValue
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "AnnotationDefaultValue",
            "value": self.value.to_dict(),
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return f"default {self.value.pretty()}"


DefaultValue = AnnotationDefaultValue


@dataclass
class AnnotationInterfaceElementDeclaration(AnnotationInterfaceMemberDeclaration):
    """
    Declaração de elemento em annotation interface (JLS §9.6.1):
    {AnnotationInterfaceElementModifier} UnannType Identifier ( ) [Dims] [DefaultValue] ;
    """
    name: str
    return_type: TypeReference
    modifiers: List[str] = field(default_factory=list)
    default_value: Optional[AnnotationDefaultValue] = None
    annotations: List[ASTNode] = field(default_factory=list)
    dims: int = 0
    dims_annotations: List[List[ASTNode]] = field(default_factory=list)
    parameters: List[ASTNode] = field(default_factory=list)
    throws_types: List[TypeReference] = field(default_factory=list)
    body: Optional[ASTNode] = None
    element_modifiers: List[AnnotationInterfaceElementModifier] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def __post_init__(self):
        if self.element_modifiers and not self.modifiers:
            self.modifiers = [m.name for m in self.element_modifiers]
        elif self.modifiers and not self.element_modifiers:
            self.element_modifiers = [
                AnnotationInterfaceElementModifier(m, self.line, self.column)
                for m in self.modifiers
            ]

    @property
    def implicit_modifiers(self) -> List[str]:
        return ["public", "abstract"]

    @property
    def effective_modifiers(self) -> List[str]:
        seen: List[str] = []
        for m in list(self.modifiers) + self.implicit_modifiers:
            if m not in seen:
                seen.append(m)
        return seen

    @property
    def has_default(self) -> bool:
        return self.default_value is not None

    @property
    def is_required(self) -> bool:
        return self.default_value is None

    @property
    def effective_return_type(self) -> str:
        return self.return_type.get_effective_type(self.dims)

    @property
    def effective_return_type_ref(self) -> TypeReference:
        return self.return_type.get_effective_type_ref(self.dims)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "AnnotationInterfaceElementDeclaration",
            "name": self.name,
            "return_type": self.effective_return_type,
            "modifiers": list(self.modifiers),
            "implicit_modifiers": self.implicit_modifiers,
            "effective_modifiers": self.effective_modifiers,
            "dims": self.dims,
            "has_default": self.has_default,
            "default_value": self.default_value.to_dict() if self.default_value else None,
            "annotations": [a.pretty() for a in self.annotations],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        dims_str = "[]" * self.dims
        def_str = f" {self.default_value.pretty()}" if self.default_value is not None else ""
        return f"AnnotationInterfaceElementDeclaration: {annos}{mods}{self.return_type.pretty()} {self.name}(){dims_str}{def_str}".strip()


@dataclass
class AnnotationInterfaceBody(ASTNode):
    """Corpo de uma annotation interface (JLS §9.6.1): { {AnnotationInterfaceMemberDeclaration} }."""
    members: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "AnnotationInterfaceBody",
            "members": [
                m.to_dict() if hasattr(m, "to_dict") else {"node": m.__class__.__name__}
                for m in self.members
            ],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return _format_children("AnnotationInterfaceBody", self.members)


@dataclass
class AnnotationInterfaceDeclaration(ASTNode):
    """
    Declaração de annotation interface Java (JLS §9.6):
    {InterfaceModifier} @ interface TypeIdentifier AnnotationInterfaceBody
    """
    name: str
    modifiers: List[str] = field(default_factory=list)
    members: List[ASTNode] = field(default_factory=list)
    annotations: List[ASTNode] = field(default_factory=list)
    body: Optional[AnnotationInterfaceBody] = None
    type_parameters: List[Any] = field(default_factory=list)
    extends_types: List[TypeReference] = field(default_factory=list)
    permits_types: List[TypeReference] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def __post_init__(self):
        if self.body is None:
            self.body = AnnotationInterfaceBody(members=self.members, line=self.line, column=self.column)
        elif not self.members and self.body.members:
            self.members = self.body.members

    @property
    def elements(self) -> List[AnnotationInterfaceElementDeclaration]:
        return [m for m in self.members if isinstance(m, AnnotationInterfaceElementDeclaration)]

    @property
    def constants(self) -> List[InterfaceConstantDeclaration]:
        return [m for m in self.members if isinstance(m, InterfaceConstantDeclaration)]

    @property
    def implicit_modifiers(self) -> List[str]:
        return ["abstract", "interface"]

    @property
    def effective_modifiers(self) -> List[str]:
        seen: List[str] = []
        for m in list(self.modifiers) + self.implicit_modifiers:
            if m not in seen:
                seen.append(m)
        return seen

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "AnnotationInterfaceDeclaration",
            "name": self.name,
            "modifiers": list(self.modifiers),
            "implicit_modifiers": self.implicit_modifiers,
            "effective_modifiers": self.effective_modifiers,
            "annotations": [a.pretty() for a in self.annotations],
            "body": self.body.to_dict() if self.body else None,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        header = f"AnnotationInterfaceDeclaration: {annos}{mods}@interface {self.name}".strip()
        return _format_children(header, [self.body] if self.body else self.members)


@dataclass
class InterfaceMethodDeclaration(MethodDeclaration, InterfaceMemberDeclaration):
    """
    Declaração de método em interface (JLS §9.4):
    {InterfaceMethodModifier} MethodHeader MethodBody
    Suporta métodos abstratos, default, static e private.
    """
    @property
    def is_default(self) -> bool:
        return "default" in self.modifiers

    @property
    def is_static(self) -> bool:
        return "static" in self.modifiers

    @property
    def is_private(self) -> bool:
        return "private" in self.modifiers

    @property
    def is_abstract(self) -> bool:
        if self.is_default or self.is_static or self.is_private:
            return False
        return "abstract" in self.modifiers or self.body is None

    @property
    def implicit_modifiers(self) -> List[str]:
        imp = []
        if not self.is_private:
            imp.append("public")
        if self.is_abstract:
            imp.append("abstract")
        return imp

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["node"] = "InterfaceMethodDeclaration"
        d["is_default"] = self.is_default
        d["is_static"] = self.is_static
        d["is_private"] = self.is_private
        d["is_abstract"] = self.is_abstract
        d["implicit_modifiers"] = self.implicit_modifiers
        return d

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        tparams = f"<{', '.join(p.pretty() for p in self.type_parameters)}> " if self.type_parameters else ""
        all_params_repr = []
        if self.receiver_parameter:
            all_params_repr.append(self.receiver_parameter.pretty())
        all_params_repr.extend(p.pretty() for p in self.parameters)
        params_str = ", ".join(all_params_repr)
        thr_str = f" throws {', '.join(t.pretty() for t in self.throws_types)}" if self.throws_types else ""
        if len(self.dims_annotations) == self.dims and any(self.dims_annotations):
            dims_str = " " + " ".join(
                (" ".join(a.pretty() for a in da) + " []") if da else "[]"
                for da in self.dims_annotations
            )
        else:
            dims_str = "[]" * self.dims
        header = f"InterfaceMethodDeclaration: {annos}{mods}{tparams}{self.return_type.pretty()} {self.name}({params_str}){dims_str}{thr_str}".strip()
        if self.body is not None:
            return _format_children(header, [self.body])
        return header + " (abstrato / sem corpo)"


@dataclass
class RecordComponentModifier(ASTNode):
    """Modificador/Annotation de um componente de record (JLS §8.10.1)."""
    annotation: ASTNode
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "RecordComponentModifier",
            "annotation": self.annotation.pretty() if hasattr(self.annotation, "pretty") else str(self.annotation),
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return self.annotation.pretty() if hasattr(self.annotation, "pretty") else str(self.annotation)


@dataclass
class RecordComponent(ASTNode):
    """
    Componente de um record (JLS §8.10.1):
    {RecordComponentModifier} UnannType Identifier
    """
    type_ref: TypeReference
    name: str
    annotations: List[ASTNode] = field(default_factory=list)
    is_varargs: bool = False
    line: int = 1
    column: int = 1

    @property
    def modifiers(self) -> List[RecordComponentModifier]:
        return [
            RecordComponentModifier(annotation=a, line=getattr(a, "line", self.line), column=getattr(a, "column", self.column))
            for a in self.annotations
        ]

    @property
    def effective_type(self) -> str:
        if self.type_ref is None:
            return ""
        base = self.type_ref.full_name
        if self.is_varargs:
            if base.endswith("..."):
                base = base[:-3] + "[]"
            elif not base.endswith("[]"):
                base = f"{base}[]"
        return base

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "RecordComponent",
            "name": self.name,
            "type": self.type_ref.pretty() if self.type_ref else None,
            "effective_type": self.effective_type,
            "is_varargs": self.is_varargs,
            "annotations": [a.pretty() if hasattr(a, "pretty") else str(a) for a in self.annotations],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        t_str = self.type_ref.pretty() if self.type_ref else ""
        var_str = "..." if (self.is_varargs and not t_str.endswith("...")) else ""
        return f"RecordComponent: {annos}{t_str}{var_str} {self.name}".strip()


@dataclass
class VariableArityRecordComponent(RecordComponent):
    """
    Componente varargs de um record (JLS §8.10.1):
    {RecordComponentModifier} UnannType {Annotation} ... Identifier
    """
    ellipsis_annotations: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.is_varargs = True

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["node"] = "VariableArityRecordComponent"
        d["ellipsis_annotations"] = [a.pretty() if hasattr(a, "pretty") else str(a) for a in self.ellipsis_annotations]
        return d

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        e_annos = (" ".join(a.pretty() for a in self.ellipsis_annotations) + " ") if self.ellipsis_annotations else ""
        t_str = self.type_ref.pretty() if self.type_ref else ""
        if t_str.endswith("..."):
            t_str = t_str[:-3]
        return f"VariableArityRecordComponent: {annos}{t_str} {e_annos}... {self.name}".strip()


@dataclass
class RecordComponentList(ASTNode):
    """Lista de componentes do cabeçalho de um record (JLS §8.10.1)."""
    components: List[RecordComponent] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "RecordComponentList",
            "components": [c.to_dict() for c in self.components],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        if not self.components:
            return "RecordComponentList (vazia)"
        return _format_children("RecordComponentList", self.components)


@dataclass
class RecordHeader(ASTNode):
    """
    Cabeçalho de um record (JLS §8.10.1):
    ( [RecordComponentList] )
    """
    component_list: Optional[RecordComponentList] = None
    line: int = 1
    column: int = 1

    def __init__(self, component_list: Any = None, components: List[RecordComponent] = None, line: int = 1, column: int = 1):
        super().__init__()
        self.line = line
        self.column = column
        if isinstance(component_list, list):
            components = component_list
            component_list = None
        if component_list is not None:
            self.component_list = component_list
        elif components is not None:
            self.component_list = RecordComponentList(components=components, line=line, column=column)
        else:
            self.component_list = RecordComponentList(components=[], line=line, column=column)

    @property
    def components(self) -> List[RecordComponent]:
        return self.component_list.components if self.component_list else []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "RecordHeader",
            "component_list": self.component_list.to_dict() if self.component_list else None,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        if not self.components:
            return "RecordHeader ()"
        return _format_children("RecordHeader", self.components)


class RecordBodyDeclaration(ASTNode):
    """Classe base para declarações de corpo de um record (JLS §8.10.2)."""
    pass


@dataclass
class NormalCanonicalConstructor(ConstructorDeclaration, RecordBodyDeclaration):
    """
    Construtor canônico normal de um record (JLS §8.10.4.1):
    {ConstructorModifier} SimpleTypeName ( [RecordComponentList] ) ConstructorBody
    """
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "NormalCanonicalConstructor",
            "name": self.name,
            "modifiers": list(self.modifiers),
            "annotations": [a.pretty() if hasattr(a, "pretty") else str(a) for a in self.annotations],
            "parameters": [p.pretty() for p in self.parameters],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        params_str = ", ".join(p.pretty() for p in self.parameters)
        header = f"NormalCanonicalConstructor: {annos}{mods}{self.name}({params_str})".strip()
        if self.body is not None:
            return _format_children(header, [self.body])
        return header


@dataclass
class CompactConstructorDeclaration(ConstructorDeclaration, RecordBodyDeclaration):
    """
    Construtor canônico compacto de um record (JLS §8.10.4.2):
    {ConstructorModifier} SimpleTypeName ConstructorBody
    Não declara lista formal de parâmetros; os parâmetros derivam do cabeçalho do record.
    """
    derived_parameters: List[RecordComponent] = field(default_factory=list)
    has_formal_parameter_list: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "CompactConstructorDeclaration",
            "name": self.name,
            "modifiers": list(self.modifiers),
            "annotations": [a.pretty() if hasattr(a, "pretty") else str(a) for a in self.annotations],
            "has_formal_parameter_list": False,
            "derived_parameters": [c.to_dict() for c in self.derived_parameters],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        header = f"CompactConstructorDeclaration: {annos}{mods}{self.name} (compacto)".strip()
        if self.body is not None:
            return _format_children(header, [self.body])
        return header


@dataclass
class NonCanonicalRecordConstructor(ConstructorDeclaration, RecordBodyDeclaration):
    """
    Construtor não canônico de um record (JLS §8.10.4):
    Deve invocar outro construtor do próprio record via this(...).
    """
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "NonCanonicalRecordConstructor",
            "name": self.name,
            "modifiers": list(self.modifiers),
            "annotations": [a.pretty() if hasattr(a, "pretty") else str(a) for a in self.annotations],
            "parameters": [p.pretty() for p in self.parameters],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        params_str = ", ".join(p.pretty() for p in self.parameters)
        header = f"NonCanonicalRecordConstructor: {annos}{mods}{self.name}({params_str})".strip()
        if self.body is not None:
            return _format_children(header, [self.body])
        return header


@dataclass
class RecordBody(ASTNode):
    """
    Corpo de um record (JLS §8.10.2):
    { {RecordBodyDeclaration} }
    Distingue a existência de construtor canônico implícito vs explícito.
    """
    declarations: List[ASTNode] = field(default_factory=list)
    has_implicit_canonical_constructor: bool = True
    line: int = 1
    column: int = 1

    def __post_init__(self):
        has_explicit = any(
            isinstance(d, (NormalCanonicalConstructor, CompactConstructorDeclaration))
            for d in self.declarations
        )
        self.has_implicit_canonical_constructor = not has_explicit

    @property
    def members(self) -> List[ASTNode]:
        return self.declarations

    @property
    def has_explicit_canonical_constructor(self) -> bool:
        return not self.has_implicit_canonical_constructor

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "RecordBody",
            "has_implicit_canonical_constructor": self.has_implicit_canonical_constructor,
            "has_explicit_canonical_constructor": self.has_explicit_canonical_constructor,
            "declarations": [d.to_dict() if hasattr(d, "to_dict") else d.pretty() for d in self.declarations],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        tag = " (construtor canônico implícito)" if self.has_implicit_canonical_constructor else " (construtor canônico explícito)"
        header = f"RecordBody{tag}"
        if not self.declarations:
            return header
        return _format_children(header, self.declarations)


@dataclass
class RecordDeclaration(LocalClassOrInterfaceDeclaration):
    """
    Declaração de um record Java (JLS §8.10):
    {ClassModifier} record TypeIdentifier [TypeParameters] RecordHeader [ClassImplements] RecordBody
    """
    name: str
    header: RecordHeader
    modifiers: List[str] = field(default_factory=list)
    type_parameters: List[TypeParameter] = field(default_factory=list)
    implements_types: List[TypeReference] = field(default_factory=list)
    body: Optional[RecordBody] = None
    annotations: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1
    is_local: bool = False

    def __post_init__(self):
        if self.body is None:
            self.body = RecordBody(declarations=[], has_implicit_canonical_constructor=True, line=self.line, column=self.column)

    @property
    def components(self) -> List[RecordComponent]:
        return self.header.components if self.header else []

    @property
    def members(self) -> List[ASTNode]:
        return self.body.declarations if self.body else []

    @property
    def has_implicit_canonical_constructor(self) -> bool:
        return self.body.has_implicit_canonical_constructor if self.body else True

    @property
    def has_explicit_canonical_constructor(self) -> bool:
        return self.body.has_explicit_canonical_constructor if self.body else False

    @property
    def canonical_constructor(self) -> Optional[ASTNode]:
        for d in self.members:
            if isinstance(d, (NormalCanonicalConstructor, CompactConstructorDeclaration)):
                return d
        return None

    @property
    def constructors(self) -> List[ConstructorDeclaration]:
        return [d for d in self.members if isinstance(d, ConstructorDeclaration)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "RecordDeclaration",
            "name": self.name,
            "modifiers": list(self.modifiers),
            "annotations": [a.pretty() if hasattr(a, "pretty") else str(a) for a in self.annotations],
            "type_parameters": [p.pretty() if hasattr(p, "pretty") else str(p) for p in self.type_parameters],
            "header": self.header.to_dict() if self.header else None,
            "implements_types": [t.pretty() for t in self.implements_types],
            "body": self.body.to_dict() if self.body else None,
            "has_implicit_canonical_constructor": self.has_implicit_canonical_constructor,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        tparams = f"<{', '.join(p.pretty() for p in self.type_parameters)}>" if self.type_parameters else ""
        comps_str = ", ".join(c.pretty() for c in self.components)
        impl = f" implements {', '.join(t.pretty() for t in self.implements_types)}" if self.implements_types else ""
        tag = " [canonical implícito]" if self.has_implicit_canonical_constructor else ""
        header = f"RecordDeclaration: {annos}{mods}{self.name}{tparams}({comps_str}){impl}{tag}".strip()
        if not self.members:
            return header
        return _format_children(header, self.members)


# =============================================================================
# SEÇÃO 7: COMANDOS E ESTRUTURAS DE CONTROLE (FASE C)
# =============================================================================
@dataclass
class Declaration(ASTNode):
    """Declaração de variável local de etapas anteriores (ex: int x = 10;)."""
    type_name: str
    name: str
    line: int
    initializer: Optional[ASTNode] = None
    column: int = 1

    def pretty(self) -> str:
        lines = [f"Declaracao ({self.type_name})", f"├── ID ({self.name})"]
        if self.initializer is not None:
            lines.append("└── Inicializador")
            if hasattr(self.initializer, "pretty"):
                init_lines = self.initializer.pretty().splitlines()
            else:
                init_lines = [str(self.initializer)]
            lines.extend("    " + x for x in init_lines)
        else:
            lines[-1] = f"└── ID ({self.name})"
        return "\n".join(lines)


@dataclass
class LocalVariableType(ASTNode):
    """Tipo de variável local (JLS §14.4): tipo explícito ou identificador contextual 'var'."""
    type_ref: Optional[TypeReference] = None
    is_var: bool = False
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        if self.is_var:
            return "LocalVariableType (var)"
        return f"LocalVariableType ({self.type_ref.pretty() if self.type_ref else 'desconhecido'})"


@dataclass
class LocalVariableDeclaration(Declaration, BlockStatement):
    """
    Declaração de variável local com suporte a modificadores, annotations e TypeReference:
    {VariableModifier} (LocalVariableType | UnannType) VariableDeclaratorList;
    """
    modifiers: List[str] = field(default_factory=list)
    type_ref: Optional[TypeReference] = None
    annotations: List[ASTNode] = field(default_factory=list)
    declarators: List[Any] = field(default_factory=list)
    is_var: bool = False
    local_type: Optional[LocalVariableType] = None
    dims: int = 0

    def pretty(self) -> str:
        annos = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        if self.is_var:
            t_name = "var"
        elif self.type_ref:
            t_name = self.type_ref.pretty()
        else:
            t_name = self.type_name
        if self.declarators and len(self.declarators) > 1:
            header = f"LocalVariableDeclaration: {annos}{mods}{t_name}".strip()
            return _format_children(header, self.declarators)
        dims_str = "[]" * self.dims if self.dims else ""
        header = f"LocalVariableDeclaration: {annos}{mods}{t_name} {self.name}{dims_str}".strip()
        if self.initializer is not None:
            return _format_children(header, [self.initializer])
        return header


LocalVariableDeclarationStatement = LocalVariableDeclaration


@dataclass
class ExpressionStatement(Statement):
    """Representa uma instrução composta por uma StatementExpression seguida de ponto e vírgula."""
    expression: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("ExpressionStatement", [self.expression])


@dataclass
class EmptyStatement(Statement):
    """Representa a instrução vazia: ;"""
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return "EmptyStatement (;)"


@dataclass
class LabeledStatement(Statement):
    """Instrução rotulada (JLS §14.7): Identificador : Statement."""
    label: str
    statement: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children(f"LabeledStatement ({self.label}:)", [self.statement])


@dataclass
class StatementExpressionList(ASTNode):
    """Lista ordenada de expressões de instrução separadas por vírgula (ForInit / ForUpdate)."""
    expressions: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("StatementExpressionList", self.expressions)


@dataclass
class ReturnStatement(Statement):
    """Representa a instrução de retorno: return [expressao];"""
    expression: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        if self.expression is not None:
            return _format_children("ReturnStatement", [self.expression])
        return "ReturnStatement"


@dataclass
class IfStatement(Statement):
    """
    Representa a estrutura condicional:
    if (condicao) ramo_verdadeiro [else ramo_falso]
    """
    condition: ASTNode
    then_branch: ASTNode
    else_branch: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        children = [
            _format_children("Condicao", [self.condition]),
            _format_children("Entao", [self.then_branch]),
        ]
        if self.else_branch is not None:
            children.append(_format_children("Senao", [self.else_branch]))
        return _format_children("IfStatement", children)


@dataclass
class WhileStatement(Statement):
    """Representa o laço while: while (condicao) corpo"""
    condition: ASTNode
    body: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children(
            "WhileStatement",
            [_format_children("Condicao", [self.condition]), _format_children("Corpo", [self.body])]
        )


@dataclass
class DoWhileStatement(Statement):
    """Representa o laço do-while: do corpo while (condicao);"""
    body: ASTNode
    condition: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children(
            "DoWhileStatement",
            [_format_children("Corpo", [self.body]), _format_children("Condicao", [self.condition])]
        )


@dataclass
class ForStatement(Statement):
    """
    Representa o laço for tradicional:
    for ([init]; [cond]; [update]) corpo
    """
    init: Optional[ASTNode] = None
    condition: Optional[ASTNode] = None
    update: Optional[ASTNode] = None
    body: Optional[ASTNode] = None
    line: int = 1
    column: int = 1
    init_expressions: List[ASTNode] = field(default_factory=list)
    update_expressions: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        if not self.init_expressions and self.init is not None:
            if isinstance(self.init, StatementExpressionList):
                self.init_expressions = list(self.init.expressions)
            elif not isinstance(self.init, LocalVariableDeclaration):
                self.init_expressions = [self.init]
        if not self.update_expressions and self.update is not None:
            if isinstance(self.update, StatementExpressionList):
                self.update_expressions = list(self.update.expressions)
            else:
                self.update_expressions = [self.update]

    def pretty(self) -> str:
        children = []
        if self.init is not None:
            children.append(_format_children("Init", [self.init]))
        if self.condition is not None:
            children.append(_format_children("Condicao", [self.condition]))
        if self.update is not None:
            children.append(_format_children("Update", [self.update]))
        if self.body is not None:
            children.append(_format_children("Corpo", [self.body]))
        return _format_children("ForStatement", children)


@dataclass
class EnhancedForStatement(Statement):
    """
    Representa o laço for aprimorado (for-each):
    for (Tipo var : iteravel) corpo
    """
    variable: ASTNode
    iterable: ASTNode
    body: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        var_name = getattr(self.variable, "name", "var")
        return _format_children(
            f"EnhancedForStatement ({var_name})",
            [
                _format_children("Variavel", [self.variable]),
                _format_children("Iteravel", [self.iterable]),
                _format_children("Corpo", [self.body]),
            ]
        )


@dataclass
class ComponentPattern(ASTNode):
    """Componente recursivo de RecordPattern (JLS §14.30.1): Pattern | MatchAllPattern."""
    line: int = 1
    column: int = 1


@dataclass
class Pattern(ComponentPattern):
    """Classe base normativa para Patterns (JLS §14.30.1): TypePattern | RecordPattern."""
    line: int = 1
    column: int = 1


@dataclass
class PatternVariable(ASTNode):
    """Variável declarada por um TypePattern (incluindo unnamed pattern variable '_')."""
    name: str
    type_ref: Optional[TypeReference] = None
    modifiers: List[str] = field(default_factory=list)
    annotations: List[ASTNode] = field(default_factory=list)
    is_final: bool = False
    is_unnamed: bool = False
    is_var: bool = False
    line: int = 1
    column: int = 1

    def __post_init__(self):
        self.is_unnamed = (self.name == "_")
        self.is_final = self.is_final or ("final" in self.modifiers)
        self.is_var = self.is_var or (self.type_ref is not None and getattr(self.type_ref, "name", None) == "var")

    @property
    def type_name(self) -> str:
        if self.type_ref is not None:
            return self.type_ref.full_name
        return "var" if self.is_var else "Object"

    def pretty(self) -> str:
        mods_str = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        ann_str = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        return f"PatternVariable: {ann_str}{mods_str}{self.type_name} {self.name}"


@dataclass
class TypePattern(Pattern):
    """Padrão de tipo baseado em LocalVariableDeclaration (JLS §14.30.1)."""
    type_ref: Optional[TypeReference] = None
    name: str = ""
    variable: Optional[PatternVariable] = None
    local_variable: Optional[LocalVariableDeclaration] = None
    modifiers: List[str] = field(default_factory=list)
    annotations: List[ASTNode] = field(default_factory=list)
    is_final: bool = False
    is_unnamed: bool = False
    is_var: bool = False
    line: int = 1
    column: int = 1

    def __post_init__(self):
        if self.variable is not None:
            if not self.name:
                self.name = self.variable.name
            if self.type_ref is None:
                self.type_ref = self.variable.type_ref
            if not self.modifiers and self.variable.modifiers:
                self.modifiers = list(self.variable.modifiers)
            if not self.annotations and self.variable.annotations:
                self.annotations = list(self.variable.annotations)
            self.is_final = self.is_final or self.variable.is_final
            self.is_var = self.is_var or self.variable.is_var
        self.is_final = self.is_final or ("final" in self.modifiers)
        self.is_var = self.is_var or (self.type_ref is not None and getattr(self.type_ref, "name", None) == "var")
        self.is_unnamed = (self.name == "_")
        if self.variable is None:
            self.variable = PatternVariable(
                name=self.name,
                type_ref=self.type_ref,
                modifiers=list(self.modifiers),
                annotations=list(self.annotations),
                is_final=self.is_final,
                is_unnamed=self.is_unnamed,
                is_var=self.is_var,
                line=self.line,
                column=self.column,
            )

    @property
    def type_name(self) -> str:
        if self.type_ref is not None:
            return self.type_ref.full_name
        return "var" if self.is_var else "Object"

    def to_dict(self) -> Dict[str, Any]:
        res = super().to_dict()
        res["type_name"] = self.type_name
        return res

    def pretty(self) -> str:
        ann_str = (" ".join(a.pretty() for a in self.annotations) + " ") if self.annotations else ""
        mods_str = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        t_str = self.type_ref.pretty() if (self.type_ref is not None and hasattr(self.type_ref, "pretty")) else self.type_name
        return f"TypePattern ({ann_str}{mods_str}{t_str} {self.name})"


@dataclass
class ComponentPatternList(ASTNode):
    """Lista ordenada de componentes de um RecordPattern (JLS §14.30.1)."""
    components: List[ComponentPattern] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("ComponentPatternList", self.components)


@dataclass
class RecordPattern(Pattern):
    """Padrão de desconstrução de record (JLS §14.30.1): ReferenceType ( [ComponentPatternList] )."""
    type_ref: Optional[TypeReference] = None
    components: List[ComponentPattern] = field(default_factory=list)
    component_list: Optional[ComponentPatternList] = None
    line: int = 1
    column: int = 1

    def __post_init__(self):
        if self.component_list is None and self.components:
            self.component_list = ComponentPatternList(components=list(self.components), line=self.line, column=self.column)
        elif self.component_list is not None and not self.components:
            self.components = list(self.component_list.components)

    @property
    def type_name(self) -> str:
        return self.type_ref.full_name if self.type_ref is not None else ""

    def to_dict(self) -> Dict[str, Any]:
        res = super().to_dict()
        res["type_name"] = self.type_name
        return res

    def pretty(self) -> str:
        t_str = self.type_ref.pretty() if (self.type_ref is not None and hasattr(self.type_ref, "pretty")) else self.type_name
        if not self.components:
            return f"RecordPattern ({t_str}())"
        return _format_children(f"RecordPattern ({t_str})", self.components)


@dataclass
class MatchAllPattern(ComponentPattern):
    """Padrão coringa '_' como componente direto de RecordPattern (JLS §14.30.1)."""
    lexeme: str = "_"
    is_unnamed: bool = True
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return "MatchAllPattern (_)"


@dataclass
class Guard(ASTNode):
    """Cláusula de guarda contextual 'when Expression' em switch labels com pattern (JLS §14.11.1)."""
    expression: ASTNode
    contextual_keyword: str = "when"
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("Guard (when)", [self.expression])


@dataclass
class SwitchLabel(ASTNode):
    """Classe base para labels de switch (JLS §14.11.1)."""
    line: int = 1
    column: int = 1


@dataclass
class CaseConstantList(ASTNode):
    """Lista ordenada de constantes de um label case (CaseConstant {, CaseConstant})."""
    constants: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("CaseConstantList", self.constants)


@dataclass
class CaseLabel(SwitchLabel):
    """Label case (JLS §14.11.1): constantes, case null[, default], patterns e guard."""
    constants: List[ASTNode] = field(default_factory=list)
    constant_list: Optional[CaseConstantList] = None
    is_null: bool = False
    has_default: bool = False
    patterns: List[ASTNode] = field(default_factory=list)
    guard: Optional[ASTNode] = None
    switch_position: Optional[int] = None
    line: int = 1
    column: int = 1

    def __post_init__(self):
        if self.constant_list is None and self.constants:
            self.constant_list = CaseConstantList(constants=list(self.constants), line=self.line, column=self.column)
        elif self.constant_list is not None and not self.constants:
            self.constants = list(self.constant_list.constants)

    def pretty(self) -> str:
        parts = []
        if self.is_null:
            parts.append("null")
        for c in self.constants:
            if self.is_null and isinstance(c, Literal) and getattr(c, "kind", "") == "NULL":
                continue
            parts.append(c.pretty() if hasattr(c, "pretty") else str(c))
        for p in self.patterns:
            parts.append(p.pretty() if hasattr(p, "pretty") else str(p))
        if self.has_default:
            parts.append("default")
        desc = f"CaseLabel ({', '.join(parts)})"
        if self.guard is not None:
            return _format_children(desc, [self.guard])
        return desc


@dataclass
class PatternCaseLabel(CaseLabel):
    """Label case com pattern(s) e guarda opcional 'when' (JLS §14.11.1)."""

    def pretty(self) -> str:
        children = list(self.patterns)
        if self.guard is not None:
            children.append(self.guard)
        return _format_children("PatternCaseLabel", children)


@dataclass
class DefaultLabel(SwitchLabel):
    """Label default em switch (JLS §14.11.1)."""
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return "DefaultLabel (default)"


@dataclass
class SwitchBlockStatementGroup(ASTNode):
    """Grupo clássico de statements em switch com ':' (SwitchLabels BlockStatements)."""
    labels: List[SwitchLabel] = field(default_factory=list)
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        label_desc = ", ".join(lb.pretty() for lb in self.labels)
        return _format_children(f"SwitchBlockStatementGroup [{label_desc}]", self.statements)


@dataclass
class SwitchRule(ASTNode):
    """Regra moderna de switch com '->' (JLS §14.11.1)."""
    labels: List[SwitchLabel] = field(default_factory=list)
    body: Optional[ASTNode] = None
    is_throw: bool = False
    is_block: bool = False
    is_expression: bool = False
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        label_desc = ", ".join(lb.pretty() for lb in self.labels)
        return _format_children(f"SwitchRule [{label_desc}] ->", [self.body])


@dataclass
class SwitchBlock(ASTNode):
    """Corpo estruturado do switch (grupos ':' ou regras '->')."""
    statement_groups: List[SwitchBlockStatementGroup] = field(default_factory=list)
    switch_rules: List[SwitchRule] = field(default_factory=list)
    entries: List[ASTNode] = field(default_factory=list)
    is_rule_based: bool = False
    line: int = 1
    column: int = 1

    def __post_init__(self):
        if not self.entries:
            self.entries = list(self.switch_rules if self.is_rule_based else self.statement_groups)

    def pretty(self) -> str:
        kind = "rules" if self.is_rule_based else "groups"
        return _format_children(f"SwitchBlock ({kind})", self.entries)


@dataclass
class SwitchCase(ASTNode):
    """Representa uma cláusula case dentro de um switch: case valor: comandos..."""
    value: ASTNode
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        val_str = self.value.pretty() if hasattr(self.value, "pretty") else str(self.value)
        return _format_children(f"SwitchCase ({val_str})", self.statements)


@dataclass
class SwitchStatement(Statement):
    """
    Representa a instrução switch do Java (JLS §14.11):
    suporta statement groups clássicos (:) e switch rules modernos (->).
    """
    expression: ASTNode
    cases: List[SwitchCase] = field(default_factory=list)
    default_block: Optional[Block] = None
    line: int = 1
    column: int = 1
    switch_block: Optional[SwitchBlock] = None

    @property
    def default(self) -> Optional[Block]:
        return self.default_block

    @property
    def default_statements(self) -> List[ASTNode]:
        if self.default_block is None:
            return []
        if isinstance(self.default_block, Block):
            return self.default_block.statements
        if isinstance(self.default_block, list):
            return self.default_block
        return [self.default_block]

    def pretty(self) -> str:
        children = [_format_children("Expressao", [self.expression])]
        if self.switch_block is not None and self.switch_block.is_rule_based:
            children.append(self.switch_block)
            return _format_children("SwitchStatement", children)
        children.extend(self.cases)
        if self.default_block is not None:
            def_stmts = (
                self.default_block.statements
                if isinstance(self.default_block, Block)
                else (self.default_block if isinstance(self.default_block, list) else [self.default_block])
            )
            children.append(_format_children("Default", def_stmts))
        if self.switch_block is not None and not self.cases and self.default_block is None and self.switch_block.entries:
            children.append(self.switch_block)
        return _format_children("SwitchStatement", children)


@dataclass
class SwitchExpression(ASTNode):
    """Representação auxiliar de switch expression para contextualização do YieldStatement na S6 (revisão completa na S8)."""
    expression: ASTNode
    switch_block: Optional[SwitchBlock] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        children = [_format_children("Expressao", [self.expression])]
        if self.switch_block is not None:
            children.append(self.switch_block)
        return _format_children("SwitchExpression", children)


@dataclass
class YieldStatement(Statement):
    """Instrução contextual yield dentro de switch expression (JLS §14.21): yield Expression;"""
    expression: ASTNode
    contextual_keyword: str = "yield"
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("YieldStatement (yield)", [self.expression])


CaseClause = SwitchCase
SwitchStmt = SwitchStatement


@dataclass
class BreakStatement(Statement):
    """Representa o comando: break [rotulo];"""
    label: Optional[str] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return "BreakStatement" + (f": {self.label}" if self.label else "")


@dataclass
class ContinueStatement(Statement):
    """Representa o comando: continue [rotulo];"""
    label: Optional[str] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return "ContinueStatement" + (f": {self.label}" if self.label else "")


@dataclass
class ThrowStatement(Statement):
    """Representa o comando: throw expressao;"""
    expression: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("ThrowStatement", [self.expression])


@dataclass
class AssertStatement(Statement):
    """Representa a instrução de assert: assert condicao [: mensagem];"""
    condition: ASTNode
    message: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        children = [_format_children("Condicao", [self.condition])]
        if self.message is not None:
            children.append(_format_children("Mensagem", [self.message]))
        return _format_children("AssertStatement", children)


@dataclass
class CatchType(ASTNode):
    """Tipo de parâmetro de captura simples ou multi-catch (T1 | T2 | ...)."""
    types: List[TypeReference] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        joined = " | ".join(t.pretty() if hasattr(t, "pretty") else str(t) for t in self.types)
        return f"CatchType ({joined})"


@dataclass
class CatchClause(ASTNode):
    """Representa uma cláusula catch: catch (Tipo1 | Tipo2 param) { ... }"""
    parameter: Parameter
    body: Block
    line: int = 1
    column: int = 1
    catch_type: Optional[CatchType] = None

    def __post_init__(self):
        if self.catch_type is None and self.parameter is not None and getattr(self.parameter, "type_ref", None) is not None:
            self.catch_type = CatchType(types=[self.parameter.type_ref], line=self.line, column=self.column)

    @property
    def catch_types(self) -> List[TypeReference]:
        return self.catch_type.types if self.catch_type else []

    def pretty(self) -> str:
        type_str = (
            " | ".join(t.pretty() for t in self.catch_type.types)
            if self.catch_type and self.catch_type.types
            else self.parameter.type_ref.pretty()
        )
        return _format_children(
            f"CatchClause: {type_str} {self.parameter.name}",
            [self.body]
        )


@dataclass
class Resource(ASTNode):
    """Recurso em try-with-resources (JLS §14.20.3): declaração local ou referência a variável existente."""
    declaration: Optional[LocalVariableDeclaration] = None
    variable_access: Optional[ASTNode] = None
    is_reference: bool = False
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        if self.is_reference:
            return _format_children("Resource (Referencia)", [self.variable_access])
        return _format_children("Resource (Declaracao)", [self.declaration])


@dataclass
class ResourceSpecification(ASTNode):
    """Especificação de recursos de TryWithResourcesStatement: ( ResourceList [;] )."""
    resources: List[Resource] = field(default_factory=list)
    has_trailing_semicolon: bool = False
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        suffix = " [trailing ';']" if self.has_trailing_semicolon else ""
        return _format_children(f"ResourceSpecification{suffix}", self.resources)


@dataclass
class TryStatement(Statement):
    """
    Representa a estrutura de tratamento de exceções:
    try [(recursos)] { corpo } catch... finally...
    """
    resources: List[ASTNode] = field(default_factory=list)
    body: Optional[Block] = None
    catches: List[CatchClause] = field(default_factory=list)
    finally_block: Optional[Block] = None
    line: int = 1
    column: int = 1
    resource_specification: Optional[ResourceSpecification] = None

    def pretty(self) -> str:
        children = []
        if self.resources:
            children.append(_format_children("Recursos", self.resources))
        if self.body is not None:
            children.append(self.body)
        children.extend(self.catches)
        if self.finally_block is not None:
            children.append(_format_children("Finally", [self.finally_block]))
        header = "TryStatement" + (" (with resources)" if self.resources else "")
        return _format_children(header, children)


TryWithResourcesStatement = TryStatement


@dataclass
class SynchronizedStatement(Statement):
    """Representa a instrução de sincronização: synchronized (lock) { ... }"""
    lock: ASTNode
    body: Block
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("SynchronizedStatement", [_format_children("Lock", [self.lock]), self.body])


@dataclass
class UnsupportedStatement(ASTNode):
    """Representa explicitamente uma construção sintática reconhecida, mas ainda não suportada."""
    description: str
    tokens: list = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return f"UnsupportedStatement ({self.description})"


# =============================================================================
# SEÇÃO 8: NÓS DE EXPRESSÃO E OPERADORES
# =============================================================================
@dataclass
class Assignment(ASTNode):
    """Atribuição simples ou composta: alvo = expressao ou alvo += expressao."""
    name: str
    line: int
    expression: ASTNode
    operator: str = "="
    column: int = 1
    target: Optional[ASTNode] = None

    def pretty(self) -> str:
        op_tag = f" ({self.operator})" if self.operator != "=" else ""
        lines = [f"Atribuicao{op_tag}", f"├── ID ({self.name})", "└── Expressao"]
        if hasattr(self.expression, "pretty"):
            expr_lines = self.expression.pretty().splitlines()
        else:
            expr_lines = [str(self.expression)]
        lines.extend("    " + x for x in expr_lines)
        return "\n".join(lines)


@dataclass
class BinaryOp(ASTNode):
    """Operação binária aritmética, relacional, lógica ou bit a bit (ex: a + b, x >= 18)."""
    op: str
    left: ASTNode
    right: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        left_str = self.left.pretty() if hasattr(self.left, "pretty") else str(self.left)
        right_str = self.right.pretty() if hasattr(self.right, "pretty") else str(self.right)
        return "\n".join([
            f"Expressao ({self.op})",
            "├── " + left_str.replace("\n", "\n│   "),
            "└── " + right_str.replace("\n", "\n    "),
        ])


@dataclass
class UnaryOp(ASTNode):
    """Operação unária prefixa ou pós-fixa (ex: ++i, i++, !flag, -x, ~mascara)."""
    op: str
    operand: ASTNode
    is_postfix: bool = False
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        pos_str = "posfixo" if self.is_postfix else "prefixo"
        operand_str = self.operand.pretty() if hasattr(self.operand, "pretty") else str(self.operand)
        return f"OperacaoUnaria ({self.op}, {pos_str}): {operand_str}"


@dataclass
class ConditionalExpression(ASTNode):
    """Expressão condicional ternária: condicao ? entao : senao"""
    condition: ASTNode
    then_expr: ASTNode
    else_expr: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children(
            "ConditionalExpression (? :)",
            [
                _format_children("Condicao", [self.condition]),
                _format_children("Entao", [self.then_expr]),
                _format_children("Senao", [self.else_expr]),
            ]
        )


@dataclass
class MemberAccess(ASTNode):
    """Acesso a membro de objeto ou classe: alvo.membro"""
    target: ASTNode
    member_name: str
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children(f"MemberAccess (. {self.member_name})", [self.target])


@dataclass
class ArrayAccess(ASTNode):
    """Acesso a elemento de array por índice: array[indice]"""
    array: ASTNode
    index: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children(
            "ArrayAccess ([])",
            [
                _format_children("Array", [self.array]),
                _format_children("Indice", [self.index]),
            ]
        )





@dataclass
class ArrayInitializer(ASTNode):
    """Inicializador literal de array: { val1, val2, ... }"""
    elements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("ArrayInitializer ({})", self.elements)


@dataclass
class ElementValueArrayInitializer(ArrayInitializer):
    """Inicializador de array em valor de anotação (JLS §9.7.1): { [ElementValueList] [,] }"""
    has_trailing_comma: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ElementValueArrayInitializer",
            "elements": [
                e.to_dict() if hasattr(e, "to_dict") else e.pretty()
                for e in self.elements
            ],
            "has_trailing_comma": self.has_trailing_comma,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        items = ", ".join(e.pretty() for e in self.elements)
        return f"{{{items}}}"


@dataclass
class ClassLiteral(ASTNode):
    """Literal de classe (JLS §15.8.2): Tipo.class | Tipo[].class | int.class | void.class."""
    type_ref: 'TypeReference'
    line: int = 1
    column: int = 1

    @property
    def is_void(self) -> bool:
        return self.type_ref.name == "void" and self.type_ref.array_dimensions == 0

    @property
    def type_name(self) -> str:
        return self.type_ref.full_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ClassLiteral",
            "type": self.type_ref.to_dict(),
            "type_name": self.type_name,
            "is_void": self.is_void,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
        return f"{self.type_ref.pretty()}.class"


@dataclass
class ArrayCreationExpression(ASTNode):
    """Criação de array: new Tipo[dim1][dim2] [inicializador]"""
    type_ref: 'TypeReference'
    dimensions: List[Optional[ASTNode]] = field(default_factory=list)
    initializer: Optional[ArrayInitializer] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        t_name = self.type_ref.name if hasattr(self.type_ref, "name") else str(self.type_ref)
        dims_str = "".join(f"[{d.pretty() if d else ''}]" for d in self.dimensions)
        header = f"ArrayCreation: new {t_name}{dims_str}"
        children = []
        for i, d in enumerate(self.dimensions):
            if d is not None:
                children.append(_format_children(f"Dimensao[{i}]", [d]))
        if self.initializer is not None:
            children.append(self.initializer)
        if children:
            return _format_children(header, children)
        return header


@dataclass
class CastExpression(ASTNode):
    """Conversão explícita de tipo (cast): (Tipo) expressao ou (Tipo & Bound1 & ...) expressao"""
    target_type: 'TypeReference'
    expression: ASTNode
    line: int = 1
    column: int = 1
    additional_bounds: List['TypeReference'] = field(default_factory=list)

    def pretty(self) -> str:
        t_name = self.target_type.pretty() if hasattr(self.target_type, "pretty") else str(self.target_type)
        if self.additional_bounds:
            bounds = " & ".join(b.pretty() if hasattr(b, "pretty") else str(b) for b in self.additional_bounds)
            t_name = f"{t_name} & {bounds}"
        return _format_children(f"CastExpression (({t_name}))", [self.expression])


@dataclass
class InstanceOfExpression(ASTNode):
    """Operador de verificação de tipo tradicional: expressao instanceof ReferenceType"""
    expression: ASTNode
    target_type: Optional['TypeReference'] = None
    line: int = 1
    column: int = 1
    is_pattern: bool = False
    pattern: Optional[Pattern] = None

    def pretty(self) -> str:
        t_name = self.target_type.pretty() if hasattr(self.target_type, "pretty") else str(self.target_type)
        return _format_children(f"InstanceOf ({t_name})", [self.expression])


@dataclass
class PatternInstanceOfExpression(InstanceOfExpression):
    """Operador instanceof com pattern matching (JLS §15.20.2): RelationalExpression instanceof Pattern"""
    is_pattern: bool = True

    def __post_init__(self):
        self.is_pattern = True
        if self.target_type is None and self.pattern is not None and hasattr(self.pattern, "type_ref"):
            self.target_type = self.pattern.type_ref

    def pretty(self) -> str:
        return _format_children("PatternInstanceOf", [self.expression, self.pattern])


@dataclass
class LambdaParameter(ASTNode):
    """Parâmetro formal de expressão lambda (JLS §15.27.1)."""
    name: str
    type_ref: Optional['TypeReference'] = None
    is_var: bool = False
    modifiers: List[str] = field(default_factory=list)
    annotations: List[ASTNode] = field(default_factory=list)
    is_varargs: bool = False
    line: int = 1
    column: int = 1

    @property
    def is_inferred(self) -> bool:
        return self.type_ref is None and not self.is_var

    def pretty(self) -> str:
        if self.type_ref is not None:
            va = "..." if self.is_varargs else ""
            return f"{self.type_ref.pretty()}{va} {self.name}"
        if self.is_var:
            return f"var {self.name}"
        return self.name


@dataclass
class LambdaExpression(ASTNode):
    """Expressão lambda: parametros -> corpo"""
    parameters: List[str] = field(default_factory=list)
    body: ASTNode = None
    is_block_body: bool = False
    line: int = 1
    column: int = 1
    typed_parameters: List[LambdaParameter] = field(default_factory=list)
    parameter_mode: str = "inferred"  # "empty" | "inferred" | "explicit" | "var"

    def pretty(self) -> str:
        if self.typed_parameters:
            params_str = ", ".join(p.pretty() for p in self.typed_parameters)
        else:
            params_str = ", ".join(self.parameters)
        header = f"LambdaExpression: ({params_str}) ->"
        return _format_children(header, [self.body])


@dataclass
class MethodReference(ASTNode):
    """Referência a método ou construtor: alvo::metodo, Tipo::new ou Tipo[]::new"""
    target: ASTNode
    method_name: str
    line: int = 1
    column: int = 1
    type_arguments: List['TypeReference'] = field(default_factory=list)
    is_array_creation: bool = False
    array_type: Optional['TypeReference'] = None

    def pretty(self) -> str:
        target_str = self.target.pretty() if hasattr(self.target, "pretty") else str(self.target)
        ta = f"<{', '.join(t.pretty() for t in self.type_arguments)}>" if self.type_arguments else ""
        return f"MethodReference: {target_str}::{ta}{self.method_name}"


@dataclass
class MethodCall(ASTNode):
    """Chamada de método: [alvo.][<TArgs>]metodo(argumentos...)"""
    method_name: str = ""
    target: Optional[ASTNode] = None
    arguments: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1
    type_arguments: List['TypeReference'] = field(default_factory=list)

    def pretty(self) -> str:
        target_str = f"{self.target.pretty()}." if self.target else ""
        ta = f"<{', '.join(t.pretty() for t in self.type_arguments)}>" if self.type_arguments else ""
        header = f"MethodCall: {target_str}{ta}{self.method_name}"
        if self.arguments:
            return _format_children(header, self.arguments)
        return header + "()"


class ObjectCreationExpression(MethodCall):
    """Instanciação de objeto com 'new': new Tipo(argumentos...) [{ corpo anonimo }]"""
    type_ref: 'TypeReference'

    def __init__(
        self,
        type_ref: 'TypeReference' = None,
        arguments: List[ASTNode] = None,
        line: int = 1,
        column: int = 1,
        is_diamond: bool = False,
        anonymous_body: Optional[List[ASTNode]] = None,
        target: Optional[ASTNode] = None,
    ):
        t_name = type_ref.name if hasattr(type_ref, "name") else str(type_ref) if type_ref else "Object"
        super().__init__(method_name=f"new {t_name}", target=target, arguments=arguments or [], line=line, column=column)
        self.type_ref = type_ref
        self.is_diamond = is_diamond
        self.anonymous_body = anonymous_body

    def pretty(self) -> str:
        t_name = self.type_ref.pretty() if hasattr(self.type_ref, "pretty") else str(self.type_ref)
        diamond = "<>" if self.is_diamond and "<" not in t_name else ""
        header = f"ObjectCreation: new {t_name}{diamond}"
        children = list(self.arguments)
        if self.anonymous_body is not None:
            children.extend(self.anonymous_body)
        if children:
            return _format_children(header, children)
        return header + "()"


@dataclass
class Literal(ASTNode):
    """Literal de valor constante (números, strings, booleanos, nulo)."""
    value: str
    kind: str
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return f"{self.kind} ({self.value})"


@dataclass
class Identifier(ASTNode):
    """Identificador de variável, campo ou membro."""
    name: str
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return f"ID ({self.name})"
