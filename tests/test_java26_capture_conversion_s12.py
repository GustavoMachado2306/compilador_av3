import unittest

from src.compiler.lexer import Lexer
from src.compiler.parser import Parser
from src.compiler.semantic import SemanticAnalyzer
from src.compiler.symbol_table import SymbolTable


def analyze_java(code: str, enable_preview: bool = False):
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer(
        SymbolTable(),
        enable_preview_primitive_patterns=enable_preview,
    )
    errors = analyzer.analyze(ast)
    return errors, analyzer


class TestJava26CaptureConversionS12(unittest.TestCase):
    """Testes abrangentes para a etapa S12 — Captura de Wildcards e Generics (JLS §5.1.10, §4.5.1, §4.10.2)."""

    def test_01_exemplos_obrigatorios_extends_super_e_irrestrito(self):
        code_ok = """
        import java.util.*;
        public class ExemplosValidos {
            void testar(
                List<? extends Number> numsExt,
                List<? super Integer> numsSup,
                List<?> valores
            ) {
                Number n = numsExt.get(0);
                numsExt.add(null);

                numsSup.add(10);
                Object objSup = numsSup.get(0);

                Object x = valores.get(0);
                valores.add(null);
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        invalid_cases = [
            (
                "add_em_extends",
                """
                import java.util.*;
                class T {
                    void m(List<? extends Number> numeros) {
                        numeros.add(10);
                    }
                }
                """,
            ),
            (
                "add_string_em_irrestrito",
                """
                import java.util.*;
                class T {
                    void m(List<?> valores) {
                        valores.add("Java");
                    }
                }
                """,
            ),
            (
                "ler_integer_de_super",
                """
                import java.util.*;
                class T {
                    void m(List<? super Integer> numeros) {
                        Integer n = numeros.get(0);
                    }
                }
                """,
            ),
            (
                "adicionar_double_em_super_integer",
                """
                import java.util.*;
                class T {
                    void m(List<? super Integer> numeros) {
                        numeros.add(3.14);
                    }
                }
                """,
            ),
        ]
        for label, src in invalid_cases:
            with self.subTest(case=label):
                errs, _ = analyze_java(src)
                self.assertTrue(len(errs) > 0, f"Era esperado erro semântico para '{label}'.")

    def test_02_preservacao_limites_declarados_e_wildcards(self):
        code_ok = """
        class Animal { void respirar() {} }
        class Cachorro extends Animal { void latir() {} }
        class CaixaAnimal<T extends Animal> {
            T valor;
            T obter() { return valor; }
            void colocar(T item) { this.valor = item; }
        }
        public class TesteLimites {
            void ok(CaixaAnimal<?> c1, CaixaAnimal<? extends Cachorro> c2, CaixaAnimal<? super Cachorro> c3) {
                Animal a = c1.obter();
                a.respirar();
                Animal ac = c2.obter();
                Cachorro dog = c2.obter();
                dog.latir();
                c3.colocar(new Cachorro());
                Animal baseC3 = c3.obter();
                baseC3.respirar();
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        code_err = """
        class Animal { void respirar() {} }
        class Cachorro extends Animal { void latir() {} }
        class CaixaAnimal<T extends Animal> {
            T valor;
            T obter() { return valor; }
            void colocar(T item) { this.valor = item; }
        }
        public class TesteLimitesErr {
            void falha(CaixaAnimal<?> c1) {
                Cachorro d = c1.obter();
            }
        }
        """
        errs, _ = analyze_java(code_err)
        self.assertTrue(len(errs) > 0, "Era esperado erro ao atribuir CaixaAnimal<?>.obter() (Animal) para Cachorro.")

        code_method_err = """
        class Animal { void respirar() {} }
        class CaixaAnimal<T extends Animal> {
            T obter() { return null; }
        }
        public class TesteMetodoCapErr {
            void falha(CaixaAnimal<?> c) {
                var a = c.obter();
                a.inexistente();
            }
        }
        """
        errs_m, _ = analyze_java(code_method_err)
        self.assertTrue(len(errs_m) > 0, "Era esperado erro ao chamar método inexistente em var capturado CAP#k.")

    def test_03_heranca_e_interfaces_genericas_com_wildcards(self):
        code_ok = """
        import java.util.*;
        interface Fonte<E> {
            E pegar();
        }
        class FonteNumerica<N extends Number> implements Fonte<N> {
            public N pegar() { return null; }
        }
        public class TesteHeranca {
            void validar(
                ArrayList<? extends Integer> alInt,
                ArrayList<? super Number> alSupNum,
                FonteNumerica<?> fn
            ) {
                Collection<? extends Number> colNum = alInt;
                List<? extends Number> lstNum = alInt;
                Collection<? super Integer> colSupInt = alSupNum;
                Fonte<? extends Number> f = fn;
                Number n1 = fn.pegar();
                Number n2 = f.pegar();
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        code_invariancia_err = """
        import java.util.*;
        public class TesteInvariancia {
            void falha(List<Integer> ints) {
                List<Number> nums = ints;
            }
        }
        """
        errs_inv, _ = analyze_java(code_invariancia_err)
        self.assertTrue(len(errs_inv) > 0, "List<Integer> não é subtipo de List<Number> (invariância).")

    def test_04_metodos_com_parametros_wildcard_e_retornos_genericos(self):
        code_ok = """
        import java.util.*;
        public class TesteMetodos {
            double somar(List<? extends Number> lista) {
                Number primeiro = lista.get(0);
                return primeiro.doubleValue();
            }
            void preencher(List<? super Integer> destino) {
                destino.add(42);
            }
            void usar(List<Integer> ints, List<Number> nums, List<Object> objs) {
                double s = somar(ints);
                preencher(ints);
                preencher(nums);
                preencher(objs);

                List<? extends Number> sub = ints.subList(0, 1);
                Number n = sub.get(0);
                Iterator<? extends Number> it = ints.iterator();
                Number next = it.next();
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        code_err = """
        import java.util.*;
        public class TesteMetodosErr {
            double somar(List<? extends Number> lista) { return 0.0; }
            void preencher(List<? super Integer> destino) {}
            void usar(List<String> strs, List<Double> doubles) {
                somar(strs);
                preencher(doubles);
            }
        }
        """
        errs_err, _ = analyze_java(code_err)
        self.assertEqual(len(errs_err), 2, f"Esperados 2 erros semânticos, obtidos: {[e.message for e in errs_err]}")

    def test_05_listas_aninhadas_e_dupla_captura(self):
        code_ok = """
        import java.util.*;
        public class TesteAninhado {
            void ok(List<List<Integer>> matriz, List<? extends List<? extends Number>> visao) {
                List<? extends List<? extends Number>> v = matriz;
                var linha = visao.get(0);
                Number elem = linha.get(0);
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        code_err_1 = """
        import java.util.*;
        public class TesteAninhadoErr1 {
            void falha(List<List<Integer>> matriz) {
                List<List<? extends Number>> invalida = matriz;
            }
        }
        """
        errs1, _ = analyze_java(code_err_1)
        self.assertTrue(len(errs1) > 0, "List<List<Integer>> não deve ser atribuível a List<List<? extends Number>>.")

        code_err_2 = """
        import java.util.*;
        public class TesteAninhadoErr2 {
            void falha(List<? extends List<? extends Number>> visao) {
                var linha = visao.get(0);
                linha.add(10);
            }
        }
        """
        errs2, _ = analyze_java(code_err_2)
        self.assertTrue(len(errs2) > 0, "Escrita em elemento obtido de captura aninhada deve falhar.")

    def test_06_inferencia_e_sobrecarga_com_wildcards(self):
        code_ok = """
        import java.util.*;
        public class TesteInferencia {
            <T> T primeiro(List<? extends T> lista) {
                return lista.get(0);
            }
            void processar(List<? extends Number> nums) {}
            void processar(List<String> strs) {}

            void executar(List<Integer> ints, List<Object> objs, List<String> strs) {
                Number p = primeiro(ints);
                Collections.copy(objs, ints);
                processar(ints);
                processar(strs);
                var elem = ints.get(0);
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        code_copy_err = """
        import java.util.*;
        public class TesteCopyErr {
            void executar(List<String> dst, List<Integer> src) {
                Collections.copy(dst, src);
            }
        }
        """
        errs_copy, _ = analyze_java(code_copy_err)
        self.assertTrue(len(errs_copy) > 0, "Collections.copy(List<String>, List<Integer>) deve falhar.")

    def test_07_capturas_independentes_e_limites_recursivos(self):
        code_ok = """
        interface Comparavel<T> {
            int comparar(T outro);
        }
        class Registro<T extends Comparavel<T>> {
            T valor;
            T obter() { return valor; }
        }
        public class TesteRecursivoOk {
            void compararConsigoMesmo(Registro<?> r) {
                var x = r.obter();
                int cmp = x.comparar(x);
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [], f"Erros inesperados: {[e.message for e in errs]}")

        code_indep_err = """
        import java.util.*;
        public class TesteCapturasIndep {
            void copiarProprio(List<?> lista) {
                lista.add(lista.get(0));
            }
        }
        """
        errs_self, _ = analyze_java(code_indep_err)
        self.assertTrue(len(errs_self) > 0, "lista.add(lista.get(0)) em List<?> gera capturas independentes e deve falhar.")

        code_rec_err = """
        interface Comparavel<T> {
            int comparar(T outro);
        }
        class Registro<T extends Comparavel<T>> {
            T obter() { return null; }
        }
        public class TesteRecursivoErr {
            void compararDiferentes(Registro<?> r1, Registro<?> r2) {
                var x = r1.obter();
                var y = r2.obter();
                int cmp = x.comparar(y);
            }
        }
        """
        errs_rec, _ = analyze_java(code_rec_err)
        self.assertTrue(len(errs_rec) > 0, "r1.obter().comparar(r2.obter()) deve falhar por capturas distintas (CAP#1 vs CAP#2).")


if __name__ == "__main__":
    unittest.main()

