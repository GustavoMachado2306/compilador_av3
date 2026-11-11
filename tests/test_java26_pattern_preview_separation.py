"""
Suíte S7.1 — Auditoria Corretiva de Separação Estrita entre Java SE 26 Estável
e Preview JEP 530 (Tipos Primitivos em Patterns, instanceof e switch).
"""

import unittest
from src.lexer import Lexer
from src.parser import Parser
from src.semantic import SemanticAnalyzer
from src.symbol_table import SymbolTable
from src.main import analyze_source


class TestJava26PatternPreviewSeparation(unittest.TestCase):
    """Testa todos os limites entre Java SE 26 estável e preview JEP 530 (parser + semântico)."""

    def _run_semantic_with_preview_ast(self, source: str, semantic_preview: bool) -> SemanticAnalyzer:
        """Faz parse com preview=True e executa SemanticAnalyzer com o modo informado."""
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens, enable_preview_primitive_patterns=True).parse()
        analyzer = SemanticAnalyzer(SymbolTable(), enable_preview_primitive_patterns=semantic_preview)
        analyzer.analyze(ast)
        return analyzer

    def test_01_pattern_primitivo_instanceof_preview_desativado(self):
        cases = [
            "class D { void f(Object o) { if (o instanceof int i) { System.out.println(i); } } }",
            "class D { void f(Object o) { if (o instanceof final double d) {} } }",
            "class D { void f(Object o) { if (o instanceof boolean b) {} } }",
            "class D { void f(Object o) { if (o instanceof byte _) {} } }",
            "class D { void f(int n) { if (n instanceof byte b) {} } }",
            "class D { void f(Object o) { boolean b = o instanceof int; } }",
            "class D { void f(int n) { boolean b = n instanceof Integer; } }",
        ]
        for code in cases:
            with self.subTest(code=code):
                res_default = analyze_source(code)
                self.assertFalse(res_default.success, msg=f"Deveria falhar sem preview: {code}")
                res_false = analyze_source(code, enable_preview_primitive_patterns=False)
                self.assertFalse(res_false.success)

        # Garante também rejeição direta na camada semântica se a AST já vier construída
        sem_pat = self._run_semantic_with_preview_ast(cases[0], semantic_preview=False)
        self.assertTrue(len(sem_pat.errors) > 0, msg="SemanticAnalyzer também deve rejeitar primitive TypePattern sem preview")
        sem_classic = self._run_semantic_with_preview_ast(cases[5], semantic_preview=False)
        self.assertTrue(len(sem_classic.errors) > 0, msg="SemanticAnalyzer também deve rejeitar instanceof primitivo sem preview")

        # Arrays de primitivos são ReferenceType (ArrayType) e permanecem válidos no modo estável
        array_stable = """
        class D {
            void f(Object o) {
                if (o instanceof int[] arr) {
                    int k = arr.length;
                }
                boolean b = o instanceof double[];
            }
        }
        """
        res_arr = analyze_source(array_stable, enable_preview_primitive_patterns=False)
        self.assertTrue(res_arr.success, msg=f"Array de primitivos é ReferenceType estável: {res_arr.semantic_errors} / {res_arr.syntactic_error}")

    def test_02_pattern_primitivo_instanceof_preview_ativado(self):
        valid_preview = """
        class D {
            void testar(Object o, int n, Integer box) {
                if (o instanceof int i) {
                    int soma = i + 1;
                }
                if (n instanceof byte b) {
                    byte cop = b;
                }
                if (n instanceof double d) {
                    double dobro = d * 2.0;
                }
                if (box instanceof int unboxed) {
                    int x = unboxed;
                }
            }
        }
        """
        res = analyze_source(valid_preview, enable_preview_primitive_patterns=True)
        self.assertTrue(res.success, msg=f"Preview deveria aceitar: {res.semantic_errors} / {res.syntactic_error}")
        for pat_var in ("i", "b", "d", "unboxed"):
            self.assertFalse(res.symbol_table.exists(pat_var), msg=f"Variável de pattern '{pat_var}' não deve vazar para a tabela global")

        # Validações semânticas continuam ativas mesmo com preview habilitado
        invalid_semantics_under_preview = [
            "class D { void f(String s) { if (s instanceof int i) {} } }",
            "class D { void f(boolean b) { if (b instanceof int i) {} } }",
            "class D { void f(Object o) { if (o instanceof int i || i > 0) {} } }",
            "class D { void f(Object o) { if (o instanceof final int i) { i = 2; } } }",
            "class D { void f(String s) { boolean b = s instanceof Integer; } }",
        ]
        for bad in invalid_semantics_under_preview:
            with self.subTest(bad=bad):
                res_bad = analyze_source(bad, enable_preview_primitive_patterns=True)
                self.assertFalse(res_bad.success, msg=f"Erro semântico deveria ser preservado em preview: {bad}")
                self.assertTrue(len(res_bad.semantic_errors) > 0, msg=f"Esperado erro semântico e não só sintático: {bad}")

    def test_03_pattern_primitivo_case_preview_desativado(self):
        cases = [
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        case int i -> System.out.println(i);
                        default -> {}
                    }
                }
            }
            """,
            """
            class D {
                int f(int n) {
                    return switch (n) {
                        case 0 -> 1;
                        case int v -> v;
                    };
                }
            }
            """,
            """
            class D {
                void f(Object o) {
                    switch (o) {
                        case double _ -> {}
                        default -> {}
                    }
                }
            }
            """,
            """
            class D {
                int f(boolean flag) {
                    return switch (flag) {
                        case true -> 1;
                        case false -> 0;
                    };
                }
            }
            """,
            """
            class D {
                int f(long l) {
                    return switch (l) {
                        case 1L -> 1;
                        default -> 0;
                    };
                }
            }
            """,
            """
            class D {
                int f(double d) {
                    return switch (d) {
                        case 1.5 -> 1;
                        default -> 0;
                    };
                }
            }
            """,
        ]
        for code in cases:
            with self.subTest(code=code):
                res = analyze_source(code, enable_preview_primitive_patterns=False)
                self.assertFalse(res.success, msg=f"Switch primitivo JEP 530 não deve passar sem preview: {code}")

        # Verifica também que a camada semântica sozinha rejeita o AST do case primitivo sem preview
        sem = self._run_semantic_with_preview_ast(cases[1], semantic_preview=False)
        self.assertTrue(len(sem.errors) > 0)

    def test_04_pattern_primitivo_case_preview_ativado(self):
        valid_preview = """
        class D {
            int avaliarInt(int n) {
                return switch (n) {
                    case 0 -> 100;
                    case int v when v > 10 -> v * 2;
                    case int v -> v;
                };
            }
            int avaliarBool(boolean flag) {
                return switch (flag) {
                    case true -> 1;
                    case false -> 0;
                };
            }
            int avaliarObject(Object o) {
                return switch (o) {
                    case int i -> i;
                    case String s -> s.length();
                    default -> -1;
                };
            }
        }
        """
        res = analyze_source(valid_preview, enable_preview_primitive_patterns=True)
        self.assertTrue(res.success, msg=f"Switch preview falhou: {res.semantic_errors} / {res.syntactic_error}")

        # Validações semânticas continuam operando com preview ativado
        dominance_err = """
        class D {
            int f(int n) {
                return switch (n) {
                    case int a -> a;
                    case int b -> b;
                };
            }
        }
        """
        res_dom = analyze_source(dominance_err, enable_preview_primitive_patterns=True)
        self.assertFalse(res_dom.success)
        self.assertTrue(any("dominado" in str(e).lower() for e in res_dom.semantic_errors), msg=res_dom.semantic_errors)

        non_exhaustive_err = """
        class D {
            int f(int n) {
                return switch (n) {
                    case 0 -> 1;
                    case int v when v > 0 -> v;
                };
            }
        }
        """
        res_exh = analyze_source(non_exhaustive_err, enable_preview_primitive_patterns=True)
        self.assertFalse(res_exh.success)
        self.assertTrue(any("exaustiv" in str(e).lower() for e in res_exh.semantic_errors), msg=res_exh.semantic_errors)

        null_on_primitive = """
        class D {
            void f(int n) {
                switch (n) {
                    case null -> {}
                    default -> {}
                }
            }
        }
        """
        res_null = analyze_source(null_on_primitive, enable_preview_primitive_patterns=True)
        self.assertFalse(res_null.success)
        self.assertTrue(any("case null" in str(e) for e in res_null.semantic_errors), msg=res_null.semantic_errors)

    def test_05_componente_primitivo_record_pattern_preview_desativado(self):
        cases = [
            """
            record P(int x) {}
            class D {
                void f(Object o) {
                    if (o instanceof P(int x)) {
                        System.out.println(x);
                    }
                }
            }
            """,
            """
            record P(int x, int y) {}
            class D {
                void f(Object o) {
                    switch (o) {
                        case P(int x, int y) -> System.out.println(x + y);
                        default -> {}
                    }
                }
            }
            """,
            """
            record P(int x) {}
            class D {
                void f(Object o) {
                    if (o instanceof P(int _)) {}
                }
            }
            """,
            """
            record P(int x) {}
            class D {
                void f(Object o) {
                    if (o instanceof P(final int x)) {}
                }
            }
            """,
            """
            record Interno(double d) {}
            record Externo(Interno i) {}
            class D {
                void f(Object o) {
                    if (o instanceof Externo(Interno(double d))) {}
                }
            }
            """,
        ]
        for code in cases:
            with self.subTest(code=code):
                res = analyze_source(code, enable_preview_primitive_patterns=False)
                self.assertFalse(res.success, msg=f"Componente primitivo em RecordPattern deve falhar sem preview: {code}")

        # SemanticAnalyzer direto também deve rejeitar componente primitivo sem preview
        for code in (cases[0], cases[1], cases[4]):
            sem = self._run_semantic_with_preview_ast(code, semantic_preview=False)
            self.assertTrue(
                len(sem.errors) > 0,
                msg=f"SemanticAnalyzer deve rejeitar componente primitivo sem preview: {code}",
            )

    def test_06_componente_primitivo_record_pattern_preview_ativado(self):
        valid_preview = """
        sealed interface Forma permits Ponto, Medida {}
        record Ponto(int x, int y) implements Forma {}
        record Medida(int valor, double peso) implements Forma {}
        record Capsula(Ponto p) {}
        class D {
            double avaliar(Object o, Forma f) {
                if (o instanceof Capsula(Ponto(int cx, int cy))) {
                    int s = cx + cy;
                }
                return switch (f) {
                    case Ponto(int x, int y) when x == y -> x + y;
                    case Ponto(int x, int _) -> x;
                    case Medida(int v, double p) -> v + p;
                };
            }
        }
        """
        res = analyze_source(valid_preview, enable_preview_primitive_patterns=True)
        self.assertTrue(res.success, msg=f"Componentes primitivos com preview falharam: {res.semantic_errors} / {res.syntactic_error}")

        # Erros semânticos preservados no modo preview
        bad_arity = """
        record Ponto(int x, int y) {}
        class D { void f(Object o) { if (o instanceof Ponto(int x)) {} } }
        """
        res_arity = analyze_source(bad_arity, enable_preview_primitive_patterns=True)
        self.assertFalse(res_arity.success)
        self.assertTrue(any("espera 2 componente" in str(e) for e in res_arity.semantic_errors))

        bad_disjoint = """
        record Medida(int valor, double peso) {}
        class D { void f(Object o) { if (o instanceof Medida(String s, double p)) {} } }
        """
        res_disj = analyze_source(bad_disjoint, enable_preview_primitive_patterns=True)
        self.assertFalse(res_disj.success)
        self.assertTrue(any("Tipos incompatíveis" in str(e) for e in res_disj.semantic_errors))

        bad_dominance = """
        record Ponto(int x, int y) {}
        class D {
            void f(Object o) {
                switch (o) {
                    case Ponto p -> {}
                    case Ponto(int x, int y) -> {}
                    default -> {}
                }
            }
        }
        """
        res_dom = analyze_source(bad_dominance, enable_preview_primitive_patterns=True)
        self.assertFalse(res_dom.success)
        self.assertTrue(any("dominado" in str(e).lower() for e in res_dom.semantic_errors))

    def test_07_record_pattern_componentes_referencia_sem_preview(self):
        valid_ref = """
        record Par(String chave, Integer codigo) {}
        record Vetor(java.util.List<String> itens, int[] nums) {}
        class D {
            int testar(Object o) {
                if (o instanceof Par(final String k, Integer _)) {
                    int tam = k.length();
                }
                if (o instanceof Vetor(java.util.List<String> lista, int[] arr)) {
                    return arr.length;
                }
                return switch (o) {
                    case Par(String c, Integer n) -> c.length();
                    default -> 0;
                };
            }
        }
        """
        res = analyze_source(valid_ref, enable_preview_primitive_patterns=False)
        self.assertTrue(res.success, msg=f"RecordPattern com referências falhou sem preview: {res.semantic_errors} / {res.syntactic_error}")

        # Validação semântica continua operando
        bad_generic = """
        record Caixa<T>(T valor) {}
        class D { void f(Object o) { if (o instanceof Caixa<String>(Integer n)) {} } }
        """
        res_bad = analyze_source(bad_generic, enable_preview_primitive_patterns=False)
        self.assertFalse(res_bad.success)
        self.assertTrue(any("Tipos incompatíveis" in str(e) for e in res_bad.semantic_errors))

    def test_08_record_pattern_patterns_aninhados_referencia_sem_preview(self):
        valid_nested = """
        sealed interface Expr permits Texto, Duo {}
        record Texto(String conteudo) implements Expr {}
        record Duo(Expr esquerda, Expr direita) implements Expr {}
        class D {
            String resumir(Expr e, Object o) {
                if (o instanceof Duo(Texto(String a), Duo(Texto(String b), _))) {
                    return a + b;
                }
                return switch (e) {
                    case Texto(String c) -> c;
                    case Duo(Texto(String t), _) -> t;
                    case Duo(Duo(Expr e1, Expr e2), _) -> "duo";
                };
            }
        }
        """
        res = analyze_source(valid_nested, enable_preview_primitive_patterns=False)
        self.assertTrue(res.success, msg=f"RecordPattern aninhado com referências falhou: {res.semantic_errors} / {res.syntactic_error}")

        # Cobertura incompleta de records aninhados sobre sealed é detectada semanticamente
        missing_nested = """
        sealed interface Cor permits Azul, Verde {}
        record Azul() implements Cor {}
        record Verde() implements Cor {}
        record Dupla(Cor a, Cor b) {}
        class D {
            int avaliar(Dupla d) {
                return switch (d) {
                    case Dupla(Azul(), Azul()) -> 1;
                    case Dupla(Verde(), _) -> 2;
                };
            }
        }
        """
        res_missing = analyze_source(missing_nested, enable_preview_primitive_patterns=False)
        self.assertFalse(res_missing.success)
        self.assertTrue(any("exaustiv" in str(e).lower() for e in res_missing.semantic_errors))

    def test_09_pattern_com_var_conforme_regras_estaveis(self):
        # 'var' em componente de RecordPattern é estável mesmo quando o componente do record é primitivo
        valid_var = """
        sealed interface Expr permits Num, Soma {}
        record Num(int valor) implements Expr {}
        record Soma(Expr a, Expr b) implements Expr {}
        record Caixa<T>(T item) {}
        class D {
            int testar(Object o, Expr e) {
                if (o instanceof Num(var n)) {
                    int copia = n;
                    return copia + 1;
                }
                if (o instanceof Caixa<String>(final var texto)) {
                    String s = texto;
                }
                return switch (e) {
                    case Num(var v) -> v;
                    case Soma(Num(var a), Num(var b)) -> a + b;
                    case Soma(var esq, var _) -> 0;
                };
            }
        }
        """
        res = analyze_source(valid_var, enable_preview_primitive_patterns=False)
        self.assertTrue(res.success, msg=f"'var' estável em RecordPattern falhou: {res.semantic_errors} / {res.syntactic_error}")

        # Tipo inferido de 'var' continua validado semanticamente
        bad_var_type_use = """
        record Num(int valor) {}
        class D {
            void f(Object o) {
                if (o instanceof Num(var v)) {
                    String errado = v;
                }
            }
        }
        """
        res_type_err = analyze_source(bad_var_type_use, enable_preview_primitive_patterns=False)
        self.assertFalse(res_type_err.success)
        self.assertTrue(any("Incompatibilidade de tipos" in str(e) for e in res_type_err.semantic_errors), msg=res_type_err.semantic_errors)

        # 'var' em nível superior continua proibido pela JLS estável (e também com preview=True)
        for bad_var in (
            "class D { void f(Object o) { if (o instanceof var v) {} } }",
            "class D { void f(Object o) { switch (o) { case var v -> {} default -> {} } } }",
            "record Num(int v) {} class D { void f(Object o) { if (o instanceof var(int x)) {} } }",
        ):
            for preview_flag in (False, True):
                with self.subTest(bad_var=bad_var, preview=preview_flag):
                    self.assertFalse(analyze_source(bad_var, enable_preview_primitive_patterns=preview_flag).success)

    def test_10_recursos_estaveis_anteriores_preservados(self):
        stable_comprehensive = """
        sealed interface Resultado permits Ok, Erro {}
        record Ok(String msg) implements Resultado {}
        final class Erro implements Resultado {
            final int codigo;
            Erro(int codigo) { this.codigo = codigo; }
        }
        class Demo {
            String processar(Object obj, Resultado r) {
                if (!(obj instanceof String s) || s.isEmpty()) {
                    return switch (r) {
                        case Ok(var texto) when texto.length() > 0 -> texto;
                        case Ok(_) -> "ok vazio";
                        case Erro e -> "erro";
                    };
                }
                boolean ehArray = obj instanceof int[];
                String when = s;
                return when;
            }
        }
        """
        res = analyze_source(stable_comprehensive, enable_preview_primitive_patterns=False)
        self.assertTrue(res.success, msg=f"Recursos estáveis anteriores quebraram: {res.semantic_errors} / {res.syntactic_error}")
        self.assertEqual(res.unresolved_checks, [])


if __name__ == "__main__":
    unittest.main()
