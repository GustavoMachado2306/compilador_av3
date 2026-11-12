import unittest
from src.main import analyze_source


class TestJava26S82RegressionsS83(unittest.TestCase):
    """S8.3 — Auditoria complementar e regressões de casts, unboxing e wildcards da S8.2."""

    def test_01_unboxing_followed_by_narrowing_cast_requires_primitive_step(self):
        # JLS §5.5: unboxing (Double -> double) não pode ser seguido de narrowing primitivo em um único cast
        bad = """
        class R {
            void f() {
                Double d = 10.5;
                int valor = (int) d;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

        # Em dois passos explícitos (unboxing para double + narrowing para int) é válido
        ok = """
        class R {
            void f() {
                Double d = 10.5;
                int valor = (int) (double) d;
            }
        }
        """
        self.assertTrue(analyze_source(ok).success)

    def test_02_unboxing_widening_and_null_unboxing_valid_at_compile_time(self):
        source = """
        class R {
            void f() {
                Integer numero = 10;
                long valor = numero;

                Integer nulo = null;
                int valorNulo = nulo;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_parameterized_cast_distinct_types_rejected(self):
        bad = """
        import java.util.*;
        class R {
            void f() {
                List<String> textos = new ArrayList<String>();
                List<Integer> numeros = (List<Integer>) textos;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_04_wildcard_casts_allowed_when_compatible_and_rejected_when_disjoint(self):
        ok_wildcard = """
        import java.util.*;
        class R {
            void f() {
                List<String> textos = new ArrayList<String>();
                List<?> desconhecida = textos;
                List<String> resultado = (List<String>) desconhecida;
            }
        }
        """
        self.assertTrue(analyze_source(ok_wildcard).success)

        ok_extends = """
        import java.util.*;
        class R {
            List<? extends Number> obterValores() { return null; }
            void f() {
                List<? extends Number> valores = obterValores();
                List<Integer> inteiros = (List<Integer>) valores;
            }
        }
        """
        self.assertTrue(analyze_source(ok_extends).success)

        bad_extends = """
        import java.util.*;
        class R {
            List<? extends Number> obterValores() { return null; }
            void f() {
                List<? extends Number> valores = obterValores();
                List<String> textos = (List<String>) valores;
            }
        }
        """
        self.assertFalse(analyze_source(bad_extends).success)

    def test_05_object_assignment_requires_cast_while_instanceof_stays_compatible(self):
        ok = """
        class R {
            void f() {
                Object objeto = "texto";
                boolean resultado = objeto instanceof Integer;
                String s = (String) objeto;
            }
        }
        """
        self.assertTrue(analyze_source(ok).success)

        bad = """
        class R {
            void f(Object o) {
                String s = o;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_06_preview_primitive_instanceof_still_gated_by_flag(self):
        src = "class R { void f(Object o) { boolean r = o instanceof int; } }"
        self.assertFalse(analyze_source(src, enable_preview_primitive_patterns=False).success)
        self.assertTrue(analyze_source(src, enable_preview_primitive_patterns=True).success)


if __name__ == "__main__":
    unittest.main()

