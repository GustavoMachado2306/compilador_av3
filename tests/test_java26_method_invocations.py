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


if __name__ == "__main__":
    unittest.main()

