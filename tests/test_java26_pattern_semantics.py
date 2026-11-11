"""
Suíte S7.8 — Auditoria S6 Herdada (break rotulado em bloco, fronteiras de lambdas/switch expressions/inicializadores),
Separação Estrita de Preview Primitive Patterns (JEP 507/530) e Fronteira de Tipos Externos (unresolved_checks).
"""

import unittest
from src.main import analyze_source


class TestJava26PatternSemanticsAndBoundaries(unittest.TestCase):
    """Testes transversais de fronteira semântica S6+S7, preview e tipos externos."""

    def test_01_auditoria_s6_break_externo_em_bloco_rotulado_valido(self):
        source = """
        class Demo {
            void executar(boolean condicao) {
                externo: {
                    if (condicao) {
                        break externo;
                    }
                    System.out.println("nao executado");
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"break rotulado em bloco externo deve compilar: {res.semantic_errors}")

    def test_02_auditoria_s6_continue_exclusivo_de_laco_e_break_sem_label(self):
        bad_continue_block = """
        class Demo {
            void f() {
                externo: {
                    continue externo;
                }
            }
        }
        """
        self.assertFalse(analyze_source(bad_continue_block).success)

        bad_unlabeled_break_in_labeled_block = """
        class Demo {
            void f(boolean c) {
                bloco: {
                    if (c) break;
                }
            }
        }
        """
        self.assertFalse(analyze_source(bad_unlabeled_break_in_labeled_block).success)

    def test_03_auditoria_s6_isolamento_de_label_e_loop_em_lambda_metodo_construtor_inicializador_e_switch_expr(self):
        # Labels e laços externos não atravessam lambda, switch expression nem classe local
        bad_break_through_lambda = """
        class Demo {
            void f() {
                for (int i = 0; i < 3; i++) {
                    Runnable r = () -> { break; };
                }
            }
        }
        """
        self.assertFalse(analyze_source(bad_break_through_lambda).success)

        bad_break_through_switch_expr = """
        class Demo {
            void f(int k) {
                fora: while (k > 0) {
                    int v = switch (k) {
                        default -> { break fora; }
                    };
                }
            }
        }
        """
        self.assertFalse(analyze_source(bad_break_through_switch_expr).success)

        bad_continue_in_local_class_method = """
        class Demo {
            void f() {
                laco: for (int i = 0; i < 2; i++) {
                    class Local {
                        void g() { continue laco; }
                    }
                }
            }
        }
        """
        self.assertFalse(analyze_source(bad_continue_in_local_class_method).success)

        bad_break_in_initializer = """
        class Demo {
            {
                break;
            }
            Demo() {}
        }
        """
        self.assertFalse(analyze_source(bad_break_in_initializer).success)

    def test_04_separacao_preview_primitive_patterns_padrao_vs_habilitado(self):
        prim_instanceof = """
        class Demo {
            void f(Object o, int n) {
                if (o instanceof int i) {
                    System.out.println(i);
                }
            }
        }
        """
        res_default = analyze_source(prim_instanceof, enable_preview_primitive_patterns=False)
        self.assertFalse(res_default.success, msg="Modo padrão Java SE 26 deve rejeitar primitive pattern top-level")

        res_preview = analyze_source(prim_instanceof, enable_preview_primitive_patterns=True)
        self.assertTrue(res_preview.success, msg=f"Com preview habilitado deveria aceitar: {res_preview.semantic_errors} / {res_preview.syntactic_error}")

        prim_switch = """
        class Demo {
            int testar(int n) {
                return switch (n) {
                    case 0 -> 100;
                    case int v when v > 10 -> v * 2;
                    case int v -> v;
                };
            }
        }
        """
        res_sw_default = analyze_source(prim_switch, enable_preview_primitive_patterns=False)
        self.assertFalse(res_sw_default.success)

        res_sw_preview = analyze_source(prim_switch, enable_preview_primitive_patterns=True)
        self.assertTrue(res_sw_preview.success, msg=f"Switch primitivo em preview falhou: {res_sw_preview.semantic_errors} / {res_sw_preview.syntactic_error}")

    def test_05_componentes_primitivos_em_record_pattern_rejeitados_sem_preview_e_var_valido(self):
        source = """
        record Medida(int valor, double peso) {}
        class Demo {
            void f(Object o) {
                if (o instanceof Medida(int v, double p)) {
                    double t = v + p;
                }
            }
        }
        """
        res_default = analyze_source(source, enable_preview_primitive_patterns=False)
        self.assertFalse(
            res_default.success,
            msg="Componente primitivo explícito em RecordPattern pertence ao preview JEP 530 e deve ser rejeitado sem preview",
        )
        self.assertIsNotNone(res_default.syntactic_error)

        res_preview = analyze_source(source, enable_preview_primitive_patterns=True)
        self.assertTrue(
            res_preview.success,
            msg=f"Com preview habilitado deveria aceitar componentes primitivos: {res_preview.semantic_errors} / {res_preview.syntactic_error}",
        )

        stable_var_source = """
        record Medida(int valor, double peso) {}
        class Demo {
            void f(Object o) {
                if (o instanceof Medida(var v, var p)) {
                    int iv = v;
                    double t = v + p;
                }
                if (o instanceof Medida(_, _)) {
                    System.out.println("ok");
                }
            }
        }
        """
        res_var = analyze_source(stable_var_source, enable_preview_primitive_patterns=False)
        self.assertTrue(
            res_var.success,
            msg=f"RecordPattern com 'var' e '_' sobre record com campos primitivos é estável no Java SE 26: {res_var.semantic_errors} / {res_var.syntactic_error}",
        )

    def test_06_fronteira_honesta_para_tipos_externos_nao_resolvidos(self):
        external_record = """
        import com.externo.Pair;
        class Demo {
            void f(Object o) {
                if (o instanceof Pair(String k, Integer v)) {
                    System.out.println(k);
                }
            }
        }
        """
        res_rec = analyze_source(external_record)
        self.assertTrue(res_rec.success, msg=f"Record externo não deve gerar falso erro: {res_rec.semantic_errors}")
        self.assertTrue(len(res_rec.unresolved_checks) > 0)

        external_sealed_switch = """
        import com.externo.ResultadoExterno;
        import com.externo.Sucesso;
        import com.externo.Falha;
        class Demo {
            int f(ResultadoExterno r) {
                return switch (r) {
                    case Sucesso s -> 1;
                    case Falha f -> 0;
                };
            }
        }
        """
        res_ext = analyze_source(external_sealed_switch)
        self.assertTrue(res_ext.success, msg=f"Tipo externo potencialmente sealed não deve gerar falso erro: {res_ext.semantic_errors}")
        self.assertTrue(len(res_ext.unresolved_checks) > 0)


if __name__ == "__main__":
    unittest.main()

