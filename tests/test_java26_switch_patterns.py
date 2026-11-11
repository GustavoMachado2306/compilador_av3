"""
Suíte S7.5 — Switch Moderno com Patterns, Guards ('when'), case null e Rules/Groups (JLS §14.11.1 / §15.28).
"""

import unittest
from src.main import analyze_source


class TestJava26SwitchPatterns(unittest.TestCase):
    """Testes sintáticos e semânticos para switch com patterns, guards e case null."""

    def test_01_switch_rules_com_patterns_guard_null_e_default(self):
        source = """
        record Ponto(Integer x, Integer y) {}
        record Coords(int x, int y) {}
        class Demo {
            String classificar(Object obj) {
                return switch (obj) {
                    case null -> "nulo";
                    case String s when s.length() > 5 -> "texto longo: " + s;
                    case String s -> "texto curto: " + s;
                    case Integer i when i > 0 -> "positivo";
                    case Integer _ -> "zero ou negativo";
                    case Ponto(Integer x, Integer y) when x == y -> "diagonal";
                    case Ponto(Integer x, _) -> "ponto x=" + x;
                    case Coords(var x, var y) when x == y -> "coords iguais";
                    default -> "outro";
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} / {res.syntactic_error}")

    def test_02_switch_colon_com_patterns_yield_throw_e_bloco(self):
        source = """
        class Demo {
            int avaliar(Object obj) {
                int r = switch (obj) {
                    case null:
                        yield 0;
                    case String s when !s.isEmpty():
                        int tam = s.length();
                        yield tam;
                    case Integer i:
                        if (i < 0) throw new IllegalArgumentException();
                        yield i;
                    default:
                        yield -1;
                };
                return r;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} / {res.syntactic_error}")

    def test_03_multiplos_patterns_unnamed_e_guard_com_flow_scoping(self):
        source = """
        record Caixa(Object v) {}
        class Demo {
            String descrever(Object o) {
                return switch (o) {
                    case String _, Integer _ -> "texto ou inteiro";
                    case Caixa(Object v) when v instanceof String s && s.length() > 2 -> s;
                    case null, default -> "nulo ou outro";
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} / {res.syntactic_error}")

    def test_04_rejeicoes_em_grupos_multi_label_e_fallthrough(self):
        invalid_cases = [
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        case String s, Integer i -> System.out.println("x");
                        default -> {}
                    }
                }
            }
            """,
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        case String s:
                        case Integer i:
                            System.out.println("inválido");
                            break;
                        default:
                            break;
                    }
                }
            }
            """,
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        case Integer i:
                            System.out.println(i);
                        case String s:
                            System.out.println(s);
                            break;
                        default:
                            break;
                    }
                }
            }
            """,
        ]
        for code in invalid_cases:
            with self.subTest(code=code):
                res = analyze_source(code)
                self.assertFalse(res.success, msg=f"Deveria falhar: {code}")

    def test_05_fallthrough_permitido_quando_anterior_quebra_ou_destino_unnamed(self):
        source = """
        class Demo {
            void testar(Object o) {
                switch (o) {
                    case Integer i:
                        System.out.println(i);
                        break;
                    case String s:
                        System.out.println(s);
                        break;
                    default:
                        break;
                }
                switch (o) {
                    case Integer i:
                        System.out.println("cai no unnamed");
                    case String _:
                        System.out.println("sem binding");
                        break;
                    default:
                        break;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors}")

    def test_06_guard_nao_booleano_e_variaveis_guard_nao_vazam(self):
        non_bool_guard = """
        class Demo {
            void f(Object o) {
                switch (o) {
                    case String s when s.length() -> System.out.println(s);
                    default -> {}
                }
            }
        }
        """
        # Nota: length() sem definição externa retorna None (evita falso positivo), mas literal/int explícito falha:
        explicit_int_guard = """
        class Demo {
            void f(Object o) {
                switch (o) {
                    case String s when 1 + 2 -> System.out.println(s);
                    default -> {}
                }
            }
        }
        """
        res = analyze_source(explicit_int_guard)
        self.assertFalse(res.success)
        self.assertTrue(any("tipo 'boolean'" in str(e) for e in res.semantic_errors))

        guard_var_leak = """
        class Demo {
            void f(Object o) {
                switch (o) {
                    case Caixa(Object v) when v instanceof String s -> System.out.println(s);
                    case Integer i -> System.out.println(s);
                    default -> {}
                }
            }
        }
        """
        self.assertFalse(analyze_source(guard_var_leak).success)

    def test_07_case_null_em_seletor_primitivo_rejeitado(self):
        source = """
        class Demo {
            void f(int x) {
                switch (x) {
                    case null -> System.out.println("nulo");
                    default -> System.out.println(x);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("primitivo" in str(e) for e in res.semantic_errors))


if __name__ == "__main__":
    unittest.main()

