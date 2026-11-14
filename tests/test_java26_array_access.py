import unittest
from src.main import analyze_source
from src.compiler.ast_nodes import ArrayAccess, MemberAccess


class TestJava26ArrayAccessS83(unittest.TestCase):
    """S8.3 — Acesso a arrays: indexação 1D/ND, tipos de índice, receptor array e campo length (JLS §10.4, §10.7, §15.10.3)."""

    def test_01_array_indexing_multidimensional_and_length(self):
        source = """
        class Arr {
            void f() {
                int[] valores = {1, 2, 3};
                int primeiro = valores[0];
                int[][] matriz = {{1, 2}, {3, 4}};
                int elemento = matriz[0][1];
                int tamanho = valores.length;
                int linhaTam = matriz[0].length;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[1].initializer, ArrayAccess)
        self.assertIsInstance(stmts[3].initializer, ArrayAccess)
        self.assertIsInstance(stmts[4].initializer, MemberAccess)
        self.assertEqual(stmts[4].initializer.member_name, "length")

    def test_02_integral_index_types_allowed(self):
        source = """
        class ArrIdx {
            void f(byte b, short s, char c, Integer w) {
                int[] v = new int[100];
                int r1 = v[b];
                int r2 = v[s];
                int r3 = v[c];
                int r4 = v[w];
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_non_array_receiver_rejected(self):
        bad1 = "class C { void f() { int x = 5; int y = x[0]; } }"
        bad2 = 'class C { void f() { String s = "abc"; char c = s[0]; } }'
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_04_non_int_compatible_index_rejected(self):
        bad1 = "class C { void f() { int[] v = new int[3]; int y = v[1.5]; } }"
        bad2 = 'class C { void f() { int[] v = new int[3]; int y = v["0"]; } }'
        bad3 = "class C { void f() { int[] v = new int[3]; int y = v[1L]; } }"
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)
        self.assertFalse(analyze_source(bad3).success)

    def test_05_length_must_be_field_not_method_and_other_fields_rejected(self):
        bad_method = "class C { void f() { int[] v = {1}; int t = v.length(); } }"
        bad_field = "class C { void f() { int[] v = {1}; int t = v.tamanho; } }"
        self.assertFalse(analyze_source(bad_method).success)
        self.assertFalse(analyze_source(bad_field).success)

    def test_06_element_type_mismatch_on_read_and_write(self):
        bad_read = "class C { void f() { String[] s = new String[2]; int x = s[0]; } }"
        bad_write = 'class C { void f() { int[] v = new int[2]; v[0] = "texto"; } }'
        self.assertFalse(analyze_source(bad_read).success)
        self.assertFalse(analyze_source(bad_write).success)

    def test_07_length_field_is_final_cannot_be_reassigned(self):
        bad = "class C { void f() { int[] v = new int[2]; v.length = 5; } }"
        self.assertFalse(analyze_source(bad).success)


if __name__ == "__main__":
    unittest.main()

