"""Suíte de Testes para a Correção D4 — Arrays Genéricos e Reificabilidade (JLS §4.7 / §15.10.1 / §15.13.1)."""

import unittest

from src.main import analyze_source


class TestJava26GenericArrayReifiabilityD4(unittest.TestCase):
    def test_01_valid_reifiable_array_creations(self):
        code = """
        import java.util.*;
        import java.util.function.*;
        class Outer<T> {
            static class Nested<U> {}
            class NonGenInner {}
        }
        class OkArrays {
            void m() {
                int[] a1 = new int[3];
                String[][] a2 = new String[2][3];
                List[] a3 = new List[2];
                List<?>[] a4 = new List<?>[2];
                Map<?, ?>[][] a5 = new Map<?, ?>[2][2];
                Object a6 = new Outer.Nested<?>[2];
                IntFunction<List<?>[]> r1 = List<?>[]::new;
                IntFunction<Map<?, ?>[]> r2 = Map<?, ?>[]::new;
                IntFunction<List[]> r3 = List[]::new;
                IntFunction<Outer.Nested<?>[]> r4 = Outer.Nested<?>[]::new;
            }
        }
        """
        res = analyze_source(code)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_non_reifiable_array_creations_rejected(self):
        bad_cases = [
            (
                "new List<String>[2]",
                "import java.util.*; class A { void m() { Object x = new List<String>[2]; } }",
            ),
            (
                "new List<String>[] init",
                "import java.util.*; class A { void m() { List<String>[] x = new List<String>[] { null }; } }",
            ),
            (
                "bounded wildcard extends",
                "import java.util.*; class A { void m() { Object x = new List<? extends Number>[2]; } }",
            ),
            (
                "bounded wildcard super",
                "import java.util.*; class A { void m() { Object x = new List<? super Integer>[2]; } }",
            ),
            (
                "nested generic arg",
                "import java.util.*; class A { void m() { Object x = new List<List<?>>[2]; } }",
            ),
            (
                "multidim parameterized",
                "import java.util.*; class A { void m() { Object x = new List<String>[2][3]; } }",
            ),
            (
                "type variable T[]",
                "class A<T> { void m() { Object x = new T[2]; } }",
            ),
            (
                "method type variable U[][]",
                "class A { <U> void m() { Object x = new U[2][]; } }",
            ),
            (
                "method ref List<String>[]::new",
                "import java.util.*; import java.util.function.*; class A { void m() { IntFunction<Object> f = List<String>[]::new; } }",
            ),
            (
                "method ref List<? extends Number>[]::new",
                "import java.util.*; import java.util.function.*; class A { void m() { IntFunction<Object> f = List<? extends Number>[]::new; } }",
            ),
            (
                "method ref T[]::new",
                "import java.util.function.*; class A<T> { void m() { IntFunction<Object> f = T[]::new; } }",
            ),
            (
                "qualified nested parameterized array new Outer.Nested<String>[2]",
                "class Outer { static class Nested<U> {} } class A { void m() { Object x = new Outer.Nested<String>[2]; } }",
            ),
            (
                "qualified nested parameterized method ref Outer.Nested<String>[]::new",
                "import java.util.function.*; class Outer { static class Nested<U> {} } class A { void m() { IntFunction<Object> f = Outer.Nested<String>[]::new; } }",
            ),
        ]
        for label, src in bad_cases:
            with self.subTest(case=label):
                res = analyze_source(src)
                self.assertFalse(res.success, msg=f"Esperado erro de não reificabilidade para: {label}")
                self.assertTrue(
                    any("reific" in e.lower() for e in res.semantic_errors),
                    msg=res.semantic_errors,
                )

    def test_03_declarations_casts_and_conversions_remain_allowed(self):
        code = """
        import java.util.*;
        class Conv<T> {
            List<String>[] fieldArr;
            T[] genericFieldArr;
            List<String>[] method(List<String>[] param, T... varargs) {
                List<String>[] local = null;
                List<String>[] cast = (List<String>[]) (Object) new List<?>[2];
                Object[] up = new List<?>[2];
                return local;
            }
        }
        """
        res = analyze_source(code)
        self.assertTrue(res.success, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()
