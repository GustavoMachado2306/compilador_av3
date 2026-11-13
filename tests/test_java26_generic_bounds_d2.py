"""
Suíte de Testes para a Correção D2 — Validação de Bounds Genéricos (JLS §4.5).
Construída incrementalmente por fases (Fase 1 -> Fase 4).
"""

import tempfile
import unittest
from pathlib import Path

from src.lexer import Lexer
from src.main import analyze_source
from src.parser import Parser
from src.semantic import SemanticAnalyzer
from src.symbol_table import SymbolTable
from tests.test_java26_generic_arity_d1 import _build_minimal_generic_class_bytes


def _analyze_with_sem(code: str):
    ast = Parser(Lexer(code).tokenize()).parse()
    sem = SemanticAnalyzer(SymbolTable())
    sem.analyze(ast)
    return sem


class TestJava26GenericBoundsD2(unittest.TestCase):
    # =========================================================================
    # FASE 1 — ESCOPOS E INFRAESTRUTURA
    # =========================================================================

    def test_f1_01_type_param_scope_cleaned_after_analyze(self):
        code = """
        class Caixa<T extends Number> {
            T v;
            <M extends Comparable<M>> Caixa<T> id(M m) { return this; }
        }
        interface Ordem<U extends Comparable<U>> {
            <R extends Number> R obter(U u);
        }
        record Par<A extends Number, B extends A>(A a, B b) {
            <K extends B> K eco(K k) { return k; }
        }
        """
        sem = _analyze_with_sem(code)
        self.assertEqual(sem.errors, [])
        self.assertEqual(sem._active_type_params, [])

    def test_f1_02_type_param_visible_during_bounds_and_headers(self):
        observed_in_bounds = {}
        code = """
        class Base<X extends Number> {}
        class Sub<T extends Number> extends Base<T> {
            <U extends T> Base<U> mk(U u) { return new Base<U>(); }
        }
        class Cicl<T extends Comparable<T>> {}
        """
        ast = Parser(Lexer(code).tokenize()).parse()
        sem = SemanticAnalyzer(SymbolTable())
        orig_check = sem._check_type_ref_annotations

        def spy(type_ref, skip_type_access=False, skip_arity=False):
            if type_ref is not None and getattr(type_ref, "name", None) in ("Base", "Comparable"):
                observed_in_bounds[getattr(type_ref, "name")] = (
                    sem._lookup_type_param_bounds("T"),
                    sem._lookup_type_param_bounds("U"),
                )
            return orig_check(type_ref, skip_type_access=skip_type_access, skip_arity=skip_arity)

        sem._check_type_ref_annotations = spy
        sem.analyze(ast)
        self.assertEqual(sem.errors, [])
        self.assertEqual(observed_in_bounds["Comparable"], (["Comparable<T>"], None))
        self.assertEqual(observed_in_bounds["Base"], (["Number"], ["T"]))

    def test_f1_03_static_vs_instance_type_param_distinction(self):
        seen = {}
        code = """
        class Outer<T extends Number> {
            static <M extends Comparable<M>> M sm(M m) { return m; }
            <M extends T> T im(M m) { return m; }
            static class StaticNested<S extends Number> {
                S val;
            }
            static void hostMethod() {
                class LocalInStatic<L extends Number> {
                    L x;
                }
            }
        }
        """
        ast = Parser(Lexer(code).tokenize()).parse()
        sem = SemanticAnalyzer(SymbolTable())
        orig_method = sem._analyze_method_member
        orig_class = sem.analyze_class

        def spy_method(member, *args, **kwargs):
            res = orig_method(member, *args, **kwargs)
            return res

        orig_check = sem._check_type_ref_annotations

        def spy_check(type_ref, skip_type_access=False, skip_arity=False):
            if type_ref is not None and getattr(type_ref, "name", None) in ("T", "M", "S", "L"):
                seen.setdefault(getattr(type_ref, "name"), []).append(
                    (
                        sem._in_static_context,
                        sem._lookup_type_param_bounds("T"),
                        sem._lookup_type_param_bounds(getattr(type_ref, "name")),
                    )
                )
            return orig_check(type_ref, skip_type_access=skip_type_access, skip_arity=skip_arity)

        sem._check_type_ref_annotations = spy_check
        sem.analyze(ast)
        self.assertEqual(sem.errors, [])
        # Em método estático: T da classe externa fica oculto, M do método permanece visível
        m_static_entries = [e for e in seen["M"] if e[0] is True]
        self.assertTrue(m_static_entries)
        self.assertIsNone(m_static_entries[0][1])
        self.assertEqual(m_static_entries[0][2], ["Comparable<M>"])
        # Em static nested class e classe local em método estático: S e L são visíveis; T da Outer não
        self.assertEqual(seen["S"], [(False, None, ["Number"])])
        self.assertEqual(seen["L"], [(False, None, ["Number"])])

    def test_f1_04_enum_generic_supertype_preserves_comparable(self):
        code = """
        enum Dia {
            SEG, TER
        }
        enum ComCorpo {
            A { int f() { return 1; } };
            abstract int f();
        }
        """
        sem = _analyze_with_sem(code)
        self.assertEqual(sem.errors, [])
        self.assertIn("Enum<Dia>", sem._direct_supertypes("Dia")[0])
        self.assertTrue(sem._is_subtype("Dia", "Enum<Dia>"))
        self.assertTrue(sem._is_subtype("Dia", "Comparable<Dia>"))
        self.assertTrue(sem._is_subtype("Dia", "Enum"))
        self.assertTrue(sem._is_subtype("ComCorpo", "Comparable<ComCorpo>"))
        self.assertFalse(sem._is_subtype("String", "Enum<String>"))

    def test_f1_05_type_param_decls_and_substitution(self):
        code = """
        import java.util.*;
        class Caixa<T extends Number> {}
        class Outer {
            class Inner<K extends Comparable<K>, V> {}
        }
        class Par<A, B extends List<A>> {}
        """
        sem = _analyze_with_sem(code)
        self.assertEqual(sem.errors, [])
        self.assertEqual(sem._type_param_decls_for_type("Caixa"), [("T", ["Number"])])
        self.assertEqual(
            sem._type_param_decls_for_type("Outer.Inner"),
            [("K", ["Comparable<K>"]), ("V", ["Object"])],
        )
        self.assertEqual(
            sem._type_param_decls_for_type("java.util.EnumMap"),
            [("K", ["Enum<K>"]), ("V", ["Object"])],
        )
        mapping = sem._type_var_mapping_for_type("Par<String, List<String>>")
        self.assertEqual(mapping, {"A": "String", "B": "List<String>"})
        self.assertEqual(sem._substitute_type_vars("List<A>", mapping), "List<String>")

    # =========================================================================
    # FASE 2 — BOUNDS DE ARGUMENTOS CONCRETOS
    # =========================================================================

    def test_f2_01_simple_bounds_positive_and_negative(self):
        res_ok = analyze_source(
            """
            class Caixa<T extends Number> {}
            class Uso {
                Caixa<Integer> a;
                Caixa<Double> b;
                Caixa<Number> c;
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        res_bad_str = analyze_source(
            "class Caixa<T extends Number> {} class Uso { Caixa<String> b; }"
        )
        self.assertFalse(res_bad_str.success)
        self.assertTrue(
            any("String" in e and "Number" in e for e in res_bad_str.semantic_errors),
            msg=res_bad_str.semantic_errors,
        )

        res_bad_obj = analyze_source(
            "class Caixa<T extends Number> {} class Uso { Caixa<Object> b; }"
        )
        self.assertFalse(res_bad_obj.success)

    def test_f2_02_multiple_bounds_class_and_interfaces(self):
        decl = """
        interface I1 {}
        interface I2 {}
        class Base {}
        class Bom extends Base implements I1, I2 {}
        class SoBase extends Base {}
        class SoIfaces implements I1, I2 {}
        class Multi<T extends Base & I1 & I2> {}
        """
        res_ok = analyze_source(decl + "class Uso { Multi<Bom> ok; }")
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        res_bad_missing_iface = analyze_source(decl + "class Uso { Multi<SoBase> bad; }")
        self.assertFalse(res_bad_missing_iface.success)

        res_bad_missing_class = analyze_source(decl + "class Uso { Multi<SoIfaces> bad; }")
        self.assertFalse(res_bad_missing_class.success)

        # Bounds com parâmetro genérico: S extends Number & Comparable<S>
        res_ok_num = analyze_source(
            """
            class NumComp<S extends Number & Comparable<S>> {}
            class Uso { NumComp<Integer> x; NumComp<Double> y; }
            """
        )
        self.assertTrue(res_ok_num.success, msg=res_ok_num.semantic_errors)

        res_bad_num = analyze_source(
            """
            class NumComp<S extends Number & Comparable<S>> {}
            class Uso { NumComp<Number> bad; }
            """
        )
        self.assertFalse(res_bad_num.success)

    def test_f2_03_dependent_type_parameters(self):
        decl = """
        import java.util.*;
        class Par<A, B extends List<A>> {}
        class Fwd<A extends Number, B extends A> {}
        """
        res_ok = analyze_source(
            decl
            + """
            class Uso {
                Par<String, List<String>> p1;
                Par<String, ArrayList<String>> p2;
                Fwd<Number, Integer> f1;
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        res_bad_par = analyze_source(
            decl + "class Uso { Par<String, List<Integer>> bad; }"
        )
        self.assertFalse(res_bad_par.success)

        res_bad_fwd = analyze_source(
            decl + "class Uso { Fwd<Integer, Number> bad; }"
        )
        self.assertFalse(res_bad_fwd.success)

    def test_f2_04_f_bounded_polymorphism_and_enums(self):
        res_ok = analyze_source(
            """
            import java.util.*;
            enum Dia { SEG, TER }
            class Rec<T extends Comparable<T>> {}
            class CustomComp implements Comparable<CustomComp> {
                public int compareTo(CustomComp o) { return 0; }
            }
            class Uso {
                Rec<String> a;
                Rec<Integer> b;
                Rec<Dia> c;
                Rec<CustomComp> d;
                EnumSet<Dia> es;
                EnumMap<Dia, String> em;
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        for bad_type in ("Rec<Object>", "EnumSet<String>", "EnumMap<String, Integer>"):
            with self.subTest(bad_type=bad_type):
                res_bad = analyze_source(
                    f"""
                    import java.util.*;
                    class Rec<T extends Comparable<T>> {{}}
                    class Uso {{ {bad_type} bad; }}
                    """
                )
                self.assertFalse(res_bad.success, msg=bad_type)

    def test_f2_05_generic_inheritance_and_method_type_params(self):
        res_ok = analyze_source(
            """
            interface Portador<T extends Number> {}
            class Caixa<T extends Number> implements Portador<T> {}
            class Sub<U extends Integer> extends Caixa<U> {
                static <M extends Number> Caixa<M> empacotar(M m) {
                    return new Caixa<M>();
                }
                <K extends U> Portador<K> subPorta(K k) {
                    return new Caixa<K>();
                }
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        res_bad_ext = analyze_source(
            """
            class Caixa<T extends Number> {}
            class Sub<U> extends Caixa<U> {}
            """
        )
        self.assertFalse(res_bad_ext.success)

        res_bad_impl = analyze_source(
            """
            interface Portador<T extends Number> {}
            class Bad implements Portador<String> {}
            """
        )
        self.assertFalse(res_bad_impl.success)

        res_bad_static_shadow = analyze_source(
            """
            class Outer<T extends Number> {
                class Caixa<X extends Number> {}
                static <M> void bad() {
                    Outer<Integer> o = new Outer<Integer>();
                }
            }
            """
        )
        self.assertTrue(res_bad_static_shadow.success, msg=res_bad_static_shadow.semantic_errors)

    def test_f2_06_unresolved_external_types_do_not_false_positive(self):
        res = analyze_source(
            """
            import com.externo.TipoDesconhecido;
            import com.externo.GenericoExterno;
            class Caixa<T extends Number> {}
            class Uso {
                Caixa<TipoDesconhecido> c;
                GenericoExterno<String> g;
            }
            """
        )
        self.assertTrue(res.success, msg=res.semantic_errors)

    # =========================================================================
    # FASE 3 — WILDCARDS, INTERSEÇÕES, CAPTURA E F-BOUNDS
    # =========================================================================

    def test_f3_01_unbounded_and_upper_bounded_wildcards(self):
        res_ok = analyze_source(
            """
            class Caixa<T extends Number> {}
            class Uso {
                Caixa<?> w1;
                Caixa<? extends Integer> w2;
                Caixa<? extends Number> w3;
                Caixa<? extends Object> w4;
                Caixa<? extends Runnable> w5;
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        # Interseções impossíveis: String é final e Thread é outra classe não relacionada a Number
        for bad in ("Caixa<? extends String>", "Caixa<? extends Thread>"):
            with self.subTest(bad=bad):
                res_bad = analyze_source(
                    f"class Caixa<T extends Number> {{}} class Uso {{ {bad} x; }}"
                )
                self.assertFalse(res_bad.success, msg=bad)

    def test_f3_02_lower_bounded_wildcards(self):
        res_ok = analyze_source(
            """
            class Caixa<T extends Number> {}
            class CharBox<T extends CharSequence> {}
            class Uso {
                Caixa<? super Integer> a;
                Caixa<? super Number> b;
                CharBox<? super String> c;
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        for decl in (
            "class Caixa<T extends Number> {} class Uso { Caixa<? super String> x; }",
            "class Caixa<T extends Number> {} class Uso { Caixa<? super Object> x; }",
            "class Caixa<T extends Number> {} class Uso { Caixa<? super Runnable> x; }",
        ):
            with self.subTest(decl=decl):
                res_bad = analyze_source(decl)
                self.assertFalse(res_bad.success, msg=decl)

    def test_f3_03_multiple_bounds_and_final_or_parameterized_intersections(self):
        base_code = """
        import java.util.*;
        interface I1 {}
        interface I2 {}
        class Base {}
        final class SoBaseFinal extends Base {}
        final class FinalBaseComI1 extends Base implements I1 {}
        class Multi<T extends Base & I1> {}
        class MultiFinal<T extends FinalBaseComI1 & I1> {}
        class Nest<T extends List<? extends Number>> {}
        """
        res_ok = analyze_source(
            base_code
            + """
            class Uso {
                Multi<? extends I2> m1;
                Multi<? extends Base> m2;
                Multi<? extends FinalBaseComI1> m3;
                Nest<? extends Collection<Integer>> n1;
                Nest<? extends ArrayList<? extends Number>> n2;
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        bad_cases = [
            "Multi<? extends SoBaseFinal> bad;",
            "MultiFinal<? extends I2> bad;",
            "Nest<? extends Collection<String>> bad;",
            "Nest<? extends List<String>> bad;",
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad):
                res_bad = analyze_source(base_code + f"class Uso {{ {bad} }}")
                self.assertFalse(res_bad.success, msg=bad)

    def test_f3_04_capture_and_f_bounds_with_wildcards_no_infinite_recursion(self):
        base_code = """
        import java.util.*;
        class Rec<T extends Comparable<T>> {}
        class Self<T extends Self<T>> {}
        final class NoComp {}
        final class BadFinalComp implements Comparable<Integer> {
            public int compareTo(Integer o) { return 0; }
        }
        class OpenWrongComp implements Comparable<String> {
            public int compareTo(String o) { return 0; }
        }
        class Par<A, B extends List<A>> {}
        """
        res_ok = analyze_source(
            base_code
            + """
            class Uso {
                Rec<?> r1;
                Rec<? extends String> r2;
                Rec<? extends Number> r3;
                Self<?> s1;
                Self<? extends Self<?>> s2;
                Par<String, ?> p1;
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        bad_cases = [
            "Rec<? extends NoComp> bad;",
            "Rec<? extends BadFinalComp> bad;",
            "Rec<? extends OpenWrongComp> bad;",
            "Par<?, List<String>> bad;",
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad):
                res_bad = analyze_source(base_code + f"class Uso {{ {bad} }}")
                self.assertFalse(res_bad.success, msg=bad)

    def test_f3_05_wildcards_with_unresolved_external_preserve_unknown(self):
        res = analyze_source(
            """
            import com.externo.ExtType;
            class Caixa<T extends Number> {}
            class Uso {
                Caixa<? extends ExtType> a;
                Caixa<? super ExtType> b;
            }
            """
        )
        self.assertTrue(res.success, msg=res.semantic_errors)

    # =========================================================================
    # FASE 4 — CONTEXTOS ADICIONAIS
    # =========================================================================

    def test_f4_01_nested_and_qualified_inner_types_and_new(self):
        base_code = """
        class Outer<A extends Number> {
            class Inner<B extends A> {}
            static class Nested<C extends Comparable<C>> {}
        }
        """
        res_ok = analyze_source(
            base_code
            + """
            class Uso {
                Outer<Number>.Inner<Integer> a;
                Outer<Integer>.Inner<Integer> b;
                Outer.Nested<String> c;
                void m() {
                    Outer<Integer> o = new Outer<Integer>();
                    o.new Inner<Integer>();
                }
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        bad_cases = [
            "class Uso { Outer<String>.Inner<String> x; }",
            "class Uso { Outer<Integer>.Inner<Double> x; }",
            "class Uso { Outer.Nested<Object> x; }",
            "class Uso { void m() { Outer<Integer> o = new Outer<Integer>(); o.new Inner<Double>(); } }",
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad):
                res_bad = analyze_source(base_code + bad)
                self.assertFalse(res_bad.success, msg=bad)

    def test_f4_02_arrays_and_method_references(self):
        base_code = """
        import java.util.function.*;
        class Caixa<T extends Number> {}
        """
        res_ok = analyze_source(
            base_code
            + """
            class Uso {
                Caixa<Integer>[] arr;
                void m() {
                    IntFunction<Caixa<?>[]> f1 = Caixa<?>[]::new;
                    Supplier<Caixa<Double>> f2 = Caixa<Double>::new;
                    Object a = new Caixa<?>[2];
                }
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        bad_cases = [
            "class Uso { Caixa<String>[] arr; }",
            "class Uso { void m() { Object a = new Caixa<String>[2]; } }",
            "class Uso { void m() { IntFunction<Caixa<String>[]> f = Caixa<String>[]::new; } }",
            "class Uso { void m() { Supplier<Caixa<String>> f = Caixa<String>::new; } }",
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad):
                res_bad = analyze_source(base_code + bad)
                self.assertFalse(res_bad.success, msg=bad)

    def test_f4_03_diamond_inference_and_bounds(self):
        base_code = """
        interface I<T> {}
        class Caixa<T extends Number> implements I<T> {
            Caixa() {}
            Caixa(T x) {}
        }
        """
        res_ok = analyze_source(
            base_code
            + """
            class Uso {
                void m() {
                    Caixa<Integer> c1 = new Caixa<>(1);
                    var c2 = new Caixa<>(1);
                    Caixa<?> c3 = new Caixa<>();
                    I<Integer> c4 = new Caixa<>();
                }
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        bad_cases = [
            'var bad = new Caixa<>("texto");',
            'Object bad = new Caixa<>("texto");',
            "I<String> bad = new Caixa<>();",
            "Caixa<String> bad = new Caixa<>();",
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad):
                res_bad = analyze_source(base_code + f"class Uso {{ void m() {{ {bad} }} }}")
                self.assertFalse(res_bad.success, msg=bad)

    def test_f4_04_explicit_generic_method_calls_arity_and_constructors(self):
        base_code = """
        class Caixa<T extends Number> {}
        class Util {
            static <X extends Number> X id(X x) { return x; }
            static <A, B extends Comparable<A>> void par(A a, B b) {}
            static void naoGen(int x) {}
        }
        class CtorGen {
            <T extends Number> CtorGen(T val) {}
        }
        """
        res_ok = analyze_source(
            base_code
            + """
            class Uso {
                void m() {
                    Integer a = Util.<Integer>id(1);
                    Util.<String, String>par("a", "b");
                    Util.naoGen(1);
                    Util.<String>naoGen(1);
                    CtorGen c = new CtorGen(1);
                }
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        bad_cases = [
            'Util.<String>id("x");',
            "Util.<Integer, String>id(1);",
            'Util.<Integer, String>par(1, "b");',
            "Util.<Caixa<String>>id(null);",
            'CtorGen c = new CtorGen("nao_numero");',
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad):
                res_bad = analyze_source(base_code + f"class Uso {{ void m() {{ {bad} }} }}")
                self.assertFalse(res_bad.success, msg=bad)

    def test_f4_05_external_classpath_classfile_with_bounds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "pkg" / "ext"
            pkg_dir.mkdir(parents=True)
            class_bytes = _build_minimal_generic_class_bytes(
                "pkg/ext/NumHolder",
                "<T:Ljava/lang/Number;>Ljava/lang/Object;",
            )
            (pkg_dir / "NumHolder.class").write_bytes(class_bytes)

            ok_code = """
            import pkg.ext.NumHolder;
            class Uso {
                NumHolder<Integer> ok1;
                NumHolder<? extends Double> ok2;
                NumHolder<?> ok3;
            }
            """
            res_ok = analyze_source(ok_code, classpath=[tmpdir])
            self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

            bad_code = "import pkg.ext.NumHolder; class Uso { NumHolder<String> bad; }"
            res_bad = analyze_source(bad_code, classpath=[tmpdir])
            self.assertFalse(res_bad.success)
            self.assertTrue(
                any("String" in e and "Number" in e for e in res_bad.semantic_errors),
                msg=res_bad.semantic_errors,
            )

    def test_f4_06_cyclic_bounds_infinite_recursion_protection(self):
        res_cyclic = analyze_source(
            """
            class Loop<A extends B, B extends A> {}
            class Uso {
                Loop<?, ?> l1;
                Loop<Object, Object> l2;
            }
            """
        )
        self.assertIsNotNone(res_cyclic)

    def test_f5_01_method_reference_explicit_type_args_simple_bounds(self):
        base_code = """
        import java.util.function.UnaryOperator;
        class Util {
            static <T extends Number> T identidade(T valor) {
                return valor;
            }
        }
        class Box<E> {
            <U extends E> U conv(U x) { return x; }
        }
        """
        res_ok = analyze_source(
            base_code
            + """
            class Uso {
                void m() {
                    UnaryOperator<Integer> ok = Util::<Integer>identidade;
                    Box<Number> b = new Box<>();
                    UnaryOperator<Double> okInst = b::<Double>conv;
                }
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        res_bad_sam_match = analyze_source(
            base_code
            + """
            class Uso {
                void m() {
                    UnaryOperator<String> bad = Util::<String>identidade;
                }
            }
            """
        )
        self.assertFalse(res_bad_sam_match.success)
        self.assertTrue(
            any("String" in e and "Number" in e for e in res_bad_sam_match.semantic_errors),
            msg=res_bad_sam_match.semantic_errors,
        )

        res_bad_inst_bound = analyze_source(
            base_code
            + """
            class Uso {
                void m() {
                    Box<Number> b = new Box<>();
                    UnaryOperator<String> bad = b::<String>conv;
                }
            }
            """
        )
        self.assertFalse(res_bad_inst_bound.success)
        self.assertTrue(
            any("String" in e and "Number" in e for e in res_bad_inst_bound.semantic_errors),
            msg=res_bad_inst_bound.semantic_errors,
        )

        res_bad_mismatch = analyze_source(
            base_code
            + """
            class Uso {
                void m() {
                    UnaryOperator<Integer> bad2 = Util::<String>identidade;
                }
            }
            """
        )
        self.assertFalse(res_bad_mismatch.success)

    def test_f5_02_method_reference_multiple_unbounded_and_f_bounds(self):
        code_defs = """
        import java.util.function.UnaryOperator;
        interface I1 {}
        class Base {}
        class Bom extends Base implements I1 {}
        class SoBase extends Base {}
        class NaoComp {}
        class Util {
            static <T extends Base & I1> T comMulti(T x) { return x; }
            static <T> T semBound(T x) { return x; }
            static <T extends Comparable<T>> T comF(T x) { return x; }
        }
        """
        res_ok = analyze_source(
            code_defs
            + """
            class Uso {
                void m() {
                    UnaryOperator<Bom> ok1 = Util::<Bom>comMulti;
                    UnaryOperator<String> ok2 = Util::<String>semBound;
                    UnaryOperator<Integer> ok3 = Util::<Integer>comF;
                }
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        bad_cases = [
            "UnaryOperator<SoBase> b1 = Util::<SoBase>comMulti;",
            "UnaryOperator<NaoComp> b2 = Util::<NaoComp>comF;",
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad):
                res_bad = analyze_source(code_defs + f"class Uso {{ void m() {{ {bad} }} }}")
                self.assertFalse(res_bad.success, msg=bad)

    def test_f5_03_method_reference_overloads_distinct_tparams_and_non_generic(self):
        code_defs = """
        import java.util.function.UnaryOperator;
        class Over {
            static <T extends Number> T escolha(T x) { return x; }
            static <T extends CharSequence> T escolha(T x) { return x; }

            static <T> T aridade(T x) { return x; }
            static <A extends Number, B> A aridade(A x) { return x; }

            static Integer naoGen(Integer x) { return x; }
        }
        """
        res_ok = analyze_source(
            code_defs
            + """
            class Uso {
                void m() {
                    UnaryOperator<String> f1 = Over::<String>escolha;
                    UnaryOperator<Integer> f2 = Over::<Integer>escolha;
                    UnaryOperator<Integer> f3 = Over::<Integer, String>aridade;
                    UnaryOperator<Integer> f4 = Over::<String>naoGen;
                }
            }
            """
        )
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        res_bad_arity_bound = analyze_source(
            code_defs
            + """
            class Uso {
                void m() {
                    UnaryOperator<String> bad = Over::<String, Integer>aridade;
                }
            }
            """
        )
        self.assertFalse(res_bad_arity_bound.success)

        res_bad_wrong_arity = analyze_source(
            code_defs
            + """
            class Uso {
                void m() {
                    UnaryOperator<String> bad = Over::<String, Integer, Object>aridade;
                }
            }
            """
        )
        self.assertFalse(res_bad_wrong_arity.success)

    def test_f5_04_method_reference_external_and_unresolved_no_false_positive(self):
        res = analyze_source(
            """
            import java.util.Collections;
            import java.util.List;
            import java.util.function.Supplier;
            import java.util.function.UnaryOperator;
            class Util {
                static <T extends Number> T identidade(T x) { return x; }
            }
            class Uso {
                void m() {
                    Supplier<List<String>> s = Collections::<String>emptyList;
                    UnaryOperator<TipoDesconhecido> u = Util::<TipoDesconhecido>identidade;
                    Supplier<Object> u2 = Desconhecida::<String>metodo;
                }
            }
            """
        )
        self.assertTrue(res.success, msg=res.semantic_errors)
