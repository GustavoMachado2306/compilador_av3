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


class ASTNode:
    def pretty(self) -> str:
        raise NotImplementedError


@dataclass
class Program(ASTNode):
    statements: list = field(default_factory=list)

    def pretty(self) -> str:
        if not self.statements:
            return "Program"
        return _format_children("Program", self.statements)


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


@dataclass
class Declaration(ASTNode):
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
class Assignment(ASTNode):
    name: str
    line: int
    expression: ASTNode
    column: int = 1
    operator: str = "="

    def pretty(self) -> str:
        label = "Atribuicao" if self.operator == "=" else f"Atribuicao ({self.operator})"
        lines = [label, f"├── ID ({self.name})", "└── Expressao"]
        if hasattr(self.expression, "pretty"):
            expr_lines = self.expression.pretty().splitlines()
        else:
            expr_lines = [str(self.expression)]
        lines.extend("    " + x for x in expr_lines)
        return "\n".join(lines)


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


@dataclass
class BinaryOp(ASTNode):
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
class Literal(ASTNode):
    value: str
    kind: str
    line: int = 1
    column: int = 1

    def pretty(self) -> str:
        return f"{self.kind} ({self.value})"


@dataclass
class Identifier(ASTNode):
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
