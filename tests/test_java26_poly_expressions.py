import unittest
from src.main import analyze_source


class TestJava26PolyExpressionsS8(unittest.TestCase):
    """Valida poly expressions, target typing em múltiplos contextos e inferência genérica (JLS §15.2)."""

    def test_01_target_typing_in_var_decl_field_assignment_return_and_cast(self):
        source = """
        import java.util.function.Function;
        class Poly {
            Function<String, Integer> campo = s -> s.length();
            Function<Integer, Integer> produzir() {
                return x -> x + 1;
            }
            void run(Object obj) {
                Function<String, Integer> fn;
                fn = s -> s.length();
                var fCast = (Function<String, Integer>) (s -> s.length());
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_target_typing_in_method_invocation_argument(self):
        source = """
        interface Mapeador<A, B> { B mapear(A a); }
        class Pipe {
            int aplicar(String s, Mapeador<String, Integer> m) {
                return m.mapear(s);
            }
            void run() {
                int tamanho = aplicar("Compilador", s -> s.length());
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_target_typed_conditional_with_poly_lambdas(self):
        source = """
        import java.util.function.UnaryOperator;
        class CondPoly {
            void run(boolean dobrar) {
                UnaryOperator<Integer> op = dobrar ? x -> x * 2 : x -> x + 1;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_generic_method_return_type_inference_collections_emptyList(self):
        source = """
        import java.util.Collections;
        import java.util.List;
        class GenInf {
            void run() {
                List<String> vazia = Collections.emptyList();
                List<Integer> unitaria = Collections.singletonList(10);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_diamond_inference_in_return_and_assignment(self):
        source = """
        import java.util.ArrayList;
        import java.util.List;
        class Diam {
            List<String> criar() {
                return new ArrayList<>();
            }
            void run() {
                List<Integer> nums;
                nums = new ArrayList<>();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_06_var_rejects_lambda_method_ref_and_poly_conditional(self):
        bad_lambda = "class V { void f() { var x = a -> a; } }"
        bad_mref = "class V { void f() { var x = String::length; } }"
        bad_cond = "class V { void f(boolean c) { var x = c ? a -> a : b -> b; } }"
        self.assertFalse(analyze_source(bad_lambda).success)
        self.assertFalse(analyze_source(bad_mref).success)
        self.assertFalse(analyze_source(bad_cond).success)

    def test_07_lambda_assigned_to_object_rejected(self):
        source = """
        class Obj {
            void run() {
                Object o = (int a, int b) -> a + b;
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_08_return_type_mismatch_in_method_rejected(self):
        bad1 = """
        class Ret {
            int f() { return "errado"; }
        }
        """
        bad2 = """
        class Ret {
            int f() { return null; }
        }
        """
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_09_conditional_expression_non_boolean_condition_rejected(self):
        source = """
        class Cond {
            void run() {
                int r = 1 ? 10 : 20;
            }
        }
        """
        self.assertFalse(analyze_source(source).success)


if __name__ == "__main__":
    unittest.main()

