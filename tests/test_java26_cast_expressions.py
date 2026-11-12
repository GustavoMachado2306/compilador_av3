import unittest
from src.main import analyze_source
from src.ast_nodes import CastExpression, BinaryOp


class TestJava26CastExpressionsS82(unittest.TestCase):
    """S8.2 — Expressões de cast: AST, desambiguação, interseção, genéricos, arrays e instanceof (JLS §15.16, §15.20)."""

    def test_01_cast_ast_structure_and_bounds(self):
        source = """
        class CastAST {
            void f(Object o) {
                String s = (String) o;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmt = res.ast.type_declarations[0].members[0].body.statements[0]
        expr = stmt.initializer
        self.assertIsInstance(expr, CastExpression)
        self.assertEqual(expr.target_type.name, "String")
        self.assertEqual(len(expr.additional_bounds), 0)

    def test_02_disambiguation_parenthesized_expression_vs_cast(self):
        source = """
        class Disambig {
            void f(int a, int b) {
                int x = (a + b) * 2;
                double d = (double) a / b;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        # x = (a + b) * 2
        self.assertIsInstance(stmts[0].initializer, BinaryOp)
        self.assertIsInstance(stmts[0].initializer.left, BinaryOp)
        # d = (double) a / b
        self.assertIsInstance(stmts[1].initializer, BinaryOp)
        self.assertIsInstance(stmts[1].initializer.left, CastExpression)

    def test_03_intersection_cast_ast_and_semantics(self):
        source = """
        import java.io.Serializable;
        class InterCast {
            void f(Object o) {
                var r = (CharSequence & Serializable) o;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmt = res.ast.type_declarations[0].members[0].body.statements[0]
        expr = stmt.initializer
        self.assertIsInstance(expr, CastExpression)
        self.assertEqual(expr.target_type.name, "CharSequence")
        self.assertEqual(len(expr.additional_bounds), 1)
        self.assertEqual(expr.additional_bounds[0].name, "Serializable")

    def test_04_intersection_cast_rejects_primitive_and_class_in_bounds(self):
        bad_prim = "class C { void f(Object o) { Object r = (int & CharSequence) o; } }"
        self.assertFalse(analyze_source(bad_prim).success)

        bad_class = "class Base {} class Extra {} class C { void f(Object o) { Object r = (Base & Extra) o; } }"
        self.assertFalse(analyze_source(bad_class).success)

    def test_05_parameterized_type_cast_compatibilities(self):
        ok = """
        import java.util.List;
        class GenCast {
            void f(List<?> wildcardList) {
                List<String> list = (List<String>) wildcardList;
            }
        }
        """
        self.assertTrue(analyze_source(ok).success)

        bad = """
        import java.util.List;
        class GenCast {
            void f(List<String> strList) {
                List<Integer> intList = (List<Integer>) strList;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_06_void_and_var_cast_rejected_at_parse_time(self):
        bad_void = "class C { void f(Object o) { Object x = (void) o; } }"
        self.assertFalse(analyze_source(bad_void).success)

        bad_var = "class C { void f(Object o) { Object x = (var) o; } }"
        self.assertFalse(analyze_source(bad_var).success)

    def test_07_instanceof_with_object_and_integer_valid(self):
        source = """
        class InstTest {
            void f() {
                Object objeto = "texto";
                boolean resultado = objeto instanceof Integer;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_08_instanceof_preview_flag_strictness(self):
        source = """
        class InstPreview {
            void f(Object o) {
                boolean r = o instanceof int;
            }
        }
        """
        res_default = analyze_source(source, enable_preview_primitive_patterns=False)
        self.assertFalse(res_default.success)

        res_preview = analyze_source(source, enable_preview_primitive_patterns=True)
        self.assertTrue(res_preview.success, msg=res_preview.semantic_errors)


if __name__ == "__main__":
    unittest.main()

