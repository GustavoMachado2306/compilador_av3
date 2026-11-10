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
    ForStatement, EnhancedForStatement, SwitchStatement, SwitchCase,
    BreakStatement, ContinueStatement, ThrowStatement, AssertStatement,
    TryStatement, CatchClause, SynchronizedStatement, ConditionalExpression,
    MemberAccess, ArrayAccess,
    ObjectCreationExpression, ArrayInitializer, ArrayCreationExpression,
    CastExpression, InstanceOfExpression, LambdaExpression, MethodReference
)


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
    Analisador semântico para Java (Fases A, B e C).
    Gerencia escopos hierárquicos e valida a consistência de tipos e símbolos,
    escopos locais em blocos/laços/métodos e previne falsos positivos para símbolos externos.
    """
    def __init__(self, symbol_table):
        self.symbols = symbol_table
        self.errors = []

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
                    self.check_assignment_type(
                        symbol["type"],
                        stmt.expression,
                        stmt.name,
                        stmt.line,
                        operator=getattr(stmt, "operator", "="),
                    )

        elif isinstance(stmt, ReturnStatement):
            if stmt.expression:
                self.check_expression(stmt.expression)

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

        elif isinstance(stmt, SwitchStatement):
            self.check_expression(stmt.expression)
            self.symbols.enter_scope()
            for case_clause in stmt.cases:
                if isinstance(case_clause, SwitchCase):
                    if case_clause.value is not None:
                        self.check_expression(case_clause.value)
                    for case_stmt in case_clause.statements:
                        self.analyze_statement(case_stmt)
            if stmt.default_block is not None:
                if isinstance(stmt.default_block, Block):
                    for def_stmt in stmt.default_block.statements:
                        self.analyze_statement(def_stmt)
                else:
                    self.analyze_statement(stmt.default_block)
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
        if node is None:
            return
        if isinstance(node, Identifier):
            # Identificadores com ponto (ex: System.out.println) ou 'this' não geram falso erro
            if node.name == "this" or node.name.startswith("this.") or "." in node.name:
                return
            symbol = self.symbols.lookup(node.name)
            if symbol is None or symbol.get("category") not in ("variavel", "parametro", "campo", "tipo"):
                line = getattr(node, "line", 1)
                self.errors.append(
                    SemanticError(f"Variável '{node.name}' não foi declarada.", line)
                )
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

        elif isinstance(node, ArrayAccess):
            self.check_expression(node.array)
            self.check_expression(node.index)

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
            elif node.name and "." not in node.name and not node.name.startswith("this."):
                symbol = self.symbols.lookup(node.name)
                if symbol is None or symbol.get("category") not in ("variavel", "parametro", "campo"):
                    self.errors.append(
                        SemanticError(f"Variável '{node.name}' não foi declarada.", getattr(node, "line", 1))
                    )
                elif "type" in symbol:
                    self.check_assignment_type(
                        symbol["type"],
                        node.expression,
                        node.name,
                        getattr(node, "line", 1),
                        operator=getattr(node, "operator", "="),
                    )
            self.check_expression(node.expression)

        elif isinstance(node, UnaryOp):
            self.check_expression(node.operand)

        elif isinstance(node, BinaryOp):
            self.check_expression(node.left)
            self.check_expression(node.right)
            if node.op in ("+", "-", "*", "/", "%"):
                left_type = self.infer_type(node.left)
                right_type = self.infer_type(node.right)
                line = getattr(node, "line", 1)

                # 1. Regra do Java para '+': se pelo menos um operando for String,
                #    trata-se de concatenação válida e o tipo resultante é String.
                if node.op == "+" and (left_type == "String" or right_type == "String"):
                    return

                # Demais operadores aritméticos (-, *, /, %) não suportam String
                if left_type == "String" or right_type == "String":
                    self.errors.append(
                        SemanticError(
                            f"Operação aritmética '{node.op}' inválida: tipo 'String' não é suportado em operações aritméticas.",
                            line,
                        )
                    )
                else:
                    numeric_types = {"int", "double", "float", "long", "short", "byte", "char"}
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
        if node is None:
            return None
        if isinstance(node, Literal):
            if node.kind == "STRING":
                return "String"
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
        if isinstance(node, Assignment):
            if node.name and "." not in node.name and not node.name.startswith("this."):
                symbol = self.symbols.lookup(node.name)
                if symbol and "type" in symbol:
                    return symbol["type"]
            return self.infer_type(node.expression)
        if isinstance(node, BinaryOp):
            if node.op in ("&&", "||", "==", "!=", "<", ">", "<=", ">="):
                return "boolean"
            left = self.infer_type(node.left)
            right = self.infer_type(node.right)
            if node.op == "+" and (left == "String" or right == "String"):
                return "String"
            if left and right:
                # Promoção binária aritmética oficial do Java (widening)
                if "double" in (left, right):
                    return "double"
                if "float" in (left, right):
                    return "float"
                if "long" in (left, right):
                    return "long"
                if left == "int" and right == "int":
                    return "int"
                numeric_int_types = {"int", "short", "byte", "char"}
                if left in numeric_int_types and right in numeric_int_types:
                    return "int"
            return left or right or None
        return None

    def check_assignment_type(
        self,
        target_type: str,
        expression: ASTNode,
        target_name: str,
        line: int,
        operator: str = "=",
    ):
        """
        Verifica compatibilidade entre o tipo alvo e o da expressão com suporte a
        promoção por alargamento e concatenação composta (+= quando o destino for String).
        """
        if operator == "+=" and target_type == "String":
            return

        if operator != "=" and target_type == "String":
            self.errors.append(
                SemanticError(
                    f"Operação aritmética '{operator}' inválida: tipo 'String' não é suportado em operações aritméticas.",
                    line,
                )
            )
            return

        expr_type = self.infer_type(expression)
        if expr_type and not self.is_assignable(target_type, expr_type):
            self.errors.append(
                SemanticError(
                    f"Incompatibilidade de tipos: não é possível atribuir {expr_type} a '{target_name}' do tipo {target_type}.",
                    line,
                )
            )
