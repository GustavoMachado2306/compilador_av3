from .ast_nodes import (
    ASTNode,
    Program,
    PackageNode,
    ImportNode,
    ClassDecl,
    ClassNode,
    MethodDecl,
    MethodNode,
    ParameterNode,
    Block,
    BlockNode,
    Declaration,
    Assignment,
    CompoundAssign,
    ArrayAccess,
    IfStmt,
    IfNode,
    WhileStmt,
    WhileNode,
    DoWhileStmt,
    DoWhileNode,
    ForStmt,
    ForNode,
    SwitchStmt,
    CaseClause,
    TryStmt,
    CatchClause,
    ThrowStmt,
    ReturnStmt,
    ReturnNode,
    BreakStmt,
    BreakNode,
    ContinueStmt,
    ContinueNode,
    MethodCall,
    MethodCallNode,
    UnaryOp,
    UnaryOpNode,
    BinaryOp,
    Literal,
    Identifier,
)

NUMERIC_TYPES = {"int", "long", "short", "byte", "float", "double", "char"}
FLOAT_TYPES = {"float", "double"}
INTEGER_TYPES = {"int", "long", "short", "byte", "char"}
ARITHMETIC_OPS = {"+", "-", "*", "/", "%"}
BITWISE_OPS = {"&", "|", "^", "<<", ">>", ">>>"}
RELATIONAL_OPS = {"==", "!=", "<", "<=", ">", ">=", "instanceof"}
LOGICAL_OPS = {"&&", "||"}
BUILTIN_JAVA_OBJECTS = {
    "System",
    "Math",
    "String",
    "Integer",
    "Double",
    "Float",
    "Long",
    "Boolean",
    "Character",
    "Arrays",
    "Collections",
    "Object",
}


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
    Analisador semântico recursivo que percorre classes, métodos, blocos,
    estruturas de controle (if/while/do-while/for/switch/try-catch-finally) e expressões completas.
    """
    def __init__(self, symbol_table):
        self.symbols = symbol_table
        self.errors = []
        self._current_target_type = None

    def analyze(self, program: Program):
        self.errors = []
        self._current_target_type = None
        if not program or not hasattr(program, "statements"):
            return self.errors

        for stmt in program.statements:
            self.visit_statement(stmt)

        return self.errors

    def visit_statement(self, stmt: ASTNode):
        if stmt is None:
            return

        if isinstance(stmt, (PackageNode, ImportNode, BreakStmt, ContinueStmt)):
            return

        if isinstance(stmt, ClassDecl):
            for member in stmt.members:
                self.visit_statement(member)
            return

        if isinstance(stmt, MethodDecl):
            # Registra parâmetros do método na tabela de símbolos para validação no escopo do corpo
            for param in stmt.parameters:
                if isinstance(param, ParameterNode):
                    base_type = param.type_name.replace("[]", "").replace("...", "")
                    if not self.symbols.exists(param.name):
                        self.symbols.declare(param.name, base_type, param.line, category="parametro")
            if stmt.body is not None:
                self.visit_statement(stmt.body)
            return

        if isinstance(stmt, Block):
            for inner_stmt in stmt.statements:
                self.visit_statement(inner_stmt)
            return

        if isinstance(stmt, Declaration):
            prev = self.symbols.lookup(stmt.name)
            if not self.symbols.declare(stmt.name, stmt.type_name, stmt.line, category="variavel"):
                # Se já existia como variável do usuário, reporta duplicidade
                if prev and prev.get("category") == "variavel":
                    prev_line = f" (declarada na linha {prev['line']})" if "line" in prev else ""
                    self.errors.append(
                        SemanticError(f"Variável '{stmt.name}' declarada novamente{prev_line}.", stmt.line)
                    )
            if stmt.initializer is not None:
                prev_target = self._current_target_type
                self._current_target_type = stmt.type_name.replace("[]", "") if stmt.type_name else None
                try:
                    self.check_expression(stmt.initializer)
                    self.check_assignment_type(stmt.type_name, stmt.initializer, stmt.name, stmt.line)
                finally:
                    self._current_target_type = prev_target
            return

        if isinstance(stmt, Assignment):
            base_name = stmt.name.split(".")[0] if "." in stmt.name else stmt.name
            symbol = self.symbols.lookup(base_name)
            if symbol is None or symbol.get("category") not in ("variavel", "parametro"):
                self.errors.append(
                    SemanticError(f"Variável '{base_name}' não foi declarada.", stmt.line)
                )
            if isinstance(stmt, CompoundAssign) and isinstance(stmt.target_node, ArrayAccess):
                self.check_expression(stmt.target_node.index)
            target_type = (
                symbol["type"].replace("[]", "")
                if (symbol is not None and symbol.get("category") in ("variavel", "parametro") and "type" in symbol)
                else None
            )
            prev_target = self._current_target_type
            self._current_target_type = target_type
            try:
                self.check_expression(stmt.expression)
                if target_type is not None:
                    self.check_assignment_type(symbol["type"], stmt.expression, base_name, stmt.line)
            finally:
                self._current_target_type = prev_target
            return

        if isinstance(stmt, IfStmt):
            self.check_expression(stmt.condition)
            self.visit_statement(stmt.then_branch)
            if stmt.else_branch is not None:
                self.visit_statement(stmt.else_branch)
            return

        if isinstance(stmt, WhileStmt):
            self.check_expression(stmt.condition)
            self.visit_statement(stmt.body)
            return

        if isinstance(stmt, DoWhileStmt):
            self.visit_statement(stmt.body)
            self.check_expression(stmt.condition)
            return

        if isinstance(stmt, ForStmt):
            if stmt.init is not None:
                if isinstance(stmt.init, (Declaration, Assignment)):
                    self.visit_statement(stmt.init)
                else:
                    self.check_expression(stmt.init)
            if stmt.condition is not None:
                self.check_expression(stmt.condition)
            if stmt.update is not None:
                if isinstance(stmt.update, Assignment):
                    self.visit_statement(stmt.update)
                else:
                    self.check_expression(stmt.update)
            self.visit_statement(stmt.body)
            return

        if isinstance(stmt, SwitchStmt):
            self.check_expression(stmt.expression)
            for case in stmt.cases:
                if isinstance(case, CaseClause):
                    if case.value is not None:
                        self.check_expression(case.value)
                    for c_stmt in case.statements:
                        self.visit_statement(c_stmt)
            return

        if isinstance(stmt, TryStmt):
            self.visit_statement(stmt.try_block)
            for catch in stmt.catches:
                if isinstance(catch, CatchClause):
                    if not self.symbols.exists(catch.exception_name):
                        self.symbols.declare(catch.exception_name, catch.exception_type, catch.line, category="parametro")
                    self.visit_statement(catch.body)
            if stmt.finally_block is not None:
                self.visit_statement(stmt.finally_block)
            return

        if isinstance(stmt, ThrowStmt):
            self.check_expression(stmt.expression)
            return

        if isinstance(stmt, ReturnStmt):
            if stmt.expression is not None:
                self.check_expression(stmt.expression)
            return

        if isinstance(stmt, MethodCall):
            for arg in stmt.arguments:
                self.check_expression(arg)
            return

        if isinstance(stmt, (UnaryOp, BinaryOp, ArrayAccess)):
            self.check_expression(stmt)

    def check_expression(self, node: ASTNode):
        if node is None:
            return

        if isinstance(node, Identifier):
            base_name = node.name.split(".")[0] if "." in node.name else node.name
            if base_name in BUILTIN_JAVA_OBJECTS or base_name in ("this", "super"):
                return
            symbol = self.symbols.lookup(base_name)
            if symbol is None or symbol.get("category") not in ("variavel", "parametro"):
                line = getattr(node, "line", 1)
                self.errors.append(
                    SemanticError(f"Variável '{base_name}' não foi declarada.", line)
                )

        elif isinstance(node, ArrayAccess):
            self.check_expression(node.array)
            self.check_expression(node.index)
            idx_type = self.infer_type(node.index)
            if idx_type in ("String", "boolean") or idx_type in FLOAT_TYPES:
                line = getattr(node, "line", 1)
                self.errors.append(
                    SemanticError(
                        f"Índice de array inválido: esperado tipo inteiro, encontrado '{idx_type}'.",
                        line,
                    )
                )

        elif isinstance(node, MethodCall):
            prev_target = self._current_target_type
            self._current_target_type = None
            try:
                for arg in node.arguments:
                    self.check_expression(arg)
            finally:
                self._current_target_type = prev_target

        elif isinstance(node, UnaryOp):
            self.check_expression(node.operand)
            op_type = self.infer_type(node.operand)
            line = getattr(node, "line", 1)
            if node.op in ("-", "+", "~", "++", "--") and op_type == "String":
                self.errors.append(
                    SemanticError(
                        f"Operação unária '{node.op}' inválida sobre o tipo 'String'.",
                        line,
                    )
                )

        elif isinstance(node, BinaryOp):
            self.check_expression(node.left)
            self.check_expression(node.right)
            left_type = self.infer_type(node.left)
            right_type = self.infer_type(node.right)
            line = getattr(node, "line", 1)

            if node.op in ARITHMETIC_OPS:
                if left_type == "String" or right_type == "String":
                    # Concatenação com '+' é válida em contexto de String/impressão,
                    # mas bloqueada quando usada em atribuição aritmética numérica ou com '-', '*', '/', '%'
                    if node.op != "+" or self._current_target_type in NUMERIC_TYPES:
                        self.errors.append(
                            SemanticError(
                                f"Operação aritmética '{node.op}' inválida: tipo 'String' não é suportado em operações aritméticas.",
                                line,
                            )
                        )
                elif left_type and right_type and (left_type not in NUMERIC_TYPES or right_type not in NUMERIC_TYPES):
                    self.errors.append(
                        SemanticError(
                            f"Operação aritmética '{node.op}' inválida entre tipos '{left_type}' e '{right_type}'.",
                            line,
                        )
                    )
            elif node.op in BITWISE_OPS:
                if left_type == "String" or right_type == "String":
                    self.errors.append(
                        SemanticError(
                            f"Operação bitwise '{node.op}' inválida para o tipo 'String'.",
                            line,
                        )
                    )
                elif left_type in FLOAT_TYPES or right_type in FLOAT_TYPES:
                    self.errors.append(
                        SemanticError(
                            f"Operação bitwise/shift '{node.op}' exige operandos inteiros.",
                            line,
                        )
                    )

    def infer_type(self, node: ASTNode):
        if node is None:
            return None
        if isinstance(node, Literal):
            if node.kind == "STRING":
                return "String"
            if node.kind == "CHAR":
                return "char"
            if node.kind == "BOOLEAN":
                return "boolean"
            if node.kind == "FLOAT":
                if node.value.endswith(("f", "F")):
                    return "float"
                return "double"
            if node.kind == "NULL":
                return "null"
            if node.kind in ("NUM", "HEX", "BINARY", "OCTAL"):
                if node.value.endswith(("l", "L")):
                    return "long"
                return "int"
            return "int"

        if isinstance(node, Identifier):
            base_name = node.name.split(".")[0] if "." in node.name else node.name
            symbol = self.symbols.lookup(base_name)
            if symbol and "type" in symbol and symbol.get("category") in ("variavel", "parametro"):
                return symbol["type"].replace("[]", "")
            return None

        if isinstance(node, ArrayAccess):
            return self.infer_type(node.array)

        if isinstance(node, UnaryOp):
            if node.op.startswith("(") and node.op.endswith(")"):
                return node.op[1:-1].replace("[]", "")
            if node.op == "!":
                return "boolean"
            return self.infer_type(node.operand)

        if isinstance(node, BinaryOp):
            if node.op == "?:":
                return self.infer_type(node.left) or self.infer_type(node.right)
            if node.op in RELATIONAL_OPS or node.op in LOGICAL_OPS:
                return "boolean"
            left = self.infer_type(node.left)
            right = self.infer_type(node.right)
            if node.op == "+" and (left == "String" or right == "String"):
                if self._current_target_type not in NUMERIC_TYPES:
                    return "String"
                return None
            if left in NUMERIC_TYPES and right in NUMERIC_TYPES:
                if "double" in (left, right):
                    return "double"
                if "float" in (left, right):
                    return "float"
                if "long" in (left, right):
                    return "long"
                return "int"
            return None

        return None

    def check_assignment_type(self, target_type: str, expression: ASTNode, target_name: str, line: int):
        expr_type = self.infer_type(expression)
        if not expr_type or not target_type:
            return

        clean_target = target_type.replace("[]", "")
        clean_expr = expr_type.replace("[]", "")

        if clean_expr == clean_target:
            return

        # Promoções numéricas implícitas em Java (int -> long -> float -> double, char/byte/short -> int/long/float/double)
        if clean_target in FLOAT_TYPES and clean_expr in NUMERIC_TYPES:
            if clean_target == "float" and clean_expr == "double":
                # Permite literais float/double ou expressões numéricas compatíveis com float/double
                return
            return
        if clean_target in INTEGER_TYPES and clean_expr in INTEGER_TYPES:
            return
        if clean_expr == "null" and clean_target not in NUMERIC_TYPES and clean_target != "boolean":
            return

        self.errors.append(
            SemanticError(
                f"Incompatibilidade de tipos: não é possível atribuir {expr_type} a '{target_name}' do tipo {target_type}.",
                line,
            )
        )
