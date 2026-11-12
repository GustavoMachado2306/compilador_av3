import unittest
from src.main import analyze_source
from src.ast_nodes import MemberAccess


class TestJava26FieldAccessS83(unittest.TestCase):
    """S8.3 — Acesso a campos: simples, qualificado, this, super, estático, encadeado e contexto (JLS §15.11)."""

    def test_01_instance_field_and_chained_access(self):
        source = """
        class Endereco { String cidade; }
        class Pessoa {
            String nome;
            Endereco endereco;
            void f(Pessoa objeto) {
                String a = objeto.nome;
                String b = objeto.endereco.cidade;
                String c = this.nome;
                nome = "Ana";
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[1].members[2].body.statements
        self.assertIsInstance(stmts[0].initializer, MemberAccess)
        self.assertIsInstance(stmts[1].initializer, MemberAccess)
        self.assertEqual(stmts[1].initializer.member_name, "cidade")

    def test_02_static_field_via_class_and_super_field(self):
        source = """
        class Base {
            protected int fator;
        }
        class Sub extends Base {
            static int quantidade = 10;
            void f() {
                int q = Sub.quantidade;
                int s = super.fator;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_03_nonexistent_field_rejected(self):
        bad = """
        class Pessoa {
            String nome;
            void f(Pessoa p) {
                String x = p.sobrenome;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_04_instance_field_from_static_context_rejected(self):
        bad1 = """
        class C {
            int x;
            static void f() { int y = C.x; }
        }
        """
        bad2 = """
        class C {
            int x;
            static void f() { int y = x; }
        }
        """
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_05_field_access_on_primitive_rejected(self):
        bad = """
        class C {
            void f() {
                int x = 10;
                int y = x.valor;
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_06_field_type_mismatch_in_assignment_and_target(self):
        bad1 = """
        class C {
            String nome;
            void f(C c) { int n = c.nome; }
        }
        """
        bad2 = """
        class C {
            int idade;
            void f(C c) { c.idade = "vinte"; }
        }
        """
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_07_this_and_super_in_static_method_rejected(self):
        bad = """
        class Base { int x; }
        class Sub extends Base {
            int y;
            static void f() { int a = this.y; }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_08_final_field_reassignment_rejected_outside_constructor(self):
        bad = """
        class C {
            final int limite = 10;
            void f(C c) { c.limite = 20; }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_09_inherited_field_access_on_subclass_instance(self):
        source = """
        class Base { String tag; }
        class Derivada extends Base {}
        class Main {
            void f(Derivada d) {
                String t = d.tag;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()
