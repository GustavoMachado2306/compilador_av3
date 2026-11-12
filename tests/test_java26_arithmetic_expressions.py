import unittest
from src.main import analyze_source


class TestJava26ArithmeticExpressionsS8(unittest.TestCase):
    """Valida operadores aritméticos, lógicos, bit-a-bit, relacionais, unários e promoções numéricas (JLS §5.6 / §15)."""

    def test_01_binary_numeric_promotions_valid(self):
        source = """
        class Calc {
            void run() {
                byte b = 10;
                short s = 20;
                char c = 'A';
                int i = b + s + c;
                long l = i + 100L;
                float f = l + 1.5f;
                double d = f + 2.0;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_byte_plus_byte_promotes_to_int_not_byte(self):
        source = """
        class Calc {
            void run() {
                byte a = 1;
                byte b = 2;
                byte c = a + b;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)

    def test_03_string_concatenation_vs_invalid_arithmetic(self):
        ok_src = """
        class Msg {
            void run() {
                String s = "Resultado: " + (10 + 20) + true;
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_src = """
        class Msg {
            void run() {
                int x = "10" - 2;
            }
        }
        """
        self.assertFalse(analyze_source(bad_src).success)

    def test_04_bitwise_vs_logical_boolean_operators(self):
        ok_src = """
        class Ops {
            void run() {
                int bits = (0x0F & 0x03) | (1 ^ 2);
                boolean b = (true & false) ^ (true | false);
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_src = """
        class Ops {
            void run() {
                int x = 10 & true;
            }
        }
        """
        self.assertFalse(analyze_source(bad_src).success)

    def test_05_shift_operators_valid_and_invalid_float(self):
        ok_src = """
        class Shifts {
            void run() {
                int a = 16 >> 2;
                long b = 1L << 40;
                int c = -1 >>> 1;
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_src = """
        class Shifts {
            void run() {
                double d = 1.5 << 2;
            }
        }
        """
        self.assertFalse(analyze_source(bad_src).success)

    def test_06_relational_operators_reject_boolean_and_string(self):
        bad1 = """
        class Rel {
            void run() { boolean r = true < false; }
        }
        """
        bad2 = """
        class Rel {
            void run() { boolean r = "a" < "b"; }
        }
        """
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_07_equality_valid_and_incomparable_error(self):
        ok_src = """
        class Eq {
            void run(Integer boxed, Object obj) {
                boolean b1 = 10 == 10.0;
                boolean b2 = boxed == 5;
                boolean b3 = obj == "abc";
                boolean b4 = obj != null;
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad1 = """
        class Eq {
            void run() { boolean b = 10 == true; }
        }
        """
        bad2 = """
        class Eq {
            void run(String s, Integer i) { boolean b = s == i; }
        }
        """
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_08_unary_operators_type_validation(self):
        ok_src = """
        class Un {
            void run() {
                int a = -(+5);
                int b = ~0x0F;
                boolean ok = !false;
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        for bad in (
            "class Un { void f() { boolean b = !10; } }",
            "class Un { void f() { double d = ~1.5; } }",
            'class Un { void f() { int x = -"abc"; } }',
        ):
            self.assertFalse(analyze_source(bad).success)

    def test_09_increment_decrement_modifiable_and_errors(self):
        ok_src = """
        class Inc {
            int campo = 0;
            void run(int[] arr) {
                int x = 1;
                x++;
                --x;
                this.campo++;
                arr[0]--;
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        for bad in (
            "class Inc { void f() { final int x = 1; x++; } }",
            "class Inc { void f() { int x = (5)++; } }",
            "class Inc { void f(boolean b) { b++; } }",
            "class Inc { void f(int[] a) { a.length++; } }",
        ):
            self.assertFalse(analyze_source(bad).success)

    def test_10_logical_and_or_require_boolean(self):
        bad = """
        class Log {
            void run() {
                boolean r = 1 && 2;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)


if __name__ == "__main__":
    unittest.main()

