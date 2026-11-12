import unittest
from src.main import analyze_source


class TestJava26SwitchExpressionsS85(unittest.TestCase):
    """Valida switch expressions (JLS §15.28): regras ->, grupos :, yield, exaustividade e separação de switch statement."""

    def test_01_arrow_switch_expression_single_and_multi_labels(self):
        source = """
        class Sw {
            String descrever(int dia) {
                return switch (dia) {
                    case 1, 2, 3 -> "Início";
                    case 4, 5 -> "Meio";
                    default -> "Fim";
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_colon_switch_expression_with_yield_and_fallthrough(self):
        source = """
        class Sw {
            int calcular(int valor) {
                int resultado = switch (valor) {
                    case 1:
                    case 2:
                        yield 10;
                    case 3:
                        yield 30;
                    default:
                        yield 0;
                };
                return resultado;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_arrow_block_with_yield_and_throw(self):
        source = """
        class Sw {
            int calcular(int x) {
                return switch (x) {
                    case 0 -> 0;
                    case 1 -> {
                        int y = x + 10;
                        yield y;
                    }
                    default -> throw new IllegalArgumentException("inválido");
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_exhaustive_enum_and_sealed_hierarchy_without_default(self):
        source = """
        enum Estado { ATIVO, INATIVO }
        sealed interface Forma permits Circulo, Quadrado {}
        final class Circulo implements Forma {}
        final class Quadrado implements Forma {}
        class Sw {
            int codigoEstado(Estado e) {
                return switch (e) {
                    case ATIVO -> 1;
                    case INATIVO -> 0;
                };
            }
            int lados(Forma f) {
                return switch (f) {
                    case Circulo c -> 0;
                    case Quadrado q -> 4;
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_pattern_matching_with_guard_and_null_case_in_switch_expr(self):
        source = """
        class Sw {
            int tamanho(Object obj) {
                return switch (obj) {
                    case null -> 0;
                    case String s when s.length() > 3 -> s.length();
                    case String s -> 1;
                    default -> -1;
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_06_non_exhaustive_switch_expression_rejected(self):
        bad_int = """
        class Sw {
            int f(int x) {
                return switch (x) {
                    case 1 -> 10;
                    case 2 -> 20;
                };
            }
        }
        """
        bad_enum = """
        enum Cor { A, B, C }
        class Sw {
            int f(Cor c) {
                return switch (c) {
                    case A -> 1;
                    case B -> 2;
                };
            }
        }
        """
        self.assertFalse(analyze_source(bad_int).success)
        self.assertFalse(analyze_source(bad_enum).success)

    def test_07_missing_yield_or_fallthrough_end_rejected(self):
        bad_block = """
        class Sw {
            int f(int x) {
                return switch (x) {
                    case 1 -> { int a = 1; }
                    default -> 0;
                };
            }
        }
        """
        bad_colon = """
        class Sw {
            int f(int x) {
                return switch (x) {
                    case 1:
                        yield 1;
                    default:
                        int b = 2;
                };
            }
        }
        """
        self.assertFalse(analyze_source(bad_block).success)
        self.assertFalse(analyze_source(bad_colon).success)

    def test_08_yield_outside_switch_expression_and_in_switch_statement_rejected(self):
        bad_method = """
        class Sw {
            void f() {
                yield 10;
            }
        }
        """
        bad_stmt = """
        class Sw {
            void f(int x) {
                switch (x) {
                    case 1:
                        yield 10;
                    default:
                        break;
                }
            }
        }
        """
        self.assertFalse(analyze_source(bad_method).success)
        self.assertFalse(analyze_source(bad_stmt).success)

    def test_09_break_and_return_inside_switch_expression_rejected(self):
        bad_break = """
        class Sw {
            int f(int x) {
                return switch (x) {
                    case 1 -> { break; }
                    default -> 0;
                };
            }
        }
        """
        bad_labeled_break = """
        class Sw {
            void f(int x) {
                laco: for (int i = 0; i < 2; i++) {
                    int r = switch (x) {
                        default -> { break laco; }
                    };
                }
            }
        }
        """
        bad_return = """
        class Sw {
            int f(int x) {
                int r = switch (x) {
                    default -> { return 1; }
                };
                return r;
            }
        }
        """
        self.assertFalse(analyze_source(bad_break).success)
        self.assertFalse(analyze_source(bad_labeled_break).success)
        self.assertFalse(analyze_source(bad_return).success)


if __name__ == "__main__":
    unittest.main()

