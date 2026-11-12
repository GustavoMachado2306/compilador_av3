import unittest
from src.main import analyze_source


class TestJava26OperatorSemanticsS81(unittest.TestCase):
    """S8.1 — Tipos resultantes e compatibilidade de operandos (JLS §5.6, §15.15–§15.26)."""

    def _run(self, body: str, members: str = ""):
        source = f"class Op {{ {members} void run() {{ {body} }} }}"
        return analyze_source(source)

    def ok(self, body: str, members: str = ""):
        res = self._run(body, members)
        self.assertTrue(res.success, msg=f"{body} -> {res.syntactic_error} {res.semantic_errors}")

    def bad(self, body: str, members: str = ""):
        res = self._run(body, members)
        self.assertFalse(res.success, msg=f"deveria falhar: {body}")

    # ---- Tipos resultantes (promoção numérica) ----
    def test_01_byte_short_char_promote_to_int(self):
        self.ok("byte a = 1; short b = 2; char c = 'x'; int r = a + b + c;")
        self.bad("byte a = 1; byte r = a + a;")
        self.bad("short a = 1; short r = a * a;")
        self.bad("char c = 'a'; char r = c + 1;")

    def test_02_long_float_double_widening_results(self):
        self.ok("int i = 1; long l = 2L; long r = i + l;")
        self.ok("long l = 2L; float f = l * 1.5f;")
        self.ok("float f = 1f; double d = f + 1.0;")
        self.bad("long l = 2L; int r = l + 1;")
        self.bad("double d = 1.0; float f = d + 1f;")

    def test_03_unary_promotion(self):
        self.ok("byte b = 1; int r = -b; int s = ~b; int t = +b;")
        self.bad("byte b = 1; byte r = -b;")
        self.bad("short s = 1; short r = ~s;")
        self.bad("double d = 1.0; int r = ~(int) d + ~d;")

    def test_04_string_concatenation_result_is_string(self):
        self.ok('String s = "a" + 1 + 2.0 + true + null + \'c\';')
        self.ok('int n = 1; String s = n + "x";')
        self.bad('int n = 1; int r = n + "x";')
        self.bad('String s = "a" - "b";')

    def test_05_integer_division_remainder_and_floating(self):
        self.ok("int a = 7 / 2; int b = 7 % 2; double c = 7 / 2.0; double d = 7.5 % 2;")
        self.bad("int a = 7 / 2.0;")
        self.bad("boolean b = true; int r = b / 2;")

    # ---- Shifts ----
    def test_06_shift_result_type_is_promoted_left_operand_only(self):
        self.ok("int i = 1; long l = 1L; int a = i << l; long b = l << i;")
        self.bad("int i = 1; long l = 1L; int a = l << i;")
        self.ok("byte b = 1; int r = b >> 2; int u = b >>> 2;")
        self.bad("byte b = 1; byte r = b << 1;")

    def test_07_shift_rejects_non_integral(self):
        self.bad("double d = 1.0; int r = 1 << d;")
        self.bad("float f = 1f; int r = f << 1;")
        self.bad("boolean b = true; int r = b << 1;")
        self.bad('String s = "a"; int r = s >> 1;')

    # ---- Relacionais e igualdade ----
    def test_08_relational_operands_numeric_and_result_boolean(self):
        self.ok("int a = 1; double d = 2.0; boolean r = a < d; boolean s = 'a' <= 98L;")
        self.bad("int r = 1 < 2;")
        self.bad("boolean r = true < false;")
        self.bad('boolean r = "a" > "b";')

    def test_09_relational_accepts_boxed_numeric(self):
        self.ok("Integer a = 1; Double d = 2.0; boolean r = a < d; boolean s = a >= 1;")

    def test_10_equality_numeric_boolean_reference(self):
        self.ok("boolean r = 1 == 1.0; boolean s = true != false; Object o = null; boolean t = o == null;")
        self.ok('String a = "x"; Object b = a; boolean r = a == b;')
        self.bad("boolean r = 1 == true;")
        self.bad('boolean r = 1 == "1";')

    def test_11_equality_boxed_unboxing_and_incomparable_references(self):
        self.ok("Integer a = 1; boolean r = a == 1; Boolean b = true; boolean s = b == false;")
        self.bad('String s = "a"; Integer i = 1; boolean r = s == i;')

    # ---- Lógicos e bitwise ----
    def test_12_conditional_and_or_require_boolean(self):
        self.ok("boolean a = true; boolean r = a && !a || a;")
        self.ok("Boolean a = true; boolean r = a && true;")
        self.bad("int a = 1; boolean r = a && true;")
        self.bad("boolean a = true; boolean r = a || 1;")

    def test_13_logical_not_requires_boolean(self):
        self.ok("boolean a = !true;")
        self.bad("int a = !1;")
        self.bad("int x = 1; boolean a = !x;")

    def test_14_bitwise_integral_and_boolean_forms(self):
        self.ok("int a = 6 & 3 | 1 ^ 2; long l = 6L & 3; boolean b = true & false | true ^ false;")
        self.bad("boolean b = true & 1;")
        self.bad("double d = 1.0; double r = d & 1;")
        self.bad("int r = 1 & true;")

    def test_15_bitwise_result_promotion(self):
        self.ok("byte b = 1; int r = b & b; long l = b | 1L;")
        self.bad("byte b = 1; byte r = b ^ b;")

    # ---- Ternário ----
    def test_16_ternary_condition_must_be_boolean(self):
        self.ok("int r = true ? 1 : 2;")
        self.bad("int r = 1 ? 1 : 2;")
        self.bad('int r = true ? "a" : 2;')

    def test_17_ternary_numeric_promotion_of_branches(self):
        self.ok("int i = 1; long l = 2L; long r = true ? i : l;")
        self.ok("double d = false ? 1 : 2.0;")
        self.bad("int i = 1; long l = 2L; int r = true ? i : l;")

    # ---- Incremento / decremento ----
    def test_18_increment_on_numeric_variables_and_array_elements(self):
        self.ok("int i = 0; i++; ++i; i--; --i; int[] a = new int[2]; a[0]++; --a[1];")
        self.ok("byte b = 1; b++; char c = 'a'; c++; double d = 1.0; d--;")
        self.ok("Integer w = 1; w++;")

    def test_19_increment_rejects_invalid_operands(self):
        self.bad("boolean b = true; b++;")
        self.bad('String s = "a"; s++;')
        self.bad("5++;")
        self.bad("int i = 0; (i + 1)++;")
        self.bad("final int i = 0; i++;")
        self.bad("int i = 0; (i++)++;")

    # ---- Atribuições ----
    def test_20_simple_assignment_widening_and_boxing(self):
        self.ok("long l = 1; double d = l; Integer w = 1; int u = w; Object o = 1;")
        self.bad("int i = 1L;")
        self.bad("float f = 1.0;")
        self.bad("Long l = 1;")
        self.bad('String s = 1;')

    def test_21_compound_assignment_has_implicit_narrowing_cast(self):
        self.ok("byte b = 1; b += 1000; short s = 1; s *= 2.5; char c = 'a'; c += 1; int i = 1; i /= 2.0;")
        self.ok("int i = 1; i <<= 2L; i >>>= 1; i &= 3; i |= 4; i ^= 5; i %= 2;")
        self.ok('String s = "a"; s += 1; s += null;')

    def test_22_compound_assignment_invalid_combinations(self):
        self.bad("boolean b = true; b += 1;")
        self.bad("int i = 1; i += true;")
        self.bad("double d = 1.0; d <<= 1;")
        self.bad("double d = 1.0; d &= 1;")
        self.bad("boolean b = true; b -= false;")
        self.bad('int i = 1; i += "x";')
        self.bad('String s = "a"; s -= "b";')

    def test_23_compound_boolean_logical_assignment(self):
        self.ok("boolean b = true; b &= false; b |= true; b ^= true;")
        self.bad("boolean b = true; b &&= false;")

    def test_24_assignment_targets_must_be_variables(self):
        self.bad("1 = 2;")
        self.bad("int a = 1; (a + 1) = 2;")
        self.bad("int a = 1; a++ = 2;")
        self.bad('"s" += "t";')
        self.bad("final int a = 1; a = 2;")
        self.bad("final int a = 1; a += 2;")

    def test_25_assignment_expression_value_and_chaining(self):
        self.ok("int a; int b; a = b = 3;")
        self.ok("int a = 1; int b = (a += 2) * 3;")
        self.ok("long l; int i = 1; l = i = 3;")
        self.bad("int i; long l = 1L; i = l = 3;")
        self.bad("boolean flag; int x = 1; flag = x = 2;")

    def test_26_undeclared_identifier_in_operators(self):
        self.bad("int r = naoDeclarada + 1;")
        self.bad("boolean b = naoDeclarada && true;")

    def test_26b_constant_expressions_narrow_but_non_constants_do_not(self):
        self.ok("byte b = 1 << 3; byte c = 0x7F & 0xFF; char d = (char) 65 + 1;")
        self.bad("byte b = 128;")
        self.bad("int i = 1; byte b = i;")
        self.bad("final int K = 200; byte b = K;")
        self.bad("int k = 10; byte b = k;")

    # ---- instanceof ----
    def test_27_instanceof_result_boolean_and_operand_rules(self):
        self.ok('Object o = "x"; boolean r = o instanceof String;')
        self.ok('Object o = "x"; boolean r = o instanceof String && o != null;')
        self.bad("Object o = 1; int r = o instanceof Integer;")
        self.bad("int i = 1; boolean r = i instanceof Integer;")
        self.bad('String s = "a"; boolean r = s instanceof Integer;')

    def test_28_instanceof_primitive_stays_preview_only(self):
        src = "class P { void f(Object o) { boolean r = o instanceof int; } }"
        self.assertFalse(analyze_source(src).success)
        self.assertTrue(analyze_source(src, enable_preview_primitive_patterns=True).success)

    # ---- Regressões e fronteiras ----
    def test_29_legal_conversions_not_rejected(self):
        self.ok("final int K = 10; byte b = K; char c = 65; short s = (short) 1 + 0;")
        self.ok("int i = 'a'; long l = 'a'; float f = 1L; double d = 1;")
        self.ok("char c = 'a'; int r = c * 2; boolean b = c == 97;")

    def test_30_field_and_method_operands(self):
        self.ok("total += 1; contador++; boolean r = total > contador;", "int total; int contador;")
        self.bad("flag += 1;", "boolean flag;")
        self.ok("int r = valor() * 2 + 1;", "int valor() { return 1; }")
        self.bad("int r = nada() + 1;", "void nada() {}")


if __name__ == "__main__":
    unittest.main()
