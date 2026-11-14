"""
Suíte de Testes Automatizados para a Etapa S4 da Gramática Java SE 26:
Declarações de Records, Cabeçalhos, Componentes, Varargs, Membros e Identificador Contextual 'record'.
Referência Normativa: JLS Java SE 26, Capítulos 8 (§8.10–§8.10.3) e 19.
"""

import unittest
from src.compiler.lexer import Lexer
from src.compiler.parser import Parser, SyntacticError
from src.main import analyze_source
from src.compiler.ast_nodes import (
    CompilationUnit, ClassDeclaration, InterfaceDeclaration, EnumDeclaration,
    RecordDeclaration, RecordHeader, RecordComponentList, RecordComponent,
    VariableArityRecordComponent, RecordComponentModifier, RecordBody,
    FieldDeclaration, MethodDeclaration, StaticInitializer, InstanceInitializer
)


def parse_code(source: str, mode: str = None) -> CompilationUnit:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse(mode=mode)


class TestJava26RecordsS4(unittest.TestCase):
    """Testes formais da Etapa S4 para Records (JLS §8.10–§8.10.3)."""

    def test_01_record_vazio_simples(self):
        source = "record Vazio() {}"
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertIsInstance(rec, RecordDeclaration)
        self.assertIsInstance(rec.header, RecordHeader)
        self.assertEqual(rec.components, [])
        self.assertIsInstance(rec.body, RecordBody)
        self.assertTrue(rec.has_implicit_canonical_constructor)
        self.assertFalse(rec.has_explicit_canonical_constructor)
        self.assertEqual(res.symbol_table.get_symbol("Vazio")["category"], "record")

    def test_02_record_com_componentes_e_modificador_final(self):
        source = """
        public final record Ponto(int x, int y, String rotulo) {
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertIn("public", rec.modifiers)
        self.assertIn("final", rec.modifiers)
        self.assertEqual([c.name for c in rec.components], ["x", "y", "rotulo"])
        self.assertEqual([c.effective_type for c in rec.components], ["int", "int", "String"])
        self.assertEqual(res.symbol_table.get_symbol("x")["category"], "componente_record")

    def test_03_record_generico_com_bounds(self):
        source = """
        public record Caixa<T extends Number, U>(T valor, U metadado) {
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertEqual([tp.name for tp in rec.type_parameters], ["T", "U"])
        self.assertEqual(len(rec.type_parameters[0].bounds), 1)
        self.assertEqual([c.effective_type for c in rec.components], ["T", "U"])

    def test_04_record_com_implements_multiplo(self):
        source = """
        public record Par(int a, int b) implements Comparavel<Par>, Serializavel {
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertEqual([t.name for t in rec.implements_types], ["Comparavel", "Serializavel"])

    def test_05_anotacoes_em_record_e_componentes(self):
        source = """
        @Deprecated
        public record Usuario(@NotNull String nome, @Min(0) int idade) {
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertEqual(rec.annotations[0].name, "Deprecated")
        c_nome, c_idade = rec.components
        self.assertEqual(c_nome.annotations[0].name, "NotNull")
        self.assertIsInstance(c_nome.modifiers[0], RecordComponentModifier)
        self.assertEqual(c_idade.annotations[0].name, "Min")

    def test_06_componente_varargs_e_anotacao_na_reticencias(self):
        source = """
        public record Mensagem(String titulo, @Tag String @NaoVazio ... linhas) {
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        c_linhas = rec.components[1]
        self.assertIsInstance(c_linhas, VariableArityRecordComponent)
        self.assertTrue(c_linhas.is_varargs)
        self.assertEqual(c_linhas.effective_type, "String[]")
        self.assertEqual(c_linhas.annotations[0].name, "Tag")
        self.assertEqual(c_linhas.ellipsis_annotations[0].name, "NaoVazio")

    def test_07_identificador_contextual_record_em_variaveis_e_metodos(self):
        source = """
        class Legado {
            int record = 10;
            String obter(String record) {
                return record;
            }
            void testar() {
                int local = record + 1;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_08_campos_static_e_inicializador_estatico_em_record(self):
        source = """
        public record Config(String host, int porta) {
            public static final int PADRAO = 8080;
            static int inicializado;
            static {
                inicializado = 1;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertTrue(any(isinstance(m, StaticInitializer) for m in rec.members))
        self.assertTrue(any(isinstance(m, FieldDeclaration) for m in rec.members))

    def test_09_metodos_de_instancia_e_estaticos_usando_componentes(self):
        source = """
        public record Retangulo(double largura, double altura) {
            public double area() {
                return largura * altura;
            }
            public static Retangulo quadrado(double lado) {
                return new Retangulo(lado, lado);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertEqual(len([m for m in rec.members if isinstance(m, MethodDeclaration)]), 2)

    def test_10_tipos_aninhados_dentro_de_record_e_record_aninhado(self):
        source = """
        public record Pai(int id) {
            static class Auxiliar {}
            interface Contrato { void ok(); }
            enum Modo { A, B }
            public record Filho(String sub) {}
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        members = res.ast.type_declarations[0].members
        self.assertIsInstance(members[0], ClassDeclaration)
        self.assertIsInstance(members[1], InterfaceDeclaration)
        self.assertIsInstance(members[2], EnumDeclaration)
        self.assertIsInstance(members[3], RecordDeclaration)

    def test_11_record_local_em_bloco_de_metodo(self):
        source = """
        class Calc {
            int somaPar() {
                record Par(int a, int b) {
                    int total() { return a + b; }
                }
                return 0;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_12_serializacao_to_dict_e_pretty_record(self):
        source = "public record Tag(String nome, int... ids) {}"
        rec = parse_code(source).type_declarations[0]
        d = rec.to_dict()
        self.assertEqual(d["node"], "RecordDeclaration")
        self.assertEqual(d["header"]["node"], "RecordHeader")
        self.assertEqual(d["header"]["component_list"]["components"][1]["node"], "VariableArityRecordComponent")
        self.assertTrue(d["has_implicit_canonical_constructor"])
        self.assertIn("RecordDeclaration", rec.pretty())
        self.assertIn("VariableArityRecordComponent", rec.pretty())

    def test_13_erro_sintatico_record_sem_parenteses(self):
        with self.assertRaises(SyntacticError):
            parse_code("record SemHeader {}")

    def test_14_erro_sintatico_record_com_extends(self):
        source = "record R(int x) extends Object {}"
        with self.assertRaises(SyntacticError) as ctx:
            parse_code(source)
        self.assertIn("extends", (ctx.exception.message + str(ctx.exception)).lower())

    def test_15_erro_sintatico_varargs_nao_ultimo_componente(self):
        source = "record R(String... args, int depois) {}"
        with self.assertRaises(SyntacticError):
            parse_code(source)

    def test_16_erro_sintatico_componente_void_ou_sem_identificador(self):
        for src in ("record R(void x) {}", "record R(int) {}"):
            with self.assertRaises(SyntacticError):
                parse_code(src)

    def test_17_erro_semantico_modificadores_proibidos_em_record(self):
        for mod in ("abstract", "sealed", "non-sealed", "private", "protected", "static"):
            res = analyze_source(f"{mod} record R(int x) {{}}")
            self.assertFalse(res.success, msg=f"Deveria falhar: {mod}")
            self.assertTrue(any(mod in str(e) for e in res.semantic_errors), msg=res.semantic_errors)

    def test_18_erro_semantico_nomes_proibidos_object_e_underscore_em_componentes(self):
        proibidos = ("clone", "finalize", "getClass", "hashCode", "notify", "notifyAll", "toString", "wait", "_")
        for nome in proibidos:
            res = analyze_source(f"record R(int {nome}) {{}}")
            self.assertFalse(res.success, msg=f"Nome de componente '{nome}' deveria falhar")

    def test_19_erro_semantico_componente_duplicado(self):
        source = """
        record Dup(
            int x,
            String x
        ) {}
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("x" in str(e) and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_20_erro_semantico_campo_de_instancia_em_record(self):
        source = """
        record R(int x) {
            private int extra = 5;
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("instância" in str(e).lower() and e.line == 3 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_21_erro_semantico_inicializador_de_instancia_em_record(self):
        source = """
        record R(int x) {
            {
                int y = x;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("inicializadores de instância" in str(e).lower() and e.line == 3 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_22_erro_semantico_metodo_abstract_ou_native_em_record(self):
        for mod in ("abstract", "native"):
            source = f"""
            record R(int x) {{
                {mod} void fazer();
            }}
            """
            res = analyze_source(source)
            self.assertFalse(res.success, msg=f"Deveria falhar método {mod} em record")
            self.assertTrue(any(mod in str(e) and e.line == 3 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_23_erro_semantico_reatribuicao_componente_final_em_metodo(self):
        source = """
        record R(int x) {
            void alterar() {
                x = 10;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("x" in str(e) and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_24_erro_semantico_record_duplicado_no_mesmo_escopo(self):
        source = """
        record A(int x) {}
        record A(int y) {}
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("A" in str(e) and e.line == 3 for e in res.semantic_errors), msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

