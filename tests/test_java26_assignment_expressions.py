import unittest
from src.main import analyze_source


class TestJava26AssignmentExpressionsS8(unittest.TestCase):
    """Valida regras de atribuição simples, composta, estreitamento constante e LHS modificável (JLS §15.26)."""

    def test_01_simple_chained_and_array_field_assignments(self):
        source = """
        class Box {
            int valor;
            void run(int[] dados) {
                int a;
                int b;
                a = b = 10;
                this.valor = a;
                dados[0] = b;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_constant_narrowing_in_byte_short_char(self):
        ok_src = """
        class Narrow {
            void run() {
                byte b = 127;
                short s = -32768;
                char c = 65;
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_src = """
        class Narrow {
            void run() {
                byte b = 200;
            }
        }
        """
        self.assertFalse(analyze_source(bad_src).success)

    def test_03_final_variable_and_final_field_reassignment_rejected(self):
        bad_local = """
        class Fin {
            void run() {
                final int x = 10;
                x = 20;
            }
        }
        """
        bad_field = """
        class Fin {
            final int id = 1;
            void alterar() {
                this.id = 2;
            }
        }
        """
        self.assertFalse(analyze_source(bad_local).success)
        self.assertFalse(analyze_source(bad_field).success)

    def test_04_final_field_initialization_in_constructor_allowed(self):
        source = """
        class Item {
            final int codigo;
            Item(int codigo) {
                this.codigo = codigo;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_compound_assignments_numeric_bitwise_shift_and_string(self):
        source = """
        class Comp {
            void run() {
                int x = 10;
                x += 2.5;
                x -= 1;
                x *= 3;
                x /= 2;
                x %= 2;
                x &= 0x0F;
                x |= 1;
                x ^= 2;
                x <<= 1;
                x >>= 1;
                x >>>= 1;
                String s = "oi";
                s += 42;
                boolean ok = true;
                ok &= false;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_06_compound_assignments_invalid_types_rejected(self):
        for bad in (
            'class E { void f() { String s = "a"; s -= "b"; } }',
            "class E { void f() { int x = 1; x <<= 1.5; } }",
            "class E { void f() { boolean b = true; b += 1; } }",
        ):
            self.assertFalse(analyze_source(bad).success)

    def test_07_non_lvalue_targets_rejected(self):
        for bad in (
            "class E { int g() { return 1; } void f() { g() = 2; } }",
            "class E { void f() { int a = 1; int b = 2; (a + b) = 3; } }",
            "class E { void f(int[] a) { a.length = 5; } }",
        ):
            self.assertFalse(analyze_source(bad).success)

    def test_08_array_element_type_mismatch_rejected(self):
        bad = """
        class E {
            void f() {
                int[] v = new int[2];
                v[0] = "texto";
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_09_member_field_assignment_type_mismatch_rejected(self):
        bad = """
        class Box { int n; }
        class E {
            void f(Box b) {
                b.n = "nao_int";
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)


if __name__ == "__main__":
    unittest.main()

