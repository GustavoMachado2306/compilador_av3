import unittest
from src.main import analyze_source
from src.ast_nodes import MethodCall


class TestJava26MethodInvocationS83(unittest.TestCase):
    """S8.3 — Invocação de métodos: simples, qualificada, estática, this, super, encadeada, void e contexto (JLS §15.12)."""

    def test_01_simple_qualified_this_super_static_and_chained_calls(self):
        source = """
        class Endereco {
            String getCidade() { return "Fortaleza"; }
        }
        class Pessoa {
            Endereco endereco = new Endereco();
            int calcular(int a, int b) { return a + b; }
            void inicializar() {}
            Endereco getEndereco() { return endereco; }
            static Pessoa criar() { return new Pessoa(); }

            void executar(Pessoa objeto) {
                int soma = calcular(10, 20);
                this.inicializar();
                String s = super.toString();
                Pessoa p = Pessoa.criar();
                String cidade = objeto.getEndereco().getCidade();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[1].members[5].body.statements
        self.assertIsInstance(stmts[0].initializer, MethodCall)
        self.assertIsInstance(stmts[4].initializer, MethodCall)
        self.assertEqual(stmts[4].initializer.method_name, "getCidade")

    def test_02_wrong_argument_count_and_incompatible_types_rejected(self):
        bad_arity = """
        class C {
            int somar(int a, int b) { return a + b; }
            void f() { int r = somar(1); }
        }
        """
        bad_type = """
        class C {
            int somar(int a, int b) { return a + b; }
            void f() { int r = somar(1, "dois"); }
        }
        """
        self.assertFalse(analyze_source(bad_arity).success)
        self.assertFalse(analyze_source(bad_type).success)

    def test_03_void_method_used_as_value_rejected(self):
        bad = """
        class C {
            void nada() {}
            void f() {
                int x = nada();
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_04_static_vs_instance_method_context_rules(self):
        bad_direct = """
        class C {
            void inst() {}
            static void f() { inst(); }
        }
        """
        bad_qual = """
        class C {
            void inst() {}
            static void f() { C.inst(); }
        }
        """
        self.assertFalse(analyze_source(bad_direct).success)
        self.assertFalse(analyze_source(bad_qual).success)

    def test_05_nonexistent_method_and_primitive_receiver_rejected(self):
        bad_missing = "class C { void f(C o) { o.inexistente(); } }"
        bad_prim = "class C { void f() { int x = 1; x.toString(); } }"
        self.assertFalse(analyze_source(bad_missing).success)
        self.assertFalse(analyze_source(bad_prim).success)

    def test_06_ambiguous_overload_rejected(self):
        bad = """
        class Amb {
            void m(int a, double b) {}
            void m(double a, int b) {}
            void f() { m(1, 2); }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_07_return_type_compatibility_on_chained_call(self):
        bad = """
        class Endereco { String getCidade() { return "SP"; } }
        class Pessoa {
            Endereco getEndereco() { return new Endereco(); }
            void f(Pessoa p) {
                int x = p.getEndereco().getCidade();
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)


if __name__ == "__main__":
    unittest.main()

