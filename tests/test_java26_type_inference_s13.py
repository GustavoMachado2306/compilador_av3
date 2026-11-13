import unittest

from src.lexer import Lexer
from src.parser import Parser
from src.semantic import SemanticAnalyzer
from src.symbol_table import SymbolTable
from src.type_inference import BoundSet, Constraint, ConstraintKind, InferenceVariable, JLS18ConstraintSolver


def analyze_java(code: str, enable_preview: bool = False):
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer(
        SymbolTable(),
        enable_preview_primitive_patterns=enable_preview,
    )
    errors = analyzer.analyze(ast)
    return errors, analyzer


class TestJava26TypeInferenceS13(unittest.TestCase):
    """Testes abrangentes para a etapa S13 — Inferência de Tipos Genéricos JLS §18."""

    def test_01_exemplos_obrigatorios_s13(self):
        code_ok = """
        import java.util.*;
        public class ExemplosS13 {
            static <T> T escolher(T a, T b) {
                return a;
            }
            static <T> List<T> criar() {
                return new ArrayList<>();
            }
            static <T extends Number> T identidade(T valor) {
                return valor;
            }
            void testar() {
                String resultado = escolher("Java", "SE 26");
                int len = escolher("Java", "SE 26").length();
                List<String> nomes = criar();
                nomes.add(resultado);
                Integer n = identidade(10);
                Number num = identidade(3.14);
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        code_err = """
        class LimiteViolado {
            static <T extends Number> T identidade(T valor) {
                return valor;
            }
            void testar() {
                String s = identidade("abc");
            }
        }
        """
        errs_b, _ = analyze_java(code_err)
        self.assertTrue(len(errs_b) > 0, "identidade('abc') deve falhar por violar <T extends Number>.")

    def test_02_restricoes_igualdade_subtipagem_e_conflitos(self):
        code_ok = """
        import java.util.*;
        class Caixa<X> {}
        public class TesteRestricoesOk {
            static <T> void unir(List<T> a, List<T> b) {}
            static <T> void par(Caixa<T> c, T v) {}
            static <T> T escolher(T a, T b) { return a; }

            void ok(List<String> l1, List<String> l2, Caixa<Number> cn) {
                unir(l1, l2);
                par(cn, 42);
                Number lub = escolher(10, 2.5);
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        invalid_cases = [
            (
                "igualdade_conflitante_listas",
                """
                import java.util.*;
                class T {
                    static <T> void unir(List<T> a, List<T> b) {}
                    void m(List<String> ls, List<Integer> li) {
                        unir(ls, li);
                    }
                }
                """,
            ),
            (
                "igualdade_vs_subtipo_caixa",
                """
                class Caixa<X> {}
                class T {
                    static <T> void par(Caixa<T> c, T v) {}
                    void m(Caixa<Integer> ci) {
                        par(ci, "texto");
                    }
                }
                """,
            ),
            (
                "retorno_incompativel_argumentos",
                """
                class T {
                    static <T> T escolher(T a, T b) { return a; }
                    void m() {
                        String s = escolher(10, 20);
                    }
                }
                """,
            ),
            (
                "argumento_explicito_viola_limite",
                """
                class T {
                    static <T extends Number> T id(T v) { return v; }
                    void m() {
                        String s = T.<String>id("abc");
                    }
                }
                """,
            ),
        ]
        for label, src in invalid_cases:
            with self.subTest(case=label):
                e_list, _ = analyze_java(src)
                self.assertTrue(len(e_list) > 0, f"Era esperado erro semântico para '{label}'.")

    def test_03_contexto_atribuicao_retorno_e_chamadas_aninhadas(self):
        code_ok = """
        import java.util.*;
        public class TesteContextoOk {
            static <T> List<T> criar() { return new ArrayList<>(); }
            static <T> List<T> emptyList() { return new ArrayList<>(); }
            static <T> List<T> singleton(T x) { return new ArrayList<>(); }
            static <U> U head(List<U> l) { return l.get(0); }

            List<String> campo = criar();

            void consumirLista(List<String> l) {}
            List<Integer> retornarLista() {
                return criar();
            }
            void testar() {
                List<String> atrib;
                atrib = criar();
                consumirLista(criar());
                consumirLista(new ArrayList<>());
                String s1 = head(emptyList());
                String s2 = head(singleton("SE 26"));
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        invalid_cases = [
            (
                "return_tipo_incompativel",
                """
                import java.util.*;
                class T {
                    static <T> List<T> criar() { return new ArrayList<>(); }
                    Set<Integer> invalido() { return criar(); }
                }
                """,
            ),
            (
                "cadeia_head_singleton_incompativel",
                """
                import java.util.*;
                class T {
                    static <T> List<T> singleton(T x) { return new ArrayList<>(); }
                    static <U> U head(List<U> l) { return l.get(0); }
                    void m() {
                        Integer n = head(singleton("oi"));
                    }
                }
                """,
            ),
        ]
        for label, src in invalid_cases:
            with self.subTest(case=label):
                e_list, _ = analyze_java(src)
                self.assertTrue(len(e_list) > 0, f"Era esperado erro para '{label}'.")

    def test_04_dependencias_entre_variaveis_e_recursividade(self):
        code_ok = """
        import java.util.*;
        public class TesteDependenciasOk {
            static <A, B extends A> A mesclar(A a, B b) { return a; }
            static <A, B extends Comparable<A>> void verificar(A a, B b) {}
            static <K, V, M extends Map<K, V>> K chaveDe(K k, V v, M mapa) { return k; }

            void ok(Map<String, Integer> m) {
                Number n = mesclar(3.14, 10);
                verificar("java", "se26");
                verificar(10, 20);
                String k = chaveDe("a", 1, m);
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        code_conflict = """
        public class TesteDependenciaConflito {
            static <A, B extends Comparable<A>> void verificar(A a, B b) {}
            static <A, B extends A> A mesclar(A a, B b) { return a; }

            void falhar() {
                verificar("texto", 123);
                String s = mesclar("texto", 123);
            }
        }
        """
        errs_c, _ = analyze_java(code_conflict)
        self.assertEqual(len(errs_c), 2, f"Esperados 2 erros de dependência conflitante, obtidos: {[e.message for e in errs_c]}")

    def test_05_integracao_com_lambdas_e_method_references(self):
        code_ok = """
        import java.util.*;
        import java.util.function.*;
        public class TestePolyFuncOk {
            static <T, R> R mapear(T x, Function<T, R> fn) { return fn.apply(x); }
            static <A, B, C> C compor(A x, Function<A, B> f, Function<B, C> g) {
                return g.apply(f.apply(x));
            }
            static <T> T construir(Supplier<T> sup) { return sup.get(); }

            void ok() {
                int tamanho = mapear("Java SE 26", s -> s.length());
                var tamBox = mapear("Java SE 26", s -> s.length());
                int valor = tamBox.intValue();

                var comp = compor("abc", s -> s.length(), n -> n * 2.5);
                double d = comp.doubleValue();

                var tamRef = mapear("Java", String::length);
                int vRef = tamRef.intValue();

                List<String> lista = construir(ArrayList::new);
                lista.add("ok");
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        invalid_cases = [
            (
                "lambda_retorno_conflita_target",
                """
                import java.util.function.*;
                class T {
                    static <T, R> R map(T x, Function<T, R> fn) { return null; }
                    void m() { String s = map(10, x -> x + 1); }
                }
                """,
            ),
            (
                "lambda_param_explicito_incompativel",
                """
                import java.util.function.*;
                class T {
                    static <T, R> R map(T x, Function<T, R> fn) { return null; }
                    void m() { int n = map("abc", (Integer s) -> 1); }
                }
                """,
            ),
            (
                "compose_encadeado_metodo_inexistente",
                """
                import java.util.function.*;
                class Num { int val() { return 1; } }
                class T {
                    static <A, B, C> C compor(A x, Function<A, B> f, Function<B, C> g) { return null; }
                    void m() { var r = compor("a", s -> new Num(), n -> n.naoExiste()); }
                }
                """,
            ),
            (
                "method_ref_retorno_incompativel",
                """
                import java.util.function.*;
                class T {
                    static <T, R> R map(T x, Function<T, R> fn) { return null; }
                    void m() { String s = map("abc", String::length); }
                }
                """,
            ),
        ]
        for label, src in invalid_cases:
            with self.subTest(case=label):
                e_list, _ = analyze_java(src)
                self.assertTrue(len(e_list) > 0, f"Era esperado erro em '{label}'.")

    def test_06_condicionais_wildcards_e_especificidade_sobrecarga(self):
        code_ok = """
        import java.util.*;
        public class TesteCondWildcardOk {
            static <T> List<T> criar() { return new ArrayList<>(); }
            static <T> T primeiro(List<? extends T> l) { return l.get(0); }
            static <T> void copiar(List<? super T> dst, List<? extends T> src) {}
            static <T> T escolher(T a, T b) { return a; }

            static <T> int selecionar(List<T> a) { return 1; }
            static <U> String selecionar(Collection<U> a) { return "c"; }

            void consumir(List<String> l) {}

            void ok(
                boolean cond,
                List<Integer> li,
                List<Double> ld,
                List<String> ls,
                List<Object> objs
            ) {
                List<String> c1 = cond ? criar() : criar();
                consumir(cond ? criar() : criar());
                Number n = primeiro(li);
                copiar(objs, li);
                List<? extends Number> numsL = escolher(li, ld);
                List<?> wild = escolher(li, ls);
                int r = selecionar(ls);
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        code_ambig_e_conflito = """
        import java.util.*;
        public class TesteAmbigEConflito {
            static <T> void amb(T a, String b) {}
            static <T> void amb(String a, T b) {}
            static <T> T escolher(T a, T b) { return a; }
            static <T> void copiar(List<? super T> dst, List<? extends T> src) {}

            void falhar(List<Integer> li, List<String> ls) {
                amb("a", "b");
                List<Number> bad = escolher(li, ls);
                copiar(ls, li);
            }
        }
        """
        errs_ac, _ = analyze_java(code_ambig_e_conflito)
        self.assertEqual(len(errs_ac), 3, f"Esperados 3 erros (ambiguidade, LUB inválido e copy inválido), obtidos: {[e.message for e in errs_ac]}")

    def test_07_solucionador_constraints_unidade_direta(self):
        sa = SemanticAnalyzer(SymbolTable())
        solver = JLS18ConstraintSolver(sa)

        # Occurs check (referência cíclica infinita α = List<α>)
        bset_cycle = BoundSet()
        bset_cycle.ensure_var(InferenceVariable("T", "INF#90"))
        solver._reduce_and_incorporate(
            bset_cycle,
            [Constraint(ConstraintKind.EQUALITY, "INF#90", "List<INF#90>")],
        )
        self.assertTrue(len(bset_cycle.contradictions) > 0, "Occurs check deveria rejeitar INF#90 = List<INF#90>.")

        # Limites superiores incompatíveis entre classe concreta final e interface não implementada
        bset_bounds = BoundSet()
        bset_bounds.ensure_var(InferenceVariable("T", "INF#91", ("String", "Number")))
        bset_bounds.add_upper("INF#91", "String")
        bset_bounds.add_upper("INF#91", "Number")
        solver._reduce_and_incorporate(bset_bounds, [])
        self.assertTrue(len(bset_bounds.contradictions) > 0, "String & Number devem gerar contradição no BoundSet.")

        # Capturas independentes passando para o mesmo parâmetro de tipo T: unir(List<?>, List<?>)
        code_indep = """
        import java.util.*;
        class T {
            static <T> void unir(List<T> a, List<T> b) {}
            void m(List<?> a, List<?> b) { unir(a, b); }
        }
        """
        errs_ind, _ = analyze_java(code_indep)
        self.assertTrue(len(errs_ind) > 0, "unir(List<?>, List<?>) gera capturas independentes e não possui solução.")


if __name__ == "__main__":
    unittest.main()
