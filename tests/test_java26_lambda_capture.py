import unittest
from src.main import analyze_source


class TestJava26LambdaCaptureS84(unittest.TestCase):
    """Valida regras de captura de variáveis locais e parâmetros (final / efetivamente final, JLS §15.27.2)."""

    def test_01_capture_final_and_effectively_final_local_and_param(self):
        source = """
        import java.util.function.IntSupplier;
        class C {
            void m(int parametro) {
                final int fixo = 5;
                int efetivo = 10;
                IntSupplier s = () -> parametro + fixo + efetivo;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_capture_for_each_loop_variable_valid(self):
        source = """
        import java.util.List;
        class C {
            void m(List<String> itens) {
                for (String item : itens) {
                    Runnable r = () -> System.out.println(item);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_capture_standard_for_loop_mutated_var_rejected(self):
        source = """
        class C {
            void m() {
                for (int i = 0; i < 3; i++) {
                    Runnable r = () -> System.out.println(i);
                }
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_04_capture_reassigned_parameter_rejected(self):
        source = """
        class C {
            void m(int p) {
                p++;
                Runnable r = () -> System.out.println(p);
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_05_nested_lambda_capturing_outer_non_effectively_final_rejected(self):
        source = """
        import java.util.function.Supplier;
        class C {
            void m() {
                int x = 1;
                Supplier<Runnable> s = () -> () -> System.out.println(x);
                x = 2;
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_06_shadowed_lambda_parameter_does_not_conflict_with_outer_reassigned_var(self):
        source = """
        import java.util.function.IntUnaryOperator;
        class C {
            void m() {
                int x = 10;
                x = 20;
                IntUnaryOperator op = x1 -> x1 + 1;
            }
        }
        """
        self.assertTrue(analyze_source(source).success)


if __name__ == "__main__":
    unittest.main()

