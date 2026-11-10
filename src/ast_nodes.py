<<<<<<< HEAD
from dataclasses import dataclass, field
from typing import List, Optional


def _format_children(header: str, children: list) -> str:
    """Formata um nó da AST e seus filhos usando caracteres de árvore ASCII/Unicode."""
    valid_children = [c for c in children if c is not None]
    if not valid_children:
        return header
    lines = [header]
    for i, child in enumerate(valid_children):
        is_last = i == len(valid_children) - 1
        branch = "└── " if is_last else "├── "
        child_prefix = "    " if is_last else "│   "
        if hasattr(child, "pretty"):
            child_str = child.pretty()
        else:
            child_str = str(child)
        child_lines = child_str.splitlines() if child_str else ["<vazio>"]
        if not child_lines:
            child_lines = ["<vazio>"]
        lines.append(branch + child_lines[0])
        lines.extend(child_prefix + line for line in child_lines[1:])
    return "\n".join(lines)

=======
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
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a

from dataclasses import dataclass, field
from typing import List, Optional, Any


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
<<<<<<< HEAD
=======
    """Classe base para todos os nós da árvore sintática abstrata."""
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
    def pretty(self) -> str:
        raise NotImplementedError


<<<<<<< HEAD
@dataclass
class Program(ASTNode):
=======
# =============================================================================
# SEÇÃO 2: PROGRAMA E UNIDADE DE COMPILAÇÃO JAVA (COMPILATION UNIT)
# =============================================================================
@dataclass
class Program(ASTNode):
    """
    Representação de nível superior de comandos e programas didáticos.
    Mantido para compatibilidade total com os testes das etapas anteriores.
    """
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
    statements: list = field(default_factory=list)

    def pretty(self) -> str:
        if not self.statements:
            return "Program"
        return _format_children("Program", self.statements)

<<<<<<< HEAD

@dataclass
class PackageNode(ASTNode):
    name: str
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return f"Package ({self.name})"


@dataclass
class ImportNode(ASTNode):
    name: str
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return f"Import ({self.name})"


@dataclass
class Block(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("Bloco", self.statements)


@dataclass
class ParameterNode(ASTNode):
    type_name: str
    name: str
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return f"Parametro ({self.type_name} {self.name})"


@dataclass
class MethodDecl(ASTNode):
    name: str
    return_type: str
    parameters: List[ParameterNode] = field(default_factory=list)
    body: Optional[Block] = None
    modifiers: List[str] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        mod_str = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        params_str = ", ".join(f"{p.type_name} {p.name}" for p in self.parameters)
        header = f"Metodo ({mod_str}{self.return_type} {self.name}({params_str}))"
        children = []
        if self.body and self.body.statements:
            children.extend(self.body.statements)
        return _format_children(header, children)


@dataclass
class ClassDecl(ASTNode):
    name: str
    members: List[ASTNode] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    superclass: Optional[str] = None
    interfaces: List[str] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        mod_str = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        ext_str = f" extends {self.superclass}" if self.superclass else ""
        impl_str = f" implements {', '.join(self.interfaces)}" if self.interfaces else ""
        header = f"Classe ({mod_str}class {self.name}{ext_str}{impl_str})"
        return _format_children(header, self.members)

=======
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a

@dataclass
class CompilationUnit(Program):
    """
    Representa uma Unidade de Compilação Java completa.
    Composta por:
    - Declaração de pacote opcional (PackageDeclaration)
    - Lista de declarações de importação (ImportDeclaration*)
    - Lista de declarações de tipos (ClassDeclaration, InterfaceDeclaration, EnumDeclaration*)
    - Lista de comandos didáticos para compatibilidade com modo de fragmento.
    """
    package: Optional['PackageDeclaration'] = None
    imports: List['ImportDeclaration'] = field(default_factory=list)
    type_declarations: List[ASTNode] = field(default_factory=list)
    statements: list = field(default_factory=list)
    line: int = 1
    column: int = 1

    @property
    def package_decl(self) -> Optional['PackageDeclaration']:
        """Alias para self.package."""
        return self.package

    def pretty(self) -> str:
        # Se for arquivo completamente vazio, retorna "Program" para compatibilidade com test_23
        if not self.package and not self.imports and not self.type_declarations and not self.statements:
            return "Program"

        # Se for um fragmento antigo (apenas comandos, sem pacote/imports/tipos)
        if not self.package and not self.imports and not self.type_declarations:
            return _format_children("Program", self.statements)

        children = []
        if self.package:
            children.append(self.package)
        children.extend(self.imports)
        children.extend(self.type_declarations)
        children.extend(self.statements)

        return _format_children("CompilationUnit", children)


# =============================================================================
# SEÇÃO 3: DECLARAÇÃO DE PACOTE E IMPORTAÇÕES
# =============================================================================
@dataclass
class PackageDeclaration(ASTNode):
    """Representa a cláusula de pacote: package nome.do.pacote;"""
    name: str
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("PackageDeclaration", [self.name])


@dataclass
class ImportDeclaration(ASTNode):
    """Representa uma importação: import [static] caminho.[*];"""
    name: str
    is_static: bool = False
    is_wildcard: bool = False
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        static_str = " (static)" if self.is_static else ""
        return f"ImportDeclaration{static_str}: {self.name}"


# =============================================================================
# SEÇÃO 4: REFERÊNCIAS DE TIPO (PRIMITIVOS, CLASSES, ARRAYS, GENERICS)
# =============================================================================
@dataclass
class TypeReference(ASTNode):
    """
    Representa o nome de um tipo Java (primitivo ou de referência).
    Suporta arrays (ex: int[]), generics simples (ex: List<T>) e varargs (...).
    """
    name: str
    array_dimensions: int = 0
    type_arguments: List['TypeReference'] = field(default_factory=list)
    is_varargs: bool = False
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        res = self.name
        if self.type_arguments:
            args_str = ", ".join(arg.pretty() for arg in self.type_arguments)
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
    [modificadores] class Nome [extends Base] [implements I1, I2] { membros }
    """
    name: str
    modifiers: List[str] = field(default_factory=list)
    extends_type: Optional[TypeReference] = None
    implements_types: List[TypeReference] = field(default_factory=list)
    members: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        ext = f" extends {self.extends_type.pretty()}" if self.extends_type else ""
        impl = f" implements {', '.join(t.pretty() for t in self.implements_types)}" if self.implements_types else ""
        header = f"ClassDeclaration: {mods}{self.name}{ext}{impl}".strip()
        if not self.members:
            return header
        return _format_children(header, self.members)


@dataclass
class InterfaceDeclaration(ASTNode):
    """
    Representa a declaração de uma interface Java:
    [modificadores] interface Nome [<T>] [extends I1, I2] { membros }
    """
    name: str
    modifiers: List[str] = field(default_factory=list)
    type_parameters: List[str] = field(default_factory=list)
    extends_types: List[TypeReference] = field(default_factory=list)
    members: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        tparams = f"<{', '.join(self.type_parameters)}>" if self.type_parameters else ""
        ext = f" extends {', '.join(t.pretty() for t in self.extends_types)}" if self.extends_types else ""
        header = f"InterfaceDeclaration: {mods}{self.name}{tparams}{ext}".strip()
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
# SEÇÃO 6: PARÂMETROS, CAMPOS, MÉTODOS E CONSTRUTORES
# =============================================================================
@dataclass
class Parameter(ASTNode):
    """Representa um parâmetro formal em método ou construtor: Tipo nome."""
    type_ref: TypeReference
    name: str
    is_varargs: bool = False
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return f"Parametro ({self.type_ref.pretty()}) {self.name}"


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
class FieldDeclaration(ASTNode):
    """
    Representa a declaração de um campo (atributo) em uma classe/interface:
    [modificadores] Tipo nome [= inicializador];
    """
    type_ref: TypeReference
    name: str
    modifiers: List[str] = field(default_factory=list)
    initializer: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        header = f"FieldDeclaration: {mods}{self.type_ref.pretty()} {self.name}".strip()
        if self.initializer is not None:
            return _format_children(header, [self.initializer])
        return header


@dataclass
class MethodDeclaration(ASTNode):
    """
    Representa a declaração de um método:
    [modificadores] TipoRetorno nome(parametros) [throws excecoes] { corpo }
    """
    name: str
    return_type: TypeReference
    parameters: List[Parameter] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    throws_types: List[TypeReference] = field(default_factory=list)
    body: Optional[Block] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        params_str = ", ".join(p.pretty() for p in self.parameters)
        thr_str = f" throws {', '.join(t.pretty() for t in self.throws_types)}" if self.throws_types else ""
        header = f"MethodDeclaration: {mods}{self.return_type.pretty()} {self.name}({params_str}){thr_str}".strip()
        if self.body is not None:
            return _format_children(header, [self.body])
        return header + " (abstrato / sem corpo)"


@dataclass
class ConstructorDeclaration(ASTNode):
    """
    Representa a declaração de um construtor:
    [modificadores] NomeClasse(parametros) [throws excecoes] { corpo }
    """
    name: str
    parameters: List[Parameter] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    throws_types: List[TypeReference] = field(default_factory=list)
    body: Optional[Block] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        mods = (" ".join(self.modifiers) + " ") if self.modifiers else ""
        params_str = ", ".join(p.pretty() for p in self.parameters)
        thr_str = f" throws {', '.join(t.pretty() for t in self.throws_types)}" if self.throws_types else ""
        header = f"ConstructorDeclaration: {mods}{self.name}({params_str}){thr_str}".strip()
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


<<<<<<< HEAD
=======
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
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
@dataclass
class Assignment(ASTNode):
    """Atribuição simples ou composta: alvo = expressao ou alvo += expressao."""
    name: str
    line: int
    expression: ASTNode
    operator: str = "="
    column: int = 1
<<<<<<< HEAD
    operator: str = "="

    def pretty(self) -> str:
        label = "Atribuicao" if self.operator == "=" else f"Atribuicao ({self.operator})"
        lines = [label, f"├── ID ({self.name})", "└── Expressao"]
=======
    target: Optional[ASTNode] = None

    def pretty(self) -> str:
        op_tag = f" ({self.operator})" if self.operator != "=" else ""
        lines = [f"Atribuicao{op_tag}", f"├── ID ({self.name})", "└── Expressao"]
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        if hasattr(self.expression, "pretty"):
            expr_lines = self.expression.pretty().splitlines()
        else:
            expr_lines = [str(self.expression)]
        lines.extend("    " + x for x in expr_lines)
        return "\n".join(lines)


<<<<<<< HEAD
@dataclass
class CompoundAssign(Assignment):
    """Nó de atribuição composta (+=, -=, *=, /=, %=, <<=, >>=, >>>=, &=, |=, ^=)."""
    target_node: Optional[ASTNode] = None
    value: Optional[ASTNode] = None


@dataclass
class ArrayAccess(ASTNode):
    array: ASTNode
    index: ASTNode
    line: int = 1
    column: int = 1

    @property
    def name(self) -> str:
        if isinstance(self.array, Identifier):
            return self.array.name
        if isinstance(self.array, ArrayAccess):
            return self.array.name
        return str(self.array)

    def pretty(self) -> str:
        return _format_children("AcessoArray", [self.array, self.index])


@dataclass
class IfStmt(ASTNode):
    condition: ASTNode
    then_branch: ASTNode
    else_branch: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        cond_node = _format_children("Condicao", [self.condition])
        then_items = self.then_branch.statements if isinstance(self.then_branch, Block) else [self.then_branch]
        then_node = _format_children("Entao", then_items)
        children = [cond_node, then_node]
        if self.else_branch is not None:
            else_items = self.else_branch.statements if isinstance(self.else_branch, Block) else [self.else_branch]
            else_node = _format_children("Senao", else_items)
            children.append(else_node)
        return _format_children("If", children)


@dataclass
class WhileStmt(ASTNode):
    condition: ASTNode
    body: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        cond_node = _format_children("Condicao", [self.condition])
        body_items = self.body.statements if isinstance(self.body, Block) else [self.body]
        body_node = _format_children("Corpo", body_items)
        return _format_children("While", [cond_node, body_node])


@dataclass
class DoWhileStmt(ASTNode):
    body: ASTNode
    condition: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        body_items = self.body.statements if isinstance(self.body, Block) else [self.body]
        body_node = _format_children("Corpo", body_items)
        cond_node = _format_children("Condicao", [self.condition])
        return _format_children("DoWhile", [body_node, cond_node])


@dataclass
class ForStmt(ASTNode):
    init: Optional[ASTNode]
    condition: Optional[ASTNode]
    update: Optional[ASTNode]
    body: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        children = []
        if self.init is not None:
            children.append(_format_children("Inicializacao", [self.init]))
        if self.condition is not None:
            children.append(_format_children("Condicao", [self.condition]))
        if self.update is not None:
            children.append(_format_children("Atualizacao", [self.update]))
        body_items = self.body.statements if isinstance(self.body, Block) else [self.body]
        children.append(_format_children("Corpo", body_items))
        return _format_children("For", children)


@dataclass
class CaseClause(ASTNode):
    value: Optional[ASTNode] = None  # None para 'default'
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        header = f"Case ({self.value.pretty() if hasattr(self.value, 'pretty') else self.value})" if self.value is not None else "Default"
        return _format_children(header, self.statements)


@dataclass
class SwitchStmt(ASTNode):
    expression: ASTNode
    cases: List[CaseClause] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        expr_node = _format_children("Expressao", [self.expression])
        return _format_children("Switch", [expr_node] + list(self.cases))


@dataclass
class CatchClause(ASTNode):
    exception_type: str
    exception_name: str
    body: Block
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        header = f"Catch ({self.exception_type} {self.exception_name})"
        items = self.body.statements if isinstance(self.body, Block) else [self.body]
        return _format_children(header, items)


@dataclass
class TryStmt(ASTNode):
    try_block: Block
    catches: List[CatchClause] = field(default_factory=list)
    finally_block: Optional[Block] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        try_items = self.try_block.statements if isinstance(self.try_block, Block) else [self.try_block]
        children = [_format_children("BlocoTry", try_items)]
        children.extend(self.catches)
        if self.finally_block is not None:
            fin_items = self.finally_block.statements if isinstance(self.finally_block, Block) else [self.finally_block]
            children.append(_format_children("Finally", fin_items))
        return _format_children("Try", children)


@dataclass
class ThrowStmt(ASTNode):
    expression: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children("Throw", [self.expression])


@dataclass
class ReturnStmt(ASTNode):
    expression: Optional[ASTNode] = None
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        if self.expression is None:
            return "Return"
        return _format_children("Return", [self.expression])


@dataclass
class BreakStmt(ASTNode):
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return "Break"


@dataclass
class ContinueStmt(ASTNode):
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return "Continue"


@dataclass
class MethodCall(ASTNode):
    target: str
    arguments: List[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return _format_children(f"ChamadaMetodo ({self.target})", self.arguments)


@dataclass
class UnaryOp(ASTNode):
    op: str
    operand: ASTNode
    is_postfix: bool = False
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        pos_label = "pos-fixo" if self.is_postfix else "prefixo"
        return _format_children(f"Unario ({self.op}, {pos_label})", [self.operand])


=======
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
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


<<<<<<< HEAD
=======
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


>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
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


# Aliases de retrocompatibilidade para código e testes existentes
BlockNode = Block
MethodNode = MethodDecl
ClassNode = ClassDecl
IfNode = IfStmt
WhileNode = WhileStmt
DoWhileNode = DoWhileStmt
ForNode = ForStmt
SwitchNode = SwitchStmt
TryNode = TryStmt
ThrowNode = ThrowStmt
ReturnNode = ReturnStmt
BreakNode = BreakStmt
ContinueNode = ContinueStmt
MethodCallNode = MethodCall
UnaryOpNode = UnaryOp
ArrayAccessNode = ArrayAccess
CompoundAssignNode = CompoundAssign
