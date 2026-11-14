"""
Suíte de Testes Automatizados para Etapa S6 — Switch Statements e Yield Contextual (JLS §14.11, §14.21).
Cobre: switch tradicional (:), fall-through, múltiplas constantes em case, default, switch rules (->) com expressão/bloco/throw,
case null / case null, default, duplicidades, exaustividade (clássico vs enhanced), rejeição de patterns S7,
e uso contextual da palavra-chave 'yield'.
"""

import unittest
from src.main import analyze_source
from src.compiler.ast_nodes import (
    SwitchStatement, SwitchBlock, SwitchBlockStatementGroup, SwitchRule,
    CaseLabel, DefaultLabel, CaseConstantList, SwitchExpression, YieldStatement,
    Block, ThrowStatement
)


class TestJava26SwitchStatementsS6(unittest.TestCase):
    """Testes sintáticos e semânticos para SwitchStatement (JLS §14.11) na Etapa S6."""

    def test_01_switch_tradicional_fallthrough_multi_constante_e_default(self):
        source = """
        class Demo {
            void executar() {}
            void cancelar() {}
            void finalizar() {}
            void processar(int opcao) {
                switch (opcao) {
                    case 1:
                        executar();
                        break;
                    case 2:
                    case 3:
                        cancelar();
                        break;
                    case 4, 5:
                        executar();
                        break;
                    default:
                        finalizar();
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        sw = res.ast.type_declarations[0].members[3].body.statements[0]
        self.assertIsInstance(sw, SwitchStatement)
        sb = sw.switch_block
        self.assertIsInstance(sb, SwitchBlock)
        self.assertFalse(sb.is_rule_based)
        self.assertEqual(len(sb.statement_groups), 4)
        self.assertIsInstance(sb.statement_groups[0], SwitchBlockStatementGroup)
        self.assertEqual(len(sb.statement_groups[1].labels), 2)
        self.assertEqual(len(sb.statement_groups[2].labels[0].constants), 2)
        self.assertIsInstance(sb.statement_groups[2].labels[0].constant_list, CaseConstantList)
        self.assertIsInstance(sb.statement_groups[3].labels[0], DefaultLabel)

    def test_02_switch_rules_com_seta_bloco_e_throw(self):
        source = """
        class Demo {
            void executar() {}
            void cancelar() {}
            void preparar() {}
            void finalizar() {}
            void processar(int opcao) {
                switch (opcao) {
                    case 1 -> executar();
                    case 2, 3 -> {
                        preparar();
                        cancelar();
                    }
                    case 9 -> throw new IllegalArgumentException("Invalido");
                    default -> finalizar();
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        sb = res.ast.type_declarations[0].members[4].body.statements[0].switch_block
        self.assertTrue(sb.is_rule_based)
        self.assertEqual(len(sb.switch_rules), 4)
        r0, r1, r2, r3 = sb.switch_rules
        self.assertIsInstance(r0, SwitchRule)
        self.assertTrue(r0.is_expression)
        self.assertTrue(r1.is_block)
        self.assertIsInstance(r1.body, Block)
        self.assertTrue(r2.is_throw)
        self.assertIsInstance(r2.body, ThrowStatement)
        self.assertIsInstance(r3.labels[0], DefaultLabel)

    def test_03_switch_com_case_null_e_case_null_default(self):
        source = """
        class Demo {
            void tratarNulo() {}
            void tratarValor() {}
            void run(Object objeto) {
                switch (objeto) {
                    case null -> tratarNulo();
                    default -> tratarValor();
                }
                switch (objeto) {
                    case "A" -> tratarValor();
                    case null, default -> tratarNulo();
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[2].body.statements
        lbl_null = stmts[0].switch_block.switch_rules[0].labels[0]
        self.assertIsInstance(lbl_null, CaseLabel)
        self.assertTrue(lbl_null.is_null)
        self.assertFalse(lbl_null.has_default)
        lbl_combo = stmts[1].switch_block.switch_rules[1].labels[0]
        self.assertTrue(lbl_combo.is_null)
        self.assertTrue(lbl_combo.has_default)

    def test_04_yield_como_identificador_contextual_fora_de_switch_expression(self):
        source = """
        class Demo {
            int yield() { return 5; }
            int testar() {
                int yield = 10;
                yield = yield + 1;
                yield += yield();
                return yield;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_switch_expression_contextualiza_yield_sem_permitir_return(self):
        ok_src = """
        class Demo {
            int calcular() { return 3; }
            int testar(int opcao) {
                return switch (opcao) {
                    case 1 -> 10;
                    case 2 -> {
                        int r = calcular();
                        yield r;
                    }
                    default -> 0;
                };
            }
        }
        """
        res_ok = analyze_source(ok_src)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        bad_return = """
        class Demo {
            int testar(int opcao) {
                int v = switch (opcao) {
                    default -> {
                        return 1;
                    }
                };
                return v;
            }
        }
        """
        res_bad = analyze_source(bad_return)
        self.assertFalse(res_bad.success)
        self.assertTrue(any("return" in e and "switch expression" in e for e in res_bad.semantic_errors), msg=res_bad.semantic_errors)

    def test_06_patterns_e_guards_s7_e_fronteira_match_all(self):
        # Na S7, os patterns de switch tornam-se válidos enquanto labels malformados ou 'case _' isolado permanecem inválidos.
        valid_s7_cases = [
            "case String s -> executar();",
            "case Integer i when i > 0 -> executar();",
            "case Ponto(Integer x, Integer y) -> executar();",
            "case Coords(var x, var y) -> executar();",
        ]
        for label_rule in valid_s7_cases:
            with self.subTest(valid_label=label_rule):
                source = f"""
                record Ponto(Integer x, Integer y) {{}}
                record Coords(int x, int y) {{}}
                class Demo {{
                    void executar() {{}}
                    void testar(Object obj) {{
                        switch (obj) {{
                            {label_rule}
                            default -> executar();
                        }}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertTrue(res.success, msg=f"S7 deve aceitar pattern em switch: {res.semantic_errors} / {res.syntactic_error}")

        invalid_cases = [
            "case _ -> executar();",
            "case Integer i when -> executar();",
            "case var v -> executar();",
        ]
        for bad_rule in invalid_cases:
            with self.subTest(bad_label=bad_rule):
                source = f"""
                class Demo {{
                    void executar() {{}}
                    void testar(Object obj) {{
                        switch (obj) {{
                            {bad_rule}
                            default -> executar();
                        }}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success, msg=f"Switch label inválido deveria falhar: {bad_rule}")

    def test_07_erros_sintaticos_rhs_invalida_labels_malformados_e_switch_incompleto(self):
        bad_switches = [
            "switch (x) { case 1 -> 10; }",
            "switch (x) { case 1 -> a + b; }",
            "switch (x) { case : break; }",
            "switch (x) { case , 1 -> executar(); }",
            "switch (x) { case 1:",
        ]
        for bad in bad_switches:
            with self.subTest(bad=bad):
                source = f"""
                class Demo {{
                    void executar() {{}}
                    void testar(int x, int a, int b) {{
                        {bad}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success, msg=f"Esperava erro sintático: {bad}")
                self.assertIsNotNone(res.syntactic_error)

    def test_08_duplicidade_case_default_null_e_exaustividade(self):
        dup_case = """
        class Demo {
            void executar() {}
            void testar(int x) {
                switch (x) {
                    case 1:
                        executar();
                        break;
                    case 1:
                        executar();
                        break;
                }
            }
        }
        """
        res_dup = analyze_source(dup_case)
        self.assertFalse(res_dup.success)
        self.assertTrue(any("duplicada" in e and e.line == 9 for e in res_dup.semantic_errors), msg=res_dup.semantic_errors)

        dup_def = """
        class Demo {
            void executar() {}
            void testar(int x) {
                switch (x) {
                    default -> executar();
                    default -> executar();
                }
            }
        }
        """
        res_def = analyze_source(dup_def)
        self.assertFalse(res_def.success)
        self.assertTrue(any("Múltiplos labels 'default'" in e for e in res_def.semantic_errors), msg=res_def.semantic_errors)

        non_exhaustive_null = """
        class Demo {
            void tratarNulo() {}
            void testar(Object o) {
                switch (o) {
                    case null -> tratarNulo();
                }
            }
        }
        """
        res_enh = analyze_source(non_exhaustive_null)
        self.assertFalse(res_enh.success)
        self.assertTrue(any("exaustividade" in e for e in res_enh.semantic_errors), msg=res_enh.semantic_errors)

    def test_09_case_com_variavel_nao_constante_rejeitado_semanticamente(self):
        source = """
        class Demo {
            void executar() {}
            void testar(int x) {
                int dinamico = 1;
                switch (x) {
                    case dinamico:
                        executar();
                        break;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("constante" in e and e.line == 7 for e in res.semantic_errors), msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

