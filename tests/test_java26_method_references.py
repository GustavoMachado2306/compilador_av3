import unittest
from src.main import analyze_source
from src.compiler.ast_nodes import MethodReference


class TestJava26MethodReferencesS8(unittest.TestCase):
    """Valida todas as 5 formas de method references segundo JLS §15.13."""

    def test_01_static_method_reference(self):
        source = """
        import java.util.function.*;
        class MRef {
            void run() {
                IntBinaryOperator mx = Math::max;
                Function<String, Integer> p = Integer::parseInt;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_bound_instance_method_reference(self):
        source = """
        import java.util.function.*;
        class MRef {
            void run() {
                String texto = "java26";
                Supplier<String> up = texto::toUpperCase;
                Consumer<String> pr = System.out::println;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_unbound_instance_method_reference(self):
        source = """
        import java.util.function.*;
        class MRef {
            void run() {
                Function<String, Integer> len = String::length;
                BiFunction<String, String, Integer> cmp = String::compareTo;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_constructor_method_reference_including_generics(self):
        source = """
        import java.util.ArrayList;
        import java.util.function.*;
        class Pessoa {
            Pessoa() {}
            Pessoa(String nome) {}
        }
        class MRef {
            void run() {
                Supplier<Pessoa> s = Pessoa::new;
                Function<String, Pessoa> f = Pessoa::new;
                Supplier<ArrayList<String>> l = ArrayList<String>::new;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_array_creation_method_reference(self):
        source = """
        import java.util.function.IntFunction;
        class MRef {
            void run() {
                IntFunction<int[]> arr1 = int[]::new;
                IntFunction<String[][]> arr2 = String[][]::new;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0].initializer, MethodReference)
        self.assertTrue(stmts[0].initializer.is_array_creation)
        self.assertIsInstance(stmts[1].initializer, MethodReference)
        self.assertTrue(stmts[1].initializer.is_array_creation)

    def test_06_generic_method_reference_with_type_arguments(self):
        source = """
        import java.util.function.UnaryOperator;
        class Util {
            static <T> T identidade(T x) { return x; }
        }
        class MRef {
            void run() {
                UnaryOperator<String> fn = Util::<String>identidade;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_07_method_reference_missing_method_or_mismatched_sam_rejected(self):
        bad_missing = """
        import java.util.function.Supplier;
        class Alvo { void ok() {} }
        class MRef {
            void run(Alvo a) { Supplier<String> s = a::inexistente; }
        }
        """
        bad_arity = """
        import java.util.function.Supplier;
        class MRef {
            void run() { Supplier<Integer> s = String::length; }
        }
        """
        self.assertFalse(analyze_source(bad_missing).success)
        self.assertFalse(analyze_source(bad_arity).success)

    def test_08_array_creation_ref_without_int_param_or_non_functional_rejected(self):
        bad1 = """
        import java.util.function.Supplier;
        class MRef {
            void run() { Supplier<int[]> s = int[]::new; }
        }
        """
        bad2 = """
        class MRef {
            void run() { Object o = String::length; }
        }
        """
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_09_inherited_instance_method_reference(self):
        source = """
        import java.util.function.*;
        class Base {
            String saudacao() { return "oi"; }
        }
        class Sub extends Base {}
        class MRef {
            void run(Sub sub) {
                Supplier<String> s1 = sub::saudacao;
                Function<Sub, String> s2 = Sub::saudacao;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_10_static_method_ref_via_instance_expr_rejected(self):
        source = """
        import java.util.function.Function;
        class MRef {
            void run() {
                String texto = "123";
                Function<Integer, String> fn = texto::valueOf;
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_11_static_void_method_ref_to_non_void_sam_rejected(self):
        source = """
        import java.util.function.Supplier;
        class Util {
            static void ping() {}
        }
        class MRef {
            void run() {
                Supplier<String> s = Util::ping;
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_12_constructor_ref_validation_arity_abstract_and_return_type(self):
        bad_abstract = """
        import java.util.function.Supplier;
        abstract class Ab { Ab() {} }
        class MRef { void run() { Supplier<Ab> s = Ab::new; } }
        """
        bad_arity = """
        import java.util.function.Supplier;
        class Pessoa { Pessoa(String nome) {} }
        class MRef { void run() { Supplier<Pessoa> s = Pessoa::new; } }
        """
        bad_ret = """
        import java.util.function.Supplier;
        class Pessoa { Pessoa() {} }
        class MRef { void run() { Supplier<String> s = Pessoa::new; } }
        """
        self.assertFalse(analyze_source(bad_abstract).success)
        self.assertFalse(analyze_source(bad_arity).success)
        self.assertFalse(analyze_source(bad_ret).success)

    def test_13_method_reference_as_method_argument_and_incompatible_unbound_receiver(self):
        ok_src = """
        import java.util.function.Function;
        class MRef {
            int converter(Function<String, Integer> fn) { return 0; }
            void run() {
                int v = converter(Integer::parseInt);
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_unbound = """
        import java.util.function.Function;
        class MRef {
            void run() {
                Function<Integer, Integer> f = String::length;
            }
        }
        """
        self.assertFalse(analyze_source(bad_unbound).success)


if __name__ == "__main__":
    unittest.main()

