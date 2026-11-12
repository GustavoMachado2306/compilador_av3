import unittest
from src.main import analyze_source


class TestJava26ConstantNarrowingS82(unittest.TestCase):
    """S8.2 — Narrowing implícito de expressões constantes inteiras em contexto de atribuição (JLS §5.2)."""

    def test_01_primitive_literal_narrowing_boundaries(self):
        ok = """
        class NarrowTest {
            void f() {
                byte bMin = -128;
                byte bMax = 127;
                short sMin = -32768;
                short sMax = 32767;
                char cMin = 0;
                char cMax = 65535;
            }
        }
        """
        self.assertTrue(analyze_source(ok).success)

        self.assertFalse(analyze_source("class C { void f() { byte b = 128; } }").success)
        self.assertFalse(analyze_source("class C { void f() { byte b = -129; } }").success)
        self.assertFalse(analyze_source("class C { void f() { short s = 32768; } }").success)
        self.assertFalse(analyze_source("class C { void f() { short s = -32769; } }").success)
        self.assertFalse(analyze_source("class C { void f() { char c = 65536; } }").success)
        self.assertFalse(analyze_source("class C { void f() { char c = -1; } }").success)

    def test_02_prompt_required_examples(self):
        source = """
        class PromptExamples {
            void f() {
                final int K = 10;
                byte a = K;

                final int X = 5 + 5;
                short b = X;

                char c = 65;
                byte d = (byte) 127;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_final_local_variable_out_of_range_rejected(self):
        source = """
        class OutOfRangeFinal {
            void f() {
                final int K = 200;
                byte a = K;
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_04_constant_expressions_arithmetic_and_bitwise(self):
        source = """
        class ConstExprs {
            void f() {
                byte b1 = 10 + 20;
                byte b2 = 1 << 3;
                byte b3 = 0x7F & 0x0F;
                short s1 = 100 * 2;
                char c1 = 60 + 5;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_constant_narrowing_with_boxing_wrappers(self):
        source = """
        class BoxNarrow {
            void f() {
                Byte b = 10;
                Short s = 100;
                Character c = 65;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_06_constant_narrowing_with_boxing_out_of_range_rejected(self):
        self.assertFalse(analyze_source("class C { void f() { Byte b = 200; } }").success)
        self.assertFalse(analyze_source("class C { void f() { Short s = 40000; } }").success)
        self.assertFalse(analyze_source("class C { void f() { Character c = 70000; } }").success)

    def test_07_constant_narrowing_in_ternary_expression(self):
        ok = """
        class TernaryNarrow {
            void f(boolean flag) {
                byte b1 = flag ? 1 : 2;
                short s1 = flag ? 10 : 20;
                char c1 = flag ? 65 : 66;
            }
        }
        """
        self.assertTrue(analyze_source(ok).success)

        bad = """
        class TernaryNarrow {
            void f(boolean flag) {
                byte b1 = flag ? 1 : 200;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_08_non_constant_int_variable_never_narrows(self):
        source = """
        class NonConst {
            void f(int k) {
                int x = 10;
                byte b1 = x;
                byte b2 = k;
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_09_constant_cast_expressions_narrow(self):
        source = """
        class CastConst {
            void f() {
                byte b = (byte) 127 + 0;
                char c = (char) 65 + 1;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

