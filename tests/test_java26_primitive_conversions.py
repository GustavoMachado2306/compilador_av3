import unittest
from src.main import analyze_source


class TestJava26PrimitiveConversionsS82(unittest.TestCase):
    """S8.2 — Conversões primitivas: identidade, widening, narrowing e promoções (JLS §5.1.1–§5.1.4, §5.6)."""

    def _ok(self, body: str):
        res = analyze_source(f"class Prim {{ void f() {{ {body} }} }}")
        self.assertTrue(res.success, msg=f"Deveria compilar: {body} -> {res.syntactic_error} {res.semantic_errors}")

    def _bad(self, body: str):
        res = analyze_source(f"class Prim {{ void f() {{ {body} }} }}")
        self.assertFalse(res.success, msg=f"Deveria falhar: {body}")

    def test_01_identity_primitive_conversions(self):
        self._ok("byte b = 1; byte b2 = b; short s = 1; short s2 = s; int i = 1; int i2 = i;")
        self._ok("long l = 1L; long l2 = l; float f = 1.0f; float f2 = f; double d = 1.0; double d2 = d;")
        self._ok("char c = 'a'; char c2 = c; boolean bool1 = true; boolean bool2 = bool1;")

    def test_02_widening_primitive_conversions_assignments(self):
        # byte -> short -> int -> long -> float -> double
        self._ok("byte b = 10; short s = b; int i = s; long l = i; float f = l; double d = f;")
        # char -> int -> long -> float -> double
        self._ok("char c = 'A'; int i = c; long l = c; float f = c; double d = c;")

    def test_03_narrowing_primitive_without_cast_rejected(self):
        self._bad("double d = 10.5; float f = d;")
        self._bad("float f = 10.5f; long l = f;")
        self._bad("long l = 100L; int i = l;")
        self._bad("int i = 10; short s = i;")
        self._bad("short s = 10; byte b = s;")
        self._bad("char c = 'a'; byte b = c;")
        self._bad("byte b = 10; char c = b;")

    def test_04_explicit_narrowing_casts_allowed(self):
        self._ok("double d = 10.5; int i = (int) d; float f = (float) d;")
        self._ok("long l = 100L; short s = (short) l; byte b = (byte) l; char c = (char) l;")
        self._ok("int i = 65; char c = (char) i; byte b = (byte) i;")

    def test_05_widening_and_narrowing_primitive_char_byte_short(self):
        # byte <-> char exige cast em ambas as direções (JLS §5.1.4)
        self._ok("byte b = 65; char c = (char) b; byte b2 = (byte) c;")
        self._ok("short s = 65; char c = (char) s; short s2 = (short) c;")

    def test_06_boolean_incompatible_with_numeric_primitives(self):
        self._bad("int x = (int) true;")
        self._bad("boolean b = (boolean) 1;")
        self._bad("boolean b = true; int x = b;")
        self._bad("int x = 1; boolean b = x;")
        self._bad("double d = 1.0; boolean b = (boolean) d;")

    def test_07_unary_and_binary_numeric_promotions(self):
        self._ok("byte b = 1; int r1 = -b; int r2 = ~b; int r3 = +b;")
        self._bad("byte b = 1; byte r = -b;")
        self._ok("byte b = 1; short s = 2; int r = b + s; long l = r + 1L; float f = l + 1.0f; double d = f + 1.0;")
        self._bad("byte b = 1; short s = 2; short r = b + s;")

    def test_08_primitive_conversions_in_conditional_operator(self):
        self._ok("boolean flag = true; double d = flag ? 1 : 2.5;")
        self._ok("boolean flag = true; long l = flag ? 1 : 2L;")
        self._bad("boolean flag = true; int i = flag ? 1 : 2.5;")

    def test_09_numeric_literal_types_and_promotions(self):
        self._ok("int a = 10; long b = 10L; long c = 10; float d = 2.5f; double e = 2.5;")
        self._bad("long a = 10L; int b = a;")
        self._ok("int a = 10; long b = 20L; long resultado = a + b;")
        res = analyze_source(
            "class T { public static long fatorial(int n) { return n <= 1 ? 1L : n * fatorial(n - 1); } }"
        )
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_10_numeric_literal_range_validation_jls_3_10(self):
        # Limites decimais int/long (incluindo mínimo negativo unário)
        self._ok("int iMax = 2147483647; int iMin = -2147483648;")
        self._ok("long lMax = 9223372036854775807L; long lMin = -9223372036854775808L;")
        self._bad("int x = 2147483648;")
        self._bad("int x = -2147483649;")
        self._bad("long y = 9223372036854775808L;")
        self._bad("long y = -9223372036854775809L;")

        # Bases não decimais: até 32 bits (int) e 64 bits (long) sem sinal
        self._ok("int h1 = 0x80000000; int h2 = 0xffffffff; long hl = 0xffffffffffffffffL;")
        self._bad("int hBad = 0x100000000;")
        self._bad("long hlBad = 0x10000000000000000L;")

        # Ponto flutuante: overflow e underflow
        self._ok("float f0 = 0.0f; float fMax = 3.4028235e38f; float fMin = 1.4e-45f; double d0 = 0.0;")
        self._bad("float fOver = 1e50f;")
        self._bad("float fUnder = 1e-50f;")
        self._bad("double dOver = 1e500;")
        self._bad("double dUnder = 1e-400;")

    def test_11_numeric_literal_bases_underscores_and_switch_octal(self):
        # Binário e octal: limites sem sinal de 32 e 64 bits
        self._ok("int b32 = 0b11111111111111111111111111111111; int o32 = 037777777777;")
        self._ok("long o64 = 01777777777777777777777L;")
        self._bad("int b33 = 0b100000000000000000000000000000000;")
        self._bad("int o33 = 040000000000;")
        self._bad("long o65 = 02000000000000000000000L;")

        # Ponto flutuante hexadecimal e underscores em todas as categorias
        self._ok("double hf = 0x1.0p0; float hff = 0x1.fp3f;")
        self._bad("float hfOver = 0x1.0p200f;")
        self._bad("double hdOver = 0x1.0p2000;")
        self._ok("int u = 1_000_000; long ul = 1_000_000L; double ud = 1_234.567_8d; float uf = 1_2.3_4f;")

        # Duplicidade em switch com literal octal (077 == 63)
        res = analyze_source(
            "class T { int f(int x) { return switch (x) { case 077 -> 1; case 63 -> 2; default -> 0; }; } }"
        )
        self.assertFalse(res.success)

    def test_12_parenthesized_minimum_integer_literals_jls_3_10_1(self):
        # Valores mínimos diretos aceitos
        self._ok("int a = -2147483648; long b = -9223372036854775808L;")
        self._ok("int a = (-2147483648); long b = (-9223372036854775808L);")

        # Valores mínimos entre parênteses rejeitados (não são operando direto de '-')
        self._bad("int a = -(2147483648);")
        self._bad("int a = -((2147483648));")
        self._bad("long b = -(9223372036854775808L);")
        self._bad("long b = -((9223372036854775808L));")

        # Parênteses em expressões numéricas comuns (sem falsos positivos)
        self._ok("int a = (10); long b = (100L); int c = -(10); int d = -((10));")
        self._ok("int a = (10 + 20); long b = (100L + 200L); int c = -(10 + 20);")


if __name__ == "__main__":
    unittest.main()

