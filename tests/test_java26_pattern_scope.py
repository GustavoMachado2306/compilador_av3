"""
Suíte S7.4 — Flow-Sensitive Pattern Variable Scoping (JLS §6.3):
&&, ||, !, ?:, if/else com return/throw, while, for, do-while, break, lambdas e isolamento de tabela de símbolos.
"""

import unittest
from src.main import analyze_source


class TestJava26PatternScope(unittest.TestCase):
    """Testes rigorosos das regras de flow-scoping do JLS §6.3."""

    def test_01_escopo_em_and_negacao_or_e_condicional_ternario(self):
        source = """
        class Demo {
            int medir(Object obj) {
                boolean b = !(obj instanceof String s) || s.isEmpty();
                int len1 = obj instanceof String t ? t.length() : 0;
                int len2 = !(obj instanceof String u) ? 0 : u.length();
                if (obj instanceof String a && a.length() > 2 && obj instanceof CharSequence cs) {
                    return a.length() + cs.length();
                }
                return len1 + len2;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros inesperados: {res.semantic_errors}")

    def test_02_or_positivo_nao_expoe_variavel_no_ramo_direito_nem_no_then(self):
        bad_cases = [
            "void f(Object o) { if (o instanceof String s || s.isEmpty()) {} }",
            "void f(Object o) { if (o instanceof String s || false) { System.out.println(s); } }",
            "void f(Object o) { if (o instanceof String s) {} System.out.println(s); }",
            "void f(Object o) { int x = (o instanceof String s) ? 1 : s.length(); }",
            "void f(Object o) { int x = !(o instanceof String s) ? s.length() : 0; }",
        ]
        for code in bad_cases:
            with self.subTest(code=code):
                res = analyze_source(f"class Demo {{ {code} }}")
                self.assertFalse(res.success, msg=f"Uso fora de escopo JLS §6.3 deveria falhar: {code}")

    def test_03_if_com_abrupt_completion_return_throw_e_else(self):
        source = """
        class Demo {
            int comReturn(Object o) {
                if (!(o instanceof String s)) {
                    return -1;
                }
                int n = s.length();
                return n;
            }
            int comThrow(Object o) {
                if (!(o instanceof String s)) throw new RuntimeException();
                return s.length();
            }
            int comElseReturn(Object o) {
                if (o instanceof String s) {
                    System.out.println("ok");
                } else {
                    return 0;
                }
                return s.length();
            }
            void reutilizarQuandoIfCompletaNormalmente(Object o) {
                if (o instanceof String s) {
                    System.out.println(s);
                }
                String s = "nova";
                System.out.println(s);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros inesperados: {res.semantic_errors}")

    def test_04_redeclaracao_apos_early_return_falha_por_colisao(self):
        source = """
        class Demo {
            void f(Object o) {
                if (!(o instanceof String s)) {
                    return;
                }
                String s = "conflito";
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("declarada novamente" in str(e) for e in res.semantic_errors))

    def test_05_while_e_for_fluxo_com_e_sem_break(self):
        valid = """
        class Demo {
            Object proximo() { return null; }
            void testarWhile(Object o) {
                while (!(o instanceof String s)) {
                    o = proximo();
                }
                int n = s.length();
            }
            void testarFor(Object o) {
                for (; !(o instanceof String s); o = proximo()) {
                    System.out.println("aguardando");
                }
                System.out.println(s.length());
            }
            void testarForCondEUpdate(Object o) {
                for (; o instanceof String s && s.length() > 0; System.out.println(s)) {
                    break;
                }
            }
        }
        """
        res_ok = analyze_source(valid)
        self.assertTrue(res_ok.success, msg=f"Erros: {res_ok.semantic_errors}")

        invalid_with_break = """
        class Demo {
            boolean cond = true;
            void f(Object o) {
                while (!(o instanceof String s)) {
                    if (cond) break;
                }
                System.out.println(s.length());
            }
        }
        """
        res_bad = analyze_source(invalid_with_break)
        self.assertFalse(res_bad.success, msg="break no while impede introdução após laço (JLS §6.3.2.3)")

    def test_06_do_while_nao_expoe_variavel_da_condicao_no_corpo(self):
        invalid = """
        class Demo {
            void f(Object o) {
                do {
                    System.out.println(s);
                } while (!(o instanceof String s));
            }
        }
        """
        res = analyze_source(invalid)
        self.assertFalse(res.success)
        self.assertTrue(any("não foi declarada" in str(e) for e in res.semantic_errors))

    def test_07_final_mutabilidade_sombreado_e_tabela_de_simbolos_global(self):
        mutable_ok = """
        class Demo {
            void f(Object o) {
                if (o instanceof String s) {
                    s = "redefinida";
                }
            }
        }
        """
        self.assertTrue(analyze_source(mutable_ok).success)

        final_bad = """
        class Demo {
            void f(Object o) {
                if (o instanceof final String s) {
                    s = "proibido";
                }
            }
        }
        """
        self.assertFalse(analyze_source(final_bad).success)

        shadow_local_bad = """
        class Demo {
            void f(Object o) {
                String s = "externa";
                if (o instanceof String s) {}
            }
        }
        """
        self.assertFalse(analyze_source(shadow_local_bad).success)

        shadow_field_ok = """
        class Demo {
            String s = "campo";
            void f(Object o) {
                if (o instanceof String s) {
                    int n = s.length();
                }
            }
        }
        """
        res_field = analyze_source(shadow_field_ok)
        self.assertTrue(res_field.success, msg=f"Pattern pode sombrear campo da classe: {res_field.semantic_errors}")
        # Variável de pattern jamais deve vazar para a tabela global de símbolos
        self.assertIsNone(res_field.symbol_table.lookup("s"))

    def test_08_lambda_e_switch_isolam_escopos_de_pattern(self):
        source = """
        class Demo {
            void usar(Object o) {
                if (o instanceof String s) {
                    Runnable r = () -> System.out.println(s.length());
                }
                Runnable outra = () -> {
                    if (o instanceof String s) {
                        System.out.println(s);
                    }
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors}")

        leak_bad = """
        class Demo {
            void testar(Object o) {
                switch (o) {
                    case String s:
                        System.out.println(s);
                        break;
                    case Integer i:
                        System.out.println(s);
                        break;
                    default:
                        break;
                }
            }
        }
        """
        self.assertFalse(analyze_source(leak_bad).success)


if __name__ == "__main__":
    unittest.main()

