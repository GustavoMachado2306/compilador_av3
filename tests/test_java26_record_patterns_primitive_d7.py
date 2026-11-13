import unittest

from src.lexer import Lexer
from src.main import analyze_source
from src.parser import Parser
from src.semantic import SemanticAnalyzer
from src.symbol_table import SymbolTable


class TestJava26RecordPatternsPrimitiveD7(unittest.TestCase):
    """D7 — Record Patterns convencionais vs componentes primitivos sob JEP 530 (Preview em Java SE 26)."""

    def _run_semantic_with_preview_ast(self, source: str, semantic_preview: bool) -> SemanticAnalyzer:
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens, enable_preview_primitive_patterns=True).parse()
        analyzer = SemanticAnalyzer(SymbolTable(), enable_preview_primitive_patterns=semantic_preview)
        analyzer.analyze(ast)
        return analyzer

    def test_01_record_patterns_convencionais_e_var_funcionam_sem_preview(self):
        source = """
        sealed interface Item permits Texto, Coordenada {}
        record Texto(String valor, Integer codigo) implements Item {}
        record Coordenada(int x, int y, int[] serie) implements Item {}
        record Capsula<T>(T conteudo, Item item) {}

        class Demo {
            int avaliar(Object o, Item it) {
                if (o instanceof Capsula<String>(String s, Coordenada(var cx, _, int[] arr))) {
                    int n = s.length() + cx + arr.length;
                }
                if (o instanceof Coordenada(final var x, var y, _)) {
                    int soma = x + y;
                }
                return switch (it) {
                    case Texto(String v, Integer c) -> v.length() + c;
                    case Coordenada(var px, var py, _) when px == py -> px * 2;
                    case Coordenada(var px, var py, _) -> px + py;
                };
            }
        }
        """
        res = analyze_source(source, enable_preview_primitive_patterns=False)
        self.assertTrue(
            res.success,
            msg=f"Record Patterns convencionais / 'var' / '_' / arrays deveriam funcionar sem preview: {res.semantic_errors} | {res.syntactic_error}",
        )

    def test_02_componentes_primitivos_exatos_conversoes_e_top_level_exigem_preview(self):
        preview_required_cases = [
            # Componentes primitivos exatos em RecordPattern (JEP 530 Preview em Java SE 26)
            """
            record P(int x) {}
            class D {
                void f(Object o) {
                    if (o instanceof P(int x)) {
                        int y = x + 1;
                    }
                }
            }
            """,
            """
            record Ponto(int x, int y) {}
            record Envelope(Ponto origem, long tag) {}
            class D {
                int f(Object o) {
                    if (o instanceof Envelope(Ponto(final int px, int py), long _)) {
                        return px + py;
                    }
                    return 0;
                }
            }
            """,
            """
            sealed interface Figura permits Ponto, Raio {}
            record Ponto(int x, int y) implements Figura {}
            record Raio(double r, boolean visivel) implements Figura {}
            class D {
                double avaliar(Figura f) {
                    return switch (f) {
                        case Ponto(int x, int y) when x == y -> x * 2.0;
                        case Ponto(int x, int y) -> x + y;
                        case Raio(double r, boolean _) -> r;
                    };
                }
            }
            """,
            # Conversões primitivas e unboxing/boxing em RecordPattern
            "record P(int x) {} class D { void f(Object o) { if (o instanceof P(long x)) {} } }",
            "record L(long x) {} class D { void f(Object o) { if (o instanceof L(int x)) {} } }",
            "record P(int x) {} class D { void f(Object o) { if (o instanceof P(Integer x)) {} } }",
            "record Box<T>(T v) {} class D { void f(Object o) { if (o instanceof Box<Integer>(int x)) {} } }",
            "record Box<T>(T v) {} class D { void f(Object o) { if (o instanceof Box<Object>(int x)) {} } }",
            # Padrões primitivos em nível superior
            "class D { void f(Object o) { if (o instanceof int i) { int j = i; } } }",
            "class D { int f(Object o) { return switch (o) { case double d -> 1; default -> 0; }; } }",
        ]

        for code in preview_required_cases:
            with self.subTest(case=code):
                res_off = analyze_source(code, enable_preview_primitive_patterns=False)
                self.assertFalse(
                    res_off.success,
                    msg=f"Componente/padrão primitivo deveria ser rejeitado sem preview: {code}",
                )
                sem_off = self._run_semantic_with_preview_ast(code, semantic_preview=False)
                self.assertTrue(
                    len(sem_off.errors) > 0,
                    msg=f"SemanticAnalyzer deveria rejeitar padrão primitivo sem preview mesmo com AST já construída: {code}",
                )

                res_on = analyze_source(code, enable_preview_primitive_patterns=True)
                self.assertTrue(
                    res_on.success,
                    msg=f"Preview deveria aceitar padrão primitivo: {res_on.semantic_errors} | {res_on.syntactic_error}",
                )

    def test_03_dominancia_aridade_e_tipos_disjuntos_em_record_patterns_com_preview(self):
        bad_dom = """
        record Ponto(int x, int y) {}
        class Demo {
            void f(Ponto p) {
                switch (p) {
                    case Ponto(int a, int b) -> {}
                    case Ponto(int c, int d) -> {}
                }
            }
        }
        """
        res_dom = analyze_source(bad_dom, enable_preview_primitive_patterns=True)
        self.assertFalse(res_dom.success)
        self.assertTrue(any("dominado" in e.lower() for e in res_dom.semantic_errors), msg=res_dom.semantic_errors)

        bad_arity = """
        record Ponto(int x, int y) {}
        class Demo {
            void f(Object o) {
                if (o instanceof Ponto(int x)) {}
            }
        }
        """
        res_ar = analyze_source(bad_arity, enable_preview_primitive_patterns=True)
        self.assertFalse(res_ar.success)
        self.assertTrue(any("espera 2 componente" in e for e in res_ar.semantic_errors), msg=res_ar.semantic_errors)

        always_bad = [
            "record R(String s) {} class D { void f(Object o) { if (o instanceof R(int x)) {} } }",
            "record B(boolean flag) {} class D { void f(Object o) { if (o instanceof B(int x)) {} } }",
        ]
        for code in always_bad:
            for prev in (False, True):
                with self.subTest(always_bad=code, preview=prev):
                    res = analyze_source(code, enable_preview_primitive_patterns=prev)
                    self.assertFalse(res.success, msg=f"Incompatível deveria falhar mesmo com preview={prev}: {code}")


if __name__ == "__main__":
    unittest.main()
