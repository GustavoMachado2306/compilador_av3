"""
Suíte de Testes Automatizados para a Etapa S5 da Gramática Java SE 26:
Declarações de Annotation Interfaces (@interface), Elementos, Valores Padrão e Validações (JLS §9.6).
Referência Normativa: JLS Java SE 26, Capítulos 9 (§9.6) e 19.
"""

import unittest
from src.lexer import Lexer
from src.parser import Parser, SyntacticError
from src.main import analyze_source
from src.ast_nodes import (
    CompilationUnit, ClassDeclaration, InterfaceDeclaration, EnumDeclaration,
    RecordDeclaration, AnnotationInterfaceDeclaration, AnnotationInterfaceBody,
    AnnotationInterfaceMemberDeclaration, AnnotationInterfaceElementDeclaration,
    AnnotationInterfaceElementModifier, AnnotationDefaultValue, DefaultValue,
    InterfaceConstantDeclaration, ElementValue, ElementValueArrayInitializer,
    MarkerAnnotation, SingleElementAnnotation, NormalAnnotation, ClassLiteral,
    TypeReference
)


def parse_code(source: str, mode: str = None) -> CompilationUnit:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse(mode=mode)


class TestJava26AnnotationInterfacesS5(unittest.TestCase):
    """Testes formais da Etapa S5 para declarações @interface (JLS §9.6)."""

    def test_01_annotation_interface_vazia(self):
        source = """
        @interface Marcador {
        }
        """
        res = analyze_source(source)
        self.assertTrue(
            res.success,
            msg=f"lex={res.lexical_error} syn={res.syntactic_error} sem={res.semantic_errors}"
        )
        decl = res.ast.type_declarations[0]
        self.assertIsInstance(decl, AnnotationInterfaceDeclaration)
        self.assertEqual(decl.name, "Marcador")
        self.assertIsInstance(decl.body, AnnotationInterfaceBody)
        self.assertEqual(decl.members, [])
        self.assertEqual(decl.elements, [])
        self.assertEqual(decl.constants, [])

    def test_02_annotation_interface_publica_e_abstrata(self):
        source = """
        public abstract @interface Servico {
            public abstract String nome();
            int prioridade() default 1;
        }
        """
        res = analyze_source(source)
        self.assertTrue(
            res.success,
            msg=f"lex={res.lexical_error} syn={res.syntactic_error} sem={res.semantic_errors}"
        )
        decl = res.ast.type_declarations[0]
        self.assertIsInstance(decl, AnnotationInterfaceDeclaration)
        self.assertIn("public", decl.modifiers)
        self.assertIn("abstract", decl.modifiers)
        self.assertIn("abstract", decl.effective_modifiers)
        self.assertEqual(len(decl.elements), 2)

        el1, el2 = decl.elements
        self.assertIsInstance(el1, AnnotationInterfaceElementDeclaration)
        self.assertIsInstance(el1, AnnotationInterfaceMemberDeclaration)
        self.assertEqual(el1.name, "nome")
        self.assertFalse(el1.has_default)
        self.assertTrue(el1.is_required)
        self.assertIn("public", el1.effective_modifiers)
        self.assertIn("abstract", el1.effective_modifiers)
        self.assertEqual(len(el1.element_modifiers), 2)
        self.assertIsInstance(el1.element_modifiers[0], AnnotationInterfaceElementModifier)

        self.assertEqual(el2.name, "prioridade")
        self.assertTrue(el2.has_default)
        self.assertFalse(el2.is_required)
        self.assertIsInstance(el2.default_value, AnnotationDefaultValue)
        self.assertIs(AnnotationDefaultValue, DefaultValue)

    def test_03_elementos_todos_os_tipos_permitidos(self):
        source = """
        enum Nivel { BAIXO, MEDIO, ALTO }
        @interface MetaTag {
            String value() default "ok";
        }
        public @interface ConfigCompleta {
            int codigo();
            long timestamp() default 100L;
            double taxa() default 1.5;
            boolean ativo() default true;
            char letra() default 'A';
            String titulo();
            Class<?> alvo() default Object.class;
            Class<? extends Number> numerico() default Integer.class;
            Nivel nivel() default Nivel.MEDIO;
            MetaTag tag() default @MetaTag("v1");
            String[] tags() default { "a", "b", };
            int[] numeros() default { 1, 2, 3 };
            Class<?>[] classes() default { String.class, int.class };
            Nivel[] niveis() default { Nivel.BAIXO, Nivel.ALTO };
            MetaTag[] metaTags() default { @MetaTag("x"), @MetaTag("y"), };
        }
        """
        res = analyze_source(source)
        self.assertTrue(
            res.success,
            msg=f"lex={res.lexical_error} syn={res.syntactic_error} sem={res.semantic_errors}"
        )
        cfg = res.ast.type_declarations[2]
        self.assertIsInstance(cfg, AnnotationInterfaceDeclaration)
        self.assertEqual(len(cfg.elements), 15)

        tags_el = next(e for e in cfg.elements if e.name == "tags")
        self.assertEqual(tags_el.effective_return_type, "String[]")
        self.assertIsInstance(tags_el.default_value.value, ElementValue)
        self.assertTrue(tags_el.default_value.value.is_array_initializer)
        self.assertIsInstance(tags_el.default_value.value.value, ElementValueArrayInitializer)
        self.assertTrue(tags_el.default_value.value.value.has_trailing_comma)

        alvo_el = next(e for e in cfg.elements if e.name == "alvo")
        self.assertIsInstance(alvo_el.default_value.value.value, ClassLiteral)
        self.assertEqual(alvo_el.default_value.value.value.type_name, "Object")

        classes_el = next(e for e in cfg.elements if e.name == "classes")
        self.assertIsInstance(classes_el.default_value.value.value, ElementValueArrayInitializer)
        self.assertEqual(len(classes_el.default_value.value.value.elements), 2)

    def test_04_constantes_em_annotation_interface(self):
        source = """
        public @interface Limites {
            int MIN = 0;
            public static final String PREFIXO = "app_", SUFIXO = "_v1";
            int valor() default MIN;
        }
        """
        res = analyze_source(source)
        self.assertTrue(
            res.success,
            msg=f"lex={res.lexical_error} syn={res.syntactic_error} sem={res.semantic_errors}"
        )
        decl = res.ast.type_declarations[0]
        self.assertEqual(len(decl.constants), 2)
        self.assertEqual(len(decl.elements), 1)
        for c in decl.constants:
            self.assertIsInstance(c, InterfaceConstantDeclaration)
            self.assertIsInstance(c, AnnotationInterfaceMemberDeclaration)

    def test_05_dimensao_array_pos_parenteses(self):
        source = """
        @interface ComDimensaoPos {
            String lista() [] default { "um", "dois" };
        }
        """
        res = analyze_source(source)
        self.assertTrue(
            res.success,
            msg=f"lex={res.lexical_error} syn={res.syntactic_error} sem={res.semantic_errors}"
        )
        decl = res.ast.type_declarations[0]
        el = decl.elements[0]
        self.assertEqual(el.dims, 1)
        self.assertEqual(el.effective_return_type, "String[]")
        self.assertTrue(el.has_default)

    def test_06_tipos_aninhados_dentro_de_annotation_e_vice_versa(self):
        source = """
        @interface Externa {
            enum Modo { RAPIDO, SEGURO }
            class Helper {
                static final int BASE = 10;
            }
            interface SubContrato {
                void executar();
            }
            @interface SubAnotacao {
                String chave() default "default";
            }
            Modo modo() default Modo.RAPIDO;
            SubAnotacao detalhe() default @SubAnotacao(chave = "init");
        }

        class Hospedeira {
            @interface InternaClasse {
                int id();
            }
        }

        interface Contrato {
            @interface InternaInterface {
                boolean obrigatorio() default false;
            }
        }

        enum Categoria {
            A;
            @interface InternaEnum {
                String desc();
            }
        }

        record Ponto(int x, int y) {
            @interface InternaRecord {
                double peso() default 1.0;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(
            res.success,
            msg=f"lex={res.lexical_error} syn={res.syntactic_error} sem={res.semantic_errors}"
        )
        externa = res.ast.type_declarations[0]
        self.assertIsInstance(externa, AnnotationInterfaceDeclaration)
        nomes_aninhados = [
            getattr(m, "name", None)
            for m in externa.members
            if not isinstance(m, (AnnotationInterfaceElementDeclaration, InterfaceConstantDeclaration))
        ]
        self.assertEqual(nomes_aninhados, ["Modo", "Helper", "SubContrato", "SubAnotacao"])

    def test_07_to_dict_e_pretty_annotation_interface(self):
        source = """
        @interface Info {
            String autor() default "anon";
            int VERSAO = 2;
        }
        """
        ast = parse_code(source)
        decl = ast.type_declarations[0]
        d = decl.to_dict()
        self.assertEqual(d["node"], "AnnotationInterfaceDeclaration")
        self.assertEqual(d["name"], "Info")
        self.assertIsInstance(d["body"], dict)
        self.assertEqual(d["body"]["members"][0]["default_value"]["node"], "AnnotationDefaultValue")
        p = decl.pretty()
        self.assertIn("AnnotationInterfaceDeclaration", p)
        self.assertIn("AnnotationInterfaceElementDeclaration", p)
        self.assertIn("default STRING (anon)", p)

    # --- TESTES NEGATIVOS SINTÁTICOS ---

    def test_08_erro_sintatico_annotation_interface_sem_nome(self):
        with self.assertRaises(SyntacticError) as ctx:
            parse_code("@interface { int x(); }")
        err = ctx.exception
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)
        self.assertIn("annotation interface", err.message.lower())

    def test_09_erro_sintatico_annotation_interface_com_clausulas_proibidas(self):
        casos = [
            ("@interface A extends B {}", "extends"),
            ("@interface A<T> {}", "parâmetros de tipo"),
            ("@interface A permits B {}", "permits"),
            ("@interface A implements B {}", "annotation interface"),
        ]
        for src, trecho in casos:
            with self.subTest(src=src):
                with self.assertRaises(SyntacticError) as ctx:
                    parse_code(src)
                self.assertEqual(ctx.exception.line, 1)
                self.assertIn(trecho, ctx.exception.message.lower())

    def test_10_erro_sintatico_elemento_com_parametros_throws_ou_corpo(self):
        casos = [
            ("@interface A { int x(int y); }", "parâmetros"),
            ("@interface A { int x() throws Exception; }", "throws"),
            ("@interface A { int x() { return 1; } }", "corpo"),
        ]
        for src, keyword in casos:
            with self.subTest(src=src):
                with self.assertRaises(SyntacticError) as ctx:
                    parse_code(src)
                self.assertIn(keyword, ctx.exception.message.lower())
                self.assertEqual(ctx.exception.line, 1)

    def test_11_erro_sintatico_default_invalido_lambda_ou_atribuicao(self):
        casos = [
            "@interface A { String x() default a = \"1\"; }",
            "@interface A { String x() default s -> s; }",
            "@interface A { int x() default ; }",
        ]
        for src in casos:
            with self.subTest(src=src):
                with self.assertRaises(SyntacticError) as ctx:
                    parse_code(src)
                self.assertEqual(ctx.exception.line, 1)

    # --- TESTES NEGATIVOS SEMÂNTICOS ---

    def test_12_erro_semantico_elemento_duplicado_e_nomes_reservados(self):
        src_dup = """
        @interface Dup {
            String valor();
            int valor();
        }
        """
        res = analyze_source(src_dup)
        self.assertFalse(res.success)
        self.assertTrue(
            any("valor" in e.message and e.line == 4 for e in res.semantic_errors),
            msg=res.semantic_errors
        )

        for reservado in ("toString", "hashCode", "equals", "annotationType", "getClass", "clone", "notify"):
            with self.subTest(metodo=reservado):
                src = f"""
                @interface Ruim {{
                    String {reservado}();
                }}
                """
                res_r = analyze_source(src)
                self.assertFalse(res_r.success, msg=f"Deveria rejeitar {reservado}")
                self.assertTrue(
                    any(reservado in e.message and e.line == 3 for e in res_r.semantic_errors),
                    msg=res_r.semantic_errors
                )

    def test_13_erro_semantico_tipos_retorno_invalidos_em_elementos(self):
        casos = [
            ("@interface A {\n    int[][] matriz();\n}", 2),
            ("@interface B {\n    Object obj();\n}", 2),
            ("@interface C {\n    java.util.List<String> lista();\n}", 2),
            ("@interface D {\n    String valor() [] [];\n}", 2),
            ("@interface E {\n    void x();\n}", 2),
        ]
        for src, linha in casos:
            with self.subTest(src=src):
                res = analyze_source(src)
                self.assertFalse(res.success, msg=f"Deveria falhar: {src}")
                self.assertTrue(
                    any(e.line == linha for e in res.semantic_errors),
                    msg=res.semantic_errors
                )

        # Tipo classe comum como elemento de annotation interface deve falhar
        src_cls = """
        class Pessoa {}
        @interface Autor {
            Pessoa pessoa();
        }
        """
        res_cls = analyze_source(src_cls)
        self.assertFalse(res_cls.success)
        self.assertTrue(
            any("Pessoa" in e.message and e.line == 4 for e in res_cls.semantic_errors),
            msg=res_cls.semantic_errors
        )

    def test_14_erro_semantico_ciclo_direto_e_indireto_annotation(self):
        src_direto = """
        @interface Ciclo {
            Ciclo selfRef();
        }
        """
        res_d = analyze_source(src_direto)
        self.assertFalse(res_d.success)
        self.assertTrue(
            any("cíclic" in e.message.lower() or "ciclo" in e.message.lower()
                for e in res_d.semantic_errors),
            msg=res_d.semantic_errors
        )

        src_indireto = """
        @interface A {
            B b();
        }
        @interface B {
            A[] a();
        }
        """
        res_i = analyze_source(src_indireto)
        self.assertFalse(res_i.success)
        self.assertTrue(
            any(("cíclic" in e.message.lower() or "ciclo" in e.message.lower()) for e in res_i.semantic_errors),
            msg=res_i.semantic_errors
        )

    def test_15_erro_semantico_modificadores_proibidos_annotation_e_elementos(self):
        casos_decl = [
            "final @interface A {}",
            "sealed @interface B {}",
            "non-sealed @interface C {}",
            "static @interface D {}",
        ]
        for src in casos_decl:
            with self.subTest(src=src):
                res = analyze_source(src)
                self.assertFalse(res.success, msg=f"Deveria falhar: {src}")

        casos_el = [
            "@interface A { private int x(); }",
            "@interface B { protected int x(); }",
            "@interface C { static int x(); }",
            "@interface D { final int x(); }",
            "@interface E { default int x(); }",
            "@interface F { synchronized int x(); }",
        ]
        for src in casos_el:
            with self.subTest(src=src):
                res = analyze_source(src)
                self.assertFalse(res.success, msg=f"Deveria falhar: {src}")

    def test_16_erro_semantico_annotation_interface_local(self):
        source = """
        class Caixa {
            void metodo() {
                @interface LocalAnot {}
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(
            any("local" in e.message.lower() and e.line == 4 for e in res.semantic_errors),
            msg=res.semantic_errors
        )

    def test_17_erro_semantico_default_value_incompativel_null_ou_aninhado(self):
        casos = [
            ("@interface A {\n    String nome() default 123;\n}", 2),
            ("@interface B {\n    int num() default \"abc\";\n}", 2),
            ("@interface C {\n    String nome() default null;\n}", 2),
            ("@interface D {\n    String[] lista() default { { \"a\" } };\n}", 2),
            ("@interface E {\n    boolean flag() default 1;\n}", 2),
        ]
        for src, linha in casos:
            with self.subTest(src=src):
                res = analyze_source(src)
                self.assertFalse(res.success, msg=f"Deveria falhar: {src}")
                self.assertTrue(
                    any(e.line == linha for e in res.semantic_errors),
                    msg=res.semantic_errors
                )


if __name__ == "__main__":
    unittest.main()
