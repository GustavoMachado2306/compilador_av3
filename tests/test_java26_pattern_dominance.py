"""
Suíte S7.6 — Regras de Dominância em Switch e Patterns (JLS §14.11.1 / §14.30.3).
"""

import unittest
from src.main import analyze_source


class TestJava26PatternDominance(unittest.TestCase):
    """Testes abrangentes de dominância entre patterns, guards, constantes, null e default."""

    def test_01_supertipo_domina_subtipo_e_record_pattern(self):
        bad_programs = [
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        case Object x -> {}
                        case String s -> {}
                    }
                }
            }
            """,
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        case CharSequence c -> {}
                        case String s -> {}
                        default -> {}
                    }
                }
            }
            """,
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        case Number n -> {}
                        case Integer i -> {}
                        default -> {}
                    }
                }
            }
            """,
            """
            record Ponto(Integer x, Integer y) {}
            class D {
                void f(Object o) {
                    switch (o) {
                        case Ponto p -> {}
                        case Ponto(Integer x, Integer y) -> {}
                        default -> {}
                    }
                }
            }
            """,
        ]
        for code in bad_programs:
            with self.subTest(code=code):
                res = analyze_source(code)
                self.assertFalse(res.success, msg=f"Deveria detectar dominância: {code}")
                self.assertTrue(any("dominado" in str(e).lower() for e in res.semantic_errors), msg=res.semantic_errors)

    def test_02_dominancia_recursiva_de_record_patterns(self):
        dom_nested = """
        record Caixa(Object item) {}
        class D {
            void f(Object o) {
                switch (o) {
                    case Caixa(Object v) -> {}
                    case Caixa(String s) -> {}
                    default -> {}
                }
            }
        }
        """
        res1 = analyze_source(dom_nested)
        self.assertFalse(res1.success)
        self.assertTrue(any("dominado" in str(e).lower() for e in res1.semantic_errors))

        dom_rec_to_type = """
        record Ponto(Integer x, Integer y) {}
        class D {
            void f(Object o) {
                switch (o) {
                    case Ponto(Integer x, Integer y) -> {}
                    case Ponto p -> {}
                    default -> {}
                }
            }
        }
        """
        res2 = analyze_source(dom_rec_to_type)
        self.assertFalse(res2.success, msg="Ponto(Integer x, Integer y) incondicional domina Ponto p (JLS §14.30.3)")
        self.assertTrue(any("dominado" in str(e).lower() for e in res2.semantic_errors))

        valid_guarded_rec = """
        record Ponto(Integer x, Integer y) {}
        class D {
            void f(Object o) {
                switch (o) {
                    case Ponto(Integer x, Integer y) when x > 0 -> {}
                    case Ponto p -> {}
                    default -> {}
                }
            }
        }
        """
        res3 = analyze_source(valid_guarded_rec)
        self.assertTrue(res3.success, msg=f"Com guard não constante não domina Ponto p: {res3.semantic_errors}")

    def test_03_guards_constantes_true_false_e_nao_constantes(self):
        non_const_valid = """
        class D {
            void f(Object o) {
                switch (o) {
                    case String s when s.length() > 5 -> {}
                    case String s -> {}
                    default -> {}
                }
            }
        }
        """
        self.assertTrue(analyze_source(non_const_valid).success)

        unguarded_dominates_guarded = """
        class D {
            void f(Object o) {
                switch (o) {
                    case String s -> {}
                    case String s2 when s2.length() > 5 -> {}
                    default -> {}
                }
            }
        }
        """
        self.assertFalse(analyze_source(unguarded_dominates_guarded).success)

        const_true_dominates = """
        class D {
            void f(Object o) {
                switch (o) {
                    case String s when 1 > 0 -> {}
                    case String s2 -> {}
                    default -> {}
                }
            }
        }
        """
        res_t = analyze_source(const_true_dominates)
        self.assertFalse(res_t.success)
        self.assertTrue(any("dominado" in str(e).lower() for e in res_t.semantic_errors))

        const_false_not_dominating = """
        class D {
            void f(Object o) {
                switch (o) {
                    case String s when false -> {}
                    case String s2 -> {}
                    default -> {}
                }
            }
        }
        """
        self.assertTrue(analyze_source(const_false_not_dominating).success)

    def test_04_pattern_domina_constante_mas_constante_antes_eh_valida(self):
        bad = """
        class D {
            void f(Object o) {
                switch (o) {
                    case String s -> {}
                    case "abc" -> {}
                    default -> {}
                }
            }
        }
        """
        res_bad = analyze_source(bad)
        self.assertFalse(res_bad.success)
        self.assertTrue(any("dominada" in str(e).lower() for e in res_bad.semantic_errors))

        bad_enum = """
        enum Cor { AZUL, VERDE }
        class D {
            void f(Cor c) {
                switch (c) {
                    case Cor x -> {}
                    case AZUL -> {}
                }
            }
        }
        """
        res_enum = analyze_source(bad_enum)
        self.assertFalse(res_enum.success)

        good = """
        class D {
            void f(Object o) {
                switch (o) {
                    case "abc" -> {}
                    case String s -> {}
                    default -> {}
                }
            }
        }
        """
        self.assertTrue(analyze_source(good).success)

    def test_05_ordenacao_default_case_null_e_compatibilidade_tradicional(self):
        invalid_orders = [
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        case Object x -> {}
                        default -> {}
                    }
                }
            }
            """,
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        case Object x -> {}
                        case null, default -> {}
                    }
                }
            }
            """,
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        default: break;
                        case String s: break;
                    }
                }
            }
            """,
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        default: break;
                        case null: break;
                    }
                }
            }
            """,
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        case null, default -> {}
                        case "ok" -> {}
                    }
                }
            }
            """,
        ]
        for code in invalid_orders:
            with self.subTest(code=code):
                res = analyze_source(code)
                self.assertFalse(res.success, msg=f"Ordenação inválida deveria falhar: {code}")

        # Case null DEPOIS de pattern incondicional Object x é válido!
        null_after_object_ok = """
        class D {
            void f(Object o) {
                switch (o) {
                    case Object x -> {}
                    case null -> {}
                }
            }
        }
        """
        self.assertTrue(analyze_source(null_after_object_ok).success)

        # Compatibilidade tradicional de switch com constantes: default antes de constante continua válido
        classic_compat = """
        class D {
            void f(int x) {
                switch (x) {
                    default: break;
                    case 1: break;
                    case 2: break;
                }
            }
        }
        """
        self.assertTrue(analyze_source(classic_compat).success)


if __name__ == "__main__":
    unittest.main()

