import unittest
from src.main import analyze_source


class TestJava26SwitchExpressionTypingS8(unittest.TestCase):
    """Valida switch expressions: regras ->, blocos com yield, unificação de tipos e exaustividade (JLS §15.28)."""

    def test_01_arrow_switch_expression_and_var_unification(self):
        source = """
        class Sw {
            void run(int dia) {
                var rotulo = switch (dia) {
                    case 1, 7 -> "fim de semana";
                    default -> "util";
                };
                String msg = rotulo.toUpperCase();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_arrow_block_with_yield_and_throw(self):
        source = """
        class Sw {
            int calcular(int x) {
                return switch (x) {
                    case 0 -> 0;
                    case 1 -> {
                        int dobro = x * 2;
                        yield dobro;
                    }
                    default -> throw new IllegalArgumentException("invalido");
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_colon_groups_with_fallthrough_and_yield(self):
        source = """
        class Sw {
            int mapear(String op) {
                return switch (op) {
                    case "ADD":
                    case "SUM":
                        yield 1;
                    case "SUB":
                        yield 2;
                    default:
                        yield 0;
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_nested_switch_expressions_and_target_typed_lambdas(self):
        source = """
        import java.util.function.IntUnaryOperator;
        class Sw {
            void run(int modo, int sub) {
                IntUnaryOperator op = switch (modo) {
                    case 1 -> switch (sub) {
                        case 0 -> x -> x + 1;
                        default -> x -> x + 2;
                    };
                    default -> x -> x * 10;
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_switch_expression_branch_incompatible_with_target_rejected(self):
        source = """
        class Sw {
            void run(int k) {
                int r = switch (k) {
                    case 1 -> 10;
                    default -> "texto";
                };
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_06_switch_expression_block_without_yield_or_throw_rejected(self):
        bad_arrow_block = """
        class Sw {
            int f(int k) {
                return switch (k) {
                    case 1 -> { int a = 1; }
                    default -> 0;
                };
            }
        }
        """
        bad_colon_group = """
        class Sw {
            int f(int k) {
                return switch (k) {
                    case 1:
                        yield 1;
                    default:
                        int x = 2;
                };
            }
        }
        """
        self.assertFalse(analyze_source(bad_arrow_block).success)
        self.assertFalse(analyze_source(bad_colon_group).success)

    def test_07_return_inside_switch_expression_and_yield_outside_rejected(self):
        bad_ret = """
        class Sw {
            int f(int k) {
                int x = switch (k) {
                    default -> { return 1; }
                };
                return x;
            }
        }
        """
        bad_yield = """
        class Sw {
            void f() {
                yield 10;
            }
        }
        """
        self.assertFalse(analyze_source(bad_ret).success)
        self.assertFalse(analyze_source(bad_yield).success)

    def test_08_switch_expression_exhaustive_enum_without_default(self):
        source = """
        enum Semaforo { VERDE, AMARELO, VERMELHO }
        class Sw {
            String descrever(Semaforo s) {
                return switch (s) {
                    case VERDE -> "siga";
                    case AMARELO -> "atencao";
                    case VERMELHO -> "pare";
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_09_switch_expression_non_exhaustive_rejected(self):
        source = """
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
        self.assertFalse(analyze_source(source).success)


if __name__ == "__main__":
    unittest.main()

