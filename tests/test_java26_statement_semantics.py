"""
Suíte de Testes Automatizados para Etapa S6 — Semântica Contextual, Integração S1–S5 e Recuperação de Erros.
Cobre: return em métodos/construtores/inicializadores/lambdas, escape de yield/break/continue,
condições não booleanas, integração com interfaces, enums, records, annotations, unidades compactas
e coleta múltipla de erros semânticos.
"""

import unittest
from src.main import analyze_source


class TestJava26StatementSemanticsS6(unittest.TestCase):
    """Testes de semântica contextual e integração completa das etapas S1–S6."""

    def test_01_return_invalido_em_void_construtor_inicializador_e_nao_void(self):
        cases = [
            ("void m() { return 10; }", 3, "void"),
            ("int m() { return; }", 3, "deve retornar valor"),
            ("Demo() { return 5; }", 3, "Construtor"),
            ("static { return; }", 3, "inicializador"),
            ("{ return; }", 3, "inicializador"),
        ]
        for member_src, err_line, msg_part in cases:
            with self.subTest(member_src=member_src):
                source = f"""
                class Demo {{
                    {member_src}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success)
                self.assertTrue(
                    any(msg_part in e and e.line == err_line for e in res.semantic_errors),
                    msg=res.semantic_errors,
                )

    def test_02_return_valido_em_lambda_dentro_de_metodo_ou_inicializador(self):
        source = """
        import java.util.function.IntUnaryOperator;
        class Demo {
            static {
                IntUnaryOperator op = x -> {
                    if (x > 0) return x;
                    return 0;
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_yield_nao_pode_escapar_atravessando_lambda_ou_metodo_de_classe_local(self):
        source = """
        import java.util.function.IntUnaryOperator;
        class Demo {
            int testar(int x) {
                int v = switch (x) {
                    default -> {
                        IntUnaryOperator fn = y -> {
                            yield y;
                        };
                        yield 1;
                    }
                };
                return v;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("yield" in e and e.line == 8 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_04_condicoes_nao_booleanas_rejeitadas_em_if_while_e_assert(self):
        for cond_stmt in ['if ("ok") {}', 'while (123) {}', 'assert "falha";']:
            with self.subTest(cond_stmt=cond_stmt):
                source = f"""
                class Demo {{
                    void m() {{
                        {cond_stmt}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success)
                self.assertTrue(any("boolean" in e and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_05_redeclaracao_de_variavel_entre_for_try_lambda_e_metodo(self):
        cases = [
            "int i = 0; for (int i = 1; i < 3; i++) {}",
            "int r = 0; try (var r = abrir()) {}",
            "int e = 0; try {} catch (Exception e) {}",
            "int p = 0; java.util.function.IntUnaryOperator f = p -> p + 1;",
        ]
        for body_code in cases:
            with self.subTest(body_code=body_code):
                source = f"""
                class Demo {{
                    Object abrir() {{ return null; }}
                    void m() {{
                        {body_code}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success)
                self.assertTrue(any("declarada novamente" in e for e in res.semantic_errors), msg=res.semantic_errors)

    def test_06_integracao_com_interface_enum_record_e_annotations(self):
        source = """
        @interface Trace { String value() default ""; }

        interface Executavel {
            default int rodar(int n) {
                int acc = 0;
                for (int i = 0; i < n; i++) {
                    acc += i;
                }
                return acc;
            }
        }

        enum Modo {
            RAPIDO {
                int fator() { return 2; }
            },
            SEGURO {
                int fator() { return 1; }
            };
            abstract int fator();
        }

        record Tarefa(@Trace("id") int id, Modo modo) implements Executavel {
            Tarefa {
                if (id < 0) {
                    throw new IllegalArgumentException("id");
                }
            }
            public int calcular() {
                return switch (modo) {
                    case RAPIDO -> 10 * modo.fator();
                    case SEGURO -> {
                        var base = rodar(3);
                        yield base;
                    }
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_07_unidade_de_compilacao_compacta_java25_26(self):
        source = """
        void saudar(String nome) {
            for (int i = 0; i < 2; i++) {
                if (i == 1) {
                    var msg = "Oi " + nome;
                }
            }
        }

        void main() {
            saudar("Java 26");
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_08_coleta_multiplos_erros_semanticos_em_uma_unica_execucao(self):
        source = """
        class MultiErro {
            void processar(int x) {
                var semInit;
                int a = 1;
                int a = 2;
                break;
                yield 99;
                return x;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertIsNone(res.syntactic_error)
        self.assertGreaterEqual(len(res.semantic_errors), 5, msg=res.semantic_errors)
        lines = {e.line for e in res.semantic_errors}
        self.assertTrue({4, 6, 7, 8, 9}.issubset(lines), msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()
