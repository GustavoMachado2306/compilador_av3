<<<<<<< HEAD
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

=======
"""
Módulo do Analisador Semântico do Compilador Java (AV3).
Responsável pela validação de escopos, verificação de variáveis e membros declarados,
duplicidade de identificadores e compatibilidade básica de tipos.
Evita falsos erros para membros qualificados externos como System.out.println(...).
"""

from typing import List, Optional
from .ast_nodes import (
    ASTNode, CompilationUnit, ClassDeclaration, InterfaceDeclaration,
    EnumDeclaration, FieldDeclaration, MethodDeclaration, ConstructorDeclaration,
    Block, ReturnStatement, Declaration, LocalVariableDeclaration, Assignment,
    BinaryOp, UnaryOp, MethodCall, Literal, Identifier, ExpressionStatement,
    EmptyStatement, IfStatement, WhileStatement, DoWhileStatement,
    ForStatement, EnhancedForStatement, BreakStatement, ContinueStatement,
    ThrowStatement, AssertStatement, TryStatement, CatchClause,
    SynchronizedStatement, ConditionalExpression, MemberAccess, ArrayAccess,
    ObjectCreationExpression, ArrayInitializer, ArrayCreationExpression,
    CastExpression, InstanceOfExpression, LambdaExpression, MethodReference
)

>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a

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
<<<<<<< HEAD
    Analisador semântico recursivo que percorre classes, métodos, blocos,
    estruturas de controle (if/while/do-while/for/switch/try-catch-finally) e expressões completas.
=======
    Analisador semântico para Java (Fases A, B e C).
    Gerencia escopos hierárquicos e valida a consistência de tipos e símbolos,
    escopos locais em blocos/laços/métodos e previne falsos positivos para símbolos externos.
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
    """
    def __init__(self, symbol_table):
        self.symbols = symbol_table
        self.errors = []
        self._current_target_type = None

<<<<<<< HEAD
    def analyze(self, program: Program):
        self.errors = []
        self._current_target_type = None
        if not program or not hasattr(program, "statements"):
            return self.errors

        for stmt in program.statements:
            self.visit_statement(stmt)
=======
    def analyze(self, program: ASTNode) -> List[SemanticError]:
        """Executa a análise semântica sobre a árvore sintática."""
        self.errors = []
        if not program:
            return self.errors

        # 1. Se for uma Unidade de Compilação completa com classes/interfaces/enums
        if isinstance(program, CompilationUnit):
            # Analisa declarações de tipo
            for type_decl in program.type_declarations:
                if isinstance(type_decl, ClassDeclaration):
                    self.analyze_class(type_decl)
                elif isinstance(type_decl, InterfaceDeclaration):
                    self.symbols.declare(type_decl.name, "interface", type_decl.line, category="interface")
                elif isinstance(type_decl, EnumDeclaration):
                    self.symbols.declare(type_decl.name, "enum", type_decl.line, category="enum")
                    for const in type_decl.constants:
                        self.symbols.declare(const.name, type_decl.name, const.line, category="constante_enum")

        # 2. Analisa comandos didáticos de nível superior ou fragmentos
        statements = getattr(program, "statements", [])
        for stmt in statements:
            self.analyze_statement(stmt)

        return self.errors

    def analyze_class(self, cls_node: ClassDeclaration):
        """Registra a classe e seus membros (campos, métodos, construtores)."""
        prev = self.symbols.lookup(cls_node.name)
        if not self.symbols.declare(cls_node.name, "classe", cls_node.line, category="classe"):
            prev_line = f" (declarada na linha {prev['line']})" if prev and "line" in prev else ""
            self.errors.append(SemanticError(f"Classe '{cls_node.name}' declarada novamente{prev_line}.", cls_node.line))

        self.symbols.enter_scope()

        for member in cls_node.members:
            if isinstance(member, FieldDeclaration):
                prev_field = self.symbols.lookup(member.name)
                if not self.symbols.declare(member.name, member.type_ref.name, member.line, category="campo"):
                    self.errors.append(SemanticError(f"Campo '{member.name}' declarado novamente na classe.", member.line))
                if member.initializer is not None:
                    self.check_expression(member.initializer)

            elif isinstance(member, MethodDeclaration):
                self.symbols.declare(member.name, member.return_type.name, member.line, category="metodo")
                self.symbols.enter_scope()
                for p in member.parameters:
                    self.symbols.declare(p.name, p.type_ref.name, p.line, category="parametro")
                if member.body:
                    self.analyze_block(member.body)
                self.symbols.exit_scope()

            elif isinstance(member, ConstructorDeclaration):
                self.symbols.declare(member.name, member.name, member.line, category="construtor")
                self.symbols.enter_scope()
                for p in member.parameters:
                    self.symbols.declare(p.name, p.type_ref.name, p.line, category="parametro")
                if member.body:
                    self.analyze_block(member.body)
                self.symbols.exit_scope()

        self.symbols.exit_scope()

    def analyze_block(self, block_node: Block):
        """Analisa instruções dentro de um bloco de código com controle de escopo local."""
        if not block_node or not hasattr(block_node, "statements"):
            return
        self.symbols.enter_scope()
        for stmt in block_node.statements:
            self.analyze_statement(stmt)
        self.symbols.exit_scope()

    def analyze_statement(self, stmt: ASTNode):
        """Analisa uma declaração ou instrução isolada."""
        if isinstance(stmt, (Declaration, LocalVariableDeclaration)):
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
            if isinstance(stmt.target, ArrayAccess):
                self.check_expression(stmt.target)
                self.check_expression(stmt.expression)
            elif isinstance(stmt.target, MemberAccess) or stmt.name.startswith("this.") or "." in stmt.name:
                if stmt.target is not None:
                    self.check_expression(stmt.target)
                self.check_expression(stmt.expression)
            else:
                symbol = self.symbols.lookup(stmt.name)
                if symbol is None or symbol.get("category") not in ("variavel", "parametro", "campo"):
                    self.errors.append(
                        SemanticError(f"Variável '{stmt.name}' não foi declarada.", stmt.line)
                    )
                self.check_expression(stmt.expression)
                if symbol is not None and "type" in symbol:
                    self.check_assignment_type(symbol["type"], stmt.expression, stmt.name, stmt.line)
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a

        elif isinstance(stmt, ReturnStatement):
            if stmt.expression:
                self.check_expression(stmt.expression)

<<<<<<< HEAD
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
=======
        elif isinstance(stmt, IfStatement):
            self.check_expression(stmt.condition)
            self.analyze_statement(stmt.then_branch)
            if stmt.else_branch is not None:
                self.analyze_statement(stmt.else_branch)

        elif isinstance(stmt, WhileStatement):
            self.check_expression(stmt.condition)
            self.analyze_statement(stmt.body)

        elif isinstance(stmt, DoWhileStatement):
            self.analyze_statement(stmt.body)
            self.check_expression(stmt.condition)

        elif isinstance(stmt, ForStatement):
            self.symbols.enter_scope()
            if stmt.init is not None:
                self.analyze_statement(stmt.init)
            if stmt.condition is not None:
                self.check_expression(stmt.condition)
            if stmt.update is not None:
                self.check_expression(stmt.update)
            if stmt.body is not None:
                self.analyze_statement(stmt.body)
            self.symbols.exit_scope()

        elif isinstance(stmt, EnhancedForStatement):
            self.symbols.enter_scope()
            if hasattr(stmt.variable, "name"):
                t_name = getattr(stmt.variable, "type_name", "Object")
                self.symbols.declare(stmt.variable.name, t_name, stmt.line, category="variavel")
            self.check_expression(stmt.iterable)
            if stmt.body is not None:
                self.analyze_statement(stmt.body)
            self.symbols.exit_scope()

        elif isinstance(stmt, TryStatement):
            if stmt.resources:
                self.symbols.enter_scope()
                for res in stmt.resources:
                    self.analyze_statement(res)
            if stmt.body is not None:
                self.analyze_block(stmt.body)
            for catch_c in stmt.catches:
                self.symbols.enter_scope()
                self.symbols.declare(catch_c.parameter.name, catch_c.parameter.type_ref.name, catch_c.line, category="parametro")
                if catch_c.body is not None:
                    self.analyze_block(catch_c.body)
                self.symbols.exit_scope()
            if stmt.finally_block is not None:
                self.analyze_block(stmt.finally_block)
            if stmt.resources:
                self.symbols.exit_scope()

        elif isinstance(stmt, SynchronizedStatement):
            self.check_expression(stmt.lock)
            if stmt.body is not None:
                self.analyze_block(stmt.body)

        elif isinstance(stmt, ThrowStatement):
            self.check_expression(stmt.expression)

        elif isinstance(stmt, AssertStatement):
            self.check_expression(stmt.condition)
            if stmt.message is not None:
                self.check_expression(stmt.message)

        elif isinstance(stmt, ExpressionStatement):
            self.check_expression(stmt.expression)

        elif isinstance(stmt, Block):
            self.analyze_block(stmt)

        elif isinstance(stmt, (EmptyStatement, BreakStatement, ContinueStatement)):
            pass

    def check_expression(self, node: Optional[ASTNode]):
        """Verifica expressões, prevenindo falsos positivos para símbolos externos e métodos."""
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        if node is None:
            return

        if isinstance(node, Identifier):
<<<<<<< HEAD
            base_name = node.name.split(".")[0] if "." in node.name else node.name
            if base_name in BUILTIN_JAVA_OBJECTS or base_name in ("this", "super"):
                return
            symbol = self.symbols.lookup(base_name)
            if symbol is None or symbol.get("category") not in ("variavel", "parametro"):
=======
            # Identificadores com ponto (ex: System.out.println) ou 'this' não geram falso erro
            if node.name == "this" or node.name.startswith("this.") or "." in node.name:
                return
            symbol = self.symbols.lookup(node.name)
            if symbol is None or symbol.get("category") not in ("variavel", "parametro", "campo", "tipo"):
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
                line = getattr(node, "line", 1)
                self.errors.append(
                    SemanticError(f"Variável '{base_name}' não foi declarada.", line)
                )
<<<<<<< HEAD
=======
        elif isinstance(node, MethodCall):
            if node.target is not None:
                if isinstance(node.target, Identifier) and (node.target.name in ("this", "super") or node.target.name[0].isupper()):
                    pass
                else:
                    self.check_expression(node.target)
            for arg in node.arguments:
                self.check_expression(arg)

        elif isinstance(node, MemberAccess):
            if isinstance(node.target, Identifier) and (node.target.name in ("this", "super") or node.target.name[0].isupper()):
                pass
            else:
                self.check_expression(node.target)

        elif isinstance(node, MethodReference):
            if isinstance(node.target, Identifier) and (node.target.name in ("this", "super") or node.target.name[0].isupper()):
                pass
            else:
                self.check_expression(node.target)
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a

        elif isinstance(node, ArrayAccess):
            self.check_expression(node.array)
            self.check_expression(node.index)
<<<<<<< HEAD
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
=======

        elif isinstance(node, ConditionalExpression):
            self.check_expression(node.condition)
            self.check_expression(node.then_expr)
            self.check_expression(node.else_expr)

        elif isinstance(node, ObjectCreationExpression):
            for arg in node.arguments:
                self.check_expression(arg)

        elif isinstance(node, ArrayCreationExpression):
            for dim in node.dimensions:
                if dim is not None:
                    self.check_expression(dim)
            if node.initializer is not None:
                self.check_expression(node.initializer)

        elif isinstance(node, ArrayInitializer):
            for elem in node.elements:
                self.check_expression(elem)

        elif isinstance(node, CastExpression):
            self.check_expression(node.expression)

        elif isinstance(node, InstanceOfExpression):
            self.check_expression(node.expression)

        elif isinstance(node, LambdaExpression):
            self.symbols.enter_scope()
            for p in node.parameters:
                self.symbols.declare(p, "Object", getattr(node, "line", 1), category="parametro")
            if node.is_block_body and isinstance(node.body, Block):
                self.analyze_block(node.body)
            elif node.body is not None:
                self.check_expression(node.body)
            self.symbols.exit_scope()

        elif isinstance(node, Assignment):
            if node.target is not None and not isinstance(node.target, Identifier):
                self.check_expression(node.target)
            self.check_expression(node.expression)

        elif isinstance(node, UnaryOp):
            self.check_expression(node.operand)
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a

        elif isinstance(node, BinaryOp):
            self.check_expression(node.left)
            self.check_expression(node.right)
            # Apenas operações puramente aritméticas requerem checagem de tipo didática
            if node.op in ("+", "-", "*", "/", "%"):
                left_type = self.infer_type(node.left)
                right_type = self.infer_type(node.right)
                line = getattr(node, "line", 1)

<<<<<<< HEAD
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
=======
                # Regra didática oficial: String não deve participar de + ou - numéricos
                if left_type == "String" or right_type == "String":
                    self.errors.append(
                        SemanticError(
                            f"Operação aritmética '{node.op}' inválida: tipo 'String' não é suportado em operações aritméticas.",
                            line,
                        )
                    )
                else:
                    numeric_types = {"int", "double", "float", "long", "short", "byte"}
                    if (
                        left_type
                        and right_type
                        and left_type not in ("Object", "desconhecido")
                        and right_type not in ("Object", "desconhecido")
                        and not (left_type in numeric_types and right_type in numeric_types)
                    ):
                        self.errors.append(
                            SemanticError(
                                f"Operação aritmética '{node.op}' inválida entre tipos '{left_type}' e '{right_type}'.",
                                line,
                            )
                        )

    def is_assignable(self, target_type: str, source_type: str) -> bool:
        """
        Verifica compatibilidade de atribuição entre o tipo alvo e o da expressão,
        suportando as regras de promoção implícita (widening primitive conversion) do Java:
        byte -> short -> int -> long -> float -> double
        char -> int
        """
        if not target_type or not source_type:
            return True
        if target_type == source_type:
            return True
        widening_map = {
            "double": {"int", "float", "long", "short", "byte", "char"},
            "float": {"int", "long", "short", "byte", "char"},
            "long": {"int", "short", "byte", "char"},
            "int": {"short", "byte", "char"},
            "short": {"byte"},
        }
        if target_type in widening_map and source_type in widening_map[target_type]:
            return True
        if target_type in ("Object", "desconhecido") or source_type in ("Object", "desconhecido"):
            return True
        return False

    def infer_type(self, node: Optional[ASTNode]) -> Optional[str]:
        """Inferência simples de tipos para expressões primitivas com suporte a widening."""
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        if node is None:
            return None
        if isinstance(node, Literal):
            if node.kind == "STRING":
                return "String"
<<<<<<< HEAD
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
=======
            if node.kind == "BOOLEAN":
                return "boolean"
            if node.kind == "CHAR":
                return "char"
            if node.kind == "DOUBLE":
                return "double"
            if node.kind == "FLOAT":
                return "float"
            if node.kind in ("NUM", "INT"):
                val_str = str(node.value)
                # Hexadecimais inteiros (ex: 0x0F, 0xFF) são int e não devem ser
                # classificados como float apenas por terminarem em 'F'/'f' ou 'D'/'d'.
                if val_str.startswith(("0x", "0X")) and not any(c in val_str for c in ('p', 'P', '.')):
                    return "int"
                if "." in val_str or "e" in val_str.lower() or val_str.endswith(("f", "F", "d", "D")):
                    if val_str.endswith(("f", "F")):
                        return "float"
                    return "double"
                return "int"
            return "int"
        if isinstance(node, Identifier):
            symbol = self.symbols.lookup(node.name)
            return symbol["type"] if symbol and "type" in symbol else None
        if isinstance(node, InstanceOfExpression):
            return "boolean"
        if isinstance(node, CastExpression):
            return node.target_type.name if hasattr(node.target_type, "name") else str(node.target_type)
        if isinstance(node, ConditionalExpression):
            then_t = self.infer_type(node.then_expr)
            else_t = self.infer_type(node.else_expr)
            if then_t and else_t:
                if then_t == else_t:
                    return then_t
                if "double" in (then_t, else_t):
                    return "double"
                if "float" in (then_t, else_t):
                    return "float"
            return then_t if then_t else else_t
        if isinstance(node, UnaryOp):
            if node.op == "!":
                return "boolean"
            return self.infer_type(node.operand)
        if isinstance(node, BinaryOp):
            if node.op in ("&&", "||", "==", "!=", "<", ">", "<=", ">="):
                return "boolean"
            left = self.infer_type(node.left)
            right = self.infer_type(node.right)
            if left and right:
                # Promoção binária aritmética oficial do Java (widening)
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
                if "double" in (left, right):
                    return "double"
                if "float" in (left, right):
                    return "float"
                if "long" in (left, right):
                    return "long"
<<<<<<< HEAD
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
=======
                if left == "int" and right == "int":
                    return "int"
            return left or right or None
        return None

    def check_assignment_type(self, target_type: str, expression: ASTNode, target_name: str, line: int):
        """Verifica compatibilidade entre o tipo alvo e o da expressão com suporte a promoção por alargamento."""
        expr_type = self.infer_type(expression)
        if expr_type and not self.is_assignable(target_type, expr_type):
            self.errors.append(
                SemanticError(
                    f"Incompatibilidade de tipos: não é possível atribuir {expr_type} a '{target_name}' do tipo {target_type}.",
                    line,
                )
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
            )
        )
