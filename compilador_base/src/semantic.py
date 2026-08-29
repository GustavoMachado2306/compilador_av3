from .ast_nodes import Declaration, Assignment, BinaryOp, Literal, Identifier, Program

class SemanticAnalyzer:
    def __init__(self, symbol_table):
        self.symbols = symbol_table
        self.errors = []

    def analyze(self, program):
        for stmt in program.statements:
            if isinstance(stmt, Declaration):
                if not self.symbols.declare(stmt.name, stmt.type_name, stmt.line):
                    self.errors.append(f"[ERRO SEMÂNTICO] Variável '{stmt.name}' declarada novamente na linha {stmt.line}.")
                if stmt.initializer:
                    self.check_expression(stmt.initializer)
                    self.check_assignment_type(stmt.type_name, stmt.initializer, stmt.name)
            elif isinstance(stmt, Assignment):
                symbol = self.symbols.lookup(stmt.name)
                if symbol is None:
                    self.errors.append(f"[ERRO SEMÂNTICO] Variável '{stmt.name}' utilizada na linha {stmt.line} não foi declarada previamente.")
                self.check_expression(stmt.expression)
        return self.errors

    def check_expression(self, node):
        if isinstance(node, Identifier) and self.symbols.lookup(node.name) is None:
            self.errors.append(f"[ERRO SEMÂNTICO] Variável '{node.name}' utilizada não foi declarada previamente.")
        elif isinstance(node, BinaryOp):
            self.check_expression(node.left)
            self.check_expression(node.right)

    def infer_type(self, node):
        if isinstance(node, Literal):
            return "String" if node.kind == "STRING" else "int"
        if isinstance(node, Identifier):
            symbol = self.symbols.lookup(node.name)
            return symbol["type"] if symbol else None
        if isinstance(node, BinaryOp):
            left = self.infer_type(node.left)
            right = self.infer_type(node.right)
            return left if left == right else None
        return None

    def check_assignment_type(self, target_type, expression, target_name):
        expr_type = self.infer_type(expression)
        if expr_type and expr_type != target_type:
            self.errors.append(
                f"[ERRO SEMÂNTICO] Incompatibilidade de tipos: não é possível atribuir {expr_type} a '{target_name}' do tipo {target_type}."
            )
