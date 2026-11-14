"""
Suíte S7.3 — InstanceOf Expressions com Patterns e Desambiguação Sintática (JLS §15.20.2).
Cobre: InstanceOfExpression clássico vs PatternInstanceOfExpression, precedência,
desambiguação de generics/arrays/annotations, compatibilidade de tipos e incondicionalidade SE 26.
"""

import unittest
from src.main import analyze_source
from src.compiler.ast_nodes import (
    InstanceOfExpression, PatternInstanceOfExpression, TypePattern, RecordPattern, BinaryOp
)


class TestJava26InstanceOfPatterns(unittest.TestCase):
    """Testes sintáticos e semânticos para instanceof com e sem patterns."""

    def test_01_instanceof_classico_preservado_vs_pattern(self):
        source = """
        @interface A {}
        class Demo {
            void testar(Object o) {
                boolean b1 = o instanceof String;
                boolean b2 = o instanceof int[];
                boolean b3 = o instanceof @A String[];
                boolean b4 = o instanceof String s && s.length() > 0;
                boolean b5 = o instanceof java.util.List<?> lista && lista.size() >= 0;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} / {res.syntactic_error}")

        stmts = res.ast.type_declarations[1].members[0].body.statements
        e1 = stmts[0].declarators[0].initializer
        e2 = stmts[1].declarators[0].initializer
        e3 = stmts[2].declarators[0].initializer
        e4 = stmts[3].declarators[0].initializer

        self.assertIs(type(e1), InstanceOfExpression)
        self.assertFalse(e1.is_pattern)
        self.assertIsNone(e1.pattern)

        self.assertIs(type(e2), InstanceOfExpression)
        self.assertFalse(e2.is_pattern)

        self.assertIs(type(e3), InstanceOfExpression)
        self.assertFalse(e3.is_pattern)

        self.assertIsInstance(e4, BinaryOp)
        self.assertIsInstance(e4.left, PatternInstanceOfExpression)
        self.assertTrue(e4.left.is_pattern)
        self.assertIsInstance(e4.left.pattern, TypePattern)

    def test_02_instanceof_com_record_pattern_e_precedencia(self):
        source = """
        record Caixa(String s) {}
        class Demo {
            boolean testar(Object o) {
                return o != null && (o instanceof Caixa(String s) && !s.isEmpty());
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} / {res.syntactic_error}")

    def test_03_instanceof_incondicional_permitido_no_java_se_26(self):
        source = """
        record Ponto(Integer x, Integer y) {}
        record PontoPrim(int x, int y) {}
        class Demo {
            void f(String texto, Ponto p, PontoPrim pp) {
                if (texto instanceof String s2 && s2.length() >= 0) {
                    System.out.println(s2);
                }
                if (texto instanceof CharSequence cs) {
                    System.out.println(cs);
                }
                if (p instanceof Ponto(Integer x, Integer y)) {
                    Integer rx = x;
                    Integer ry = y;
                }
                if (pp instanceof PontoPrim(var a, var b)) {
                    int z = a + b;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Java SE 26 permite pattern incondicional em instanceof: {res.semantic_errors}")

    def test_04_instanceof_rejeita_tipos_disjuntos_e_primitivos_no_modo_padrao(self):
        disjoint_cases = [
            "void f(String s) { if (s instanceof Integer i) {} }",
            "void f(String s) { boolean b = s instanceof Integer; }",
            "void f(int n) { boolean b = n instanceof Integer; }",
            "void f(int n) { if (n instanceof Integer i) {} }",
            "void f(Object o) { if (o instanceof int i) {} }",
            "void f(Object o) { boolean b = o instanceof int; }",
        ]
        for method_code in disjoint_cases:
            with self.subTest(method_code=method_code):
                source = f"class Demo {{ {method_code} }}"
                res = analyze_source(source)
                self.assertFalse(res.success, msg=f"Deveria ser rejeitado: {method_code}")

    def test_05_instanceof_sealed_com_subtipo_impossivel(self):
        source = """
        sealed interface Expr permits Literal {}
        record Literal(int v) implements Expr {}
        class Demo {
            void f(Expr e) {
                if (e instanceof String s) {
                    System.out.println(s);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("Tipos incompatíveis" in str(e) for e in res.semantic_errors))

    def test_06_instanceof_hierarquia_aberta_nao_falso_positivo(self):
        source = """
        class Base {}
        interface Mixin {}
        class Demo {
            void f(Base b) {
                if (b instanceof Mixin m) {
                    System.out.println(m);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Classe não-final pode ter subclasse que implementa interface: {res.semantic_errors}")


if __name__ == "__main__":
    unittest.main()

