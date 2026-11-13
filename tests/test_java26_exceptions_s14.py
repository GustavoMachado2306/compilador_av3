"""
Suíte de Testes Automatizados para Etapa S14 — Análise Completa de Exceções Verificadas (JLS §11).
Cobre todas as 12 funcionalidades obrigatórias e os exemplos obrigatórios da especificação S14.
"""

import unittest
from src.main import analyze_source


class TestJava26CheckedExceptionsS14(unittest.TestCase):
    """Testes semânticos abrangentes para exceções verificadas conforme a JLS §11."""

    # -------------------------------------------------------------------------
    # Exemplos Obrigatórios da Especificação S14
    # -------------------------------------------------------------------------
    def test_01_exemplo_obrigatorio_filereader_sem_tratamento_erro(self):
        source = """
        import java.io.FileReader;
        class Leitor {
            void carregar() {
                FileReader arquivo = new FileReader("dados.txt");
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(
            any("Exceção verificada não reportada" in str(e) and "FileNotFoundException" in str(e) for e in res.semantic_errors),
            msg=res.semantic_errors,
        )

    def test_02_exemplo_obrigatorio_filereader_com_throws_superclasse_valido(self):
        source = """
        import java.io.*;
        class Leitor {
            void carregar() throws IOException {
                FileReader arquivo = new FileReader("dados.txt");
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_exemplo_obrigatorio_filereader_com_try_catch_valido(self):
        source = """
        import java.io.*;
        class Leitor {
            void carregar() {
                try {
                    new FileReader("dados.txt");
                } catch (IOException e) {
                    System.out.println(e);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    # -------------------------------------------------------------------------
    # Funcionalidades 1 e 2: Checked vs Unchecked (JLS §11.1.1)
    # -------------------------------------------------------------------------
    def test_04_checked_vs_unchecked_hierarquias_embutidas_e_customizadas(self):
        source = """
        class MinhaChecked extends Exception {}
        class MinhaUnchecked extends RuntimeException {}
        class MeuErro extends Error {}
        class Demo {
            void okUnchecked() {
                if (false) throw new MinhaUnchecked();
                if (false) throw new MeuErro();
                if (false) throw new IllegalArgumentException("bad");
            }
            void erroCheckedCustom() {
                throw new MinhaChecked();
            }
            void erroThrowableDireto() {
                throw new Throwable();
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertTrue(any("MinhaChecked" in m and "não reportada" in m for m in msgs), msg=msgs)
        self.assertTrue(any("Throwable" in m and "não reportada" in m for m in msgs), msg=msgs)
        self.assertFalse(any("MinhaUnchecked" in m or "MeuErro" in m or "IllegalArgumentException" in m for m in msgs), msg=msgs)

    def test_05_throw_tipo_nao_throwable_invalido(self):
        source = """
        class Demo {
            void bad1() { throw 123; }
            void bad2() { throw new Object(); }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertGreaterEqual(sum("JLS §14.18" in m for m in msgs), 2, msg=msgs)

    # -------------------------------------------------------------------------
    # Funcionalidades 3, 4 e 6: Métodos, Construtores e super()/this()
    # -------------------------------------------------------------------------
    def test_06_chamadas_de_metodos_propagam_excecoes_verificadas(self):
        source = """
        class ParseEx extends Exception {}
        class Servico {
            void ler() throws ParseEx {}
            void chamarSemTratar() {
                ler();
            }
            void chamarComThrows() throws ParseEx {
                ler();
            }
            void chamarComCatch() {
                try {
                    ler();
                } catch (ParseEx e) {}
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertEqual(sum("ParseEx" in m and "não reportada" in m for m in msgs), 1, msg=msgs)

    def test_07_construtores_super_explicito_implicito_e_this(self):
        source = """
        class InitEx extends Exception {}
        class Pai {
            Pai() throws InitEx {}
        }
        class FilhoErroImplicito extends Pai {
            FilhoErroImplicito() {
            }
        }
        class FilhoErroExplicito extends Pai {
            FilhoErroExplicito() {
                super();
            }
        }
        class FilhoOk extends Pai {
            FilhoOk() throws InitEx {
                super();
            }
            FilhoOk(int x) {
                this();
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertTrue(any("FilhoErroImplicito" in m for m in msgs), msg=msgs)
        self.assertTrue(any("FilhoErroExplicito" in m for m in msgs), msg=msgs)
        self.assertTrue(any("construtor 'FilhoOk'" in m for m in msgs), msg=msgs)

    def test_08_construtor_padrao_implicito_em_subclasse_nao_propaga_checked_de_super(self):
        source = """
        class FalhaEx extends Exception {}
        class Base {
            Base() throws FalhaEx {}
        }
        class Derivada extends Base {
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("FalhaEx" in str(e) and "Derivada" in str(e) for e in res.semantic_errors), msg=res.semantic_errors)

    # -------------------------------------------------------------------------
    # Funcionalidade 5: Validação de Cláusulas throws (JLS §8.4.6)
    # -------------------------------------------------------------------------
    def test_09_validacao_clausula_throws_e_generics(self):
        source = """
        class App<E extends Exception, T> {
            void ok() throws E {}
            void errPrimitive() throws int {}
            void errString() throws String {}
            void errUnboundedTypeVar() throws T {}
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertTrue(any("int" in m and "throws" in m for m in msgs), msg=msgs)
        self.assertTrue(any("String" in m and "throws" in m for m in msgs), msg=msgs)
        self.assertTrue(any("'T'" in m and "throws" in m for m in msgs), msg=msgs)
        self.assertFalse(any("'E'" in m for m in msgs), msg=msgs)

    # -------------------------------------------------------------------------
    # Funcionalidades 7, 8 e 9: try/catch/finally, try-with-resources e alcançabilidade
    # -------------------------------------------------------------------------
    def test_10_try_catch_finally_escapam_excecoes_de_catch_e_finally(self):
        source = """
        class ExA extends Exception {}
        class ExB extends Exception {}
        class ExC extends Exception {}
        class Fluxo {
            void podeA() throws ExA {}
            void podeB() throws ExB {}
            void podeC() throws ExC {}
            void m1() {
                try {
                    podeA();
                } catch (ExA e) {
                    podeB();
                } finally {
                    podeC();
                }
            }
            void m2() throws ExB, ExC {
                try {
                    podeA();
                } catch (ExA e) {
                    podeB();
                } finally {
                    podeC();
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertTrue(any("ExB" in m and "m1" in m for m in msgs), msg=msgs)
        self.assertTrue(any("ExC" in m and "m1" in m for m in msgs), msg=msgs)
        self.assertFalse(any("m2" in m for m in msgs), msg=msgs)

    def test_11_try_with_resources_propaga_close_verificado(self):
        source = """
        class CloseEx extends Exception {}
        class Recurso implements AutoCloseable {
            public void close() throws CloseEx {}
        }
        class Uso {
            void ok() {
                try (Recurso r = new Recurso()) {
                    int x = 1;
                } catch (CloseEx e) {}
            }
            void erro() {
                try (Recurso r = new Recurso()) {
                    int x = 1;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertEqual(len(msgs), 1, msg=msgs)
        self.assertTrue("CloseEx" in msgs[0] and "close()" in msgs[0], msg=msgs)

    def test_12_catch_parametros_invalidos_e_inalcancaveis(self):
        source = """
        class ExBase extends Exception {}
        class ExSub extends ExBase {}
        class ExNaoLancada extends Exception {}
        class TesteCatch {
            void lancar() throws ExSub {}
            void casosInvalidos() {
                try { int a = 1; } catch (int x) {}
                try { int b = 1; } catch (String s) {}
                try { int c = 1; } catch (ExNaoLancada e) {}
                try { lancar(); } catch (ExBase e) {} catch (ExSub s) {}
            }
            void casosValidosExentos() {
                try { int x = 1; } catch (Exception e) {}
                try { int y = 1; } catch (Throwable t) {}
                try { int z = 1; } catch (RuntimeException r) {}
                try { int w = 1; } catch (Error err) {}
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertTrue(any("'int'" in m and "JLS §14.20" in m for m in msgs), msg=msgs)
        self.assertTrue(any("'String'" in m and "JLS §14.20" in m for m in msgs), msg=msgs)
        self.assertTrue(any("ExNaoLancada" in m and "JLS §11.2.3" in m for m in msgs), msg=msgs)
        self.assertTrue(any("ExSub" in m and "JLS §14.20" in m for m in msgs), msg=msgs)
        self.assertFalse(any("casosValidosExentos" in m for m in msgs), msg=msgs)

    def test_13_chamada_externa_desconhecida_em_try_nao_gera_falso_inalcancavel(self):
        source = """
        class ExLocal extends Exception {}
        class IntegracaoExterna {
            void executar(PacoteExterno lib) {
                try {
                    lib.acaoDesconhecida();
                } catch (ExLocal e) {
                    System.out.println(e);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        self.assertTrue(len(res.unresolved_checks) > 0)

    # -------------------------------------------------------------------------
    # Funcionalidade 10: Sobrescrita de Métodos (JLS §8.4.8.3)
    # -------------------------------------------------------------------------
    def test_14_sobrescrita_throws_incompativel_e_compativel(self):
        source = """
        class ExPai extends Exception {}
        class ExFilho extends ExPai {}
        class ExEstranha extends Exception {}
        interface Contrato {
            void operar() throws ExPai;
            void semChecked();
        }
        class ImplInvalida implements Contrato {
            public void operar() throws ExEstranha {}
            public void semChecked() throws ExPai {}
        }
        class ImplValida implements Contrato {
            public void operar() throws ExFilho {}
            public void semChecked() throws IllegalStateException {}
            public String toString() throws ExEstranha { return ""; }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertTrue(any("operar" in m and "ExEstranha" in m and "JLS §8.4.8.3" in m for m in msgs), msg=msgs)
        self.assertTrue(any("semChecked" in m and "ExPai" in m and "JLS §8.4.8.3" in m for m in msgs), msg=msgs)
        self.assertTrue(any("toString" in m and "ExEstranha" in m and "JLS §8.4.8.3" in m for m in msgs), msg=msgs)
        self.assertFalse(any("ExFilho" in m or "IllegalStateException" in m for m in msgs), msg=msgs)

    # -------------------------------------------------------------------------
    # Funcionalidade 11: Lambdas e Method References (JLS §15.27.3 / §15.13.2)
    # -------------------------------------------------------------------------
    def test_15_lambdas_e_method_references_isolam_e_validam_throws(self):
        source = """
        import java.io.*;
        @FunctionalInterface
        interface AcaoIO {
            void run() throws IOException;
        }
        class Helpers {
            static void ler() throws FileNotFoundException {}
        }
        class LambdasERefs {
            void okLambda() {
                AcaoIO a = () -> { new FileReader("ok.txt"); };
                Callable<String> c = () -> { new FileReader("ok.txt"); return "ok"; };
            }
            void erroLambdaMesmoComThrowsExterno() throws IOException {
                Runnable r = () -> { new FileReader("bad.txt"); };
            }
            void okMethodRef() {
                AcaoIO ref = Helpers::ler;
            }
            void erroMethodRef() throws IOException {
                Runnable ref = Helpers::ler;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertTrue(any("lambda" in m.lower() and "FileNotFoundException" in m for m in msgs), msg=msgs)
        self.assertTrue(any("Referência a método/construtor" in m and "FileNotFoundException" in m for m in msgs), msg=msgs)
        self.assertEqual(len(msgs), 2, msg=msgs)

    # -------------------------------------------------------------------------
    # Funcionalidade 12: Inicializadores, Classes Anônimas, Switch Expr e Rethrow Preciso
    # -------------------------------------------------------------------------
    def test_16_inicializadores_classe_anonima_e_constante_enum(self):
        source = """
        class InitFail extends Exception {}
        class Helper {
            static int boom() throws InitFail { return 1; }
        }
        class SemCtorValido {
            int campo = Helper.boom();
        }
        class ComCtorOk {
            int x;
            { x = Helper.boom(); }
            ComCtorOk() throws InitFail {}
        }
        class ComBlocoEstaticoInvalido {
            static { Helper.boom(); }
        }
        enum MeuEnum {
            A(Helper.boom());
            MeuEnum(int v) {}
        }
        class AnonHolder {
            void metodo() {
                Object o = new Object() {
                    int v = Helper.boom();
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertTrue(any("SemCtorValido" in m and "InitFail" in m for m in msgs), msg=msgs)
        self.assertTrue(any("inicializador estático" in m and "InitFail" in m for m in msgs), msg=msgs)
        self.assertTrue(any("constante de enum 'A'" in m and "InitFail" in m for m in msgs), msg=msgs)
        self.assertTrue(any("metodo" in m and "InitFail" in m for m in msgs), msg=msgs)
        self.assertFalse(any("ComCtorOk" in m for m in msgs), msg=msgs)

    def test_17_precise_rethrow_e_switch_expression(self):
        source = """
        import java.io.*;
        class RethrowESwitch {
            void preciseRethrowOk() throws FileNotFoundException {
                try {
                    new FileReader("a.txt");
                } catch (Exception e) {
                    throw e;
                }
            }
            int switchThrows(int k) {
                return switch (k) {
                    case 1 -> {
                        try {
                            new FileReader("a.txt");
                            yield 10;
                        } catch (FileNotFoundException e) {
                            yield 0;
                        }
                    }
                    default -> {
                        new FileReader("b.txt");
                        yield 1;
                    }
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = [str(e) for e in res.semantic_errors]
        self.assertEqual(len(msgs), 1, msg=msgs)
        self.assertTrue("switchThrows" in msgs[0] and "FileNotFoundException" in msgs[0], msg=msgs)
        self.assertFalse(any("preciseRethrowOk" in m for m in msgs), msg=msgs)


if __name__ == "__main__":
    unittest.main()
