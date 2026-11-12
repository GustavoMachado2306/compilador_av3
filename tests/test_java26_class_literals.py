import unittest
from src.main import analyze_source
from src.ast_nodes import ClassLiteral


class TestJava26ClassLiteralsS85(unittest.TestCase):
    """Valida class literals (.class) e expressões primárias qualificadas (Outer.this / Outer.super)."""

    def test_01_reference_and_primitive_class_literals(self):
        source = """
        class Cls {
            void m() {
                Class<?> c1 = String.class;
                Class<?> c2 = int.class;
                Class<?> c3 = double.class;
                Class<?> c4 = boolean.class;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0].initializer, ClassLiteral)
        self.assertIsInstance(stmts[1].initializer, ClassLiteral)

    def test_02_void_and_array_class_literals(self):
        source = """
        class Cls {
            void m() {
                Class<?> v = void.class;
                Class<?> a1 = int[].class;
                Class<?> a2 = String[][].class;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_class_literal_generic_type_argument_compatibility(self):
        source = """
        class Cls {
            void m() {
                Class<String> cs = String.class;
                Class<Integer> ci = int.class;
                Class<Void> cv = void.class;
                Class<int[]> ca = int[].class;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_class_literal_generic_mismatch_rejected(self):
        bad1 = "class Cls { void m() { Class<String> c = int.class; } }"
        bad2 = "class Cls { void m() { Class<Integer> c = String.class; } }"
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_05_class_literal_member_access_and_method_call(self):
        source = """
        class Cls {
            void m() {
                String nome = String.class.getName();
                String simples = int[].class.getSimpleName();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_06_outer_this_and_outer_super_qualified_expressions(self):
        source = """
        class Base {
            int baseVal = 5;
            int getBase() { return baseVal; }
        }
        class Outer extends Base {
            int outerVal = 10;
            class Inner {
                int soma() {
                    return Outer.this.outerVal + Outer.super.baseVal + Outer.super.getBase();
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_07_outer_this_in_static_context_rejected(self):
        bad = """
        class Outer {
            int x = 1;
            static void m() {
                int y = Outer.this.x;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)


if __name__ == "__main__":
    unittest.main()

