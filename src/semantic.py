from .ast_nodes import Declaration, Assignment, BinaryOp, Literal, Identifier, Program

class SemanticError(str):
    """Exceção/mensagem estruturada de erro semântico compatível com string."""
    def __new__(cls, message: str, line: int):
        formatted = f"[ERRO SEMÂNTICO]\nLinha {line}:\n{message}"
        instance = super().__new__(cls, formatted)
        instance.message = message
        instance.line = line
        return instance


class SemanticAnalyzer:
    """Analisador semântico para o subconjunto didático."""
    def __init__(self, symbol_table):
        self.symbols = symbol_table
        self.errors = []

    def analyze(self, program):
        self.errors = []
        if not program or not hasattr(program, "statements"):
            return self.errors

        for stmt in program.statements:
            if isinstance(stmt, Declaration):
                prev = self.symbols.lookup(stmt.name)
                if not self.symbols.declare(stmt.name, stmt.type_name, stmt.line, category="variavel"):
                    prev_line = f" (declarada na linha {prev['line']})" if prev and "line" in prev else ""
                    self.errors.append(
                        SemanticError(f"Variável '{stmt.name}' declarada novamente{prev_line}.", stmt.line)
                    )
                if stmt.initializer is not None:
                    self.check_expression(stmt.initializer)
                    self.check_assignment_type(stmt.type_name, stmt.initializer, stmt.name, stmt.line)

            elif isinstance(stmt, Assignment):
                symbol = self.symbols.lookup(stmt.name)
                if symbol is None or symbol.get("category") != "variavel":
                    self.errors.append(
                        SemanticError(f"Variável '{stmt.name}' não foi declarada.", stmt.line)
                    )
                self.check_expression(stmt.expression)
                if symbol is not None and symbol.get("category") == "variavel" and "type" in symbol:
                    self.check_assignment_type(symbol["type"], stmt.expression, stmt.name, stmt.line)

        return self.errors

    def check_expression(self, node):
        if node is None:
            return
        if isinstance(node, Identifier):
            symbol = self.symbols.lookup(node.name)
            if symbol is None or symbol.get("category") != "variavel":
                line = getattr(node, "line", 1)
                self.errors.append(
                    SemanticError(f"Variável '{node.name}' não foi declarada.", line)
                )
        elif isinstance(node, BinaryOp):
            self.check_expression(node.left)
            self.check_expression(node.right)
            left_type = self.infer_type(node.left)
            right_type = self.infer_type(node.right)
            line = getattr(node, "line", 1)

            # Regra oficial: String não deve participar de + ou -
            if left_type == "String" or right_type == "String":
                self.errors.append(
                    SemanticError(
                        f"Operação aritmética '{node.op}' inválida: tipo 'String' não é suportado em operações aritméticas.",
                        line,
                    )
                )
            elif left_type and right_type and (left_type != "int" or right_type != "int"):
                self.errors.append(
                    SemanticError(
                        f"Operação aritmética '{node.op}' inválida entre tipos '{left_type}' e '{right_type}'.",
                        line,
                    )
                )

    def infer_type(self, node):
        if node is None:
            return None
        if isinstance(node, Literal):
            return "String" if node.kind == "STRING" else "int"
        if isinstance(node, Identifier):
            symbol = self.symbols.lookup(node.name)
            return symbol["type"] if symbol and "type" in symbol and symbol.get("category") == "variavel" else None
        if isinstance(node, BinaryOp):
            left = self.infer_type(node.left)
            right = self.infer_type(node.right)
            # Apenas int + int e int - int produzem int
            if left == "int" and right == "int":
                return "int"
            return None
        return None

    def check_assignment_type(self, target_type, expression, target_name, line):
        expr_type = self.infer_type(expression)
        if expr_type and expr_type != target_type:
            self.errors.append(
                SemanticError(
                    f"Incompatibilidade de tipos: não é possível atribuir {expr_type} a '{target_name}' do tipo {target_type}.",
                    line,
                )
            )
