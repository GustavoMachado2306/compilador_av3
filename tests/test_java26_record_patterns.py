"""
Suíte S7.2 — Record Patterns (JLS §14.30.1): sintaxe, aridade, aninhamento, genéricos,
var em componentes, '_' (MatchAll vs unnamed TypePattern), proibições de annotations e validações.
"""

import unittest
from src.main import analyze_source
from src.compiler.ast_nodes import RecordPattern, TypePattern, MatchAllPattern, PatternInstanceOfExpression


class TestJava26RecordPatterns(unittest.TestCase):
    """Testes sintáticos e semânticos para Record Patterns na Etapa S7."""

    def test_01_record_patterns_basicos_e_vazios(self):
        source = """
        record Vazio() {}
        record PontoRef(Integer x, Integer y) {}
        record Ponto(int x, int y) {}
        class Demo {
            void f(Object o) {
                if (o instanceof Vazio()) {
                    System.out.println("vazio");
                }
                if (o instanceof PontoRef(Integer x, Integer y)) {
                    Integer refX = x;
                    Integer refY = y;
                }
                if (o instanceof Ponto(var x, var y)) {
                    int soma = x + y;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} / {res.syntactic_error}")

    def test_02_record_patterns_aninhados_com_var_e_unnamed(self):
        source = """
        record Ponto(Double x, Double y) {}
        record Cor(Integer r, Integer g, Integer b) {}
        record PontoPrim(double x, double y) {}
        record Retangulo(Ponto supEsq, Ponto infDir, Cor cor, PontoPrim prim) {}
        class Demo {
            void inspecionar(Object obj) {
                if (obj instanceof Retangulo(Ponto(Double x1, _), Ponto(var x2, var y2), Cor(_, Integer _, _), PontoPrim(var px, _))) {
                    Double a = x1;
                    Double b = x2;
                    Double c = y2;
                    double dx = px;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} / {res.syntactic_error}")

    def test_03_record_pattern_generico_e_inferencia_de_var(self):
        source = """
        record Caixa<T>(T valor) {}
        record Par<A, B>(A primeiro, B segundo) {}
        class Demo {
            void f(Object o) {
                if (o instanceof Caixa<String>(var texto)) {
                    String s = texto;
                }
                if (o instanceof Par<String, Integer>(var a, var b)) {
                    String s = a;
                    Integer n = b;
                }
                if (o instanceof Caixa(var bruto)) {
                    Object v = bruto;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} / {res.syntactic_error}")

    def test_04_record_pattern_invalida_aridade_incorreta(self):
        source = """
        record Ponto(Integer x, Integer y) {}
        class Demo {
            void f(Object o) {
                if (o instanceof Ponto(Integer x)) {
                    System.out.println(x);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("espera 2 componente" in str(e) for e in res.semantic_errors))

    def test_05_record_pattern_em_classe_nao_record_invalida(self):
        for decl in ("class Ponto { Integer x; }", "interface Ponto {}", "enum Ponto { A }"):
            with self.subTest(decl=decl):
                source = f"""
                {decl}
                class Demo {{
                    void f(Object o) {{
                        if (o instanceof Ponto(Integer x)) {{}}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success)
                self.assertTrue(any("não um 'record'" in str(e) for e in res.semantic_errors))

    def test_06_variavel_duplicada_em_componentes_de_record_pattern(self):
        source = """
        record Par(String a, String b) {}
        record Tripla(Par p, String c) {}
        class Demo {
            void f(Object o) {
                if (o instanceof Tripla(Par(String x, _), String x)) {
                    System.out.println(x);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("declarada novamente no mesmo pattern" in str(e) for e in res.semantic_errors))

    def test_07_incompatibilidade_generica_em_record_pattern(self):
        source = """
        record Caixa<T>(T valor) {}
        class Demo {
            void f(Object o) {
                if (o instanceof Caixa<String>(Integer n)) {
                    System.out.println(n);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("Tipos incompatíveis" in str(e) for e in res.semantic_errors))

    def test_08_rejeicao_anotacao_sobre_record_pattern_e_record_local_em_metodo(self):
        source_valid_local = """
        class Demo {
            void processar(Object o) {
                record LocalPar(String k, Integer v) {}
                if (o instanceof LocalPar(String k, Integer v)) {
                    Integer n = v;
                }
            }
        }
        """
        res_ok = analyze_source(source_valid_local)
        self.assertTrue(res_ok.success, msg=f"Record local em método deveria validar: {res_ok.semantic_errors}")

        source_bad_anno = """
        @interface Tag {}
        record Ponto(Integer x, Integer y) {}
        class Demo {
            void processar(Object o) {
                if (o instanceof @Tag Ponto(Integer x, Integer y)) {}
            }
        }
        """
        res_bad = analyze_source(source_bad_anno)
        self.assertFalse(res_bad.success)
        self.assertTrue(any("Anotações não são permitidas" in str(e) for e in res_bad.semantic_errors))

    def test_09_component_pattern_ast_distingue_match_all_e_type_unnamed(self):
        source = """
        record Par(String a, int b) {}
        class Demo {
            void testar(Object o) {
                if (o instanceof Par(String _, _)) {}
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors}")
        if_stmt = res.ast.type_declarations[1].members[0].body.statements[0]
        cond = if_stmt.condition
        self.assertIsInstance(cond, PatternInstanceOfExpression)
        rpat = cond.pattern
        self.assertIsInstance(rpat, RecordPattern)
        self.assertIsInstance(rpat.components[0], TypePattern)
        self.assertTrue(rpat.components[0].is_unnamed)
        self.assertIsInstance(rpat.components[1], MatchAllPattern)


if __name__ == "__main__":
    unittest.main()

