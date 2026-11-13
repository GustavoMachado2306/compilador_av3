"""
Suíte de Testes Automatizados para Etapa S6 — Laços de Repetição e Labels (JLS §14.7, §14.12–§14.16).
Cobre: while, do/while, for tradicional (múltiplas inicializações e atualizações, infinito),
enhanced for (explícito, var, underscore), loops aninhados, labeled statements/loops, break/continue
rotulados e não rotulados, e erros sintáticos/semânticos associados.
"""

import unittest
from src.main import analyze_source
from src.ast_nodes import (
    WhileStatement, DoWhileStatement, ForStatement, EnhancedForStatement,
    LabeledStatement, BreakStatement, ContinueStatement, StatementExpressionList,
    LocalVariableDeclaration
)


class TestJava26LoopsLabelsS6(unittest.TestCase):
    """Testes para while, do/while, for, for-each e instruções rotuladas (JLS §14)."""

    def test_01_while_e_do_while(self):
        source = """
        class Demo {
            void repetir(int limite) {
                int i = 0;
                while (i < limite) {
                    i++;
                }
                do {
                    i--;
                } while (i > 0);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[1], WhileStatement)
        self.assertIsInstance(stmts[2], DoWhileStatement)

    def test_02_for_basico_e_for_infinito(self):
        source = """
        class Demo {
            void contar() {
                for (int i = 0; i < 10; i++) {
                    if (i == 5) break;
                }
                for (;;) {
                    break;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0], ForStatement)
        self.assertIsInstance(stmts[0].init, LocalVariableDeclaration)
        self.assertIsNotNone(stmts[0].condition)
        self.assertIsNotNone(stmts[0].update)
        self.assertIsInstance(stmts[1], ForStatement)
        self.assertIsNone(stmts[1].init)
        self.assertIsNone(stmts[1].condition)
        self.assertIsNone(stmts[1].update)

    def test_03_for_com_inicializacao_e_atualizacoes_multiplas(self):
        source = """
        class Demo {
            void varrer() {
                int i;
                int j;
                for (i = 0, j = 10; i < j; i++, j--) {
                    continue;
                }
                for (int a = 1, b = 2; a < b; a++) {
                    a += 1;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        for1 = stmts[2]
        self.assertIsInstance(for1, ForStatement)
        self.assertIsInstance(for1.init, StatementExpressionList)
        self.assertEqual(len(for1.init_expressions), 2)
        self.assertIsInstance(for1.update, StatementExpressionList)
        self.assertEqual(len(for1.update_expressions), 2)
        for2 = stmts[3]
        self.assertIsInstance(for2.init, LocalVariableDeclaration)
        self.assertEqual([d.name for d in for2.init.declarators], ["a", "b"])

    def test_04_enhanced_for_com_tipo_var_e_underscore(self):
        source = """
        class Demo {
            void percorrer(String[] nomes, int[] itens) {
                for (String nome : nomes) {
                    String copia = nome;
                }
                for (var item : itens) {
                    int x = item;
                }
                for (var _ : itens) {
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0], EnhancedForStatement)
        self.assertEqual(stmts[0].variable.name, "nome")
        self.assertIsInstance(stmts[1], EnhancedForStatement)
        self.assertTrue(stmts[1].variable.is_var)
        self.assertEqual(stmts[1].variable.name, "item")
        self.assertIsInstance(stmts[2], EnhancedForStatement)
        self.assertEqual(stmts[2].variable.name, "_")

    def test_05_loops_aninhados_com_labels_break_e_continue(self):
        source = """
        class Demo {
            void buscar(int n) {
                externo:
                for (int i = 0; i < n; i++) {
                    for (int j = 0; j < n; j++) {
                        if (j == 2) {
                            continue externo;
                        }
                        if (i == 3) {
                            break externo;
                        }
                    }
                }
                bloco: {
                    if (n == 0) break bloco;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0], LabeledStatement)
        self.assertEqual(stmts[0].label, "externo")
        self.assertIsInstance(stmts[0].statement, ForStatement)
        self.assertIsInstance(stmts[1], LabeledStatement)
        self.assertEqual(stmts[1].label, "bloco")

    def test_06_labels_sequenciais_com_mesmo_nome_permitidos_e_aninhados_rejeitados(self):
        seq_ok = """
        class Demo {
            void ok(boolean cond) {
                laco: while (cond) {}
                laco: while (cond) {}
            }
        }
        """
        self.assertTrue(analyze_source(seq_ok).success)

        nested_bad = """
        class Demo {
            void bad(boolean cond) {
                laco: {
                    laco: while (cond) {}
                }
            }
        }
        """
        res = analyze_source(nested_bad)
        self.assertFalse(res.success)
        self.assertTrue(any("Label 'laco' declarado novamente" in e and e.line == 5 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_07_label_inexistente_e_continue_para_label_nao_iterativa(self):
        for kind, kw, body_line in [
            ("inexistente", "break fantasma;", 4),
            ("inexistente", "continue fantasma;", 4),
            ("nao_iterativa", "bloco: { continue bloco; }", 4),
        ]:
            with self.subTest(kind=kind, kw=kw):
                source = f"""
                class Demo {{
                    void m() {{
                        {kw}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success)
                self.assertIsNone(res.syntactic_error)
                self.assertTrue(any(e.line == body_line for e in res.semantic_errors), msg=res.semantic_errors)

    def test_08_break_e_continue_fora_de_contexto(self):
        for stmt_txt in ["break;", "continue;"]:
            with self.subTest(stmt_txt=stmt_txt):
                source = f"""
                class Demo {{
                    void m() {{
                        {stmt_txt}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success)
                self.assertTrue(any("fora de" in e and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_09_cabecalhos_invalidos_e_parenteses_nao_fechados(self):
        bad_headers = [
            "while () {}",
            "do {} while (true)",
            "for (int i = 0) {}",
            "for (int i = 0; i < 10; i++ {}",
            "for (int a, b : lista) {}",
        ]
        for bad in bad_headers:
            with self.subTest(bad=bad):
                source = f"""
                class Demo {{
                    void m(int[] lista) {{
                        {bad}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success, msg=f"Esperava erro sintático para: {bad}")
                self.assertIsNotNone(res.syntactic_error)


if __name__ == "__main__":
    unittest.main()

