import unittest
from src.main import analyze_source


class TestJava26S85Regressions(unittest.TestCase):
    """Auditoria final e regressões integradas das expressões S8.1–S8.5."""

    def test_01_s81_precedence_and_associativity_with_switch_expression(self):
        source = """
        class Reg {
            int calc(int k) {
                int r = 2 + switch (k) {
                    case 1 -> 3 * 4;
                    default -> 5;
                };
                return r;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_s82_casts_and_boxing_with_switch_expression(self):
        source = """
        class Reg {
            void m(int k) {
                double d = (double) switch (k) {
                    case 1 -> 10;
                    default -> 20;
                };
                Integer boxed = switch (k) {
                    case 1 -> 1;
                    default -> 2;
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_s83_member_access_method_call_and_array_creation_with_class_literal(self):
        source = """
        class Reg {
            void m() {
                Class<?>[] tipos = new Class<?>[] { String.class, int.class, int[].class };
                int len = tipos.length;
                String n = tipos[0].getName();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_s84_lambda_and_method_ref_inside_switch_expression(self):
        source = """
        import java.util.function.Function;
        class Reg {
            Function<String, Integer> selecionar(int modo) {
                return switch (modo) {
                    case 1 -> String::length;
                    default -> s -> s.length() + 1;
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_parenthesized_constants_and_casts_integration(self):
        source = """
        class Reg {
            void m() {
                byte b = (10 + 20);
                int c = ((int) 3.5) + (1 << 2);
                boolean ok = !(false) && (c > 0);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_06_switch_statement_vs_switch_expression_separation(self):
        source = """
        class Reg {
            int testar(int x) {
                int acc = 0;
                switch (x) {
                    case 1:
                        acc = 10;
                        break;
                    default:
                        acc = 20;
                }
                return switch (acc) {
                    case 10 -> 1;
                    default -> 2;
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_07_preview_primitive_patterns_flag_preserved_in_switch_expression(self):
        src = """
        class Reg {
            int f(Object o) {
                return switch (o) {
                    case int i -> i;
                    default -> 0;
                };
            }
        }
        """
        self.assertFalse(analyze_source(src, enable_preview_primitive_patterns=False).success)
        self.assertTrue(analyze_source(src, enable_preview_primitive_patterns=True).success)

    def test_08_unresolved_external_type_in_switch_expression_recorded(self):
        src = """
        import com.externo.Desconhecido;
        class Reg {
            int f(Desconhecido d) {
                return switch (d) {
                    default -> 0;
                };
            }
        }
        """
        res = analyze_source(src)
        self.assertTrue(res.success, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

