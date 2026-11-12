import unittest
from src.main import analyze_source


class TestJava26FunctionalInterfacesS84(unittest.TestCase):
    """Valida reconhecimento de interfaces funcionais segundo JLS §9.8 e @FunctionalInterface (JLS §9.6.4.9)."""

    def test_01_single_abstract_method_with_default_static_private(self):
        source = """
        interface Operacao {
            int executar(int a, int b);
            default int dobrar(int a) { return executar(a, a); }
            static int zero() { return 0; }
            private int aux(int x) { return x; }
        }
        class C {
            void m() {
                Operacao op = (a, b) -> a + b;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_inherited_sam_and_equivalent_multiple_inheritance(self):
        source = """
        interface Base {
            int calc(int x);
        }
        interface Filha extends Base {
            default int calcMaisUm(int x) { return calc(x) + 1; }
        }
        interface A {
            int combinar(int a, int b);
        }
        interface B {
            int combinar(int x, int y);
        }
        interface Unificada extends A, B {}
        class C {
            void m() {
                Filha f = x -> x * 2;
                Unificada u = (a, b) -> a + b;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_default_overrides_super_abstract_method(self):
        source = """
        interface A {
            void passo();
        }
        interface B extends A {
            default void passo() {}
            int executar(int x);
        }
        class C {
            void m() {
                B b = x -> x + 10;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_object_public_methods_excluded_and_non_object_equals_counted(self):
        ok_src = """
        interface ComparadorTexto {
            int comparar(String a, String b);
            boolean equals(Object obj);
            String toString();
            int hashCode();
        }
        class C {
            void m() {
                ComparadorTexto ct = (a, b) -> a.compareTo(b);
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_src = """
        interface NaoFuncional {
            void executar();
            boolean equals(String outro);
        }
        class C {
            void m() {
                NaoFuncional nf = () -> {};
            }
        }
        """
        self.assertFalse(analyze_source(bad_src).success)

    def test_05_generic_and_void_functional_interfaces(self):
        source = """
        interface Acao {
            void executar();
        }
        interface Conversor<T, R> {
            R converter(T valor);
        }
        class C {
            void m() {
                Acao a = () -> System.out.println("ok");
                Conversor<String, Integer> c = texto -> texto.length();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_06_functional_interface_annotation_valid_and_invalid(self):
        ok_src = """
        @FunctionalInterface
        interface Valida {
            int aplicar(int x);
            default int id(int x) { return x; }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_empty = "@FunctionalInterface interface Vazia {}"
        bad_two = "@FunctionalInterface interface Dupla { void a(); void b(); }"
        bad_class = "@FunctionalInterface class NaoInterface { void a() {} }"
        self.assertFalse(analyze_source(bad_empty).success)
        self.assertFalse(analyze_source(bad_two).success)
        self.assertFalse(analyze_source(bad_class).success)

    def test_07_empty_and_multi_abstract_interfaces_rejected_as_lambda_target(self):
        bad_empty = """
        interface Marcadora {}
        class C { void m() { Marcadora m = () -> {}; } }
        """
        bad_multi = """
        interface Duas { void a(); void b(); }
        class C { void m() { Duas d = () -> {}; } }
        """
        self.assertFalse(analyze_source(bad_empty).success)
        self.assertFalse(analyze_source(bad_multi).success)

    def test_08_interface_with_conflicting_inherited_return_types_not_functional(self):
        bad = """
        interface A { int valor(); }
        interface B { String valor(); }
        interface C extends A, B {}
        class T { void m() { C c = () -> 1; } }
        """
        self.assertFalse(analyze_source(bad).success)


if __name__ == "__main__":
    unittest.main()

