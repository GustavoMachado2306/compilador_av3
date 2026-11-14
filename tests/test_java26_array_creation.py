import unittest
from src.main import analyze_source
from src.compiler.ast_nodes import ArrayCreationExpression, ArrayInitializer


class TestJava26ArrayCreationS83(unittest.TestCase):
    """S8.3 — Criação de arrays: dimensões, dimensões parciais, inicializadores e validações (JLS §10.6, §15.10.1)."""

    def test_01_sized_partial_and_initializer_array_creations(self):
        source = """
        class ArrCreate {
            void f() {
                int[] valores = new int[10];
                int[][] matriz = new int[3][4];
                int[][] irregular = new int[3][];
                int[] inicializado = new int[] {1, 2, 3};
                String[] nomes = {"Ana", "João"};
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0].initializer, ArrayCreationExpression)
        self.assertIsInstance(stmts[2].initializer, ArrayCreationExpression)
        self.assertIsInstance(stmts[3].initializer, ArrayCreationExpression)
        self.assertIsInstance(stmts[4].initializer, ArrayInitializer)

    def test_02_empty_dimension_before_sized_dimension_rejected(self):
        bad = "class C { void f() { int[][] m = new int[][3]; } }"
        self.assertFalse(analyze_source(bad).success)

    def test_03_dimension_size_combined_with_initializer_rejected(self):
        bad = "class C { void f() { int[] v = new int[3] {1, 2, 3}; } }"
        self.assertFalse(analyze_source(bad).success)

    def test_04_non_integral_dimension_expression_rejected(self):
        bad1 = "class C { void f() { int[] v = new int[2.5]; } }"
        bad2 = 'class C { void f() { int[] v = new int["10"]; } }'
        bad3 = "class C { void f() { int[] v = new int[10L]; } }"
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)
        self.assertFalse(analyze_source(bad3).success)

    def test_05_incompatible_initializer_elements_rejected(self):
        bad1 = 'class C { void f() { int[] v = {"a", "b"}; } }'
        bad2 = "class C { void f() { String[] s = {1, 2}; } }"
        bad3 = 'class C { void f() { int[][] m = {{1}, {"x"}}; } }'
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)
        self.assertFalse(analyze_source(bad3).success)

    def test_06_var_with_shorthand_array_initializer_rejected(self):
        bad = "class C { void f() { var v = {1, 2, 3}; } }"
        self.assertFalse(analyze_source(bad).success)


if __name__ == "__main__":
    unittest.main()

