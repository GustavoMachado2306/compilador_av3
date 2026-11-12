import unittest
from src.main import analyze_source


class TestJava26SwitchExpressionTypesS85(unittest.TestCase):
    """Valida compatibilidade e unificação de tipos em switch expressions (JLS §15.28.1)."""

    def test_01_numeric_promotion_int_long_double_with_var(self):
        source = """
        class Sw {
            void m(int v) {
                var r1 = switch (v) {
                    case 1 -> 10;
                    case 2 -> 20L;
                    default -> 30;
                };
                long l = r1;

                var r2 = switch (v) {
                    case 1 -> 10;
                    default -> 2.5;
                };
                double d = r2;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_boxed_numeric_branches_unified_to_number(self):
        source = """
        class Sw {
            void m(int v) {
                Number resultado = switch (v) {
                    case 1 -> Integer.valueOf(10);
                    default -> Double.valueOf(20.5);
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_reference_and_null_branch_unification(self):
        source = """
        class Sw {
            void m(int v) {
                String s = switch (v) {
                    case 1 -> "ok";
                    default -> null;
                };
                var r = switch (v) {
                    case 1 -> "ok";
                    default -> null;
                };
                String t = r;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_incompatible_branches_in_var_not_assignable_to_int(self):
        bad = """
        class Sw {
            void m(int v) {
                var r = switch (v) {
                    case 1 -> 10;
                    default -> "texto";
                };
                int n = r;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_05_incompatible_branch_with_explicit_target_rejected(self):
        bad = """
        class Sw {
            void m(int v) {
                int r = switch (v) {
                    case 1 -> 10;
                    default -> "invalido";
                };
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_06_void_branch_in_switch_expression_rejected_with_and_without_target(self):
        bad_target = """
        class Sw {
            void ping() {}
            void m(int v) {
                Object o = switch (v) { default -> ping(); };
            }
        }
        """
        bad_var = """
        class Sw {
            void ping() {}
            void m(int v) {
                var o = switch (v) { default -> ping(); };
            }
        }
        """
        self.assertFalse(analyze_source(bad_target).success)
        self.assertFalse(analyze_source(bad_var).success)

    def test_07_all_throw_switch_expression_valid_for_target_type(self):
        source = """
        class Sw {
            int falhar(int v) {
                return switch (v) {
                    default -> throw new RuntimeException("erro");
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_08_switch_expression_as_method_argument_and_return(self):
        source = """
        class Sw {
            int dobrar(int x) { return x * 2; }
            int executar(int v) {
                return dobrar(switch (v) {
                    case 1 -> 5;
                    default -> 10;
                });
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

