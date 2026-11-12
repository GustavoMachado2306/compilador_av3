import unittest
from src.main import analyze_source


class TestJava26MethodInvocationsS8(unittest.TestCase):
    """Valida resolução de métodos, herança, sobrecarga em 3 fases e erros (JLS §15.12)."""

    def test_01_inherited_and_interface_default_method_calls(self):
        source = """
        interface Nomeado {
            default String nome() { return "padrao"; }
        }
        class Base {
            int dobrar(int x) { return x * 2; }
        }
        class Filha extends Base implements Nomeado {
            void run() {
                int r = dobrar(21);
                String n = nome();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_overload_phase1_strict_widening_beats_boxing(self):
        source = """
        class Over {
            String testar(long x) { return "long"; }
            String testar(Integer x) { return "Integer"; }
            void run() {
                String a = testar(10);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_overload_phase2_boxing_beats_varargs(self):
        source = """
        class Over {
            String escolher(Integer x) { return "boxed"; }
            String escolher(int... xs) { return "varargs"; }
            void run() {
                String s = escolher(5);
                String v = escolher(1, 2, 3);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_overload_most_specific_subtype(self):
        source = """
        class Spec {
            int f(Object o) { return 1; }
            int f(String s) { return 2; }
            void run() {
                int x = f("ola");
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_ambiguous_overload_rejected(self):
        source = """
        interface IA {}
        interface IB {}
        class C implements IA, IB {}
        class Amb {
            void f(IA a) {}
            void f(IB b) {}
            void run(C c) {
                f(c);
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)

    def test_06_explicit_type_arguments_generic_method_call(self):
        source = """
        class Util {
            static <T> T eco(T valor) { return valor; }
            void run() {
                String s = Util.<String>eco("Java 26");
                int n = Util.<Integer>eco(10);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_07_static_context_calling_instance_method_rejected(self):
        source = """
        class St {
            void inst() {}
            static void okStatic() {}
            static void run() {
                okStatic();
                inst();
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)

    def test_08_instance_method_called_via_class_name_rejected(self):
        source = """
        class Box {
            int get() { return 1; }
        }
        class Main {
            void run() {
                int x = Box.get();
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)

    def test_09_missing_method_and_wrong_args_on_declared_class_rejected(self):
        bad1 = """
        class Conta { int saldo() { return 0; } }
        class Main {
            void run(Conta c) { int x = c.inexistente(); }
        }
        """
        bad2 = """
        class Conta { void depositar(double v) {} }
        class Main {
            void run(Conta c) { c.depositar("cem"); }
        }
        """
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_10_builtin_methods_math_string_system_out(self):
        ok_src = """
        class BuiltinDemo {
            void run() {
                int n = "Java26".length();
                double m = Math.max(1.5, 2.5);
                System.out.println("ok");
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_src = """
        class BuiltinDemo {
            void run() {
                char c = "Java".charAt("zero");
            }
        }
        """
        self.assertFalse(analyze_source(bad_src).success)

    def test_11_list_generic_add_overloads_and_rejection(self):
        ok_src = """
        import java.util.*;
        interface Figura {}
        class Retangulo implements Figura {
            Retangulo(double a, double b) {}
        }
        class Triangulo implements Figura {
            Triangulo(double a, double b) {}
        }
        class Main {
            void run() {
                List<Figura> figuras = new ArrayList<>();
                boolean b1 = figuras.add(new Retangulo(4.0, 3.0));
                boolean b2 = figuras.add(new Triangulo(6.0, 2.5));
                figuras.add(0, new Retangulo(1.0, 2.0));
            }
        }
        """
        res = analyze_source(ok_src)
        self.assertTrue(res.success, msg=res.semantic_errors)

        bad1 = """
        import java.util.*;
        interface Figura {}
        class Main {
            void run(List<Figura> figuras) {
                figuras.add("invalido");
            }
        }
        """
        bad2 = """
        import java.util.*;
        interface Figura {}
        class Retangulo implements Figura {}
        class Main {
            void run(List<Figura> figuras) {
                figuras.add("zero", new Retangulo());
            }
        }
        """
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_12_arrays_tostring_static_overloads_and_println(self):
        ok_src = """
        import java.util.*;
        class Main {
            void run(double[] pts, int[] nums, Object[] objs, String[] strs, Object obj) {
                String s1 = Arrays.toString(pts);
                String s2 = Arrays.toString(nums);
                String s3 = Arrays.toString(objs);
                String s4 = Arrays.toString(strs);
                String s5 = obj.toString();
                System.out.println(Arrays.toString(pts));
            }
        }
        """
        res = analyze_source(ok_src)
        self.assertTrue(res.success, msg=res.semantic_errors)

        bad_zero_arg = """
        import java.util.*;
        class Main {
            void run() {
                String s = Arrays.toString();
            }
        }
        """
        self.assertFalse(analyze_source(bad_zero_arg).success)

    def test_13_real_overload_ambiguity_still_rejected(self):
        ambig_src = """
        class Amb {
            void g(String a, Object b) {}
            void g(Object a, String b) {}
            void run() {
                g("x", "y");
            }
        }
        """
        res = analyze_source(ambig_src)
        self.assertFalse(res.success)


if __name__ == "__main__":
    unittest.main()

