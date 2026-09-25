from dataclasses import dataclass
from typing import Optional

class ASTNode:
    def pretty(self):
        raise NotImplementedError

@dataclass
class Program(ASTNode):
    statements: list

    def pretty(self):
        if not self.statements:
            return "Program"
        lines = ["Program"]
        for i, stmt in enumerate(self.statements):
            branch = "└── " if i == len(self.statements) - 1 else "├── "
            child_prefix = "    " if i == len(self.statements) - 1 else "│   "
            if hasattr(stmt, "pretty"):
                child_lines = stmt.pretty().splitlines()
            else:
                child_lines = [str(stmt)]
            if not child_lines:
                child_lines = ["<vazio>"]
            lines.append(branch + child_lines[0])
            lines.extend(child_prefix + line for line in child_lines[1:])
        return "\n".join(lines)

@dataclass
class Declaration(ASTNode):
    type_name: str
    name: str
    line: int
    initializer: Optional[ASTNode] = None
    column: int = 1

    def pretty(self):
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

    def pretty(self):
        lines = ["Atribuicao", f"├── ID ({self.name})", "└── Expressao"]
        if hasattr(self.expression, "pretty"):
            expr_lines = self.expression.pretty().splitlines()
        else:
            expr_lines = [str(self.expression)]
        lines.extend("    " + x for x in expr_lines)
        return "\n".join(lines)

@dataclass
class BinaryOp(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode
    line: int = 1
    column: int = 1

    def pretty(self):
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

    def pretty(self):
        return f"{self.kind} ({self.value})"

@dataclass
class Identifier(ASTNode):
    name: str
    line: int = 1
    column: int = 1

    def pretty(self):
        return f"ID ({self.name})"
