"""
Suíte de Testes Automatizados para Etapa S6 — Blocos e Escopo Local (JLS §14.2, §14.4.2).
Cobre: blocos vazios, bloco simples, blocos aninhados, intercalação de declarações/comandos,
escopo léxico, sombreamento de campos vs redeclaração local e recuperação de erros sintáticos.
"""

import unittest
from src.main import analyze_source
from src.ast_nodes import (
    Block, LocalVariableDeclaration, ExpressionStatement, Assignment,
    BinaryOp, UnaryOp, ClassDeclaration, MethodDeclaration,
    ConstructorDeclaration, InstanceInitializer, StaticInitializer,
    ReturnStatement, IfStatement
)


class TestJava26BlocksS6(unittest.TestCase):
    """Testes sintáticos e semânticos para Block e BlockStatements (JLS §14.2)."""

    def test_01_bloco_vazio_em_metodo_e_instrucao(self):
        source = """
        class Demo {
            void executar() {
                {}
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        cls = res.ast.type_declarations[0]
        method = cls.members[0]
        self.assertIsInstance(method, MethodDeclaration)
        self.assertIsInstance(method.body, Block)
        self.assertEqual(len(method.body.block_statements), 1)
        inner = method.body.block_statements[0]
        self.assertIsInstance(inner, Block)
        self.assertEqual(inner.block_statements, [])
        self.assertIn("Block", inner.pretty())
        self.assertEqual(inner.to_dict()["node"], "Block")

    def test_02_bloco_com_uma_instrucao(self):
        source = """
        class Demo {
            int x;
            void configurar() {
                x = 42;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        method = res.ast.type_declarations[0].members[1]
        self.assertEqual(len(method.body.statements), 1)
        stmt = method.body.statements[0]
        self.assertIsInstance(stmt, Assignment)
        self.assertEqual(stmt.name, "x")

    def test_03_blocos_aninhados_preservam_ordem_e_hierarquia(self):
        source = """
        class Demo {
            void executar() {
                {
                    int x = 1;
                    {
                        int y = x + 2;
                    }
                }
                {
                    int x = 99;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertEqual(len(stmts), 2)
        first_block, second_block = stmts[0], stmts[1]
        self.assertIsInstance(first_block, Block)
        self.assertIsInstance(second_block, Block)
        self.assertEqual(len(first_block.statements), 2)
        self.assertIsInstance(first_block.statements[0], LocalVariableDeclaration)
        self.assertIsInstance(first_block.statements[1], Block)
        deep_decl = first_block.statements[1].statements[0]
        self.assertIsInstance(deep_decl, LocalVariableDeclaration)
        self.assertEqual(deep_decl.name, "y")
        self.assertIsInstance(deep_decl.initializer, BinaryOp)

    def test_04_declaracoes_intercaladas_com_comandos_e_tipos_locais(self):
        source = """
        class Demo {
            int testar() {
                int a = 1;
                a += 2;
                int b = a;
                class Auxiliar {
                    int valor() { return 5; }
                }
                b++;
                return b;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertEqual(len(stmts), 6)
        self.assertIsInstance(stmts[0], LocalVariableDeclaration)
        self.assertIsInstance(stmts[1], Assignment)
        self.assertIsInstance(stmts[2], LocalVariableDeclaration)
        self.assertIsInstance(stmts[3], ClassDeclaration)
        self.assertTrue(stmts[3].is_local)
        self.assertIsInstance(stmts[4], ExpressionStatement)
        self.assertIsInstance(stmts[4].expression, UnaryOp)
        self.assertIsInstance(stmts[5], ReturnStatement)

    def test_05_blocos_em_inicializadores_e_construtor_flexivel(self):
        source = """
        class Base { Base(int v) {} }
        class Filha extends Base {
            static {
                int s = 1;
            }
            {
                int inst = 2;
            }
            Filha(int x) {
                int prep = x * 2;
                super(prep);
                {
                    prep++;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        filha = res.ast.type_declarations[1]
        self.assertIsInstance(filha.members[0], StaticInitializer)
        self.assertIsInstance(filha.members[1], InstanceInitializer)
        self.assertIsInstance(filha.members[2], ConstructorDeclaration)
        self.assertIsInstance(filha.members[2].body.prologue[0], LocalVariableDeclaration)
        self.assertIsInstance(filha.members[2].body.epilogue[0], Block)

    def test_06_sombreamento_de_campo_por_variavel_local_permitido(self):
        source = """
        class Caixa {
            int valor = 10;
            int ler() {
                int valor = 20;
                return valor;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_07_redeclaracao_em_bloco_interno_do_mesmo_metodo_rejeitada(self):
        source = """
        class Caixa {
            void processar() {
                int x = 1;
                {
                    int x = 2;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertIsNone(res.syntactic_error)
        self.assertTrue(any("declarada novamente" in e and e.line == 6 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_08_variavel_declarada_em_bloco_nao_vaza_para_fora(self):
        source = """
        class Caixa {
            int ler() {
                {
                    int segredo = 7;
                }
                return segredo;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertIsNone(res.syntactic_error)
        self.assertTrue(any("segredo" in e and e.line == 7 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_09_uso_antes_da_declaracao_no_mesmo_bloco_rejeitado(self):
        source = """
        class Caixa {
            void calcular() {
                int y = x + 1;
                int x = 5;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("x" in e and "não foi declarada" in e and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_10_bloco_nao_fechado_erro_sintatico_com_linha(self):
        source = """
        class Quebrada {
            void f() {
                int a = 1;
                {
                    a++;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertIsNotNone(res.syntactic_error)
        self.assertIn("'}'", str(res.syntactic_error))

    def test_11_if_com_bloco_e_bloco_aninhado_ordenados(self):
        source = """
        class Fluxo {
            void m(boolean ok) {
                if (ok) {
                    int a = 1;
                    {
                        a += 2;
                    }
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        if_stmt = res.ast.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(if_stmt, IfStatement)
        self.assertIsInstance(if_stmt.then_branch, Block)
        self.assertEqual(len(if_stmt.then_branch.statements), 2)
        self.assertIsInstance(if_stmt.then_branch.statements[1], Block)


if __name__ == "__main__":
    unittest.main()
