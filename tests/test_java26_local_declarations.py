"""
Suíte de Testes Automatizados para Etapa S6 — Declarações Locais, Arrays, Annotations, 'var' e '_' (JLS §14.4).
Cobre: declaradores simples e múltiplos, dimensões pré e pós-identificador, final, annotations locais,
todas as regras de validação e rejeição de 'var', e variáveis não nomeadas '_'.
"""

import unittest
from src.main import analyze_source
from src.ast_nodes import (
    LocalVariableDeclaration, VariableDeclarator, LocalVariableType,
    ArrayCreationExpression, ArrayInitializer, Annotation, MarkerAnnotation
)


class TestJava26LocalDeclarationsS6(unittest.TestCase):
    """Testes para LocalVariableDeclarationStatement, LocalVariableType e 'var' (JLS §14.4)."""

    def test_01_declaracao_local_com_e_sem_inicializador(self):
        source = """
        class Demo {
            void m() {
                int idade = 20;
                String nome;
                final double PI = 3.14159;
                nome = "Ana";
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0], LocalVariableDeclaration)
        self.assertEqual(stmts[0].name, "idade")
        self.assertIsNotNone(stmts[0].initializer)
        self.assertIsInstance(stmts[1], LocalVariableDeclaration)
        self.assertEqual(stmts[1].name, "nome")
        self.assertIsNone(stmts[1].initializer)
        self.assertIn("final", stmts[2].modifiers)
        self.assertEqual(stmts[2].name, "PI")

    def test_02_multiplos_declaradores_ordenados_e_na_tabela_de_simbolos(self):
        source = """
        class Demo {
            int somar() {
                int a = 1, b = 2, c = 3;
                return a + b + c;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        decl = res.ast.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(decl, LocalVariableDeclaration)
        self.assertEqual(len(decl.declarators), 3)
        self.assertTrue(all(isinstance(d, VariableDeclarator) for d in decl.declarators))
        self.assertEqual([d.name for d in decl.declarators], ["a", "b", "c"])
        self.assertEqual([d.effective_type for d in decl.declarators], ["int", "int", "int"])

    def test_03_declaracoes_locais_com_arrays_e_dimensoes_mistas(self):
        source = """
        class Demo {
            void arrays() {
                String[] nomes = new String[10];
                int matriz[][], vetor[];
                int[] lista = {1, 2, 3};
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0].initializer, ArrayCreationExpression)
        self.assertEqual(stmts[0].declarators[0].effective_type, "String[]")
        self.assertEqual([d.name for d in stmts[1].declarators], ["matriz", "vetor"])
        self.assertEqual([d.effective_type for d in stmts[1].declarators], ["int[][]", "int[]"])
        self.assertIsInstance(stmts[2].initializer, ArrayInitializer)

    def test_04_annotations_locais_e_final(self):
        source = """
        @interface NotNull {}
        class Pessoa {}
        class Demo {
            void run() {
                final int quantidade = 10;
                @NotNull String nome = "Ana";
                final @NotNull Pessoa pessoa = new Pessoa();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[2].members[0].body.statements
        self.assertEqual(stmts[0].modifiers, ["final"])
        self.assertEqual(len(stmts[1].annotations), 1)
        self.assertIsInstance(stmts[1].annotations[0], (Annotation, MarkerAnnotation))
        self.assertIn("final", stmts[2].modifiers)
        self.assertEqual(len(stmts[2].annotations), 1)

    def test_05_variaveis_var_validas(self):
        source = """
        class Pessoa {}
        class Demo {
            void run() {
                var idade = 20;
                var nome = "Ana";
                final var pessoa = new Pessoa();
                var soma = idade + 5;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[1].members[0].body.statements
        for i in range(4):
            self.assertTrue(stmts[i].is_var)
            self.assertIsInstance(stmts[i].local_type, LocalVariableType)
            self.assertTrue(stmts[i].local_type.is_var)

    def test_06_rejeicao_var_sem_inicializador(self):
        source = """
        class Demo {
            void m() {
                var idade;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("inicializador" in e and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_07_rejeicao_var_com_multiplos_declaradores(self):
        source = """
        class Demo {
            void m() {
                var a = 1, b = 2;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("múltiplos declaradores" in e and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_08_rejeicao_var_com_dimensoes_de_array(self):
        for bad_line in ["var valores[] = new int[10];", "var[] valores = new int[10];"]:
            with self.subTest(bad_line=bad_line):
                source = f"""
                class Demo {{
                    void m() {{
                        {bad_line}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success)

    def test_09_rejeicao_var_com_array_initializer_direto(self):
        source = """
        class Demo {
            void m() {
                var valores = {1, 2, 3};
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("array" in e.lower() and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_10_rejeicao_var_com_null(self):
        source = """
        class Demo {
            void m() {
                var objeto = null;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("null" in e and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_11_rejeicao_var_com_lambda_ou_method_reference(self):
        for expr in ["x -> x + 1", "objeto::executar"]:
            with self.subTest(expr=expr):
                source = f"""
                class Demo {{
                    void m(Object objeto) {{
                        var ref = {expr};
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success)
                self.assertTrue(any("var" in e and ("lambda" in e or "method reference" in e) for e in res.semantic_errors), msg=res.semantic_errors)

    def test_12_rejeicao_var_autorreferencia_no_inicializador(self):
        source = """
        class Demo {
            void m() {
                var x = x + 1;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("Autorreferência" in e and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_13_rejeicao_var_em_campo_retorno_e_parametro(self):
        cases = [
            "class Demo { var campo = 1; }",
            "class Demo { var metodo() { return 1; } }",
            "class Demo { void metodo(var x) {} }",
            "class Demo { Demo(var x) {} }",
            "record R(var x) {}",
        ]
        for source in cases:
            with self.subTest(source=source):
                res = analyze_source(source)
                self.assertFalse(res.success)

    def test_14_variaveis_unnamed_underscore_multiplas_sem_registro(self):
        source = """
        class Demo {
            void executar() {
                int _ = 10;
                int _ = 20;
                var _ = "texto";
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        self.assertIsNone(res.symbol_table.get("_"))

    def test_15_referencia_a_underscore_rejeitada_semanticamente(self):
        source = """
        class Demo {
            int executar() {
                int _ = 10;
                return _;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("'_' " in e or "'_'" in e for e in res.semantic_errors), msg=res.semantic_errors)

    def test_16_rejeicao_modificador_nao_local_em_variavel_local(self):
        for bad_mod in ["public", "private", "static"]:
            with self.subTest(bad_mod=bad_mod):
                source = f"""
                class Demo {{
                    void m() {{
                        {bad_mod} int x = 1;
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success)

    def test_17_reatribuicao_de_variavel_final_local_rejeitada(self):
        source = """
        class Demo {
            void m() {
                final int x = 10;
                x = 20;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("final" in e and e.line == 5 for e in res.semantic_errors), msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

