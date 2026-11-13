"""
Suíte de Testes para a Correção D1 — Validação da Aridade de Argumentos de Tipo (JLS §4.5).
Cobre tipos do usuário, interfaces, built-ins, raw types, '<>' ilegal vs diamond válido em 'new',
tipos aninhados/segmentados, classpath externo, tipos não resolvidos e reconstruções de TypeReference.
"""

import struct
import tempfile
import unittest
from pathlib import Path
from typing import List

from src.ast_nodes import FieldDeclaration
from src.classpath_resolver import ACC_PUBLIC, ACC_SUPER
from src.lexer import Lexer
from src.main import analyze_source
from src.parser import Parser


def _build_minimal_generic_class_bytes(internal_name: str, signature: str) -> bytes:
    """Gera um .class JVM mínimo e válido contendo atributo Signature de classe genérica."""
    entries: List[bytes] = []
    utf8_cache = {}

    def utf8(text: str) -> int:
        if text in utf8_cache:
            return utf8_cache[text]
        data = text.encode("utf-8")
        entries.append(struct.pack(">BH", 1, len(data)) + data)
        idx = len(entries)
        utf8_cache[text] = idx
        return idx

    def class_ref(name: str) -> int:
        nidx = utf8(name)
        entries.append(struct.pack(">BH", 7, nidx))
        return len(entries)

    this_idx = class_ref(internal_name)
    super_idx = class_ref("java/lang/Object")
    sig_name_idx = utf8("Signature")
    sig_val_idx = utf8(signature)

    cp_bytes = struct.pack(">H", len(entries) + 1) + b"".join(entries)
    header = struct.pack(">IHHI", 0xCAFEBABE, 0, 52, 0)[:-4]  # unused; mount directly below
    _ = header
    sig_attr = struct.pack(">HIH", sig_name_idx, 2, sig_val_idx)
    return b"".join([
        struct.pack(">IHH", 0xCAFEBABE, 0, 52),
        cp_bytes,
        struct.pack(">HHHH", ACC_PUBLIC | ACC_SUPER, this_idx, super_idx, 0),
        struct.pack(">HHH", 0, 0, 1),  # 0 fields, 0 methods, 1 class attribute
        sig_attr,
    ])


class TestJava26GenericArityD1(unittest.TestCase):
    """Testes obrigatórios de conformidade da aridade genérica (D1 / JLS §4.5)."""

    def test_01_user_classes_and_interfaces_arity(self):
        ok = """
        interface Repo<T> {
            T find(int id);
        }
        class Pair<K, V> {
            K key;
            V value;
        }
        record Entry<A, B>(A first, B second) {}
        class App {
            Repo<String> repo;
            Pair<String, Integer> pair;
            Entry<Integer, Boolean> entry;
            Repo<Pair<String, Integer>> nested;
        }
        """
        res = analyze_source(ok)
        self.assertTrue(res.success, msg=res.semantic_errors)

        too_few_cls = "class Pair<K, V> {} class T { Pair<String> p; }"
        res_few = analyze_source(too_few_cls)
        self.assertFalse(res_few.success)
        self.assertTrue(any("esperado 2, encontrado 1" in str(e) for e in res_few.semantic_errors), res_few.semantic_errors)

        too_many_cls = "class Box<T> {} class T { Box<String, Integer> b; }"
        res_many = analyze_source(too_many_cls)
        self.assertFalse(res_many.success)
        self.assertTrue(any("esperado 1, encontrado 2" in str(e) for e in res_many.semantic_errors), res_many.semantic_errors)

        bad_iface_return = "interface Repo<T> {} class T { Repo<String, Integer> f() { return null; } }"
        res_iface = analyze_source(bad_iface_return)
        self.assertFalse(res_iface.success)
        self.assertTrue(any("esperado 1, encontrado 2" in str(e) for e in res_iface.semantic_errors), res_iface.semantic_errors)

        bad_record = "record Par<A, B>(A a, B b) {} class T { Par<String> p; }"
        res_rec = analyze_source(bad_record)
        self.assertFalse(res_rec.success)

    def test_02_stdlib_builtins_list_map_set_optional(self):
        valid = """
        import java.util.*;
        class S {
            List<String> xs;
            Map<String, Integer> m;
            Set<Double> s;
            Optional<String> o;
            void f(List<Set<Optional<Integer>>> deep) {
                Map<String, List<Optional<String>>> local = null;
            }
        }
        """
        res_ok = analyze_source(valid)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        invalid_cases = [
            ("import java.util.List; class T { List<String, Integer> xs; }", 1, 2),
            ("import java.util.Map; class T { Map<String> m; }", 2, 1),
            ("import java.util.Map; class T { Map<String, Integer, Double> m; }", 2, 3),
            ("import java.util.Set; class T { Set<String, Integer> s; }", 1, 2),
            ("import java.util.Optional; class T { Optional<String, Integer> o; }", 1, 2),
            ("import java.util.*; class T { List<Map<String>> nestedErr; }", 2, 1),
            ("import java.util.*; class T { List<? extends Optional<String, Integer>> wcErr; }", 1, 2),
            ("import java.util.*; class T { void m(Object o) { var x = (Set<String, Integer>) o; } }", 1, 2),
        ]
        for code, exp, got in invalid_cases:
            with self.subTest(code=code):
                res = analyze_source(code)
                self.assertFalse(res.success, msg=f"Deveria rejeitar aridade em: {code}")
                self.assertTrue(
                    any(f"esperado {exp}, encontrado {got}" in str(e) for e in res.semantic_errors),
                    msg=f"Mensagem esperada ausente para {code}: {res.semantic_errors}",
                )

    def test_03_non_generic_types_reject_type_arguments(self):
        cases = [
            "class Simple {} class T { Simple<String> s; }",
            "class T { String<Integer> s; }",
            "class Gen<T> { T<String> bad; }",
            "enum Cor { AZUL } class T { Cor<String> c; }",
            "record Ponto(int x, int y) {} class T { Ponto<Integer> p; }",
            "class Box {} class T { void m() { Object o = new Box<String>(); } }",
        ]
        for code in cases:
            with self.subTest(code=code):
                res = analyze_source(code)
                self.assertFalse(res.success, msg=f"Tipo não genérico não pode aceitar <...>: {code}")
                self.assertTrue(
                    any("não é genérico" in str(e) for e in res.semantic_errors),
                    msg=res.semantic_errors,
                )

    def test_04_raw_types_valid_vs_explicit_empty_diamond_in_declaration_invalid(self):
        raw_ok = """
        import java.util.*;
        class Box<T> {}
        class T {
            List rawList;
            Map rawMap;
            Set rawSet;
            Optional rawOpt;
            Box rawBox;
            void m() {
                List l = new ArrayList();
                Box b = new Box();
            }
        }
        """
        res_raw = analyze_source(raw_ok)
        self.assertTrue(res_raw.success, msg=res_raw.semantic_errors)

        bad_empty_decls = [
            "import java.util.List; class T { List<> xs; }",
            "import java.util.Map; class T { Map<> m; }",
            "class Box<T> {} class T { Box<> b; }",
            "class O<T> { class I<U> {} } class T { O<>.I<Integer> x; }",
            "class O<T> { class I<U> {} } class T { O<String>.I<> x; }",
        ]
        for code in bad_empty_decls:
            with self.subTest(code=code):
                res = analyze_source(code)
                self.assertFalse(res.success, msg=f"'<>' fora de 'new' deveria falhar: {code}")
                self.assertTrue(
                    any("diamond '<>'" in str(e) for e in res.semantic_errors),
                    msg=res.semantic_errors,
                )

    def test_05_diamond_instantiation_preserved(self):
        code = """
        import java.util.*;
        class Caixa<K, V> {
            K k;
            V v;
            Caixa(K k, V v) { this.k = k; this.v = v; }
        }
        class T {
            void m() {
                List<String> l = new ArrayList<>();
                Map<String, Integer> mp = new HashMap<>();
                Caixa<String, Integer> c = new Caixa<>("um", 1);
                var inferred = new ArrayList<>();
            }
        }
        """
        res = analyze_source(code)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_06_nested_and_segmented_inner_types(self):
        valid_nested = """
        class O<T> {
            class I<U> {}
            class NonGen {}
            static class S<W> {}
            void inside() {
                O<String>.I<Integer> a = this.new I<Integer>();
            }
        }
        class Use {
            O<String>.I<Integer> x;
            O<String>.I rawInner;
            O.I<Integer> rawOuter;
            O<String>.NonGen okOuterOnly;
            O.S<Double> okStatic;
            void f(O<String> o) {
                O<String>.I<Integer> created = o.new I<Integer>();
            }
        }
        """
        res_ok = analyze_source(valid_nested)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        invalid_nested = [
            "class O<T> { class I<U> {} } class Use { O<String, Integer>.I<Double> x; }",
            "class O<T> { class I<U> {} } class Use { O<String>.I<Integer, Double> x; }",
            "class O<T> { class NonGen {} } class Use { O.NonGen<String> x; }",
            "class O<T> { class I<U> {} } class Use { void f(O<String> o) { Object x = o.new I<Integer, Double>(); } }",
            "class O<T> { class I<U> {} void f() { Object x = this.new I<Integer, Double>(); } }",
        ]
        for code in invalid_nested:
            with self.subTest(code=code):
                res = analyze_source(code)
                self.assertFalse(res.success, msg=f"Deveria rejeitar aridade segmentada/aninhada em: {code}")

    def test_07_external_types_via_classpath_and_map_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "pkg" / "ext"
            pkg_dir.mkdir(parents=True)
            class_bytes = _build_minimal_generic_class_bytes(
                "pkg/ext/PairBox",
                "<A:Ljava/lang/Object;B:Ljava/lang/Object;>Ljava/lang/Object;",
            )
            (pkg_dir / "PairBox.class").write_bytes(class_bytes)

            ok_code = """
            import pkg.ext.PairBox;
            import java.util.Map;
            class T {
                PairBox<String, Integer> p;
                PairBox rawP;
                Map.Entry<String, Integer> e;
            }
            """
            res_ok = analyze_source(ok_code, classpath=[tmpdir])
            self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

            bad_code_few = "import pkg.ext.PairBox; class T { PairBox<String> p; }"
            res_few = analyze_source(bad_code_few, classpath=[tmpdir])
            self.assertFalse(res_few.success)
            self.assertTrue(any("esperado 2, encontrado 1" in str(e) for e in res_few.semantic_errors))

            bad_code_many = "import pkg.ext.PairBox; class T { PairBox<String, Integer, Double> p; }"
            res_many = analyze_source(bad_code_many, classpath=[tmpdir])
            self.assertFalse(res_many.success)
            self.assertTrue(any("esperado 2, encontrado 3" in str(e) for e in res_many.semantic_errors))

            bad_entry = "import java.util.Map; class T { Map.Entry<String> e; }"
            res_entry = analyze_source(bad_entry, classpath=[tmpdir])
            self.assertFalse(res_entry.success)
            self.assertTrue(any("esperado 2, encontrado 1" in str(e) for e in res_entry.semantic_errors))

    def test_08_unresolved_types_produce_no_spurious_arity_errors(self):
        cases = [
            "class T { TotallyUnknown<String, Integer> u; }",
            "import bogus.pkg.Missing; class T { Missing<String, Integer> m; }",
            "import bogus.pkg.List; class T { List<String, Integer> shadowed; }",
            "import java.util.*; class T { Map.Entry<String, Integer> e; }",
        ]
        for code in cases:
            with self.subTest(code=code):
                res = analyze_source(code)
                self.assertEqual(
                    res.semantic_errors,
                    [],
                    msg=f"Tipo não resolvido não deveria gerar erro de aridade: {code} -> {res.semantic_errors}",
                )

    def test_09_type_reference_segment_metadata_and_copies(self):
        src = """
        class O<T> { class I<U> {} class NonGen {} }
        class T {
            O<String>.I x;
            O<String>.I<Integer> y;
            java.util.List xs[];
            java.util.List<> ys[];
            java.util.List<String, Integer> bad[];
        }
        """
        ast = Parser(Lexer(src).tokenize()).parse()
        t_cls = ast.type_declarations[1]
        fields = [m for m in t_cls.members if isinstance(m, FieldDeclaration)]

        # Verifica representação na AST antes de reconstruir
        f_outer_only = fields[0].type_ref
        self.assertEqual(f_outer_only.name, "O.I")
        self.assertEqual(f_outer_only.type_arguments, [])
        self.assertEqual(len(f_outer_only.segment_type_arguments), 2)
        self.assertEqual(len(f_outer_only.segment_type_arguments[0]), 1)
        self.assertIsNone(f_outer_only.segment_type_arguments[1])

        f_both = fields[1].type_ref
        self.assertEqual(len(f_both.segment_type_arguments), 2)
        self.assertEqual(f_both.segment_type_arguments[0][0].name, "String")
        self.assertEqual(f_both.segment_type_arguments[1][0].name, "Integer")

        # Verifica propagação em get_effective_type_ref (cópia profunda por segmento)
        eff_raw = fields[2].type_ref.get_effective_type_ref(fields[2].declarators[0].dims)
        self.assertEqual(eff_raw.array_dimensions, 1)
        self.assertEqual(eff_raw.segment_type_arguments, [None, None, None])

        eff_empty = fields[3].type_ref.get_effective_type_ref(fields[3].declarators[0].dims)
        self.assertEqual(eff_empty.segment_type_arguments, [None, None, []])

        eff_bad = fields[4].type_ref.get_effective_type_ref(fields[4].declarators[0].dims)
        self.assertEqual(len(eff_bad.segment_type_arguments[2]), 2)
        eff_bad.segment_type_arguments[2].pop()
        self.assertEqual(len(fields[4].type_ref.segment_type_arguments[2]), 2)

        # Validação semântica completa para arrays com dimensões pós-declarador
        res = analyze_source(
            "import java.util.*; class T { List xs[]; O<String>.NonGen ok[]; }"
        )
        self.assertTrue(res.success, msg=res.semantic_errors)

        res_bad = analyze_source(
            "import java.util.*; class T { List<String, Integer> bad[]; }"
        )
        self.assertFalse(res_bad.success)

        res_bad_diamond_arr = analyze_source(
            "import java.util.*; class T { List<> bad[]; }"
        )
        self.assertFalse(res_bad_diamond_arr.success)

    def test_10_d2_bounds_enforced_without_breaking_d1_arity(self):
        # D2 ativada: aridade de D1 preservada e bounds de argumentos concretos validados
        code_ok = "class Box<T extends Number> {} class T { Box<Integer> b; }"
        res_ok = analyze_source(code_ok)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        code_bad = "class Box<T extends Number> {} class T { Box<String> b; }"
        res_bad = analyze_source(code_bad)
        self.assertFalse(res_bad.success)
        self.assertTrue(
            any("limite" in e or "bound" in e.lower() for e in res_bad.semantic_errors),
            msg=res_bad.semantic_errors,
        )

    def test_11_array_creation_method_reference_arity(self):
        # 1. List<String>[]::new — aridade correta
        # 3. Map<String, Integer>[]::new — aridade correta
        # 5. String[]::new — tipo não genérico válido
        ok = """
        import java.util.*;
        import java.util.function.*;
        class MRefArr {
            void m() {
                IntFunction<List<String>[]> f1 = List<String>[]::new;
                IntFunction<Map<String, Integer>[]> f2 = Map<String, Integer>[]::new;
                IntFunction<String[]> f3 = String[]::new;
            }
        }
        """
        res_ok = analyze_source(ok)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        # 2. List<String, Integer>[]::new — aridade incorreta
        bad_list = """
        import java.util.*;
        import java.util.function.*;
        class MRefArr {
            void m() {
                IntFunction<Object> f = List<String, Integer>[]::new;
            }
        }
        """
        res_bad_list = analyze_source(bad_list)
        self.assertFalse(res_bad_list.success)
        self.assertTrue(
            any("esperado 1, encontrado 2" in str(e) for e in res_bad_list.semantic_errors),
            msg=res_bad_list.semantic_errors,
        )

        # 4. Map<String>[]::new — aridade incorreta
        bad_map = """
        import java.util.*;
        import java.util.function.*;
        class MRefArr {
            void m() {
                IntFunction<Object> f = Map<String>[]::new;
            }
        }
        """
        res_bad_map = analyze_source(bad_map)
        self.assertFalse(res_bad_map.success)
        self.assertTrue(
            any("esperado 2, encontrado 1" in str(e) for e in res_bad_map.semantic_errors),
            msg=res_bad_map.semantic_errors,
        )

        # 6. Tipo genérico não resolvido em referência de criação de array — sem falso positivo
        unresolved = """
        import java.util.function.*;
        class MRefArr {
            void m() {
                IntFunction<Object> f = UnknownGen<String, Integer>[]::new;
            }
        }
        """
        res_unres = analyze_source(unresolved)
        self.assertEqual(res_unres.semantic_errors, [], msg=res_unres.semantic_errors)


if __name__ == "__main__":
    unittest.main()

