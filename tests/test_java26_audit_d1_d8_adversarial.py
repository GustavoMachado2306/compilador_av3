import unittest

from src.compiler.lexer import Lexer
from src.main import analyze_source
from src.compiler.parser import Parser
from src.compiler.semantic import SemanticAnalyzer
from src.compiler.symbol_table import SymbolTable


class TestJava26AuditD1D8Adversarial(unittest.TestCase):
    """Testes adversariais e de regressão cruzada da auditoria independente D1–D8."""

    def test_d1_d2_d7_record_and_type_pattern_generics_and_diamond(self):
        # Record não genérico com argumentos explícitos deve ser rejeitado
        res_nongen = analyze_source(
            """
            record P(int x) {}
            class C {
                void f(Object o) {
                    if (o instanceof P<String>(var a)) {}
                }
            }
            """
        )
        self.assertFalse(res_nongen.success)
        self.assertTrue(
            any("não é genérico" in e for e in res_nongen.semantic_errors),
            msg=res_nongen.semantic_errors,
        )

        # Bound violado em RecordPattern deve ser rejeitado
        res_bad_bound = analyze_source(
            """
            record BoxN<T extends Number>(T v) {}
            class C {
                void f(Object o) {
                    if (o instanceof BoxN<String>(var a)) {}
                }
            }
            """
        )
        self.assertFalse(res_bad_bound.success)
        self.assertTrue(
            any("limite 'Number'" in e for e in res_bad_bound.semantic_errors),
            msg=res_bad_bound.semantic_errors,
        )

        # Diamond '<>' fora de new deve ser rejeitado em RecordPattern e TypePattern
        for src in (
            "record Box<T>(T v) {} class C { void f(Object o) { if (o instanceof Box<>(var a)) {} } }",
            "class Box<T> {} class C { void f(Object o) { if (o instanceof Box<> b) {} } }",
        ):
            res_dia = analyze_source(src)
            self.assertFalse(res_dia.success, msg=src)
            self.assertTrue(
                any("diamond '<>'" in e for e in res_dia.semantic_errors),
                msg=res_dia.semantic_errors,
            )

        # RecordPattern sem '<>' (inferido) e com bound válido devem continuar passando
        res_ok = analyze_source(
            """
            record BoxN<T extends Number>(T v) {}
            class C {
                void f(Object o, BoxN<Integer> b) {
                    if (o instanceof BoxN<Integer>(var a)) {}
                    if (o instanceof BoxN(var a)) {}
                    switch (b) {
                        case BoxN(Integer n) -> {}
                    }
                }
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

    def test_d2_cyclic_vs_f_bounded_type_parameter_bounds(self):
        for bad_src in (
            "class C<T extends T> {}",
            "class C<T extends U, U extends T> {}",
            "class C { <T extends U, U extends T> void m() {} }",
        ):
            res = analyze_source(bad_src)
            self.assertFalse(res.success, msg=bad_src)
            self.assertTrue(
                any("Dependência cíclica" in e for e in res.semantic_errors),
                msg=res.semantic_errors,
            )

        ok_src = """
        interface I<X> {}
        class FBound<T extends Comparable<T>> {}
        class MutualFBound<T extends I<S>, S extends I<T>> {
            <A extends Comparable<A>, B extends A> B id(B b) { return b; }
        }
        """
        res_ok = analyze_source(ok_src)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

    def test_d3_method_ref_constructor_enclosing_and_qualified_no_crash(self):
        # Não pode gerar AttributeError para Outer.Inner::new e deve rejeitar em contexto estático
        for bad_src in (
            """
            import java.util.function.Supplier;
            class Outer {
                class Inner {}
                static void m() { Supplier<Inner> s = Inner::new; }
            }
            """,
            """
            import java.util.function.Supplier;
            class Outer {
                class Inner {}
                static void m() { Supplier<Outer.Inner> s = Outer.Inner::new; }
            }
            """,
            """
            import java.util.function.Function;
            class Outer {
                class Inner {}
                static void m() { Function<Outer, Outer.Inner> f = Outer.Inner::new; }
            }
            """,
            """
            class Outer {
                class Inner {}
                static void m() {
                    Runnable r = new Runnable() {
                        public void run() { new Inner(); }
                    };
                }
            }
            """,
        ):
            res = analyze_source(bad_src)
            self.assertFalse(res.success, msg=bad_src)
            self.assertTrue(res.semantic_errors, msg=bad_src)

        ok_src = """
        import java.util.function.Supplier;
        class Outer {
            class Inner {}
            static class Nested {}
            void inst() {
                Supplier<Inner> s1 = Inner::new;
                Supplier<Outer.Inner> s2 = Outer.Inner::new;
            }
            static void stat() {
                Supplier<Outer.Nested> s3 = Outer.Nested::new;
                Supplier<Nested> s4 = Nested::new;
            }
        }
        """
        res_ok = analyze_source(ok_src)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

    def test_d4_generic_array_creation_and_method_ref_variants(self):
        for bad_src in (
            "import java.util.List; class C { Object a = new List<String>[2][3]; }",
            "import java.util.List; import java.util.function.IntFunction; class C { IntFunction<List<String>[]> f = List<String>[]::new; }",
            "import java.util.List; class C { Object a = new List<? extends Number>[2]; }",
        ):
            res = analyze_source(bad_src)
            self.assertFalse(res.success, msg=bad_src)
            self.assertTrue(res.semantic_errors, msg=bad_src)

        res_ok = analyze_source(
            """
            import java.util.List;
            import java.util.function.IntFunction;
            class C {
                List<?>[] a = new List<?>[2];
                List<?>[][] b = new List<?>[2][3];
                IntFunction<String[]> f = String[]::new;
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

    def test_d5_try_with_resources_var_generic_and_order(self):
        ok_src = """
        import java.io.Closeable;
        class GenRes<T extends AutoCloseable> {
            static class MyRes implements AutoCloseable {
                public void close() {}
                void ping() {}
            }
            void f(T ext, Closeable c) throws Exception {
                try (ext; c; var a = new MyRes(); MyRes b = a) {
                    b.ping();
                }
            }
        }
        """
        res_ok = analyze_source(ok_src)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        for bad_src in (
            "class NotRes {} class C { void f() { try (var r = new NotRes()) {} } }",
            "class C { void f() { int x = 1; try (x) {} } }",
            "class R implements AutoCloseable { public void close() {} } class C { void f() { try (R a = b; R b = new R()) {} } }",
        ):
            res_bad = analyze_source(bad_src)
            self.assertFalse(res_bad.success, msg=bad_src)

    def test_d6_switch_unconditional_pattern_reachability(self):
        # Switch statement com pattern incondicional sem guard torna instrução seguinte inalcançável (JLS §14.22)
        for bad_src in (
            """
            class C {
                int f(Object o) {
                    switch (o) {
                        case Object x -> { return 1; }
                    }
                    return 2;
                }
            }
            """,
            """
            class C {
                int f(Object o) {
                    switch (o) {
                        case Object x:
                            return 1;
                    }
                    return 2;
                }
            }
            """,
        ):
            res = analyze_source(bad_src)
            self.assertFalse(res.success, msg=bad_src)
            self.assertTrue(
                any("Instrução inalcançável" in e for e in res.semantic_errors),
                msg=res.semantic_errors,
            )

        # Pattern com guard não é incondicional para alcance: caminho seguinte permanece alcançável
        ok_src = """
        class C {
            int f(Object o) {
                switch (o) {
                    case Object x when o.hashCode() > 0 -> { return 1; }
                    case Object _ -> {}
                }
                return 2;
            }
        }
        """
        res_ok = analyze_source(ok_src)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

    def test_d7_primitive_record_pattern_preview_boundary_with_generics(self):
        src_prim = "record P(int x) {} class C { void f(Object o) { if (o instanceof P(int x)) {} } }"
        self.assertFalse(analyze_source(src_prim, enable_preview_primitive_patterns=False).success)
        self.assertTrue(analyze_source(src_prim, enable_preview_primitive_patterns=True).success)

        src_gen_prim = "record Box<T>(T v) {} class C { void f(Object o) { if (o instanceof Box<Integer>(int x)) {} } }"
        self.assertFalse(analyze_source(src_gen_prim, enable_preview_primitive_patterns=False).success)
        self.assertTrue(analyze_source(src_gen_prim, enable_preview_primitive_patterns=True).success)

        # Sem preview: P(var x) e Box<Integer>(Integer x) funcionam; P(Integer x) rejeitado por incompatibilidade
        self.assertTrue(analyze_source("record P(int x) {} class C { void f(Object o) { if (o instanceof P(var x)) {} } }").success)
        self.assertTrue(analyze_source("record Box<T>(T v) {} class C { void f(Object o) { if (o instanceof Box<Integer>(Integer x)) {} } }").success)
        self.assertFalse(analyze_source("record P(int x) {} class C { void f(Object o) { if (o instanceof P(Integer x)) {} } }").success)

    def test_d8_internal_module_requires_transitive_external_and_boundaries(self):
        u_mod = Parser(Lexer("module app.facade { requires transitive java.sql; exports app.api; }").tokenize()).parse()
        u_api = Parser(Lexer("package app.api; public class Facade { public int ok() { return 1; } }").tokenize()).parse()
        u_cli = Parser(Lexer("import module app.facade; class Cli { Connection c = null; Facade f = null; }").tokenize()).parse()

        sa = SemanticAnalyzer(SymbolTable(), include_stdlib=True)
        errs = sa.analyze_units([u_mod, u_api, u_cli])
        self.assertEqual(errs, [], msg=errs)
        self.assertEqual(sa.unresolved_checks, [], msg=sa.unresolved_checks)


if __name__ == "__main__":
    unittest.main()

