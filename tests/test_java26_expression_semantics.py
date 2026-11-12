import unittest
from src.main import analyze_source


class TestJava26ExpressionSemanticsS8(unittest.TestCase):
    """Valida integração entre expressões S8, patterns, JEP 530, early construction e limites externos."""

    def test_01_inherited_s7_1_instanceof_object_integer_passes_without_preview(self):
        source = """
        class HerancaS71 {
            void run() {
                Object objeto = "texto";
                boolean resultado = objeto instanceof Integer;
            }
        }
        """
        res_off = analyze_source(source, enable_preview_primitive_patterns=False)
        res_on = analyze_source(source, enable_preview_primitive_patterns=True)
        self.assertTrue(res_off.success, msg=res_off.semantic_errors)
        self.assertTrue(res_on.success, msg=res_on.semantic_errors)

    def test_02_disjoint_final_instanceof_string_integer_rejected(self):
        source = """
        class Disj {
            void run(String s) {
                boolean b = s instanceof Integer;
            }
        }
        """
        res = analyze_source(source, enable_preview_primitive_patterns=False)
        self.assertFalse(res.success)

    def test_03_preview_separation_primitive_instanceof_and_switch_selector(self):
        src_inst = """
        class Prev {
            void run(int x) {
                boolean ok = x instanceof double;
            }
        }
        """
        self.assertFalse(analyze_source(src_inst, enable_preview_primitive_patterns=False).success)
        self.assertTrue(analyze_source(src_inst, enable_preview_primitive_patterns=True).success)

        src_sw = """
        class PrevSw {
            String run(double d) {
                return switch (d) {
                    case 0.0 -> "zero";
                    default -> "outro";
                };
            }
        }
        """
        self.assertFalse(analyze_source(src_sw, enable_preview_primitive_patterns=False).success)
        self.assertTrue(analyze_source(src_sw, enable_preview_primitive_patterns=True).success)

    def test_04_flow_scoping_in_logical_operators_and_ternary(self):
        source = """
        class Flow {
            int run(Object obj) {
                if (obj instanceof String s && s.length() > 0) {
                    return s.length();
                }
                int tam = (obj instanceof String txt) ? txt.length() : 0;
                if (!(obj instanceof Integer n)) {
                    return tam;
                }
                return n.intValue() + tam;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_early_construction_context_blocks_this_access_before_super(self):
        bad_src = """
        class Pai { Pai(int v) {} }
        class Filho extends Pai {
            int campo = 5;
            Filho() {
                super(this.campo);
            }
        }
        """
        ok_src = """
        class Pai { Pai(int v) {} }
        class Filho extends Pai {
            int campo;
            Filho(int v) {
                int local = v + 1;
                super(local);
                this.campo = v;
            }
        }
        """
        self.assertFalse(analyze_source(bad_src).success)
        self.assertTrue(analyze_source(ok_src).success)

    def test_06_external_types_record_unresolved_checks_without_false_errors(self):
        source = """
        import java.nio.file.Path;
        import java.nio.file.Files;
        class Ext {
            void run(Path p) {
                boolean existe = Files.exists(p);
                var len = p.toString().length();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        self.assertTrue(len(res.unresolved_checks) > 0)

    def test_07_switch_expression_exhaustiveness_with_sealed_records_and_expressions(self):
        source = """
        sealed interface Expr permits Num, Soma {}
        record Num(int v) implements Expr {}
        record Soma(Expr e, Expr d) implements Expr {}
        class Aval {
            int avaliar(Expr expr) {
                return switch (expr) {
                    case Num(var n) -> n;
                    case Soma(var a, var b) -> avaliar(a) + avaliar(b);
                };
            }
        }
        """
        res = analyze_source(source, enable_preview_primitive_patterns=False)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_08_anonymous_class_capturing_effectively_final_local_and_method_call(self):
        source = """
        interface Gerador { int gerar(); }
        class Demo {
            void run() {
                int fator = 7;
                Gerador g = new Gerador() {
                    @Override
                    public int gerar() {
                        return fator * 6;
                    }
                };
                int v = g.gerar();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

