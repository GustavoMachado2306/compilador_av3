import unittest
from src.main import analyze_source
from src.ast_nodes import LambdaExpression


class TestJava26LambdaExpressionsS8(unittest.TestCase):
    """Valida lambdas: formas de parâmetros, incompatibilidades, blocos vs expressões e captura efetivamente final (JLS §15.27)."""

    def test_01_zero_single_and_multi_inferred_lambdas(self):
        source = """
        import java.util.function.*;
        class Lam {
            void run() {
                Runnable r = () -> System.out.println("ok");
                Function<String, Integer> len = s -> s.length();
                BiFunction<Integer, Integer, Integer> soma = (a, b) -> a + b;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_explicit_typed_and_var_lambda_parameters(self):
        source = """
        import java.util.function.*;
        @interface NonNull {}
        class Lam {
            void run() {
                IntBinaryOperator soma = (int a, int b) -> a + b;
                BiFunction<Integer, Integer, Integer> mul = (Integer a, Integer b) -> a * b;
                BiFunction<String, String, String> juntar = (@NonNull final var a, var b) -> a + b;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[1].members[0].body.statements
        self.assertIsInstance(stmts[0].initializer, LambdaExpression)
        self.assertEqual(stmts[0].initializer.parameter_mode, "explicit")
        self.assertEqual(stmts[1].initializer.parameter_mode, "explicit")
        self.assertEqual(stmts[2].initializer.parameter_mode, "var")

        bad = """
        import java.util.function.*;
        class LamBad {
            void run() {
                BiFunction<Integer, Integer, Integer> soma = (int a, int b) -> a + b;
            }
        }
        """
        res_bad = analyze_source(bad)
        self.assertFalse(res_bad.success)

    def test_03_mixing_parameter_kinds_in_lambda_rejected(self):
        for bad in (
            "interface F { int f(int a, int b); } class C { void r() { F fn = (int a, b) -> a; } }",
            "interface F { int f(int a, int b); } class C { void r() { F fn = (var a, b) -> a; } }",
            "interface F { int f(int a, int b); } class C { void r() { F fn = (var a, int b) -> a; } }",
            "interface F { int f(int a); } class C { void r() { F fn = var x -> x; } }",
        ):
            self.assertFalse(analyze_source(bad).success, msg=f"Deveria falhar: {bad}")

    def test_04_effectively_final_capture_valid_and_post_mutation_rejected(self):
        ok_src = """
        interface Op { int get(); }
        class Cap {
            void run() {
                int base = 10;
                Op op = () -> base * 2;
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_after = """
        interface Op { int get(); }
        class Cap {
            void run() {
                int base = 10;
                Op op = () -> base * 2;
                base = 20;
            }
        }
        """
        self.assertFalse(analyze_source(bad_after).success)

        bad_before = """
        interface Op { int get(); }
        class Cap {
            void run() {
                int base = 10;
                base = 20;
                Op op = () -> base * 2;
            }
        }
        """
        self.assertFalse(analyze_source(bad_before).success)

    def test_05_lambda_mutating_captured_outer_variable_rejected(self):
        source = """
        class Cap {
            void run() {
                int acc = 0;
                Runnable r = () -> { acc++; };
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_06_block_lambda_value_return_and_void_compatibility(self):
        ok_src = """
        import java.util.function.Function;
        class Lam {
            void run() {
                Runnable r = () -> { return; };
                Function<Integer, Integer> f = x -> {
                    if (x > 0) return x;
                    return 0;
                };
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_void_val = """
        class Lam {
            void run() {
                Runnable r = () -> { return 42; };
            }
        }
        """
        bad_missing_val = """
        import java.util.function.Supplier;
        class Lam {
            void run() {
                Supplier<Integer> s = () -> { int a = 1; };
            }
        }
        """
        self.assertFalse(analyze_source(bad_void_val).success)
        self.assertFalse(analyze_source(bad_missing_val).success)

    def test_07_expression_lambda_void_statement_expr_vs_non_statement_expr(self):
        ok_src = """
        class Lam {
            int c = 0;
            void tocar() {}
            void run() {
                Runnable r1 = () -> tocar();
                Runnable r2 = () -> this.c++;
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_src = """
        class Lam {
            void run() {
                Runnable r = () -> 42;
            }
        }
        """
        self.assertFalse(analyze_source(bad_src).success)

    def test_08_lambda_arity_and_param_type_mismatch_rejected(self):
        bad_arity = """
        interface F { int f(int x, int y); }
        class Lam { void run() { F fn = x -> x; } }
        """
        bad_param_type = """
        interface F { int f(int x); }
        class Lam { void run() { F fn = (String s) -> s.length(); } }
        """
        self.assertFalse(analyze_source(bad_arity).success)
        self.assertFalse(analyze_source(bad_param_type).success)

    def test_09_unnamed_lambda_parameter_underscore_valid(self):
        source = """
        interface Par { int pegarSegundo(int a, int b); }
        class Lam {
            void run() {
                Par p = (_, b) -> b * 10;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_10_lambda_with_non_functional_target_rejected(self):
        source = """
        interface NaoFuncional { void a(); void b(); }
        class Lam {
            void run() {
                NaoFuncional nf = () -> {};
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_11_block_lambda_with_locals_if_else_and_loops(self):
        source = """
        import java.util.function.IntUnaryOperator;
        class Lam {
            void run() {
                IntUnaryOperator somaAte = n -> {
                    int acc = 0;
                    for (int i = 1; i <= n; i++) {
                        acc += i;
                    }
                    if (acc < 0) {
                        return 0;
                    } else {
                        return acc;
                    }
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_12_block_lambda_partial_return_path_rejected(self):
        source = """
        import java.util.function.Function;
        class Lam {
            void run() {
                Function<Integer, Integer> f = x -> {
                    if (x > 0) return x;
                };
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_13_block_lambda_incompatible_return_type_rejected(self):
        source = """
        import java.util.function.Function;
        class Lam {
            void run() {
                Function<Integer, Integer> f = x -> {
                    return "incompativel";
                };
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_14_explicit_generic_lambda_parameter_mismatch_rejected(self):
        source = """
        import java.util.List;
        import java.util.function.Function;
        class Lam {
            void run() {
                Function<List<String>, Integer> f = (List<Integer> xs) -> xs.size();
            }
        }
        """
        self.assertFalse(analyze_source(source).success)


if __name__ == "__main__":
    unittest.main()
