"""
Suíte de Testes Automatizados para a Etapa S5 da Gramática Java SE 26:
Uso de Annotations (Marker, Single-Element, Normal), ElementValue, ClassLiteral e Alvos de Declaração (JLS §9.7).
Referência Normativa: JLS Java SE 26, Capítulos 7, 8, 9 (§9.7), 14, 15 e 19.
"""

import unittest
from src.lexer import Lexer
from src.parser import Parser, SyntacticError
from src.main import analyze_source
from src.ast_nodes import (
    CompilationUnit, Annotation, MarkerAnnotation, SingleElementAnnotation,
    NormalAnnotation, ElementValue, ElementValuePair, ElementValuePairList,
    ElementValueArrayInitializer, ClassLiteral, ClassDeclaration,
    InterfaceDeclaration, EnumDeclaration, EnumConstant,
    RecordDeclaration, RecordComponent, ConstructorDeclaration,
    CompactConstructorDeclaration, MethodDeclaration, FieldDeclaration,
    PackageDeclaration, ModuleDeclaration, LocalVariableDeclaration,
    CatchClause, TryStatement, EnhancedForStatement
)


def parse_code(source: str, mode: str = None) -> CompilationUnit:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse(mode=mode)


class TestJava26AnnotationsS5(unittest.TestCase):
    """Testes formais da Etapa S5 para todas as formas e usos de Annotations (JLS §9.7)."""

    def test_01_marker_single_element_e_normal_annotations(self):
        source = """
        @interface Marcador {}
        @interface Unica {
            String value();
        }
        @interface Config {
            int timeout() default 10;
            String host() default "localhost";
        }

        @Marcador
        @Unica("producao")
        @Config()
        @Config(timeout = 30, host = "api.local")
        class Servico {
        }
        """
        ast = parse_code(source)
        cls = ast.type_declarations[3]
        self.assertIsInstance(cls, ClassDeclaration)
        self.assertEqual(len(cls.annotations), 4)

        a0, a1, a2, a3 = cls.annotations
        self.assertIsInstance(a0, MarkerAnnotation)
        self.assertIsInstance(a0, Annotation)
        self.assertEqual(a0.name, "Marcador")

        self.assertIsInstance(a1, SingleElementAnnotation)
        self.assertIsInstance(a1, Annotation)
        self.assertEqual(a1.name, "Unica")
        self.assertIsInstance(a1.element_value, ElementValue)
        self.assertIs(a1.value, a1.element_value)

        self.assertIsInstance(a2, NormalAnnotation)
        self.assertTrue(a2.has_parentheses)
        self.assertIsNotNone(a2.element_value_pair_list)
        self.assertEqual(a2.pairs, [])

        self.assertIsInstance(a3, NormalAnnotation)
        self.assertEqual(len(a3.pairs), 2)
        self.assertEqual(a3.pairs[0].name, "timeout")
        self.assertEqual(a3.pairs[1].name, "host")
        self.assertIsInstance(a3.pairs[0], ElementValuePair)
        self.assertIsInstance(a3.pairs[0].value, ElementValue)

    def test_02_nomes_qualificados_de_annotations(self):
        source = """
        @java.lang.Deprecated
        @com.empresa.core.Auditavel(ativo = true)
        class Legado {
            @java.lang.SuppressWarnings("all")
            public void executar() {}
        }
        """
        ast = parse_code(source)
        cls = ast.type_declarations[0]
        self.assertIsInstance(cls.annotations[0], MarkerAnnotation)
        self.assertEqual(cls.annotations[0].name, "java.lang.Deprecated")
        self.assertIsInstance(cls.annotations[1], NormalAnnotation)
        self.assertEqual(cls.annotations[1].name, "com.empresa.core.Auditavel")
        mtd = cls.members[0]
        self.assertIsInstance(mtd.annotations[0], SingleElementAnnotation)
        self.assertEqual(mtd.annotations[0].name, "java.lang.SuppressWarnings")

    def test_03_todas_as_formas_de_element_value_e_class_literals(self):
        source = """
        enum Prioridade { ALTA, MEDIA, BAIXA }
        @interface Tag {
            String value();
        }
        @interface MetaCompleta {
            String texto() default "";
            int calculo() default 0;
            int condicional() default 1;
            Prioridade prioridade() default Prioridade.MEDIA;
            Class<?> classe() default Object.class;
            Class<?> primitivo() default int.class;
            Class<?> vazio() default void.class;
            Class<?> vetor() default String[].class;
            Class<?> matriz() default int[][].class;
            Class<?> qualificada() default java.lang.String[].class;
            Tag aninhada() default @Tag("padrao");
            int[] lista() default { 1 };
        }

        @MetaCompleta(
            texto = "v" + "1",
            calculo = 2 + 3 * 4,
            condicional = true ? 10 : 20,
            prioridade = Prioridade.ALTA,
            classe = String.class,
            primitivo = int.class,
            vazio = void.class,
            vetor = String[].class,
            matriz = int[][].class,
            qualificada = java.lang.String[].class,
            aninhada = @Tag("interna"),
            lista = { 1, 2, 3, }
        )
        class Alvo {
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        alvo = res.ast.type_declarations[3]
        ann = alvo.annotations[0]
        self.assertIsInstance(ann, NormalAnnotation)
        pairs = {p.name: p.value for p in ann.pairs}

        for cname in ("classe", "primitivo", "vazio", "vetor", "matriz", "qualificada"):
            ev = pairs[cname]
            self.assertIsInstance(ev, ElementValue)
            self.assertIsInstance(ev.value, ClassLiteral)

        self.assertTrue(pairs["vazio"].value.is_void)
        self.assertEqual(pairs["vazio"].value.type_name, "void")
        self.assertEqual(pairs["vetor"].value.type_name, "String[]")
        self.assertEqual(pairs["matriz"].value.type_name, "int[][]")

        self.assertTrue(pairs["aninhada"].is_annotation)
        self.assertIsInstance(pairs["aninhada"].value, SingleElementAnnotation)

        self.assertTrue(pairs["lista"].is_array_initializer)
        self.assertIsInstance(pairs["lista"].value, ElementValueArrayInitializer)
        self.assertTrue(pairs["lista"].value.has_trailing_comma)
        self.assertEqual(len(pairs["lista"].value.elements), 3)

    def test_04_annotations_em_package_e_module(self):
        pkg_src = """
        @PkgMeta("dominio")
        @Auditoria(nivel = 2)
        package com.exemplo.dominio;
        """
        ast_pkg = parse_code(pkg_src)
        self.assertIsInstance(ast_pkg.package, PackageDeclaration)
        self.assertEqual(len(ast_pkg.package.annotations), 2)
        self.assertEqual(ast_pkg.package.annotations[0].name, "PkgMeta")

        mod_src = """
        @ModuloInfo(versao = "1.0")
        @Deprecated
        module com.exemplo.app {
            requires java.base;
        }
        """
        ast_mod = parse_code(mod_src)
        self.assertIsInstance(ast_mod.module_declaration, ModuleDeclaration)
        self.assertEqual(len(ast_mod.module_declaration.annotations), 2)
        self.assertIsInstance(ast_mod.module_declaration.annotations[0], NormalAnnotation)
        self.assertIsInstance(ast_mod.module_declaration.annotations[1], MarkerAnnotation)

    def test_05_annotations_em_declaracoes_de_tipos_e_membros(self):
        source = """
        @interface Ann {}
        @interface Named { String value(); }

        @Ann
        public interface IContrato {
            @Ann int CONST = 1;
            @Ann void operar(@Named("p") int param);
        }

        @Ann
        enum Cor {
            @Ann VERMELHO,
            @Named("azul") AZUL {
                @Ann String codigo() { return "#00F"; }
            };
            @Ann
            Cor() {}
        }

        @Ann
        record Usuario(@Named("id") int id, @Ann String nome) {
            @Ann
            public Usuario {
                if (id < 0) id = 0;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        iface = res.ast.type_declarations[2]
        self.assertIsInstance(iface, InterfaceDeclaration)
        self.assertEqual(len(iface.annotations), 1)
        self.assertEqual(len(iface.members[0].annotations), 1)
        self.assertEqual(len(iface.members[1].annotations), 1)
        self.assertEqual(len(iface.members[1].parameters[0].annotations), 1)

        enum_decl = res.ast.type_declarations[3]
        self.assertIsInstance(enum_decl, EnumDeclaration)
        self.assertEqual(len(enum_decl.annotations), 1)
        self.assertEqual(len(enum_decl.constants[0].annotations), 1)
        self.assertEqual(len(enum_decl.constants[1].annotations), 1)

        rec_decl = res.ast.type_declarations[4]
        self.assertIsInstance(rec_decl, RecordDeclaration)
        self.assertEqual(len(rec_decl.annotations), 1)
        self.assertEqual(len(rec_decl.components[0].annotations), 1)
        self.assertEqual(len(rec_decl.components[1].annotations), 1)
        self.assertIsInstance(rec_decl.members[0], CompactConstructorDeclaration)
        self.assertEqual(len(rec_decl.members[0].annotations), 1)

    def test_06_annotations_em_campos_construtores_locais_catch_for_e_try_resources(self):
        source = """
        @interface Inject {}
        @interface Valid { String value(); }

        class Fluxo {
            @Inject
            private final int contador = 0;

            @Inject
            public Fluxo(@Valid("cfg") String cfg) {}

            void processar(int[] itens, AutoCloseable recurso) throws Exception {
                @Valid("local") final int x = 1;
                for (@Valid("loop") int item : itens) {
                    int y = item + x;
                }
                try (@Valid("res") AutoCloseable r = recurso) {
                    r.close();
                } catch (@Valid("err") Exception e) {
                    String msg = "falha";
                }
            }
        }
        """
        ast = parse_code(source)
        cls = ast.type_declarations[2]
        field = cls.members[0]
        ctor = cls.members[1]
        mtd = cls.members[2]
        self.assertIsInstance(field, FieldDeclaration)
        self.assertEqual(field.annotations[0].name, "Inject")
        self.assertIsInstance(ctor, ConstructorDeclaration)
        self.assertEqual(ctor.annotations[0].name, "Inject")
        self.assertEqual(ctor.parameters[0].annotations[0].name, "Valid")

        stmts = mtd.body.statements
        self.assertIsInstance(stmts[0], LocalVariableDeclaration)
        self.assertEqual(stmts[0].annotations[0].name, "Valid")

        self.assertIsInstance(stmts[1], EnhancedForStatement)
        self.assertEqual(stmts[1].variable.annotations[0].name, "Valid")

        self.assertIsInstance(stmts[2], TryStatement)
        self.assertIsInstance(stmts[2].resources[0], LocalVariableDeclaration)
        self.assertEqual(stmts[2].resources[0].annotations[0].name, "Valid")
        self.assertIsInstance(stmts[2].catches[0], CatchClause)
        self.assertEqual(stmts[2].catches[0].parameter.annotations[0].name, "Valid")

    def test_07_to_dict_e_pretty_annotations(self):
        source = """
        @A
        @B("um")
        @C(x = 1, y = { 2, 3 })
        class Exemplo {}
        """
        ast = parse_code(source)
        cls = ast.type_declarations[0]
        d0 = cls.annotations[0].to_dict()
        d1 = cls.annotations[1].to_dict()
        d2 = cls.annotations[2].to_dict()
        self.assertEqual(d0["node"], "MarkerAnnotation")
        self.assertEqual(d1["node"], "SingleElementAnnotation")
        self.assertEqual(d2["node"], "NormalAnnotation")
        self.assertEqual(d2["element_value_pair_list"]["pairs"][0]["node"], "ElementValuePair")
        pretty_str = cls.annotations[2].pretty()
        self.assertEqual(pretty_str, "@C(x = NUM (1), y = {NUM (2), NUM (3)})")

    # --- TESTES NEGATIVOS SINTÁTICOS ---

    def test_08_erro_sintatico_arroba_sem_identificador(self):
        with self.assertRaises(SyntacticError) as ctx:
            parse_code("@ 123 class A {}")
        self.assertEqual(ctx.exception.line, 1)

    def test_09_erro_sintatico_virgula_sobrando_em_normal_annotation(self):
        source = """
        @Config(a = 1, b = 2,)
        class A {}
        """
        with self.assertRaises(SyntacticError) as ctx:
            parse_code(source)
        self.assertEqual(ctx.exception.line, 2)

    def test_10_erro_sintatico_falta_igual_ou_multi_posicional(self):
        casos = [
            "@Config(a 1) class A {}",
            '@Unica("a", "b") class B {}',
            "@Config(a = 1 class C {}",
            "@Lista({,}) class D {}",
        ]
        for src in casos:
            with self.subTest(src=src):
                with self.assertRaises(SyntacticError) as ctx:
                    parse_code(src)
                self.assertEqual(ctx.exception.line, 1)

    def test_11_erro_sintatico_lambda_ou_atribuicao_em_element_value(self):
        casos = [
            "@A(x -> x + 1) class X {}",
            "@A(valor = x -> x) class Y {}",
            "@A(x = y = 1) class Z {}",
        ]
        for src in casos:
            with self.subTest(src=src):
                with self.assertRaises(SyntacticError) as ctx:
                    parse_code(src)
                self.assertEqual(ctx.exception.line, 1)


if __name__ == "__main__":
    unittest.main()
