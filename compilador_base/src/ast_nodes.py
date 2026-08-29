from dataclasses import dataclass
from typing import Optional

class ASTNode:
    def pretty(self):
        raise NotImplementedError

@dataclass
class Program(ASTNode):
    statements: list
    def pretty(self):
        lines = ["Program"]
        for i, stmt in enumerate(self.statements):
            branch = "└── " if i == len(self.statements) - 1 else "├── "
            child_prefix = "    " if i == len(self.statements) - 1 else "│   "
            child_lines = stmt.pretty().splitlines()
            lines.append(branch + child_lines[0])
            lines.extend(child_prefix + line for line in child_lines[1:])
        return "\n".join(lines)

@dataclass
class Declaration(ASTNode):
    type_name: str
    name: str
    line: int
    initializer: Optional[ASTNode] = None
    def pretty(self):
        lines = [f"Declaracao ({self.type_name})", f"├── ID ({self.name})"]
        if self.initializer:
            lines.append("└── Inicializador")
            lines.extend("    " + x for x in self.initializer.pretty().splitlines())
        else:
            lines[-1] = f"└── ID ({self.name})"
        return "\n".join(lines)

@dataclass
class Assignment(ASTNode):
    name: str
    line: int
    expression: ASTNode
    def pretty(self):
        lines = ["Atribuicao", f"├── ID ({self.name})", "└── Expressao"]
        lines.extend("    " + x for x in self.expression.pretty().splitlines())
        return "\n".join(lines)

@dataclass
class BinaryOp(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode
    def pretty(self):
        return "\n".join([
            f"Expressao ({self.op})",
            "├── " + self.left.pretty().replace("\n", "\n│   "),
            "└── " + self.right.pretty().replace("\n", "\n    "),
        ])

@dataclass
class Literal(ASTNode):
    value: str
    kind: str
    def pretty(self):
        return f"{self.kind} ({self.value})"

@dataclass
class Identifier(ASTNode):
    name: str
    def pretty(self):
        return f"ID ({self.name})"
