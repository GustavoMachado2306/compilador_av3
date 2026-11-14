"""
Suíte de Testes Automatizados para Etapa S6 — Declarações Locais de Tipos (JLS §14.3).
Cobre: class, interface, enum e record locais, is_local=True, herança de LocalClassOrInterfaceDeclaration,
rejeição de @interface local, modificadores proibidos, duplicidade aninhada vs blocos irmãos e conflito com classe envolvente.
"""

import unittest
from src.main import analyze_source
from src.compiler.ast_nodes import (
    LocalClassOrInterfaceDeclaration, ClassDeclaration, InterfaceDeclaration,
    EnumDeclaration, RecordDeclaration, Block
)


class TestJava26LocalTypesS6(unittest.TestCase):
    """Testes para declarações locais de tipos dentro de blocos e métodos (JLS §14.3)."""

    def test_01_classe_local_valida(self):
        source = """
        class Externa {
            void executar() {
                class Auxiliar {
                    int x = 10;
                    int obter() { return x; }
                }
                Auxiliar a = new Auxiliar();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        local_cls = stmts[0]
        self.assertIsInstance(local_cls, ClassDeclaration)
        self.assertIsInstance(local_cls, LocalClassOrInterfaceDeclaration)
        self.assertTrue(local_cls.is_local)
        self.assertEqual(local_cls.name, "Auxiliar")

    def test_02_interface_local_implementada_por_classe_local(self):
        source = """
        class Externa {
            void executar() {
                interface Acao {
                    void realizar();
                }
                class Implementacao implements Acao {
                    public void realizar() {}
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0], InterfaceDeclaration)
        self.assertIsInstance(stmts[0], LocalClassOrInterfaceDeclaration)
        self.assertTrue(stmts[0].is_local)
        self.assertIsInstance(stmts[1], ClassDeclaration)
        self.assertTrue(stmts[1].is_local)

    def test_03_enum_local_valido_implicitamente_static(self):
        source = """
        class Externa {
            void executar() {
                enum Status {
                    ATIVO,
                    INATIVO
                }
                Status atual = Status.ATIVO;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        local_enum = res.ast.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(local_enum, EnumDeclaration)
        self.assertIsInstance(local_enum, LocalClassOrInterfaceDeclaration)
        self.assertTrue(local_enum.is_local)
        self.assertEqual([c.name for c in local_enum.constants], ["ATIVO", "INATIVO"])

    def test_04_record_local_valido_implicitamente_static(self):
        source = """
        class Externa {
            void executar() {
                record Pessoa(String nome, int idade) {}
                Pessoa pessoa = new Pessoa("Ana", 20);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        local_rec = res.ast.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(local_rec, RecordDeclaration)
        self.assertIsInstance(local_rec, LocalClassOrInterfaceDeclaration)
        self.assertTrue(local_rec.is_local)
        self.assertEqual([c.name for c in local_rec.components], ["nome", "idade"])

    def test_05_rejeicao_annotation_interface_local(self):
        source = """
        class Externa {
            void executar() {
                @interface LocalAnn {
                    String value() default "";
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("Annotation interface" in e and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_06_proibicao_modificadores_acesso_static_sealed_em_tipos_locais(self):
        bad_decls = [
            "public class L {}",
            "protected class L {}",
            "private class L {}",
            "static class L {}",
            "sealed class L permits Sub {}",
            "non-sealed class L {}",
            "public interface I {}",
            "static enum E { A }",
            "static record R(int x) {}",
        ]
        for decl in bad_decls:
            with self.subTest(decl=decl):
                source = f"""
                class Externa {{
                    void executar() {{
                        {decl}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success, msg=f"Esperava erro para: {decl}")

    def test_07_modificadores_validos_final_e_abstract_em_classe_local(self):
        source = """
        class Externa {
            void executar() {
                abstract class BaseLocal {}
                final class ConcretaLocal extends BaseLocal {}
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_08_duplicidade_classe_local_no_mesmo_bloco_ou_bloco_interno_rejeitada(self):
        source = """
        class Externa {
            void executar() {
                class Local {}
                {
                    class Local {}
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("Local" in e and "declarada novamente" in e and e.line == 6 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_09_blocos_irmaos_disjuntos_podem_reutilizar_nome_de_tipo_local(self):
        source = """
        class Externa {
            void executar() {
                {
                    class Local { int a = 1; }
                }
                {
                    class Local { int b = 2; }
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[0].members[0].body.statements
        self.assertIsInstance(stmts[0], Block)
        self.assertIsInstance(stmts[1], Block)
        self.assertTrue(stmts[0].statements[0].is_local)
        self.assertTrue(stmts[1].statements[0].is_local)

    def test_10_classe_local_com_mesmo_nome_da_classe_envolvente_rejeitada(self):
        source = """
        class Teste {
            void executar() {
                class Teste {}
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("envolvente" in e and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_11_sombreamento_de_variavel_do_metodo_externo_dentro_de_metodo_de_classe_local(self):
        source = """
        class Externa {
            void executar() {
                int x = 10;
                class Local {
                    int m() {
                        int x = 20;
                        return x;
                    }
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

