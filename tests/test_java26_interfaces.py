"""
Suíte de Testes Automatizados para a Etapa S4 da Gramática Java SE 26:
Declarações de Interfaces Normais, Constantes, Métodos (abstract, default, static, private) e Tipos Aninhados.
Referência Normativa: JLS Java SE 26, Capítulos 9 e 19.
"""

import unittest
from src.compiler.lexer import Lexer
from src.compiler.parser import Parser, SyntacticError
from src.main import analyze_source
from src.compiler.ast_nodes import (
    CompilationUnit, ClassDeclaration, InterfaceDeclaration, InterfaceBody,
    InterfaceExtends, InterfacePermits, InterfaceConstantDeclaration,
    InterfaceMethodDeclaration, EnumDeclaration, RecordDeclaration,
    ReceiverParameter, EmptyStatement
)


def parse_code(source: str, mode: str = None) -> CompilationUnit:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse(mode=mode)


class TestJava26InterfacesS4(unittest.TestCase):
    """Testes formais da Etapa S4 para Interfaces Normais (JLS §9.1–§9.5)."""

    def test_01_interface_vazia_simples(self):
        source = "interface Vazia {}"
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        iface = res.ast.type_declarations[0]
        self.assertIsInstance(iface, InterfaceDeclaration)
        self.assertEqual(iface.name, "Vazia")
        self.assertIsInstance(iface.body, InterfaceBody)
        self.assertEqual(iface.members, [])
        sym = res.symbol_table.get_symbol("Vazia")
        self.assertIsNotNone(sym)
        self.assertEqual(sym["category"], "interface")

    def test_02_interface_publica_e_anotacoes(self):
        source = """
        @Deprecated
        public abstract strictfp interface Servico {
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        iface = res.ast.type_declarations[0]
        self.assertIsInstance(iface, InterfaceDeclaration)
        self.assertIn("public", iface.modifiers)
        self.assertIn("abstract", iface.modifiers)
        self.assertIn("strictfp", iface.modifiers)
        self.assertEqual(len(iface.annotations), 1)
        self.assertEqual(iface.annotations[0].name, "Deprecated")

    def test_03_interface_generica_com_bounds(self):
        source = """
        public interface Repositorio<T, ID extends Comparable<ID>> {
            T buscar(ID id);
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        iface = res.ast.type_declarations[0]
        self.assertEqual(len(iface.type_parameters), 2)
        self.assertEqual(iface.type_parameters[0].name, "T")
        self.assertEqual(iface.type_parameters[1].name, "ID")
        self.assertEqual(len(iface.type_parameters[1].bounds), 1)

    def test_04_interface_extends_multiplo(self):
        source = """
        public interface Combinada<T> extends Serializavel, Comparavel<T>, Iterable<String> {
            void processar();
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        iface = res.ast.type_declarations[0]
        self.assertIsInstance(iface.extends_clause, InterfaceExtends)
        self.assertEqual(len(iface.extends_types), 3)
        self.assertEqual([t.name for t in iface.extends_types], ["Serializavel", "Comparavel", "Iterable"])

    def test_05_interface_sealed_e_permits(self):
        source = """
        public sealed interface Forma permits Circulo, Retangulo {
            double area();
        }
        public non-sealed interface FormaAberta extends Forma {
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        forma = res.ast.type_declarations[0]
        aberta = res.ast.type_declarations[1]
        self.assertIn("sealed", forma.modifiers)
        self.assertIsInstance(forma.permits_clause, InterfacePermits)
        self.assertEqual([t.name for t in forma.permits_types], ["Circulo", "Retangulo"])
        self.assertIn("non-sealed", aberta.modifiers)

    def test_06_constantes_interface_e_modificadores_implicitos(self):
        source = """
        public interface Config {
            int MAXIMO = 100;
            public static final String PREFIXO = "APP";
            int A = 1, B = 2;
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        iface = res.ast.type_declarations[0]
        self.assertEqual(len(iface.members), 3)
        c1 = iface.members[0]
        c2 = iface.members[1]
        c3 = iface.members[2]
        self.assertIsInstance(c1, InterfaceConstantDeclaration)
        self.assertEqual(c1.implicit_modifiers, ["public", "static", "final"])
        self.assertEqual(c1.effective_modifiers, ["public", "static", "final"])
        self.assertEqual(c1.name, "MAXIMO")
        self.assertIsInstance(c2, InterfaceConstantDeclaration)
        self.assertEqual(c2.effective_modifiers, ["public", "static", "final"])
        self.assertEqual([d.name for d in c3.declarators], ["A", "B"])
        self.assertEqual(res.symbol_table.get_symbol("MAXIMO")["category"], "constante_interface")
        self.assertTrue(res.symbol_table.get_symbol("MAXIMO")["is_static"])

    def test_07_constantes_com_dimensoes_array_mistas(self):
        source = """
        interface Matrizes {
            int[] VETOR = {1, 2}, MATRIZ[] = {{1}};
        }
        """
        unit = parse_code(source)
        const = unit.type_declarations[0].members[0]
        self.assertIsInstance(const, InterfaceConstantDeclaration)
        self.assertEqual([d.name for d in const.declarators], ["VETOR", "MATRIZ"])
        self.assertEqual(const.effective_types, ["int[]", "int[][]"])

    def test_08_metodo_abstrato_sem_corpo_e_com_throws_e_generics(self):
        source = """
        public interface Conversor<I> {
            public abstract <O> O converter(I entrada, String... flags) throws Exception;
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        m = res.ast.type_declarations[0].members[0]
        self.assertIsInstance(m, InterfaceMethodDeclaration)
        self.assertTrue(m.is_abstract)
        self.assertFalse(m.is_default)
        self.assertFalse(m.is_static)
        self.assertFalse(m.is_private)
        self.assertEqual(m.implicit_modifiers, ["public", "abstract"])
        self.assertEqual(len(m.type_parameters), 1)
        self.assertEqual(len(m.throws_types), 1)
        self.assertTrue(m.parameters[1].is_varargs)

    def test_09_metodo_default_com_corpo(self):
        source = """
        public interface Saudavel {
            String nome();
            default String saudar() {
                String prefixo = "Olá, ";
                return prefixo + nome();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        iface = res.ast.type_declarations[0]
        m_def = iface.members[1]
        self.assertIsInstance(m_def, InterfaceMethodDeclaration)
        self.assertTrue(m_def.is_default)
        self.assertFalse(m_def.is_abstract)
        self.assertEqual(m_def.implicit_modifiers, ["public"])
        self.assertIsNotNone(m_def.body)

    def test_10_metodo_static_em_interface(self):
        source = """
        public interface Fabrica {
            static int versao() {
                return 26;
            }
            public static String etiqueta() {
                return "Java SE " + versao();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        for m in res.ast.type_declarations[0].members:
            self.assertIsInstance(m, InterfaceMethodDeclaration)
            self.assertTrue(m.is_static)
            self.assertFalse(m.is_abstract)
            self.assertIsNotNone(m.body)

    def test_11_metodo_private_e_private_static_em_interface(self):
        source = """
        public interface Auditoria {
            private void logInterno(String msg) {
                String txt = "[LOG] " + msg;
            }
            private static int calcularHash(int x) {
                return x * 31;
            }
            default void registrar() {
                logInterno("ok");
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        m_priv, m_priv_stat, m_def = res.ast.type_declarations[0].members
        self.assertTrue(m_priv.is_private)
        self.assertFalse(m_priv.is_static)
        self.assertEqual(m_priv.implicit_modifiers, [])
        self.assertTrue(m_priv_stat.is_private)
        self.assertTrue(m_priv_stat.is_static)
        self.assertTrue(m_def.is_default)

    def test_12_metodo_interface_com_receiver_parameter_e_trailing_dims(self):
        source = """
        interface Grade {
            int[] linha(Grade this, int idx)[];
        }
        """
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertIsInstance(m, InterfaceMethodDeclaration)
        self.assertIsInstance(m.receiver_parameter, ReceiverParameter)
        self.assertEqual(m.dims, 1)
        self.assertEqual(m.effective_return_type, "int[][]")

    def test_13_tipos_aninhados_em_interface(self):
        source = """
        public interface Container {
            class Impl { int x = 1; }
            interface Sub { void m(); }
            enum Estado { ATIVO, INATIVO }
            record Par(String k, int v) {}
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        members = res.ast.type_declarations[0].members
        self.assertIsInstance(members[0], ClassDeclaration)
        self.assertIsInstance(members[1], InterfaceDeclaration)
        self.assertIsInstance(members[2], EnumDeclaration)
        self.assertIsInstance(members[3], RecordDeclaration)

    def test_14_ponto_e_virgula_avulso_em_interface(self):
        source = """
        interface ComVazio {
            ;
            void ok();
            ;
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        members = res.ast.type_declarations[0].members
        self.assertIsInstance(members[0], EmptyStatement)
        self.assertIsInstance(members[1], InterfaceMethodDeclaration)
        self.assertIsInstance(members[2], EmptyStatement)

    def test_15_interface_aninhada_e_local(self):
        source = """
        class Externa {
            private interface Interna {
                int VALOR = 7;
                default int dobro() { return VALOR * 2; }
            }
            void testar() {
                interface Local {
                    String tag();
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_16_serializacao_to_dict_e_pretty_interface(self):
        source = """
        public interface I {
            int X = 10;
            default int get() { return X; }
        }
        """
        unit = parse_code(source)
        iface = unit.type_declarations[0]
        d = iface.to_dict()
        self.assertEqual(d["node"], "InterfaceDeclaration")
        self.assertEqual(d["name"], "I")
        self.assertEqual(d["body"]["node"], "InterfaceBody")
        self.assertIn("InterfaceDeclaration", iface.pretty())
        self.assertIn("InterfaceConstantDeclaration", iface.pretty())
        self.assertIn("InterfaceMethodDeclaration", iface.pretty())

    def test_17_erro_sintatico_interface_com_implements(self):
        source = "interface A implements B {}"
        with self.assertRaises(SyntacticError) as ctx:
            parse_code(source)
        self.assertIn("implements", str(ctx.exception) + ctx.exception.message)

    def test_18_erro_sintatico_construtor_em_interface(self):
        source = """
        interface A {
            A() {}
        }
        """
        with self.assertRaises(SyntacticError) as ctx:
            parse_code(source)
        self.assertIn("construtor", (ctx.exception.message + str(ctx.exception)).lower())

    def test_19_erro_sintatico_inicializador_de_instancia_e_estatico_em_interface(self):
        for src in ("interface A { { int x = 1; } }", "interface B { static { int x = 1; } }"):
            with self.assertRaises(SyntacticError):
                parse_code(src)

    def test_20_erro_sintatico_constante_sem_inicializador(self):
        source = "interface Config { int LIMITE; }"
        with self.assertRaises(SyntacticError) as ctx:
            parse_code(source)
        self.assertEqual(ctx.exception.line, 1)

    def test_21_erro_sintatico_anotacao_solta_sem_membro_em_interface(self):
        source = """
        interface Quebrada {
            @Override
        }
        """
        with self.assertRaises(SyntacticError):
            parse_code(source)

    def test_22_erro_semantico_interface_final(self):
        source = """
        final interface Impossivel {
            void m();
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("final" in str(e).lower() and e.line == 2 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_23_erro_semantico_modificadores_top_level_e_sealed_conflitante(self):
        src1 = "private interface Secreta {}"
        res1 = analyze_source(src1)
        self.assertFalse(res1.success)
        self.assertTrue(any("private" in str(e).lower() for e in res1.semantic_errors))

        src2 = "sealed non-sealed interface Conflito {}"
        res2 = analyze_source(src2)
        self.assertFalse(res2.success)
        self.assertTrue(any("non-sealed" in str(e).lower() for e in res2.semantic_errors))

    def test_24_erro_semantico_combinacao_invalida_modificadores_metodo_interface(self):
        casos = [
            "interface A { default static void m() {} }",
            "interface B { default abstract void m(); }",
            "interface C { static abstract void m(); }",
            "interface D { private abstract void m(); }",
            "interface E { protected void m(); }",
            "interface F { final default void m() {} }",
            "interface G { synchronized default void m() {} }",
        ]
        for src in casos:
            res = analyze_source(src)
            self.assertFalse(res.success, msg=f"Deveria falhar: {src}")

    def test_25_erro_semantico_corpo_incompativel_metodo_interface(self):
        src_abs_com_corpo = """
        interface A {
            abstract void m() {}
        }
        """
        res1 = analyze_source(src_abs_com_corpo)
        self.assertFalse(res1.success)
        self.assertEqual(res1.semantic_errors[0].line, 3)

        for src in (
            "interface B { default void m(); }",
            "interface C { static void m(); }",
            "interface D { private void m(); }",
        ):
            res = analyze_source(src)
            self.assertFalse(res.success, msg=f"Falta corpo deveria falhar: {src}")

    def test_26_erro_semantico_reatribuicao_constante_interface(self):
        source = """
        interface Limites {
            int MAX = 10;
            default void quebrar() {
                MAX = 20;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("MAX" in str(e) and e.line == 5 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_27_erro_semantico_duplicidade_constante_e_interface(self):
        source = """
        interface Dup {
            int A = 1;
            int A = 2;
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("A" in str(e) and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_28_leitura_constante_interface_dentro_de_metodo_default_e_static(self):
        source = """
        interface Calculadora {
            int FATOR = 3;
            default int aplicar(int v) {
                return v * FATOR;
            }
            static int base() {
                return FATOR + 1;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()
