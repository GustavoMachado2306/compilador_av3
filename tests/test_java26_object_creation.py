import unittest
from src.main import analyze_source
from src.compiler.ast_nodes import ObjectCreationExpression


class TestJava26ObjectCreationS8(unittest.TestCase):
    """Valida criação de objetos, construtores, diamond <>, outer.new e classes anônimas (JLS §15.9)."""

    def test_01_constructor_overload_and_default_constructor(self):
        source = """
        class Simples {}
        class Pessoa {
            String nome;
            int idade;
            Pessoa(String nome) { this.nome = nome; }
            Pessoa(String nome, int idade) { this.nome = nome; this.idade = idade; }
        }
        class Main {
            void run() {
                Simples s = new Simples();
                Pessoa p1 = new Pessoa("Ana");
                Pessoa p2 = new Pessoa("Bob", 30);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_diamond_operator_inference_valid(self):
        source = """
        import java.util.ArrayList;
        import java.util.List;
        class Caixa<T> {
            Caixa(T item) {}
        }
        class Main {
            void run() {
                List<String> lista = new ArrayList<>();
                Caixa<Integer> cx = new Caixa<>(42);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[1].members[0].body.statements
        self.assertIsInstance(stmts[0].initializer, ObjectCreationExpression)
        self.assertTrue(stmts[0].initializer.is_diamond)

    def test_03_qualified_outer_new_inner_valid(self):
        source = """
        class Externa {
            class Interna {
                Interna(int v) {}
            }
        }
        class Main {
            void run() {
                Externa ext = new Externa();
                var in = ext.new Interna(10);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_04_record_canonical_constructor_invocation(self):
        source = """
        record Ponto(int x, int y) {}
        class Main {
            void run() {
                Ponto p = new Ponto(3, 4);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_anonymous_class_implementing_interface_and_abstract_class(self):
        source = """
        interface Acao { void executar(); }
        abstract class Base { abstract int valor(); }
        class Main {
            void run() {
                Acao a = new Acao() {
                    @Override
                    public void executar() {}
                };
                Base b = new Base() {
                    @Override
                    int valor() { return 99; }
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_06_instantiate_abstract_class_or_interface_without_body_rejected(self):
        bad1 = """
        abstract class Abstrata {}
        class Main { void f() { Abstrata a = new Abstrata(); } }
        """
        bad2 = """
        interface Faz {}
        class Main { void f() { Faz fz = new Faz(); } }
        """
        self.assertFalse(analyze_source(bad1).success)
        self.assertFalse(analyze_source(bad2).success)

    def test_07_instantiate_enum_or_final_anonymous_subclass_rejected(self):
        bad_enum = """
        enum Cor { VERMELHO, AZUL }
        class Main { void f() { Cor c = new Cor(); } }
        """
        bad_final_anon = """
        final class Fechada {}
        class Main { void f() { Object o = new Fechada() {}; } }
        """
        self.assertFalse(analyze_source(bad_enum).success)
        self.assertFalse(analyze_source(bad_final_anon).success)

    def test_08_anonymous_class_with_explicit_constructor_rejected(self):
        source = """
        class Base {}
        class Main {
            void run() {
                Base b = new Base() {
                    Anon() {}
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)

    def test_09_wrong_constructor_arguments_rejected(self):
        source = """
        class Par {
            Par(int a, int b) {}
        }
        class Main {
            void run() {
                Par p = new Par(1);
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)

    def test_10_chained_method_after_object_creation_and_generic_list(self):
        source = """
        import java.util.*;
        class Pessoa {
            String nome;
            Pessoa() {}
            Pessoa(String nome, int idade) { this.nome = nome; }
            void inicializar() {}
            String getNome() { return nome; }
        }
        class Main {
            void run() {
                Pessoa p1 = new Pessoa();
                Pessoa p2 = new Pessoa("Gustavo", 25);
                List<String> textos = new ArrayList<String>();
                new Pessoa().inicializar();
                String n = new Pessoa("Ana", 20).getNome();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_11_incompatible_constructor_argument_type_rejected(self):
        bad = """
        class Pessoa {
            Pessoa(String nome, int idade) {}
        }
        class Main {
            void run() {
                Pessoa p = new Pessoa("Gustavo", "vinte");
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)


if __name__ == "__main__":
    unittest.main()

