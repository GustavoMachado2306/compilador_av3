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
class Annotation(ASTNode):
    """Representa uma anotação Java: @Nome ou @Nome(argumentos)."""
    name: str
    arguments: Any = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        if self.arguments is not None:
            return f"@{self.name}(...)"
        return f"@{self.name}"


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

    @property
    def full_name(self) -> str:
        """Nome completo do tipo incluindo suas dimensões de array."""
        return self.get_effective_type(0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "TypeReference",
            "name": self.name,
            "array_dimensions": self.array_dimensions,
            "full_name": self.full_name,
            "is_varargs": self.is_varargs,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
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
            res += "[]" * self.array_dimensions
        if self.is_varargs:
            res += "..."
        return res


# =============================================================================
# SEÇÃO 5: DECLARAÇÃO DE CLASSES, INTERFACES E ENUMS
# =============================================================================
@dataclass
class ClassDeclaration(ASTNode):
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
class InterfaceDeclaration(ASTNode):
    """
    Representa a declaração de uma interface Java:
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

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        tparams = ""
        if self.type_parameters:
            tparams = f"<{', '.join(p.pretty() if hasattr(p, 'pretty') else str(p) for p in self.type_parameters)}>"
        ext = f" extends {', '.join(t.pretty() for t in self.extends_types)}" if self.extends_types else ""
        perm = f" permits {', '.join(t.pretty() for t in self.permits_types)}" if self.permits_types else ""
        header = f"InterfaceDeclaration: {mods}{self.name}{tparams}{ext}{perm}".strip()
        if not self.members:
            return header
        return _format_children(header, self.members)


@dataclass
class EnumConstant(ASTNode):
    """Representa uma constante dentro de um enum (ex: NOVO, ATIVO(1))."""
    name: str
    arguments: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return f"EnumConstant: {self.name}"


@dataclass
class EnumDeclaration(ASTNode):
    """
    Representa a declaração de um enum Java:
    [modificadores] enum Nome [implements I1] { CONSTANTES... [; membros] }
    """
    name: str
    modifiers: List[str] = field(default_factory=list)
    implements_types: List[TypeReference] = field(default_factory=list)
    constants: List[EnumConstant] = field(default_factory=list)
    members: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        impl = f" implements {', '.join(t.pretty() for t in self.implements_types)}" if self.implements_types else ""
        header = f"EnumDeclaration: {mods}{self.name}{impl}".strip()
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

    @property
    def is_unnamed(self) -> bool:
        return self.name == "_"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "VariableDeclaratorId",
            "name": self.name,
            "dims": self.dims,
            "is_unnamed": self.is_unnamed,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self) -> str:
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
    """Parâmetro de aridade variável / varargs (JLS §8.4.1): Tipo... nome."""
    def __init__(self, type_ref: TypeReference, name: str, line: int = 1, column: int = 1, modifiers: List[str] = None, annotations: List[ASTNode] = None):
        super().__init__(type_ref=type_ref, name=name, is_varargs=True, line=line, column=column, modifiers=modifiers or [], annotations=annotations or [])


@dataclass
class Block(ASTNode):
    """Representa um bloco de comandos delimitado por chaves: { ... }."""
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

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
        return {
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
class LocalVariableDeclaration(Declaration):
    """
    Declaração de variável local com suporte a modificadores e TypeReference:
    [final] Tipo nome [= inicializador];
    """
    modifiers: List[str] = field(default_factory=list)
    type_ref: Optional[TypeReference] = None

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        t_name = self.type_ref.pretty() if self.type_ref else self.type_name
        header = f"LocalVariableDeclaration: {mods}{t_name} {self.name}".strip()
        if self.initializer is not None:
            return _format_children(header, [self.initializer])
        return header


@dataclass
class ExpressionStatement(ASTNode):
    """Representa uma instrução composta por uma expressão seguida de ponto e vírgula: expr;"""
    expression: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("ExpressionStatement", [self.expression])


@dataclass
class EmptyStatement(ASTNode):
    """Representa a instrução vazia: ;"""
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return "EmptyStatement (;)"


@dataclass
class ReturnStatement(ASTNode):
    """Representa a instrução de retorno: return [expressao];"""
    expression: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        if self.expression is not None:
            return _format_children("ReturnStatement", [self.expression])
        return "ReturnStatement"


@dataclass
class IfStatement(ASTNode):
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
class WhileStatement(ASTNode):
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
class DoWhileStatement(ASTNode):
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
class ForStatement(ASTNode):
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
class EnhancedForStatement(ASTNode):
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
class SwitchStatement(ASTNode):
    """
    Representa a instrução switch / case do Java:
    switch (expressao) { case valor: ... default: ... }
    """
    expression: ASTNode
    cases: List[SwitchCase] = field(default_factory=list)
    default_block: Optional[Block] = None
    line: int = 1
    column: int = 1

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
        children.extend(self.cases)
        if self.default_block is not None:
            def_stmts = (
                self.default_block.statements
                if isinstance(self.default_block, Block)
                else (self.default_block if isinstance(self.default_block, list) else [self.default_block])
            )
            children.append(_format_children("Default", def_stmts))
        return _format_children("SwitchStatement", children)


CaseClause = SwitchCase
SwitchStmt = SwitchStatement


@dataclass
class BreakStatement(ASTNode):
    """Representa o comando: break [rotulo];"""
    label: Optional[str] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return "BreakStatement" + (f": {self.label}" if self.label else "")


@dataclass
class ContinueStatement(ASTNode):
    """Representa o comando: continue [rotulo];"""
    label: Optional[str] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return "ContinueStatement" + (f": {self.label}" if self.label else "")


@dataclass
class ThrowStatement(ASTNode):
    """Representa o comando: throw expressao;"""
    expression: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("ThrowStatement", [self.expression])


@dataclass
class AssertStatement(ASTNode):
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
class CatchClause(ASTNode):
    """Representa uma cláusula catch: catch (Tipo param) { ... }"""
    parameter: Parameter
    body: Block
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children(
            f"CatchClause: {self.parameter.type_ref.pretty()} {self.parameter.name}",
            [self.body]
        )


@dataclass
class TryStatement(ASTNode):
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


@dataclass
class SynchronizedStatement(ASTNode):
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
    """Conversão explícita de tipo (cast): (Tipo) expressao"""
    target_type: 'TypeReference'
    expression: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        t_name = self.target_type.pretty() if hasattr(self.target_type, "pretty") else str(self.target_type)
        return _format_children(f"CastExpression (({t_name}))", [self.expression])


@dataclass
class InstanceOfExpression(ASTNode):
    """Operador de verificação de tipo: expressao instanceof Tipo"""
    expression: ASTNode
    target_type: 'TypeReference'
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        t_name = self.target_type.pretty() if hasattr(self.target_type, "pretty") else str(self.target_type)
        return _format_children(f"InstanceOf ({t_name})", [self.expression])


@dataclass
class LambdaExpression(ASTNode):
    """Expressão lambda: parametros -> corpo"""
    parameters: List[str] = field(default_factory=list)
    body: ASTNode = None
    is_block_body: bool = False
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        params_str = ", ".join(self.parameters)
        header = f"LambdaExpression: ({params_str}) ->"
        return _format_children(header, [self.body])


@dataclass
class MethodReference(ASTNode):
    """Referência a método ou construtor: alvo::metodo ou Tipo::new"""
    target: ASTNode
    method_name: str
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        target_str = self.target.pretty() if hasattr(self.target, "pretty") else str(self.target)
        return f"MethodReference: {target_str}::{self.method_name}"


@dataclass
class MethodCall(ASTNode):
    """Chamada de método: [alvo.]metodo(argumentos...)"""
    method_name: str = ""
    target: Optional[ASTNode] = None
    arguments: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        target_str = f"{self.target.pretty()}." if self.target else ""
        header = f"MethodCall: {target_str}{self.method_name}"
        if self.arguments:
            return _format_children(header, self.arguments)
        return header + "()"


class ObjectCreationExpression(MethodCall):
    """Instanciação de objeto com 'new': new Tipo(argumentos...)"""
    type_ref: 'TypeReference'

    def __init__(self, type_ref: 'TypeReference' = None, arguments: List[ASTNode] = None, line: int = 1, column: int = 1):
        t_name = type_ref.name if hasattr(type_ref, "name") else str(type_ref) if type_ref else "Object"
        super().__init__(method_name=f"new {t_name}", target=None, arguments=arguments or [], line=line, column=column)
        self.type_ref = type_ref

    def pretty(self) -> str:
        t_name = self.type_ref.pretty() if hasattr(self.type_ref, "pretty") else str(self.type_ref)
        header = f"ObjectCreation: new {t_name}"
        if self.arguments:
            return _format_children(header, self.arguments)
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
