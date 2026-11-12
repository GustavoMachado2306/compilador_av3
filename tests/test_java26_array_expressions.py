import unittest
from src.main import analyze_source


class TestJava26ArrayExpressionsS8(unittest.TestCase):
    """Valida criação, inicialização, indexação e .length de arrays (JLS §10 / §15.10 / §15.13)."""

    def test_01_array_creation_1d_and_2d_sizes(self):
        source = """
        class Arr {
            void run() {
                int[] v = new int[5];
                String[][] m = new String[2][3];
                int[][] irreg = new int[3][];
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_array_creation_with_initializer_and_nested(self):
        source = """
        class Arr {
            void run() {
                int[] v = new int[] {1, 2, 3};
                int[][] m = new int[][] {{1, 2}, {3, 4}};
                String[] nomes = {"Ana", "Bob"};
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_array_creation_without_size_or_initializer_rejected(self):
        source = """
        class Arr {
            void run() {
                int[] v = new int[];
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_04_array_creation_with_both_size_and_initializer_rejected(self):
        source = """
        class Arr {
            void run() {
                int[] v = new int[3] {1, 2, 3};
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_05_array_creation_sparse_trailing_dimension_rejected(self):
        source = """
        class Arr {
            void run() {
                int[][] m = new int[][3];
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_06_array_access_and_length_type_inference(self):
        source = """
        class Arr {
            void run() {
                int[][] m = {{10, 20}, {30, 40}};
                int elem = m[0][1];
                int tam = m.length;
                byte idx = 1;
                int ok = m[idx][0];
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_07_array_index_non_int_rejected(self):
        bad_long = "class Arr { void f(int[] a) { int x = a[0L]; } }"
        bad_str = 'class Arr { void f(int[] a) { int x = a["0"]; } }'
        bad_not_arr = "class Arr { void f(int a) { int x = a[0]; } }"
        self.assertFalse(analyze_source(bad_long).success)
        self.assertFalse(analyze_source(bad_str).success)
        self.assertFalse(analyze_source(bad_not_arr).success)

    def test_08_array_length_reassignment_rejected(self):
        source = """
        class Arr {
            void run(int[] a) {
                a.length = 10;
            }
        }
        """
        self.assertFalse(analyze_source(source).success)

    def test_09_array_initializer_element_type_mismatch_rejected(self):
        source = """
        class Arr {
            void run() {
                int[] v = new int[] {1, "dois", 3};
            }
        }
        """
        self.assertFalse(analyze_source(source).success)


if __name__ == "__main__":
    unittest.main()

