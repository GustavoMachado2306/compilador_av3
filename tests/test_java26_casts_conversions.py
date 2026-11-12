import unittest
from src.main import analyze_source


class TestJava26CastsConversionsS8(unittest.TestCase):
    """Valida casts primitivos, de referência, boxing/unboxing, genéricos e interseção (JLS §5.5 / §15.16)."""

    def test_01_primitive_widening_and_narrowing_casts(self):
        source = """
        class PrimCast {
            void run() {
                double d = 9.75;
                int i = (int) d;
                byte b = (byte) i;
                char c = (char) 65;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_boolean_primitive_casts_rejected(self):
        bad1 = "class C { void f() { int x = (int) true; } }"
        bad2 = "class C { void f() { boolean b = (boolean) 1; } }"
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_03_primitive_to_reference_boxing_only(self):
        ok_src = """
        class BoxCast {
            void run() {
                Object o = (Object) 10;
                Number n = (Number) 10;
                Integer w = (Integer) 10;
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_src = """
        class BoxCast {
            void run() {
                String s = (String) 10;
            }
        }
        """
        self.assertFalse(analyze_source(bad_src).success)

    def test_04_reference_to_primitive_unboxing_and_invalid(self):
        ok_src = """
        class UnboxCast {
            void run(Object o, Integer w) {
                int a = (int) w;
                double d = (double) w;
                int b = (int) o;
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_src = """
        class UnboxCast {
            void run() {
                int x = (int) "123";
            }
        }
        """
        self.assertFalse(analyze_source(bad_src).success)

    def test_05_reference_disjoint_final_cast_rejected(self):
        source = """
        final class A {}
        final class B {}
        class Test {
            void run(A a) {
                B b = (B) a;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)

    def test_06_nested_generic_cast_lookahead_valid(self):
        source = """
        import java.util.List;
        class GenCast {
            void run(Object obj) {
                List<List<String>> matriz = (List<List<String>>) obj;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_07_cast_of_switch_expression_valid(self):
        source = """
        class SwCast {
            void run(Object k) {
                String s = (String) switch (k) {
                    case String str -> str;
                    default -> "fallback";
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_08_intersection_cast_valid_and_invalid_bounds(self):
        ok_src = """
        interface FazA { void a(); }
        interface FazB { void b(); }
        class Algo implements FazA, FazB {
            public void a() {}
            public void b() {}
        }
        class Inter {
            void run(Object obj) {
                var r = (FazA & FazB) obj;
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_src = """
        class Base {}
        class Otra {}
        class Inter {
            void run(Object obj) {
                Object r = (Base & Otra) obj;
            }
        }
        """
        self.assertFalse(analyze_source(bad_src).success)

    def test_09_void_cast_syntax_rejected(self):
        source = """
        class V {
            void run(Object x) {
                Object y = (void) x;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)


if __name__ == "__main__":
    unittest.main()

