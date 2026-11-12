import unittest
from src.main import analyze_source


class TestJava26ReferenceConversionsS82(unittest.TestCase):
    """S8.2 — Conversões de referência: widening, narrowing, classes finais, interfaces e arrays (JLS §5.1.5, §5.1.6, §5.5)."""

    def test_01_widening_reference_subclass_to_superclass(self):
        source = """
        class Base {}
        class Derivada extends Base {}
        class RefTest {
            void f(Derivada d, String s) {
                Base b = d;
                Object o1 = d;
                Object o2 = s;
                CharSequence cs = s;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_narrowing_reference_requires_cast(self):
        bad = """
        class RefTest {
            void f(Object o) {
                String s = o;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

        ok = """
        class RefTest {
            void f(Object o) {
                String s = (String) o;
            }
        }
        """
        self.assertTrue(analyze_source(ok).success)

    def test_03_disjoint_final_classes_cast_rejected(self):
        source = """
        class RefTest {
            void f(String s) {
                Integer i = (Integer) s;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)

    def test_04_interface_casts_to_non_final_class_allowed(self):
        # Em Java, classe não-final pode ser convertida para interface via cast pois subclasse pode implementá-la
        source = """
        interface Processador {}
        class Trabalhador {}
        class RefTest {
            void f(Trabalhador t) {
                Processador p = (Processador) t;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_interface_cast_to_final_class_not_implementing_rejected(self):
        source = """
        interface Processador {}
        final class TrabalhadorFixo {}
        class RefTest {
            void f(TrabalhadorFixo t) {
                Processador p = (Processador) t;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)

    def test_06_array_reference_covariance_and_casts(self):
        ok = """
        class RefTest {
            void f(String[] arr) {
                Object[] objs = arr;
                String[] deVolta = (String[]) objs;
            }
        }
        """
        self.assertTrue(analyze_source(ok).success)

        bad = """
        class RefTest {
            void f(String[] arr) {
                Integer[] err = (Integer[]) arr;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_07_multidimensional_array_to_object_array(self):
        # int[][] é um array de int[], que é Object; logo int[][] pode ser convertido para Object[]
        ok = """
        class RefTest {
            void f(int[][] matriz) {
                Object[] objs = matriz;
                Object[] objsCast = (Object[]) matriz;
                int[][] deVolta = (int[][]) objs;
            }
        }
        """
        self.assertTrue(analyze_source(ok).success)

        # int[] é array de primitivos, NÃO é Object[]
        bad = """
        class RefTest {
            void f(int[] vetor) {
                Object[] objs = (Object[]) vetor;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_08_null_reference_conversion(self):
        ok = """
        class RefTest {
            void f() {
                Object o = null;
                String s = null;
                int[] a = null;
                String s2 = (String) null;
            }
        }
        """
        self.assertTrue(analyze_source(ok).success)

        bad = """
        class RefTest {
            void f() {
                int x = null;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_09_cloneable_and_serializable_array_casts(self):
        source = """
        import java.io.Serializable;
        class RefTest {
            void f(int[] v, String[] s) {
                Cloneable c1 = (Cloneable) v;
                Serializable s1 = (Serializable) v;
                Cloneable c2 = (Cloneable) s;
                Serializable s2 = (Serializable) s;
                int[] v2 = (int[]) c1;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

