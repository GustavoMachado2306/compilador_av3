import unittest
from src.main import analyze_source
from src.compiler.ast_nodes import (
    Assignment,
    BinaryOp,
    CastExpression,
    ConditionalExpression,
    InstanceOfExpression,
    LambdaExpression,
    MethodCall,
    MemberAccess,
    UnaryOp,
)


class TestJava26ExpressionPrecedenceS8(unittest.TestCase):
    """Valida todos os 17 níveis de precedência e associatividade de expressões (JLS §15)."""

    def _first_init(self, body_code: str):
        source = f"""
        class PrecedenceDemo {{
            void run() {{
                {body_code}
            }}
        }}
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Sintático: {res.syntactic_error} | Semântico: {res.semantic_errors}")
        return res.ast.type_declarations[0].members[0].body.statements

    def test_01_multiplicative_over_additive_and_left_assoc(self):
        stmts = self._first_init("int r = 10 - 2 * 3 + 4 / 2;")
        expr = stmts[0].initializer
        self.assertIsInstance(expr, BinaryOp)
        self.assertEqual(expr.op, "+")
        self.assertIsInstance(expr.left, BinaryOp)
        self.assertEqual(expr.left.op, "-")
        self.assertIsInstance(expr.left.right, BinaryOp)
        self.assertEqual(expr.left.right.op, "*")
        self.assertIsInstance(expr.right, BinaryOp)
        self.assertEqual(expr.right.op, "/")

    def test_02_unary_and_postfix_over_multiplicative(self):
        stmts = self._first_init("int a = 5; int r = -a++ * 2;")
        expr = stmts[1].initializer
        self.assertIsInstance(expr, BinaryOp)
        self.assertEqual(expr.op, "*")
        self.assertIsInstance(expr.left, UnaryOp)
        self.assertEqual(expr.left.op, "-")
        self.assertIsInstance(expr.left.operand, UnaryOp)
        self.assertEqual(expr.left.operand.op, "++")
        self.assertTrue(expr.left.operand.is_postfix)

    def test_03_shift_below_additive_above_relational(self):
        stmts = self._first_init("boolean b = 1 + 2 << 1 < 10;")
        expr = stmts[0].initializer
        self.assertIsInstance(expr, BinaryOp)
        self.assertEqual(expr.op, "<")
        self.assertIsInstance(expr.left, BinaryOp)
        self.assertEqual(expr.left.op, "<<")
        self.assertIsInstance(expr.left.left, BinaryOp)
        self.assertEqual(expr.left.left.op, "+")

    def test_04_relational_and_instanceof_above_equality(self):
        stmts = self._first_init('Object x = "ok"; boolean b = x instanceof String == true;')
        expr = stmts[1].initializer
        self.assertIsInstance(expr, BinaryOp)
        self.assertEqual(expr.op, "==")
        self.assertIsInstance(expr.left, InstanceOfExpression)

    def test_05_bitwise_hierarchy_and_xor_or(self):
        stmts = self._first_init("int r = 1 | 2 ^ 3 & 4;")
        expr = stmts[0].initializer
        self.assertIsInstance(expr, BinaryOp)
        self.assertEqual(expr.op, "|")
        self.assertIsInstance(expr.right, BinaryOp)
        self.assertEqual(expr.right.op, "^")
        self.assertIsInstance(expr.right.right, BinaryOp)
        self.assertEqual(expr.right.right.op, "&")

    def test_06_logical_and_over_logical_or(self):
        stmts = self._first_init("boolean r = false || true && false;")
        expr = stmts[0].initializer
        self.assertIsInstance(expr, BinaryOp)
        self.assertEqual(expr.op, "||")
        self.assertIsInstance(expr.right, BinaryOp)
        self.assertEqual(expr.right.op, "&&")

    def test_07_ternary_right_associative(self):
        stmts = self._first_init("boolean c1 = true; boolean c2 = false; int r = c1 ? 1 : c2 ? 2 : 3;")
        expr = stmts[2].initializer
        self.assertIsInstance(expr, ConditionalExpression)
        self.assertIsInstance(expr.else_expr, ConditionalExpression)

    def test_08_assignment_right_associative_and_below_ternary(self):
        stmts = self._first_init("int a = 0; int b = 0; boolean c = true; a = b = c ? 10 : 20;")
        expr = stmts[3]
        self.assertIsInstance(expr, Assignment)
        self.assertIsInstance(expr.expression, Assignment)
        self.assertIsInstance(expr.expression.expression, ConditionalExpression)

    def test_09_cast_and_lambda_precedence_in_assignment_and_ternary(self):
        source = """
        interface F { int apply(int x); }
        class Demo {
            void run(boolean flag, Object obj) {
                F f = (F) (x -> x + 1);
                F g = flag ? x -> x + 1 : x -> x - 1;
                String s = (String) obj;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[1].members[0].body.statements
        self.assertIsInstance(stmts[0].initializer, CastExpression)
        self.assertIsInstance(stmts[0].initializer.expression, LambdaExpression)
        self.assertIsInstance(stmts[1].initializer, ConditionalExpression)
        self.assertIsInstance(stmts[1].initializer.then_expr, LambdaExpression)
        self.assertIsInstance(stmts[1].initializer.else_expr, LambdaExpression)
        self.assertIsInstance(stmts[2].initializer, CastExpression)

    # ---- S8.1: precedência/associatividade adicionais, verificadas pela AST ----
    def test_10_prompt_examples_a_to_f(self):
        stmts = self._first_init(
            "int a = 2 + 3 * 4; int b = (2 + 3) * 4; int c = 20 - 5 - 3;"
            " int d = a << 2 + 1; boolean e = a > b && c < d; int f = a > b ? c : d;"
        )
        a = stmts[0].initializer
        self.assertEqual((a.op, a.right.op), ("+", "*"))
        b = stmts[1].initializer
        self.assertEqual((b.op, b.left.op), ("*", "+"))
        c = stmts[2].initializer
        self.assertEqual((c.op, c.left.op), ("-", "-"))
        self.assertNotIsInstance(c.right, BinaryOp)
        d = stmts[3].initializer
        self.assertEqual((d.op, d.right.op), ("<<", "+"))
        e = stmts[4].initializer
        self.assertEqual((e.op, e.left.op, e.right.op), ("&&", ">", "<"))
        f = stmts[5].initializer
        self.assertIsInstance(f, ConditionalExpression)
        self.assertEqual(f.condition.op, ">")

    def test_11_bitwise_levels_and_below_equality(self):
        # & > ^ > | ; todos abaixo de ==
        expr = self._first_init("int a = 1; int r = a | a ^ a & a;")[1].initializer
        self.assertEqual(expr.op, "|")
        self.assertEqual(expr.right.op, "^")
        self.assertEqual(expr.right.right.op, "&")
        expr = self._first_init("int a = 1; boolean r = a & 1 == 1;".replace("a & 1 == 1", "true & a == 1"))[1].initializer
        self.assertEqual(expr.op, "&")
        self.assertEqual(expr.right.op, "==")

    def test_12_logical_and_over_or_and_below_bitwise(self):
        expr = self._first_init("boolean a = true; boolean r = a || a && a | a;")[1].initializer
        self.assertEqual(expr.op, "||")
        self.assertEqual(expr.right.op, "&&")
        self.assertEqual(expr.right.right.op, "|")

    def test_13_equality_and_relational_left_associative(self):
        expr = self._first_init("boolean r = 1 < 2 == 3 > 4;")[0].initializer
        self.assertEqual(expr.op, "==")
        self.assertEqual(expr.left.op, "<")
        self.assertEqual(expr.right.op, ">")
        expr = self._first_init("boolean r = true == false != true;")[0].initializer
        self.assertEqual(expr.op, "!=")
        self.assertEqual(expr.left.op, "==")

    def test_14_shift_left_associative_and_unsigned(self):
        expr = self._first_init("int r = 64 >> 2 >>> 1 << 1;")[0].initializer
        self.assertEqual(expr.op, "<<")
        self.assertEqual(expr.left.op, ">>>")
        self.assertEqual(expr.left.left.op, ">>")

    def test_15_ternary_right_associative(self):
        expr = self._first_init("boolean a = true; boolean b = false; int r = a ? 1 : b ? 2 : 3;")[2].initializer
        self.assertIsInstance(expr, ConditionalExpression)
        self.assertIsInstance(expr.else_expr, ConditionalExpression)
        self.assertNotIsInstance(expr.then_expr, ConditionalExpression)

    def test_16_ternary_below_logical_or(self):
        expr = self._first_init("boolean a = true; int r = a || a ? 1 : 2;")[1].initializer
        self.assertIsInstance(expr, ConditionalExpression)
        self.assertEqual(expr.condition.op, "||")

    def test_17_compound_assignment_right_associative(self):
        stmts = self._first_init("int a = 1; int b = 1; a += b -= 2;")
        expr = stmts[2]
        self.assertIsInstance(expr, Assignment)
        self.assertEqual(expr.operator, "+=")
        self.assertIsInstance(expr.expression, Assignment)
        self.assertEqual(expr.expression.operator, "-=")

    def test_18_unary_binds_tighter_than_binary_and_cast(self):
        expr = self._first_init("int a = 2; int r = - a * 3;")[1].initializer
        self.assertEqual(expr.op, "*")
        self.assertIsInstance(expr.left, UnaryOp)
        expr = self._first_init("double d = 1.5; int r = (int) d + 1;")[1].initializer
        self.assertEqual(expr.op, "+")
        self.assertIsInstance(expr.left, CastExpression)

    def test_19_not_and_bitwise_complement_prefix_nesting(self):
        expr = self._first_init("boolean r = !!true;")[0].initializer
        self.assertIsInstance(expr, UnaryOp)
        self.assertIsInstance(expr.operand, UnaryOp)
        expr = self._first_init("int r = - -1;")[0].initializer
        self.assertEqual(expr.op, "-")
        self.assertIsInstance(expr.operand, UnaryOp)

    def test_20_instanceof_relational_level(self):
        expr = self._first_init("Object o = null; boolean r = o instanceof String && 1 + 1 > 1;")[1].initializer
        self.assertEqual(expr.op, "&&")
        self.assertIsInstance(expr.left, InstanceOfExpression)
        self.assertEqual(expr.right.op, ">")
        self.assertEqual(expr.right.left.op, "+")

    def test_21_parentheses_override_precedence(self):
        expr = self._first_init("boolean a = true; boolean r = (a || a) && a;")[1].initializer
        self.assertEqual(expr.op, "&&")
        self.assertEqual(expr.left.op, "||")


if __name__ == "__main__":
    unittest.main()
