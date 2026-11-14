"""
Suíte S7.1 — Patterns Gerais, TypePattern, MatchAllPattern ('_'), Guard ('when') Contextual
e Formas Sintáticas da Gramática Java SE 26 (JLS §14.30.1).
"""

import unittest
from src.main import analyze_source
from src.compiler.parser import Parser
from src.compiler.lexer import Lexer
from src.compiler.ast_nodes import (
    CompilationUnit, TypePattern, RecordPattern, MatchAllPattern, Guard,
    PatternCaseLabel, PatternInstanceOfExpression, PatternVariable, SwitchStatement
)


class TestJava26Patterns(unittest.TestCase):
    """Testes sintáticos e estruturais de patterns na Etapa S7."""

    def test_01_type_pattern_variantes_validas(self):
        source = """
        @interface Tag {}
        class Demo {
            void testar(Object obj) {
                if (obj instanceof String s) {
                    System.out.println(s);
                }
                if (obj instanceof final String f) {
                    System.out.println(f);
                }
                if (obj instanceof @Tag final String a) {
                    System.out.println(a);
                }
                if (obj instanceof java.lang.String q) {
                    System.out.println(q);
                }
                if (obj instanceof int[] arr) {
                    System.out.println(arr.length);
                }
                if (obj instanceof java.util.List<?> lista) {
                    System.out.println(lista);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros inesperados: {res.semantic_errors} / {res.syntactic_error}")

    def test_02_type_pattern_unnamed_e_atributos_ast(self):
        source = """
        class Demo {
            void testar(Object obj) {
                switch (obj) {
                    case String _ -> System.out.println("string");
                    case Integer _ -> System.out.println("int");
                    default -> System.out.println("outro");
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} / {res.syntactic_error}")
        self.assertIsInstance(res.ast, CompilationUnit)

        cls = res.ast.type_declarations[0]
        sw = cls.members[0].body.statements[0]
        self.assertIsInstance(sw, SwitchStatement)

        dumped_sw = sw.to_dict()
        text_sw = str(dumped_sw)
        self.assertIn("PatternCaseLabel", text_sw)
        self.assertIn("TypePattern", text_sw)
        self.assertIn("PatternVariable", text_sw)
        self.assertIn("PatternCaseLabel", res.ast.pretty())

        # Confirma is_unnamed=True na AST de 'case String _'
        found_unnamed = False
        for rule in sw.switch_block.switch_rules:
            for lbl in rule.labels:
                if isinstance(lbl, PatternCaseLabel) and lbl.patterns:
                    pat = lbl.patterns[0]
                    self.assertIsInstance(pat, TypePattern)
                    if pat.is_unnamed:
                        found_unnamed = True
                        self.assertEqual(pat.name, "_")
                        self.assertIsInstance(pat.variable, PatternVariable)
                        self.assertTrue(pat.variable.is_unnamed)
        self.assertTrue(found_unnamed)

    def test_03_when_como_identificador_contextual(self):
        source = """
        class Demo {
            int when = 10;
            int calcular(int when) {
                return when + this.when;
            }
            void usarSwitch(Object obj) {
                switch (obj) {
                    case String when when when.length() > 0 -> System.out.println(when);
                    default -> System.out.println("vazio");
                }
            }
        }
        """
        tokens = Lexer(source).tokenize()
        when_toks = [t for t in tokens if t.lexeme == "when"]
        self.assertTrue(len(when_toks) >= 5)
        for t in when_toks:
            self.assertEqual(t.type.name, "IDENTIFIER")

        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"when contextual deveria compilar sem erro: {res.semantic_errors} / {res.syntactic_error}")

    def test_04_rejeicoes_sintaticas_de_type_pattern(self):
        invalid_programs = [
            "class D { void f(Object o) { if (o instanceof _) {} } }",
            "class D { void f(Object o) { if (o instanceof var v) {} } }",
            "class D { void f(Object o) { if (o instanceof void v) {} } }",
            "class D { void f(Object o) { if (o instanceof String s[]) {} } }",
            "class D { void f(Object o) { if (o instanceof String s = \"x\") {} } }",
            "class D { void f(Object o) { switch (o) { case _ -> {} default -> {} } } }",
            "class D { void f(Object o) { switch (o) { case var v -> {} default -> {} } } }",
        ]
        for code in invalid_programs:
            with self.subTest(code=code):
                res = analyze_source(code)
                self.assertFalse(res.success, msg=f"Deveria falhar: {code}")

    def test_05_match_all_pattern_e_guard_na_ast(self):
        source = """
        record Caixa(Object item) {}
        class Demo {
            String descrever(Object obj) {
                return switch (obj) {
                    case Caixa(_) -> "caixa qualquer";
                    case String s when s.length() > 3 -> s;
                    default -> "padrao";
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} / {res.syntactic_error}")
        tree_str = res.ast.pretty()
        self.assertIn("RecordPattern", tree_str)
        self.assertIn("MatchAllPattern", tree_str)
        self.assertIn("Guard", tree_str)

    def test_06_profundidade_aninhada_de_patterns_e_serializacao(self):
        source = """
        record Noh(Object valor, Noh prox) {}
        class Demo {
            void inspecionar(Object o) {
                if (o instanceof Noh(String s, Noh(Integer i, Noh(_, _)))) {
                    System.out.println(s);
                    System.out.println(i);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} / {res.syntactic_error}")
        d = res.ast.to_dict()
        self.assertEqual(d["node"], "OrdinaryCompilationUnit")

    def test_07_modificador_invalido_ou_anotacao_no_type_pattern(self):
        # static/public não são permitidos em TypePattern; apenas final e annotations locais
        for bad_mod in ("public", "static", "volatile"):
            with self.subTest(bad_mod=bad_mod):
                src = f"""
                class Demo {{
                    void f(Object o) {{
                        if (o instanceof {bad_mod} String s) {{}}
                    }}
                }}
                """
                res = analyze_source(src)
                self.assertFalse(res.success, msg=f"Modificador '{bad_mod}' não deve ser aceito em pattern")


if __name__ == "__main__":
    unittest.main()
