"""
Suíte de Testes Automatizados - Fase D: Expressões Java, Precedência de Operadores e Chamadas Encadeadas.

Cobre obrigatoriamente os 29 cenários mínimos exigidos na Seção 8 do Prompt 11:
1. Precedência de multiplicação e adição
2. Associatividade de subtrações encadeadas
3. Atribuição encadeada
4. Operadores de comparação e igualdade
5. Operadores lógicos e bit a bit
6. Operadores de deslocamento
7. Operadores unários prefixados e pós-fixados
8. Parênteses e agrupamento
9. Expressões ternárias simples e aninhadas
10. Atribuições compostas
11. Chamadas encadeadas
12. Acesso a membros e arrays
13. Criação de objetos
14. Criação e inicialização de arrays
15. instanceof
16. Casts
17. Lambdas simples e com vários parâmetros
18. Lambdas com corpo em bloco
19. Referências a métodos e construtores
20. Expressões em condições de if e laços (incluindo for com ternário)
21. Expressões em inicializadores e retornos
22. Combinações de diferentes níveis de precedência
23. Parênteses, argumentos ou índices não fechados
24. Expressões ternárias incompletas
25. Atribuições malformadas
26. Operadores duplicados ou operandos ausentes
27. Integração com classes e métodos das fases anteriores
28. Integração com analyze_source(source)
29. Ausência de regressões nos testes anteriores
"""

import unittest
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.token import TokenType
from src.lexer import Lexer
from src.parser import Parser, SyntacticError
from src.ast_nodes import (
    CompilationUnit, ClassDeclaration, MethodDeclaration, Block,
    ReturnStatement, ExpressionStatement, IfStatement, WhileStatement,
    ForStatement, BinaryOp, UnaryOp, Assignment, Literal, Identifier,
    MethodCall, ConditionalExpression, MemberAccess, ArrayAccess,
    ObjectCreationExpression, ArrayInitializer, ArrayCreationExpression,
    CastExpression, InstanceOfExpression, LambdaExpression, MethodReference,
    LocalVariableDeclaration
)
from src.main import analyze_source


def parse_java(source: str) -> CompilationUnit:
    """Helper para analisar uma unidade de compilação Java completa."""
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


def parse_statement(statement_str: str):
    """Helper para analisar um comando ou declaração em modo isolado/didático."""
    tokens = Lexer(statement_str).tokenize()
    p = Parser(tokens)
    return p.statement()


def parse_expression(expr_str: str):
    """Helper para analisar uma expressão Java isolada."""
    tokens = Lexer(expr_str).tokenize()
    p = Parser(tokens)
    return p.expression()


class TestExpressoesJava(unittest.TestCase):
    """Bateria de testes da Fase D - Expressões Java, Precedência e Associatividade."""

    # -------------------------------------------------------------------------
    # 1. PRECEDÊNCIA DE MULTIPLICAÇÃO E ADIÇÃO
    # -------------------------------------------------------------------------
    def test_01_precedencia_multiplicacao_e_adicao(self):
        # a + b * c deve ter '+' na raiz e 'b * c' à direita
        node1 = parse_expression("a + b * c")
        self.assertIsInstance(node1, BinaryOp)
        self.assertEqual(node1.op, "+")
        self.assertIsInstance(node1.left, Identifier)
        self.assertEqual(node1.left.name, "a")
        self.assertIsInstance(node1.right, BinaryOp)
        self.assertEqual(node1.right.op, "*")
        self.assertEqual(node1.right.left.name, "b")
        self.assertEqual(node1.right.right.name, "c")

        # a * b + c deve ter '+' na raiz e 'a * b' à esquerda
        node2 = parse_expression("a * b + c")
        self.assertIsInstance(node2, BinaryOp)
        self.assertEqual(node2.op, "+")
        self.assertIsInstance(node2.left, BinaryOp)
        self.assertEqual(node2.left.op, "*")
        self.assertEqual(node2.left.left.name, "a")
        self.assertEqual(node2.left.right.name, "b")
        self.assertIsInstance(node2.right, Identifier)
        self.assertEqual(node2.right.name, "c")

    # -------------------------------------------------------------------------
    # 2. ASSOCIATIVIDADE DE SUBTRAÇÕES ENCADEADAS
    # -------------------------------------------------------------------------
    def test_02_associatividade_subtracao_esquerda(self):
        # a - b - c deve ser associativo à esquerda: ((a - b) - c)
        node = parse_expression("a - b - c")
        self.assertIsInstance(node, BinaryOp)
        self.assertEqual(node.op, "-")
        # Raiz tem 'c' à direita
        self.assertIsInstance(node.right, Identifier)
        self.assertEqual(node.right.name, "c")
        # Subárvore esquerda é (a - b)
        self.assertIsInstance(node.left, BinaryOp)
        self.assertEqual(node.left.op, "-")
        self.assertEqual(node.left.left.name, "a")
        self.assertEqual(node.left.right.name, "b")

    # -------------------------------------------------------------------------
    # 3. ATRIBUIÇÃO ENCADEADA
    # -------------------------------------------------------------------------
    def test_03_atribuicao_encadeada_direita(self):
        # a = b = c deve ser associativo à direita: a = (b = c)
        node = parse_statement("a = b = c;")
        self.assertIsInstance(node, Assignment)
        self.assertEqual(node.name, "a")
        self.assertEqual(node.operator, "=")
        self.assertIsInstance(node.expression, Assignment)
        self.assertEqual(node.expression.name, "b")
        self.assertEqual(node.expression.operator, "=")
        self.assertIsInstance(node.expression.expression, Identifier)
        self.assertEqual(node.expression.expression.name, "c")

    # -------------------------------------------------------------------------
    # 4. OPERADORES DE COMPARAÇÃO E IGUALDADE
    # -------------------------------------------------------------------------
    def test_04_operadores_comparacao_e_igualdade(self):
        # x >= 10 == y != 0
        # Comparações (>=) têm maior precedência que igualdade (==, !=)
        # Igualdade é associativa à esquerda: ((x >= 10) == y) != 0
        node = parse_expression("x >= 10 == y != 0")
        self.assertIsInstance(node, BinaryOp)
        self.assertEqual(node.op, "!=")
        self.assertIsInstance(node.right, Literal)
        self.assertEqual(node.right.value, "0")

        self.assertIsInstance(node.left, BinaryOp)
        self.assertEqual(node.left.op, "==")
        self.assertIsInstance(node.left.left, BinaryOp)
        self.assertEqual(node.left.left.op, ">=")
        self.assertEqual(node.left.left.left.name, "x")
        self.assertEqual(node.left.left.right.value, "10")
        self.assertIsInstance(node.left.right, Identifier)
        self.assertEqual(node.left.right.name, "y")

    # -------------------------------------------------------------------------
    # 5. OPERADORES LÓGICOS E BIT A BIT
    # -------------------------------------------------------------------------
    def test_05_operadores_logicos_e_bitwise(self):
        # Precedência: & > ^ > | > && > ||
        # a || b && c | d ^ e & f
        node = parse_expression("a || b && c | d ^ e & f")
        self.assertIsInstance(node, BinaryOp)
        self.assertEqual(node.op, "||")
        self.assertEqual(node.left.name, "a")

        and_node = node.right
        self.assertIsInstance(and_node, BinaryOp)
        self.assertEqual(and_node.op, "&&")
        self.assertEqual(and_node.left.name, "b")

        or_bit = and_node.right
        self.assertIsInstance(or_bit, BinaryOp)
        self.assertEqual(or_bit.op, "|")
        self.assertEqual(or_bit.left.name, "c")

        xor_bit = or_bit.right
        self.assertIsInstance(xor_bit, BinaryOp)
        self.assertEqual(xor_bit.op, "^")
        self.assertEqual(xor_bit.left.name, "d")

        and_bit = xor_bit.right
        self.assertIsInstance(and_bit, BinaryOp)
        self.assertEqual(and_bit.op, "&")
        self.assertEqual(and_bit.left.name, "e")
        self.assertEqual(and_bit.right.name, "f")

    # -------------------------------------------------------------------------
    # 6. OPERADORES DE DESLOCAMENTO
    # -------------------------------------------------------------------------
    def test_06_operadores_de_deslocamento(self):
        # valor << 2 + 1: Adição (+) tem maior precedência que shift (<<)
        # Deve estruturar: valor << (2 + 1)
        node = parse_expression("valor << 2 + 1")
        self.assertIsInstance(node, BinaryOp)
        self.assertEqual(node.op, "<<")
        self.assertEqual(node.left.name, "valor")
        self.assertIsInstance(node.right, BinaryOp)
        self.assertEqual(node.right.op, "+")
        self.assertEqual(node.right.left.value, "2")
        self.assertEqual(node.right.right.value, "1")

        # Shifts associativos à esquerda: a >> 1 >>> 2
        node2 = parse_expression("a >> 1 >>> 2")
        self.assertIsInstance(node2, BinaryOp)
        self.assertEqual(node2.op, ">>>")
        self.assertEqual(node2.right.value, "2")
        self.assertIsInstance(node2.left, BinaryOp)
        self.assertEqual(node2.left.op, ">>")

    # -------------------------------------------------------------------------
    # 7. OPERADORES UNÁRIOS PREFIXADOS E PÓS-FIXADOS
    # -------------------------------------------------------------------------
    def test_07_unarios_prefixados_e_posfixados(self):
        # ++contador (prefixo)
        pre_inc = parse_expression("++contador")
        self.assertIsInstance(pre_inc, UnaryOp)
        self.assertEqual(pre_inc.op, "++")
        self.assertFalse(pre_inc.is_postfix)
        self.assertEqual(pre_inc.operand.name, "contador")

        # contador++ (pós-fixo)
        pos_inc = parse_expression("contador++")
        self.assertIsInstance(pos_inc, UnaryOp)
        self.assertEqual(pos_inc.op, "++")
        self.assertTrue(pos_inc.is_postfix)

        # --contador e contador--
        self.assertFalse(parse_expression("--contador").is_postfix)
        self.assertTrue(parse_expression("contador--").is_postfix)

        # !ativo e ~mascara
        not_op = parse_expression("!ativo")
        self.assertIsInstance(not_op, UnaryOp)
        self.assertEqual(not_op.op, "!")
        self.assertFalse(not_op.is_postfix)

        bitnot_op = parse_expression("~mascara")
        self.assertIsInstance(bitnot_op, UnaryOp)
        self.assertEqual(bitnot_op.op, "~")

        # +a e -10
        pos_sign = parse_expression("+a")
        self.assertIsInstance(pos_sign, UnaryOp)
        self.assertEqual(pos_sign.op, "+")

        neg_sign = parse_expression("-10")
        self.assertIsInstance(neg_sign, UnaryOp)
        self.assertEqual(neg_sign.op, "-")
        self.assertEqual(neg_sign.operand.value, "10")

    # -------------------------------------------------------------------------
    # 8. PARÊNTESES E AGRUPAMENTO
    # -------------------------------------------------------------------------
    def test_08_parenteses_e_agrupamento(self):
        # (2 + 3) * 4 altera a ordem natural: '*' na raiz, '+' à esquerda
        node = parse_expression("(2 + 3) * 4")
        self.assertIsInstance(node, BinaryOp)
        self.assertEqual(node.op, "*")
        self.assertIsInstance(node.left, BinaryOp)
        self.assertEqual(node.left.op, "+")
        self.assertEqual(node.left.left.value, "2")
        self.assertEqual(node.left.right.value, "3")
        self.assertEqual(node.right.value, "4")

        # (x > 0) && (y > 0)
        node2 = parse_expression("(x > 0) && (y > 0)")
        self.assertIsInstance(node2, BinaryOp)
        self.assertEqual(node2.op, "&&")
        self.assertEqual(node2.left.op, ">")
        self.assertEqual(node2.right.op, ">")

    # -------------------------------------------------------------------------
    # 9. EXPRESSÕES TERNÁRIAS SIMPLES E ANINHADAS
    # -------------------------------------------------------------------------
    def test_09_expressoes_ternarias(self):
        # Simples: a > b ? a : b
        node = parse_expression("a > b ? a : b")
        self.assertIsInstance(node, ConditionalExpression)
        self.assertIsInstance(node.condition, BinaryOp)
        self.assertEqual(node.condition.op, ">")
        self.assertEqual(node.then_expr.name, "a")
        self.assertEqual(node.else_expr.name, "b")

        # Aninhada à direita: condicao ? valorA : outraCondicao ? valorB : valorC
        node2 = parse_expression("condicao ? valorA : outraCondicao ? valorB : valorC")
        self.assertIsInstance(node2, ConditionalExpression)
        self.assertEqual(node2.condition.name, "condicao")
        self.assertEqual(node2.then_expr.name, "valorA")
        self.assertIsInstance(node2.else_expr, ConditionalExpression)
        self.assertEqual(node2.else_expr.condition.name, "outraCondicao")
        self.assertEqual(node2.else_expr.then_expr.name, "valorB")
        self.assertEqual(node2.else_expr.else_expr.name, "valorC")

    # -------------------------------------------------------------------------
    # 10. ATRIBUIÇÕES COMPOSTAS
    # -------------------------------------------------------------------------
    def test_10_atribuicoes_compostas(self):
        # x += 10;
        stmt1 = parse_statement("x += 10;")
        self.assertIsInstance(stmt1, Assignment)
        self.assertEqual(stmt1.name, "x")
        self.assertEqual(stmt1.operator, "+=")
        self.assertEqual(stmt1.expression.value, "10")

        # y *= fator;
        stmt2 = parse_statement("y *= fator;")
        self.assertIsInstance(stmt2, Assignment)
        self.assertEqual(stmt2.name, "y")
        self.assertEqual(stmt2.operator, "*=")
        self.assertEqual(stmt2.expression.name, "fator")

    # -------------------------------------------------------------------------
    # 11. CHAMADAS ENCADEADAS
    # -------------------------------------------------------------------------
    def test_11_chamadas_encadeadas(self):
        # objeto.getEndereco().getCidade()
        call = parse_expression("objeto.getEndereco().getCidade()")
        self.assertIsInstance(call, MethodCall)
        self.assertEqual(call.method_name, "getCidade")
        self.assertIsInstance(call.target, MethodCall)
        self.assertEqual(call.target.method_name, "getEndereco")
        self.assertIsInstance(call.target.target, Identifier)
        self.assertEqual(call.target.target.name, "objeto")

        # lista.get(0).toString()
        call2 = parse_expression("lista.get(0).toString()")
        self.assertIsInstance(call2, MethodCall)
        self.assertEqual(call2.method_name, "toString")
        self.assertIsInstance(call2.target, MethodCall)
        self.assertEqual(call2.target.method_name, "get")
        self.assertEqual(len(call2.target.arguments), 1)
        self.assertEqual(call2.target.arguments[0].value, "0")

    # -------------------------------------------------------------------------
    # 12. ACESSO A MEMBROS E ARRAYS
    # -------------------------------------------------------------------------
    def test_12_acesso_a_membros_e_arrays(self):
        # matriz[i][j]
        arr = parse_expression("matriz[i][j]")
        self.assertIsInstance(arr, ArrayAccess)
        self.assertEqual(arr.index.name, "j")
        self.assertIsInstance(arr.array, ArrayAccess)
        self.assertEqual(arr.array.index.name, "i")
        self.assertEqual(arr.array.array.name, "matriz")

        # this.objeto.valor
        mem = parse_expression("this.objeto.valor")
        self.assertIsInstance(mem, MemberAccess)
        self.assertEqual(mem.member_name, "valor")
        self.assertIsInstance(mem.target, MemberAccess)
        self.assertEqual(mem.target.member_name, "objeto")
        self.assertEqual(mem.target.target.name, "this")

    # -------------------------------------------------------------------------
    # 13. CRIAÇÃO DE OBJETOS
    # -------------------------------------------------------------------------
    def test_13_criacao_de_objetos(self):
        # new Pessoa("Ana")
        obj = parse_expression("new Pessoa(\"Ana\")")
        self.assertIsInstance(obj, ObjectCreationExpression)
        self.assertEqual(obj.type_ref.name, "Pessoa")
        self.assertEqual(len(obj.arguments), 1)
        self.assertEqual(obj.arguments[0].value, "Ana")

    # -------------------------------------------------------------------------
    # 14. CRIAÇÃO E INICIALIZAÇÃO DE ARRAYS
    # -------------------------------------------------------------------------
    def test_14_criacao_e_inicializacao_de_arrays(self):
        # new int[10]
        arr_new = parse_expression("new int[10]")
        self.assertIsInstance(arr_new, ArrayCreationExpression)
        self.assertEqual(arr_new.type_ref.name, "int")
        self.assertEqual(len(arr_new.dimensions), 1)
        self.assertEqual(arr_new.dimensions[0].value, "10")

        # new String[2][3]
        arr_mat = parse_expression("new String[2][3]")
        self.assertIsInstance(arr_mat, ArrayCreationExpression)
        self.assertEqual(arr_mat.type_ref.name, "String")
        self.assertEqual(len(arr_mat.dimensions), 2)
        self.assertEqual(arr_mat.dimensions[0].value, "2")
        self.assertEqual(arr_mat.dimensions[1].value, "3")

        # Inicializador literal de array: {1, 2, 3}
        init = parse_expression("{1, 2, 3}")
        self.assertIsInstance(init, ArrayInitializer)
        self.assertEqual(len(init.elements), 3)

        # new int[] {1, 2}
        arr_init = parse_expression("new int[] {1, 2}")
        self.assertIsInstance(arr_init, ArrayCreationExpression)
        self.assertIsNone(arr_init.dimensions[0])
        self.assertIsNotNone(arr_init.initializer)
        self.assertEqual(len(arr_init.initializer.elements), 2)

    # -------------------------------------------------------------------------
    # 15. INSTANCEOF
    # -------------------------------------------------------------------------
    def test_15_instanceof(self):
        # objeto instanceof String
        node = parse_expression("objeto instanceof String")
        self.assertIsInstance(node, InstanceOfExpression)
        self.assertEqual(node.expression.name, "objeto")
        self.assertEqual(node.target_type.name, "String")

        # Integrado com if
        src = "public class T { void m() { if (objeto instanceof String) { System.out.println(1); } } }"
        unit = parse_java(src)
        if_node = unit.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(if_node.condition, InstanceOfExpression)

    # -------------------------------------------------------------------------
    # 16. CASTS
    # -------------------------------------------------------------------------
    def test_16_casts(self):
        # (int) valor
        c1 = parse_expression("(int) valor")
        self.assertIsInstance(c1, CastExpression)
        self.assertEqual(c1.target_type.name, "int")
        self.assertEqual(c1.expression.name, "valor")

        # (String) objeto
        c2 = parse_expression("(String) objeto")
        self.assertIsInstance(c2, CastExpression)
        self.assertEqual(c2.target_type.name, "String")
        self.assertEqual(c2.expression.name, "objeto")

        # (double) a / b: cast tem maior precedência que divisão
        # Raiz deve ser '/' com cast à esquerda
        c3 = parse_expression("(double) a / b")
        self.assertIsInstance(c3, BinaryOp)
        self.assertEqual(c3.op, "/")
        self.assertIsInstance(c3.left, CastExpression)
        self.assertEqual(c3.left.target_type.name, "double")
        self.assertEqual(c3.left.expression.name, "a")
        self.assertEqual(c3.right.name, "b")

        # Distinção de expressão parentizada: (a + b) não é cast!
        paren = parse_expression("(a + b)")
        self.assertIsInstance(paren, BinaryOp)
        self.assertEqual(paren.op, "+")

    # -------------------------------------------------------------------------
    # 17. LAMBDAS SIMPLES E COM VÁRIOS PARÂMETROS
    # -------------------------------------------------------------------------
    def test_17_lambdas_simples_e_multiplos_parametros(self):
        # x -> x * 2
        l1 = parse_expression("x -> x * 2")
        self.assertIsInstance(l1, LambdaExpression)
        self.assertEqual(l1.parameters, ["x"])
        self.assertFalse(l1.is_block_body)
        self.assertIsInstance(l1.body, BinaryOp)
        self.assertEqual(l1.body.op, "*")

        # (a, b) -> a + b
        l2 = parse_expression("(a, b) -> a + b")
        self.assertIsInstance(l2, LambdaExpression)
        self.assertEqual(l2.parameters, ["a", "b"])

        # () -> executar()
        l3 = parse_expression("() -> executar()")
        self.assertIsInstance(l3, LambdaExpression)
        self.assertEqual(len(l3.parameters), 0)
        self.assertIsInstance(l3.body, MethodCall)

    # -------------------------------------------------------------------------
    # 18. LAMBDAS COM CORPO EM BLOCO
    # -------------------------------------------------------------------------
    def test_18_lambdas_com_bloco(self):
        # x -> { return x + 1; }
        l = parse_expression("x -> { return x + 1; }")
        self.assertIsInstance(l, LambdaExpression)
        self.assertEqual(l.parameters, ["x"])
        self.assertTrue(l.is_block_body)
        self.assertIsInstance(l.body, Block)
        self.assertEqual(len(l.body.statements), 1)
        self.assertIsInstance(l.body.statements[0], ReturnStatement)

    # -------------------------------------------------------------------------
    # 19. REFERÊNCIAS A MÉTODOS E CONSTRUTORES
    # -------------------------------------------------------------------------
    def test_19_referencias_a_metodos(self):
        # System.out::println
        mr1 = parse_expression("System.out::println")
        self.assertIsInstance(mr1, MethodReference)
        self.assertEqual(mr1.method_name, "println")
        self.assertIsInstance(mr1.target, MemberAccess)
        self.assertEqual(mr1.target.member_name, "out")

        # String::valueOf
        mr2 = parse_expression("String::valueOf")
        self.assertIsInstance(mr2, MethodReference)
        self.assertEqual(mr2.method_name, "valueOf")
        self.assertEqual(mr2.target.name, "String")

        # String::new (referência a construtor)
        mr3 = parse_expression("String::new")
        self.assertIsInstance(mr3, MethodReference)
        self.assertEqual(mr3.method_name, "new")

        # objeto::executar
        mr4 = parse_expression("objeto::executar")
        self.assertIsInstance(mr4, MethodReference)
        self.assertEqual(mr4.method_name, "executar")

    # -------------------------------------------------------------------------
    # 20. EXPRESSÕES EM CONDIÇÕES DE IF E LAÇOS (INCLUINDO TERNÁRIO EM FOR)
    # -------------------------------------------------------------------------
    def test_20_expressoes_em_condicoes_e_for_com_ternario(self):
        src = (
            "public class Teste {\n"
            "    void fluxo() {\n"
            "        if (x > 0 && y != 0) {\n"
            "            contador++;\n"
            "        }\n"
            "        while (ativo || retryCount < 3) {\n"
            "            processar();\n"
            "        }\n"
            "        for (int i = cond ? 1 : 0; i < 10; i++) {\n"
            "            total += i;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(src)
        stmts = unit.type_declarations[0].members[0].body.statements
        self.assertEqual(len(stmts), 3)

        # 20.1 if com expressão lógica
        self.assertIsInstance(stmts[0], IfStatement)
        self.assertEqual(stmts[0].condition.op, "&&")

        # 20.2 while com expressão lógica
        self.assertIsInstance(stmts[1], WhileStatement)
        self.assertEqual(stmts[1].condition.op, "||")

        # 20.3 for tradicional cujo inicializador contém expressão ternária
        # ':' do ternário NÃO pode ser confundido com for aprimorado (for-each)
        for_stmt = stmts[2]
        self.assertIsInstance(for_stmt, ForStatement)
        self.assertIsInstance(for_stmt.init, LocalVariableDeclaration)
        self.assertIsInstance(for_stmt.init.initializer, ConditionalExpression)

    # -------------------------------------------------------------------------
    # 21. EXPRESSÕES EM INICIALIZADORES E RETORNOS
    # -------------------------------------------------------------------------
    def test_21_expressoes_em_inicializadores_e_retornos(self):
        src = (
            "public class Teste {\n"
            "    int calcular() {\n"
            "        int x = a + b * c;\n"
            "        return x > y ? x : y;\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(src)
        stmts = unit.type_declarations[0].members[0].body.statements
        decl = stmts[0]
        self.assertIsInstance(decl, LocalVariableDeclaration)
        self.assertEqual(decl.initializer.op, "+")

        ret = stmts[1]
        self.assertIsInstance(ret, ReturnStatement)
        self.assertIsInstance(ret.expression, ConditionalExpression)

    # -------------------------------------------------------------------------
    # 22. COMBINAÇÕES DE DIFERENTES NÍVEIS DE PRECEDÊNCIA
    # -------------------------------------------------------------------------
    def test_22_combinacao_complexa_de_precedencias(self):
        # a + b * c > d && !flag
        # Raiz: &&
        # Esquerda: (a + (b * c)) > d
        # Direita: !flag
        node = parse_expression("a + b * c > d && !flag")
        self.assertIsInstance(node, BinaryOp)
        self.assertEqual(node.op, "&&")

        # Lado esquerdo: >
        rel = node.left
        self.assertIsInstance(rel, BinaryOp)
        self.assertEqual(rel.op, ">")
        self.assertEqual(rel.right.name, "d")

        # Sub-esquerdo: +
        add = rel.left
        self.assertIsInstance(add, BinaryOp)
        self.assertEqual(add.op, "+")
        self.assertEqual(add.left.name, "a")
        self.assertEqual(add.right.op, "*")

        # Lado direito: !flag
        unary = node.right
        self.assertIsInstance(unary, UnaryOp)
        self.assertEqual(unary.op, "!")
        self.assertEqual(unary.operand.name, "flag")

    # -------------------------------------------------------------------------
    # 23. PARÊNTESES, ARGUMENTOS OU ÍNDICES NÃO FECHADOS (ERROS NEGATIVOS)
    # -------------------------------------------------------------------------
    def test_23_delimitadores_nao_fechados(self):
        # Parêntese não fechado na expressão
        with self.assertRaises(SyntacticError):
            parse_expression("(1 + 2")

        # Argumentos de chamada de método não fechados
        with self.assertRaises(SyntacticError):
            parse_expression("metodo(a, b")

        # Índice de array não fechado
        with self.assertRaises(SyntacticError):
            parse_expression("matriz[i")

    # -------------------------------------------------------------------------
    # 24. EXPRESSÕES TERNÁRIAS INCOMPLETAS (ERROS NEGATIVOS)
    # -------------------------------------------------------------------------
    def test_24_ternario_incompleto(self):
        # Faltando ':'
        with self.assertRaises(SyntacticError):
            parse_expression("condicao ? valorA")

        # Faltando ramo falso após ':'
        with self.assertRaises(SyntacticError):
            parse_expression("condicao ? valorA :")

    # -------------------------------------------------------------------------
    # 25. ATRIBUIÇÕES MALFORMADAS (ERROS NEGATIVOS)
    # -------------------------------------------------------------------------
    def test_25_atribuicoes_malformadas(self):
        # Operador de atribuição sem expressão à direita
        with self.assertRaises(SyntacticError):
            parse_statement("a += ;")

        # Atribuição sem expressão após '='
        with self.assertRaises(SyntacticError):
            parse_statement("x = ;")

    # -------------------------------------------------------------------------
    # 26. OPERADORES DUPLICADOS OU OPERANDOS AUSENTES (ERROS NEGATIVOS)
    # -------------------------------------------------------------------------
    def test_26_operadores_duplicados_ou_operandos_ausentes(self):
        # Operadores binários adjacentes inválidos: a + * b
        with self.assertRaises(SyntacticError):
            parse_expression("a + * b")

        # Operadores lógicos duplicados inválidos: a && || b
        with self.assertRaises(SyntacticError):
            parse_expression("a && || b")

        # Operador binário no fim sem operando: a +
        with self.assertRaises(SyntacticError):
            parse_expression("a +")

    # -------------------------------------------------------------------------
    # 27. INTEGRAÇÃO COM CLASSES E MÉTODOS DAS FASES ANTERIORES
    # -------------------------------------------------------------------------
    def test_27_integracao_classes_metodos_e_expressoes(self):
        source = (
            "package com.exemplo.calculo;\n"
            "import java.util.List;\n"
            "public class Calculadora {\n"
            "    private int total = 0;\n"
            "    public int processar(int[] valores, boolean dobro) {\n"
            "        for (int v : valores) {\n"
            "            this.total += dobro ? v * 2 : v;\n"
            "        }\n"
            "        return (int) this.total;\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        self.assertIsInstance(unit, CompilationUnit)
        self.assertEqual(unit.package_decl.name, "com.exemplo.calculo")
        self.assertEqual(len(unit.type_declarations), 1)

        cls = unit.type_declarations[0]
        self.assertEqual(cls.name, "Calculadora")
        self.assertEqual(len(cls.members), 2)

        method = cls.members[1]
        self.assertEqual(method.name, "processar")
        stmts = method.body.statements
        self.assertEqual(len(stmts), 2)

        # For-each contendo atribuição composta e ternário
        for_stmt = stmts[0]
        assign_stmt = for_stmt.body.statements[0]
        self.assertEqual(assign_stmt.operator, "+=")
        self.assertIsInstance(assign_stmt.expression, ConditionalExpression)

        # Return com cast
        ret_stmt = stmts[1]
        self.assertIsInstance(ret_stmt.expression, CastExpression)

    # -------------------------------------------------------------------------
    # 28. INTEGRAÇÃO COM analyze_source(source)
    # -------------------------------------------------------------------------
    def test_28_integracao_analyze_source_fase_d(self):
        source = (
            "public class ExpressoesDemo {\n"
            "    void demo() {\n"
            "        int a = 10;\n"
            "        int b = 20;\n"
            "        int c = a + b * 2;\n"
            "        boolean ok = c >= 50 && a != 0;\n"
            "        String status = ok ? \"sucesso\" : \"falha\";\n"
            "    }\n"
            "}\n"
        )
        res = analyze_source(source)
        self.assertTrue(res.success)
        self.assertFalse(res.has_errors)
        self.assertIsNotNone(res.ast)
        self.assertEqual(len(res.semantic_errors), 0)
        self.assertIn("ExpressoesDemo", res.ast.pretty())
        self.assertIn("ConditionalExpression", res.ast.pretty())

    # -------------------------------------------------------------------------
    # 29. AUSÊNCIA DE REGRESSÕES NOS TESTES ANTERIORES
    # -------------------------------------------------------------------------
    def test_29_ausencia_de_regressoes(self):
        # Fragmento didático da Etapa 2
        res1 = analyze_source("int x = 10;\nint y = x + 5;\n")
        self.assertTrue(res1.success)
        self.assertFalse(res1.has_errors)

        # Controle de fluxo da Fase C com laço for e try/catch
        res2 = analyze_source(
            "public class Teste {\n"
            "    void m() {\n"
            "        try {\n"
            "            for (int i = 0; i < 5; i++) { int y = i; }\n"
            "        } catch (Exception e) {\n"
            "            System.out.println(\"erro\");\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        self.assertTrue(res2.success)
        self.assertFalse(res2.has_errors)


if __name__ == "__main__":
    unittest.main()
