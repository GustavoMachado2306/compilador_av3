import unittest
from src.main import analyze_source


class TestJava26S84Regressions(unittest.TestCase):
    """Regressões e integrações entre S8.4 e recursos de S6/S7/S8.1-S8.3."""

    def test_01_existing_s81_s82_s83_features_with_lambdas(self):
        source = """
        import java.util.function.*;
        class C {
            void m() {
                IntUnaryOperator calc = x -> (x + 2) * 3;
                IntFunction<int[]> alloc = int[]::new;
                int[] arr = alloc.apply(4);
                int len = arr.length;
                double d = 10.5;
                int v = (int) d;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_conditional_expression_with_lambdas_target_typed(self):
        source = """
        import java.util.function.IntUnaryOperator;
        class C {
            void m(boolean flag) {
                IntUnaryOperator op = flag ? (x -> x + 1) : (x -> x * 2);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_cast_expression_providing_target_type_for_lambda(self):
        source = """
        class C {
            void m() {
                Object o = (Runnable) () -> System.out.println("ok");
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_method_ref_on_bound_expr_does_not_require_effectively_final(self):
        source = """
        import java.util.function.Supplier;
        class C {
            void m() {
                String s = "java";
                s = "java26";
                Supplier<Integer> sup = s::length;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_void_compatible_expression_lambda_accepts_non_void_statement_expr(self):
        source = """
        class C {
            void m() {
                Runnable r = () -> "abc".length();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_06_lambda_block_with_local_var_and_switch_statement(self):
        source = """
        import java.util.function.IntUnaryOperator;
        class C {
            void m() {
                IntUnaryOperator op = x -> {
                    int base = 1;
                    return switch (x) {
                        case 0 -> base;
                        default -> x + base;
                    };
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

