"""
Suíte de Testes Automatizados para Etapa S6 — Expression Statements e Instruções de Controle (JLS §14.6–§14.10, §14.15–§14.21).
Cobre: StatementExpression válidas e rejeitadas, EmptyStatement, if/else/else-if, dangling else,
StatementNoShortIf, assert, throw, synchronized, return e yield.
"""

import unittest
from src.main import analyze_source
from src.compiler.ast_nodes import (
    Block, EmptyStatement, ExpressionStatement, Assignment, UnaryOp,
    MethodCall, ObjectCreationExpression, IfStatement, WhileStatement,
    AssertStatement, ThrowStatement, SynchronizedStatement, ReturnStatement,
    YieldStatement, SwitchExpression
)


class TestJava26ControlStatementsS6(unittest.TestCase):
    """Testes para StatementExpression, If, Dangling Else, Empty, Assert, Throw, Synchronized, Return e Yield."""

    def test_01_expression_statements_validas(self):
        source = """
        class Pessoa {}
        class Demo {
            void executar() {}
            void run() {
                int x = 0;
                x = 10;
                x += 2;
                ++x;
                x++;
                --x;
                x--;
                executar();
                new Pessoa();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[1].members[1].body.statements
        self.assertIsInstance(stmts[1], Assignment)
        self.assertEqual(stmts[1].name, "x")
        self.assertIsInstance(stmts[2], Assignment)
        self.assertEqual(stmts[2].operator, "+=")
        self.assertEqual(stmts[3].expression.op, "++")
        self.assertFalse(stmts[3].expression.is_postfix)
        self.assertEqual(stmts[4].expression.op, "++")
        self.assertTrue(stmts[4].expression.is_postfix)
        self.assertEqual(stmts[5].expression.op, "--")
        self.assertFalse(stmts[5].expression.is_postfix)
        self.assertEqual(stmts[6].expression.op, "--")
        self.assertTrue(stmts[6].expression.is_postfix)
        self.assertIsInstance(stmts[7].expression, MethodCall)
        self.assertIsInstance(stmts[8].expression, ObjectCreationExpression)

    def test_02_rejeicao_expressoes_isoladas_nao_statement_expression(self):
        invalid_exprs = [
            "a + b;",
            "a == b;",
            "flag ? 1 : 2;",
            "(int x) -> x + 1;",
            "x -> x + 1;",
            "a;",
        ]
        for expr_stmt in invalid_exprs:
            with self.subTest(expr_stmt=expr_stmt):
                source = f"""
                class Demo {{
                    void run(int a, int b, boolean flag) {{
                        {expr_stmt}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success, msg=f"Deveria rejeitar expression statement: {expr_stmt}")
                self.assertIsNotNone(res.syntactic_error)

    def test_03_if_simples_if_else_e_else_if(self):
        source = """
        class Demo {
            int classificar(int nota) {
                if (nota >= 9) {
                    return 3;
                } else if (nota >= 6) {
                    return 2;
                } else {
                    return 1;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        outer = res.ast.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(outer, IfStatement)
        self.assertIsInstance(outer.then_branch, Block)
        self.assertIsInstance(outer.else_branch, IfStatement)
        self.assertIsInstance(outer.else_branch.else_branch, Block)

    def test_04_dangling_else_associa_ao_if_mais_proximo(self):
        source = """
        class Demo {
            void executar() {}
            void cancelar() {}
            void run(boolean a, boolean b) {
                if (a)
                    if (b)
                        executar();
                    else
                        cancelar();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        outer_if = res.ast.type_declarations[0].members[2].body.statements[0]
        self.assertIsInstance(outer_if, IfStatement)
        self.assertIsNone(outer_if.else_branch)
        inner_if = outer_if.then_branch
        self.assertIsInstance(inner_if, IfStatement)
        self.assertEqual(inner_if.then_branch.expression.method_name, "executar")
        self.assertEqual(inner_if.else_branch.expression.method_name, "cancelar")

    def test_05_dangling_else_com_bloco_externo_associa_ao_if_externo(self):
        source = """
        class Demo {
            void executar() {}
            void finalizar() {}
            void run(boolean a, boolean b) {
                if (a) {
                    if (b)
                        executar();
                } else {
                    finalizar();
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        outer_if = res.ast.type_declarations[0].members[2].body.statements[0]
        self.assertIsInstance(outer_if.then_branch, Block)
        inner_if = outer_if.then_branch.statements[0]
        self.assertIsInstance(inner_if, IfStatement)
        self.assertIsNone(inner_if.else_branch)
        self.assertIsInstance(outer_if.else_branch, Block)
        self.assertEqual(outer_if.else_branch.statements[0].expression.method_name, "finalizar")

    def test_06_statement_no_short_if_valido_e_rejeicao_declaracao_direta_em_if(self):
        valid_src = """
        class Demo {
            void f() {}
            void g() {}
            void run(boolean a, boolean b) {
                if (a)
                    while (b)
                        f();
                else
                    g();
            }
        }
        """
        res_ok = analyze_source(valid_src)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)
        if_stmt = res_ok.ast.type_declarations[0].members[2].body.statements[0]
        self.assertIsInstance(if_stmt.then_branch, WhileStatement)
        self.assertIsInstance(if_stmt.else_branch, ExpressionStatement)

        invalid_src = """
        class Demo {
            void run(boolean a) {
                if (a) int x = 1;
            }
        }
        """
        res_bad = analyze_source(invalid_src)
        self.assertFalse(res_bad.success)
        self.assertIsNotNone(res_bad.syntactic_error)

    def test_07_empty_statement(self):
        source = """
        class Demo {
            void run(boolean ok) {
                ;
                if (ok) ;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0], EmptyStatement)
        self.assertIsInstance(stmts[1], IfStatement)
        self.assertIsInstance(stmts[1].then_branch, EmptyStatement)

    def test_08_assert_simples_e_com_mensagem(self):
        source = """
        class Demo {
            void validar(int x) {
                assert x > 0;
                assert x < 100 : "Valor fora da faixa";
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0], AssertStatement)
        self.assertIsNone(stmts[0].message)
        self.assertIsInstance(stmts[1], AssertStatement)
        self.assertIsNotNone(stmts[1].message)

    def test_09_throw_e_synchronized(self):
        source = """
        class Demo {
            void executar(Object lock, boolean falhar) {
                synchronized (lock) {
                    if (falhar) {
                        throw new RuntimeException("Falha");
                    }
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        sync_stmt = res.ast.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(sync_stmt, SynchronizedStatement)
        throw_stmt = sync_stmt.body.statements[0].then_branch.statements[0]
        self.assertIsInstance(throw_stmt, ThrowStatement)

    def test_10_synchronized_sem_bloco_rejeitado(self):
        source = """
        class Demo {
            void executar(Object lock) {
                synchronized (lock) ;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertIsNotNone(res.syntactic_error)

    def test_11_return_valido_e_yield_valido_em_switch_expression(self):
        source = """
        class Demo {
            int calcular() { return 7; }
            int obter(int opcao) {
                int valor = switch (opcao) {
                    case 1 -> 10;
                    default -> {
                        int resultado = calcular();
                        yield resultado;
                    }
                };
                return valor;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[1].body.statements
        sw_expr = stmts[0].initializer
        self.assertIsInstance(sw_expr, SwitchExpression)
        default_rule_block = sw_expr.switch_block.switch_rules[1].body
        self.assertIsInstance(default_rule_block.statements[1], YieldStatement)
        self.assertEqual(default_rule_block.statements[1].contextual_keyword, "yield")
        self.assertIsInstance(stmts[1], ReturnStatement)

    def test_12_yield_sem_alvo_rejeitado_semanticamente(self):
        source = """
        class Demo {
            int obter() {
                yield 10;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertIsNone(res.syntactic_error)
        self.assertTrue(any("yield" in e and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()
