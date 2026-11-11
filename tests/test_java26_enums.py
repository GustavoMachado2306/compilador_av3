"""
Suíte de Testes Automatizados para a Etapa S4 da Gramática Java SE 26:
Declarações de Enums, Constantes, Argumentos, Corpos Específicos, Construtores e Membros.
Referência Normativa: JLS Java SE 26, Capítulos 8 (§8.9) e 19.
"""

import unittest
from src.lexer import Lexer
from src.parser import Parser, SyntacticError
from src.main import analyze_source
from src.ast_nodes import (
    CompilationUnit, ClassDeclaration, InterfaceDeclaration, EnumDeclaration,
    EnumBody, EnumConstantList, EnumBodyDeclarations, EnumConstant,
    EnumConstantBody, ConstructorDeclaration, MethodDeclaration,
    FieldDeclaration, RecordDeclaration, StaticInitializer
)


def parse_code(source: str, mode: str = None) -> CompilationUnit:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse(mode=mode)


class TestJava26EnumsS4(unittest.TestCase):
    """Testes formais da Etapa S4 para Enums (JLS §8.9)."""

    def test_01_enum_simples(self):
        source = "enum Dia { SEG, TER, QUA }"
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        en = res.ast.type_declarations[0]
        self.assertIsInstance(en, EnumDeclaration)
        self.assertIsInstance(en.body, EnumBody)
        self.assertIsInstance(en.body.constant_list, EnumConstantList)
        self.assertEqual([c.name for c in en.constants], ["SEG", "TER", "QUA"])
        self.assertFalse(en.has_trailing_comma)
        self.assertFalse(en.has_semicolon)
        self.assertEqual(res.symbol_table.get_symbol("Dia")["category"], "enum")
        self.assertEqual(res.symbol_table.get_symbol("SEG")["category"], "constante_enum")

    def test_02_enum_vazio_com_ponto_e_virgula(self):
        source = "enum Vazio { ; }"
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        en = res.ast.type_declarations[0]
        self.assertEqual(en.constants, [])
        self.assertTrue(en.has_semicolon)
        self.assertIsInstance(en.body.body_declarations, EnumBodyDeclarations)

    def test_03_enum_com_virgula_final_trailing_comma(self):
        src1 = "enum Cor { VERMELHO, AZUL, }"
        en1 = parse_code(src1).type_declarations[0]
        self.assertEqual([c.name for c in en1.constants], ["VERMELHO", "AZUL"])
        self.assertTrue(en1.has_trailing_comma)
        self.assertFalse(en1.has_semicolon)

        src2 = "enum Cor { VERMELHO, ; }"
        en2 = parse_code(src2).type_declarations[0]
        self.assertEqual([c.name for c in en2.constants], ["VERMELHO"])
        self.assertTrue(en2.has_trailing_comma)
        self.assertTrue(en2.has_semicolon)

    def test_04_enum_publico_com_implements_e_anotacao(self):
        source = """
        @Deprecated
        public enum Status implements Serializavel, Comparavel<Status> {
            ATIVO, INATIVO
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        en = res.ast.type_declarations[0]
        self.assertIn("public", en.modifiers)
        self.assertEqual(en.annotations[0].name, "Deprecated")
        self.assertEqual([t.name for t in en.implements_types], ["Serializavel", "Comparavel"])

    def test_05_constantes_enum_com_argumentos_e_anotacoes(self):
        source = """
        public enum Planeta {
            @Deprecated MERCURIO(3.30e23, 2439),
            TERRA(5.97e24, 6371);

            private final double massa;
            private final int raio;

            Planeta(double massa, int raio) {
                this.massa = massa;
                this.raio = raio;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        en = res.ast.type_declarations[0]
        c_merc, c_terra = en.constants
        self.assertEqual(c_merc.annotations[0].name, "Deprecated")
        self.assertEqual(len(c_merc.arguments), 2)
        self.assertEqual(len(c_terra.arguments), 2)
        self.assertEqual(len(en.members), 3)

    def test_06_corpo_especifico_de_constante_enum(self):
        source = """
        public enum Operacao {
            SOMA("+") {
                @Override
                public int aplicar(int a, int b) {
                    return a + b;
                }
            },
            SUB("-") {
                public int aplicar(int a, int b) {
                    return a - b;
                }
            };

            private final String simbolo;
            private Operacao(String simbolo) {
                this.simbolo = simbolo;
            }
            public abstract int aplicar(int a, int b);
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        en = res.ast.type_declarations[0]
        self.assertIsInstance(en.constants[0].body, EnumConstantBody)
        self.assertIsInstance(en.constants[0].body.members[0], MethodDeclaration)
        self.assertIsInstance(en.constants[1].body, EnumConstantBody)

    def test_07_corpo_de_constante_enum_com_campo_e_metodo_extra(self):
        source = """
        enum Especial {
            UNICO {
                private int contador = 1;
                public int obter() { return contador; }
            };
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        body = res.ast.type_declarations[0].constants[0].body
        self.assertIsInstance(body.members[0], FieldDeclaration)
        self.assertIsInstance(body.members[1], MethodDeclaration)

    def test_08_construtor_enum_com_delegacao_this(self):
        source = """
        enum Tamanho {
            PEQUENO(1), MEDIO;
            private final int codigo;
            private Tamanho() {
                this(0);
            }
            private Tamanho(int codigo) {
                this.codigo = codigo;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_09_membros_diversos_e_inicializador_estatico_no_enum(self):
        source = """
        public enum Codigo {
            OK(200), ERRO(500);
            private final int http;
            static int total = 2;
            static {
                total = 2;
            }
            Codigo(int http) { this.http = http; }
            public static int getTotal() { return total; }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        en = res.ast.type_declarations[0]
        self.assertTrue(any(isinstance(m, StaticInitializer) for m in en.members))

    def test_10_tipos_aninhados_dentro_de_enum(self):
        source = """
        enum Modulo {
            CORE;
            static class Helper { int id = 1; }
            interface Hook { void onRun(); }
            enum Sub { A, B }
            record Info(String nome) {}
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        members = res.ast.type_declarations[0].members
        self.assertIsInstance(members[0], ClassDeclaration)
        self.assertIsInstance(members[1], InterfaceDeclaration)
        self.assertIsInstance(members[2], EnumDeclaration)
        self.assertIsInstance(members[3], RecordDeclaration)

    def test_11_enum_aninhado_e_enum_local(self):
        source = """
        class Externa {
            public enum Interno { X, Y }
            void rodar() {
                enum Local { L1, L2 }
                int x = 1;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_12_uso_constantes_enum_em_metodo_do_proprio_enum(self):
        source = """
        enum Turno {
            MANHA, TARDE, NOITE;
            public boolean ehNoite() {
                return this == NOITE;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_13_serializacao_to_dict_e_pretty_enum(self):
        source = """
        enum Cor {
            AZUL(1) { public int v() { return 1; } };
            Cor(int n) {}
        }
        """
        en = parse_code(source).type_declarations[0]
        d = en.to_dict()
        self.assertEqual(d["node"], "EnumDeclaration")
        self.assertEqual(d["body"]["node"], "EnumBody")
        self.assertEqual(d["body"]["constant_list"]["node"], "EnumConstantList")
        self.assertEqual(d["body"]["constant_list"]["constants"][0]["body"]["node"], "EnumConstantBody")
        self.assertIn("EnumDeclaration", en.pretty())
        self.assertIn("EnumConstantBody", en.pretty())

    def test_14_enum_sem_constantes_com_membros(self):
        source = """
        public enum Utilitario {
            ;
            public static int dobrar(int x) { return x * 2; }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        en = res.ast.type_declarations[0]
        self.assertEqual(en.constants, [])
        self.assertEqual(len(en.members), 1)

    def test_15_erro_sintatico_enum_com_extends(self):
        source = "enum E extends Base { A }"
        with self.assertRaises(SyntacticError) as ctx:
            parse_code(source)
        self.assertIn("extends", (ctx.exception.message + str(ctx.exception)).lower())

    def test_16_erro_sintatico_lista_constantes_malformada_virgula_inicial(self):
        with self.assertRaises(SyntacticError):
            parse_code("enum E { , A }")

    def test_17_erro_sintatico_lista_constantes_virgula_dupla(self):
        with self.assertRaises(SyntacticError):
            parse_code("enum E { A,, B }")

    def test_18_erro_sintatico_ausencia_ponto_e_virgula_antes_de_membro(self):
        source = """
        enum E {
            A, B
            int x = 1;
        }
        """
        with self.assertRaises(SyntacticError):
            parse_code(source)

    def test_19_erro_sintatico_enum_sem_chaves(self):
        with self.assertRaises(SyntacticError):
            parse_code("enum Quebrado")

    def test_20_erro_semantico_modificadores_proibidos_enum(self):
        for mod in ("abstract", "final", "sealed", "non-sealed"):
            res = analyze_source(f"{mod} enum E {{ A }}")
            self.assertFalse(res.success, msg=f"Deveria falhar com {mod}")
            self.assertTrue(any(mod in str(e) for e in res.semantic_errors), msg=res.semantic_errors)

    def test_21_erro_semantico_enum_top_level_private_e_static(self):
        for mod in ("private", "protected", "static"):
            res = analyze_source(f"{mod} enum E {{ A }}")
            self.assertFalse(res.success, msg=f"Deveria falhar: {mod}")

    def test_22_erro_semantico_constante_enum_duplicada(self):
        source = """
        enum Dup {
            A,
            A
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("A" in str(e) and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_23_erro_semantico_construtor_enum_public_ou_protected(self):
        for vis in ("public", "protected"):
            source = f"""
            enum E {{
                A;
                {vis} E() {{}}
            }}
            """
            res = analyze_source(source)
            self.assertFalse(res.success, msg=f"Construtor {vis} deveria falhar")
            self.assertTrue(any(vis in str(e) and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_24_erro_semantico_super_em_construtor_enum(self):
        source = """
        enum E {
            A;
            private E() {
                super();
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("super" in str(e).lower() and e.line == 5 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_25_erro_semantico_construtor_dentro_de_enum_constant_body(self):
        source = """
        enum E {
            A {
                A() {}
            };
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("construtor" in str(e).lower() and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_26_erro_semantico_nome_construtor_diferente_e_reatribuicao_constante(self):
        source = """
        enum E {
            A, B;
            Outro() {}
            void quebrar() {
                A = B;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(len(res.semantic_errors) >= 2, msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

