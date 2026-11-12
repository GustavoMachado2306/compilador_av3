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


if __name__ == "__main__":
    unittest.main()

