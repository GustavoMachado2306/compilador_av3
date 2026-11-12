import unittest
from src.main import analyze_source


class TestJava26LambdaTypingS84(unittest.TestCase):
    """Valida target typing de expressões lambda em declarações, retornos, argumentos e sobrecargas."""

    def test_01_target_typing_in_variable_declaration_and_assignment(self):
        source = """
        interface Operacao { int executar(int a, int b); }
        class C {
            void m() {
                Operacao op = (a, b) -> a + b;
                op = (a, b) -> a * b;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_target_typing_in_method_return_statement(self):
        source = """
        import java.util.function.Function;
        class C {
            Function<String, Integer> criarTamanho() {
                return texto -> texto.length();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_target_typing_in_method_and_constructor_arguments(self):
        source = """
        import java.util.function.Function;
        class Runner {
            Runner(Runnable r) {}
        }
        class C {
            int processar(Function<String, Integer> fn) { return 0; }
            void executar(Runnable r) {}
            void m() {
                int n = processar(texto -> texto.length());
                executar(() -> System.out.println("Olá"));
                Runner r = new Runner(() -> System.out.println("ctor"));
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_target_typing_selects_distinct_arity_overloads(self):
        source = """
        import java.util.function.Consumer;
        class C {
            void exec(Runnable r) {}
            void exec(Consumer<String> c) {}
            void m() {
                exec(() -> System.out.println("zero"));
                exec(s -> System.out.println(s));
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_ambiguous_same_arity_overload_rejected(self):
        source = """
        import java.util.function.*;
        class C {
            void proc(Function<String, Integer> f) {}
            void proc(Consumer<String> c) {}
            void m() {
                proc(s -> s.length());
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)

    def test_06_lambda_without_functional_target_rejected(self):
        bad_var = "class C { void m() { var f = (int x) -> x + 1; } }"
        bad_obj = "class C { void m() { Object o = () -> {}; } }"
        self.assertFalse(analyze_source(bad_var).success)
        self.assertFalse(analyze_source(bad_obj).success)

    def test_07_inferred_parameter_type_checked_inside_lambda_body(self):
        bad = """
        import java.util.function.Function;
        class Texto { int tamanho() { return 0; } }
        class C {
            void m() {
                Function<Texto, Integer> f = t -> t.metodoInexistente();
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)


if __name__ == "__main__":
    unittest.main()
