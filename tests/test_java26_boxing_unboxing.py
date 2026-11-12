import unittest
from src.main import analyze_source


class TestJava26BoxingUnboxingS82(unittest.TestCase):
    """S8.2 — Conversões de boxing e unboxing (JLS §5.1.7, §5.1.8, §5.2)."""

    def test_01_autoboxing_primitive_to_wrapper(self):
        source = """
        class BoxTest {
            void f() {
                Integer i = 10;
                Double d = 10.5;
                Boolean b = true;
                Character c = 'a';
                Long l = 10L;
                Float fl = 2.5f;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_autounboxing_wrapper_to_primitive(self):
        source = """
        class BoxTest {
            void f(Integer wI, Double wD, Boolean wB, Character wC) {
                int i = wI;
                double d = wD;
                boolean b = wB;
                char c = wC;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_autoboxing_followed_by_widening_reference(self):
        source = """
        class BoxTest {
            void f() {
                Object o1 = 10;
                Object o2 = 2.5;
                Number n1 = 10;
                Number n2 = 10.5;
                Comparable c = 10;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_unboxing_followed_by_widening_primitive(self):
        source = """
        class BoxTest {
            void f(Integer w) {
                long l = w;
                double d = w;
                float f = w;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_unboxing_followed_by_narrowing_primitive_rejected(self):
        # Double não pode ser atribuído a int sem cast
        bad1 = """
        class BoxTest {
            void f(Double d) {
                int i = d;
            }
        }
        """
        self.assertFalse(analyze_source(bad1).success)

        # Em um único cast, unboxing só pode ser seguido de widening primitivo, não narrowing
        bad2 = """
        class BoxTest {
            void f(Double d) {
                int i = (int) d;
            }
        }
        """
        self.assertFalse(analyze_source(bad2).success)

    def test_06_primitive_cannot_box_to_unrelated_wrapper(self):
        # int não pode fazer autoboxing para Long sem widening prévio (Java proíbe int -> Long)
        bad = """
        class BoxTest {
            void f() {
                Long l = 10;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_07_unboxing_null_variable_valid_compilation(self):
        # Válido sintática e semanticamente em tempo de compilação (JLS §5.1.8; NPE ocorre em execução)
        source = """
        class BoxTest {
            void f() {
                Integer nulo = null;
                int valor = nulo;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_08_boxing_unboxing_in_binary_and_relational_expressions(self):
        source = """
        class BoxTest {
            void f(Integer a, Double b) {
                double soma = a + b;
                boolean menor = a < b;
                boolean igual = a == 1;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_09_boxing_unboxing_in_ternary_expression(self):
        source = """
        class BoxTest {
            void f(boolean flag, Integer w) {
                int r = flag ? w : 10;
                Number num = flag ? 1 : 2.0;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

