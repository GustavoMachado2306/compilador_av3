"""
Suíte de Testes Automatizados para a Etapa S2 da Gramática Java SE 26:
Unidades de Compilação (Ordinary, Modular, Compact), Pacotes, Imports e Módulos.
Referência Normativa: JLS Java SE 26, Capítulos 7 e 19.
"""

import unittest
from src.lexer import Lexer
from src.parser import Parser, SyntacticError
from src.main import analyze_source
from src.ast_nodes import (
    CompilationUnit, OrdinaryCompilationUnit, ModularCompilationUnit,
    CompactCompilationUnit, PackageDeclaration, ImportDeclaration,
    SingleTypeImport, TypeImportOnDemand, SingleStaticImport,
    StaticImportOnDemand, SingleModuleImport, ModuleDeclaration,
    RequiresDirective, ExportsDirective, OpensDirective, UsesDirective,
    ProvidesDirective, ClassDeclaration, MethodDeclaration, FieldDeclaration,
    Annotation
)


def parse_code(source: str, mode: str = None) -> CompilationUnit:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse(mode=mode)


class TestJava26CompilationUnitsS2(unittest.TestCase):
    """Testes formais da Etapa S2 cobrindo JLS §7 e §19."""

    # -------------------------------------------------------------------------
    # 1. AS TRÊS FORMAS DE COMPILATION UNIT (ORDINARY, MODULAR, COMPACT)
    # -------------------------------------------------------------------------
    def test_01_unidade_ordinaria_sem_pacote(self):
        source = "public class Pessoa {}"
        unit = parse_code(source)
        self.assertIsInstance(unit, OrdinaryCompilationUnit)
        self.assertTrue(unit.is_ordinary)
        self.assertFalse(unit.is_modular)
        self.assertFalse(unit.is_compact)
        self.assertIsNone(unit.package)
        self.assertEqual(len(unit.type_declarations), 1)

    def test_02_unidade_ordinaria_com_pacote(self):
        source = "package br.com.exemplo; public class Pessoa {}"
        unit = parse_code(source)
        self.assertIsInstance(unit, OrdinaryCompilationUnit)
        self.assertTrue(unit.is_ordinary)
        self.assertIsNotNone(unit.package)
        self.assertEqual(unit.package.name, "br.com.exemplo")

    def test_03_unidade_ordinaria_com_imports(self):
        source = """
        package br.com.exemplo;
        import java.util.List;
        import java.util.Map;
        public class Pessoa {}
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, OrdinaryCompilationUnit)
        self.assertEqual(len(unit.imports), 2)
        self.assertIsInstance(unit.imports[0], SingleTypeImport)
        self.assertEqual(unit.imports[0].name, "java.util.List")
        self.assertIsInstance(unit.imports[1], SingleTypeImport)
        self.assertEqual(unit.imports[1].name, "java.util.Map")

    def test_04_unidade_ordinaria_com_multiplos_tipos(self):
        source = """
        package br.com.exemplo;
        class A {}
        interface B {}
        enum C {}
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, OrdinaryCompilationUnit)
        self.assertEqual(len(unit.type_declarations), 3)

    # -------------------------------------------------------------------------
    # 2. COMPACT COMPILATION UNITS (CLASSES DECLARADAS IMPLICITAMENTE)
    # -------------------------------------------------------------------------
    def test_05_unidade_compacta_com_metodo_main(self):
        source = """
        void main() {
            System.out.println("Olá Java 26!");
        }
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, CompactCompilationUnit)
        self.assertTrue(unit.is_compact)
        self.assertFalse(unit.is_ordinary)
        self.assertIsNotNone(unit.implicit_class)
        self.assertEqual(unit.implicit_class.name, "Unnamed")
        self.assertEqual(len(unit.class_members), 1)
        self.assertIsInstance(unit.class_members[0], MethodDeclaration)
        self.assertEqual(unit.class_members[0].name, "main")

    def test_06_unidade_compacta_com_multiplos_metodos(self):
        source = """
        static void main() {
            executar();
        }

        static int somar(int a, int b) {
            return a + b;
        }

        void executar() {}
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, CompactCompilationUnit)
        self.assertEqual(len(unit.class_members), 3)
        self.assertEqual(unit.class_members[0].name, "main")
        self.assertEqual(unit.class_members[1].name, "somar")
        self.assertEqual(unit.class_members[2].name, "executar")

    def test_07_unidade_compacta_com_campos(self):
        source = """
        int contador = 0;
        static final int LIMITE = 100;

        void main() {
            contador = 10;
        }
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, CompactCompilationUnit)
        self.assertEqual(len(unit.class_members), 3)
        self.assertIsInstance(unit.class_members[0], FieldDeclaration)
        self.assertEqual(unit.class_members[0].name, "contador")
        self.assertIsInstance(unit.class_members[1], FieldDeclaration)
        self.assertEqual(unit.class_members[1].name, "LIMITE")
        self.assertIn("static", unit.class_members[1].modifiers)
        self.assertIn("final", unit.class_members[1].modifiers)

    def test_08_unidade_compacta_com_classes_internas(self):
        source = """
        static class Utilidades {
            int chave = 42;
        }

        void main() {}
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, CompactCompilationUnit)
        self.assertIsInstance(unit.class_members[0], ClassDeclaration)
        self.assertEqual(unit.class_members[0].name, "Utilidades")

    def test_09_unidade_compacta_com_imports(self):
        source = """
        import java.util.List;
        import static java.lang.Math.max;

        void main() {
            int maior = max(10, 20);
        }
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, CompactCompilationUnit)
        self.assertEqual(len(unit.imports), 2)
        self.assertEqual(unit.imports[0].name, "java.util.List")
        self.assertEqual(unit.imports[1].name, "java.lang.Math.max")

    # -------------------------------------------------------------------------
    # 3. MODULAR COMPILATION UNITS E DECLARAÇÃO DE MÓDULOS (JLS §7.7)
    # -------------------------------------------------------------------------
    def test_10_unidade_modular_simples(self):
        source = "module br.com.exemplo {}"
        unit = parse_code(source)
        self.assertIsInstance(unit, ModularCompilationUnit)
        self.assertTrue(unit.is_modular)
        self.assertFalse(unit.is_ordinary)
        self.assertIsNotNone(unit.module_declaration)
        self.assertEqual(unit.module_declaration.name, "br.com.exemplo")
        self.assertFalse(unit.module_declaration.is_open)

    def test_11_unidade_modular_anotada(self):
        source = "@Deprecated module br.com.exemplo {}"
        unit = parse_code(source)
        self.assertIsInstance(unit, ModularCompilationUnit)
        mod = unit.module_declaration
        self.assertEqual(len(mod.annotations), 1)
        self.assertEqual(mod.annotations[0].name, "Deprecated")

    def test_12_modulo_aberto(self):
        source = "open module br.com.exemplo {}"
        unit = parse_code(source)
        self.assertIsInstance(unit, ModularCompilationUnit)
        self.assertTrue(unit.module_declaration.is_open)

    def test_13_nome_qualificado_de_modulo(self):
        source = "module br.com.empresa.sistema.nucleo {}"
        unit = parse_code(source)
        self.assertEqual(unit.module_declaration.name, "br.com.empresa.sistema.nucleo")

    # -------------------------------------------------------------------------
    # 4. PACKAGE MODIFIERS E ANNOTATIONS EM PACOTE (JLS §7.4)
    # -------------------------------------------------------------------------
    def test_14_package_modifier_com_uma_annotation(self):
        source = """
        @Deprecated
        package br.com.exemplo.modelo;

        public class Item {}
        """
        unit = parse_code(source)
        pkg = unit.package
        self.assertIsNotNone(pkg)
        self.assertEqual(pkg.name, "br.com.exemplo.modelo")
        self.assertEqual(len(pkg.modifiers), 1)
        self.assertEqual(pkg.modifiers[0].name, "Deprecated")

    def test_15_package_modifier_com_multiplas_annotations(self):
        source = """
        @AnnotationA
        @AnnotationB(valor = "teste")
        package br.com.exemplo;

        public class Item {}
        """
        unit = parse_code(source)
        pkg = unit.package
        self.assertEqual(len(pkg.modifiers), 2)
        self.assertEqual(pkg.modifiers[0].name, "AnnotationA")
        self.assertEqual(pkg.modifiers[1].name, "AnnotationB")

    # -------------------------------------------------------------------------
    # 5. AS CINCO CATEGORIAS DE IMPORTS (JLS §7.5)
    # -------------------------------------------------------------------------
    def test_16_import_de_classe_individual(self):
        source = "import java.util.List;\nclass A {}"
        unit = parse_code(source)
        imp = unit.imports[0]
        self.assertIsInstance(imp, SingleTypeImport)
        self.assertEqual(imp.name, "java.util.List")
        self.assertFalse(imp.is_static)
        self.assertFalse(imp.is_wildcard)

    def test_17_import_com_wildcard(self):
        source = "import java.util.*;\nclass A {}"
        unit = parse_code(source)
        imp = unit.imports[0]
        self.assertIsInstance(imp, TypeImportOnDemand)
        self.assertEqual(imp.name, "java.util.*")
        self.assertTrue(imp.is_wildcard)
        self.assertFalse(imp.is_static)

    def test_18_import_static_individual(self):
        source = "import static java.lang.Math.PI;\nclass A {}"
        unit = parse_code(source)
        imp = unit.imports[0]
        self.assertIsInstance(imp, SingleStaticImport)
        self.assertEqual(imp.name, "java.lang.Math.PI")
        self.assertTrue(imp.is_static)
        self.assertFalse(imp.is_wildcard)

    def test_19_import_static_wildcard(self):
        source = "import static java.lang.Math.*;\nclass A {}"
        unit = parse_code(source)
        imp = unit.imports[0]
        self.assertIsInstance(imp, StaticImportOnDemand)
        self.assertEqual(imp.name, "java.lang.Math.*")
        self.assertTrue(imp.is_static)
        self.assertTrue(imp.is_wildcard)

    def test_20_single_module_import(self):
        source = "import module java.base;\nclass A {}"
        unit = parse_code(source)
        imp = unit.imports[0]
        self.assertIsInstance(imp, SingleModuleImport)
        self.assertEqual(imp.name, "java.base")
        self.assertTrue(imp.is_module)
        self.assertIn("(module)", imp.pretty())

    def test_21_single_module_import_em_unidade_modular(self):
        source = """
        import module java.sql;
        module com.app {
            requires java.sql;
        }
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, ModularCompilationUnit)
        self.assertEqual(len(unit.imports), 1)
        self.assertIsInstance(unit.imports[0], SingleModuleImport)
        self.assertEqual(unit.imports[0].name, "java.sql")

    def test_22_single_module_import_em_unidade_ordinaria(self):
        source = """
        package com.app;
        import module java.base;
        import module java.desktop;
        public class Janela {}
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, OrdinaryCompilationUnit)
        self.assertEqual(len(unit.imports), 2)
        self.assertEqual(unit.imports[0].name, "java.base")
        self.assertEqual(unit.imports[1].name, "java.desktop")

    # -------------------------------------------------------------------------
    # 6. DIRETIVAS DE MÓDULO (JLS §7.7)
    # -------------------------------------------------------------------------
    def test_23_requires_comum(self):
        source = "module com.app { requires java.sql; }"
        unit = parse_code(source)
        d = unit.module_declaration.directives[0]
        self.assertIsInstance(d, RequiresDirective)
        self.assertEqual(d.module_name, "java.sql")
        self.assertFalse(d.is_transitive)
        self.assertFalse(d.is_static)

    def test_24_requires_transitive(self):
        source = "module com.app { requires transitive java.logging; }"
        unit = parse_code(source)
        d = unit.module_declaration.directives[0]
        self.assertIsInstance(d, RequiresDirective)
        self.assertEqual(d.module_name, "java.logging")
        self.assertTrue(d.is_transitive)
        self.assertFalse(d.is_static)
        self.assertIn("transitive", d.pretty())

    def test_25_requires_static(self):
        source = "module com.app { requires static java.compiler; }"
        unit = parse_code(source)
        d = unit.module_declaration.directives[0]
        self.assertIsInstance(d, RequiresDirective)
        self.assertEqual(d.module_name, "java.compiler")
        self.assertFalse(d.is_transitive)
        self.assertTrue(d.is_static)
        self.assertIn("static", d.pretty())

    def test_26_requires_com_os_dois_modificadores(self):
        source = """
        module com.app {
            requires static transitive java.xml;
            requires transitive static java.desktop;
        }
        """
        unit = parse_code(source)
        d1 = unit.module_declaration.directives[0]
        d2 = unit.module_declaration.directives[1]
        self.assertTrue(d1.is_static and d1.is_transitive)
        self.assertTrue(d2.is_static and d2.is_transitive)

    def test_27_exports_comum(self):
        source = "module com.app { exports com.app.api; }"
        unit = parse_code(source)
        d = unit.module_declaration.directives[0]
        self.assertIsInstance(d, ExportsDirective)
        self.assertEqual(d.package_name, "com.app.api")
        self.assertEqual(len(d.to_modules), 0)

    def test_28_exports_com_varios_modulos_de_destino(self):
        source = "module com.app { exports com.app.api to moduloA, moduloB, moduloC; }"
        unit = parse_code(source)
        d = unit.module_declaration.directives[0]
        self.assertIsInstance(d, ExportsDirective)
        self.assertEqual(d.package_name, "com.app.api")
        self.assertEqual(d.to_modules, ["moduloA", "moduloB", "moduloC"])
        self.assertIn("to moduloA, moduloB, moduloC", d.pretty())

    def test_29_opens_comum(self):
        source = "module com.app { opens com.app.interno; }"
        unit = parse_code(source)
        d = unit.module_declaration.directives[0]
        self.assertIsInstance(d, OpensDirective)
        self.assertEqual(d.package_name, "com.app.interno")
        self.assertEqual(len(d.to_modules), 0)

    def test_30_opens_com_destinos(self):
        source = "module com.app { opens com.app.interno to moduloA, moduloB; }"
        unit = parse_code(source)
        d = unit.module_declaration.directives[0]
        self.assertIsInstance(d, OpensDirective)
        self.assertEqual(d.package_name, "com.app.interno")
        self.assertEqual(d.to_modules, ["moduloA", "moduloB"])

    def test_31_uses(self):
        source = "module com.app { uses com.app.api.Servico; }"
        unit = parse_code(source)
        d = unit.module_declaration.directives[0]
        self.assertIsInstance(d, UsesDirective)
        self.assertEqual(d.service_type.name, "com.app.api.Servico")

    def test_32_provides_com_um_tipo(self):
        source = "module com.app { provides com.app.api.Servico with com.app.impl.ServicoPadrao; }"
        unit = parse_code(source)
        d = unit.module_declaration.directives[0]
        self.assertIsInstance(d, ProvidesDirective)
        self.assertEqual(d.service_type.name, "com.app.api.Servico")
        self.assertEqual(len(d.with_types), 1)
        self.assertEqual(d.with_types[0].name, "com.app.impl.ServicoPadrao")

    def test_33_provides_com_multiplas_implementacoes(self):
        source = """
        module com.app {
            provides com.app.api.Servico with com.app.impl.ServicoA, com.app.impl.ServicoB;
        }
        """
        unit = parse_code(source)
        d = unit.module_declaration.directives[0]
        self.assertIsInstance(d, ProvidesDirective)
        self.assertEqual(len(d.with_types), 2)
        self.assertEqual(d.with_types[0].name, "com.app.impl.ServicoA")
        self.assertEqual(d.with_types[1].name, "com.app.impl.ServicoB")

    # -------------------------------------------------------------------------
    # 7. INTERAÇÕES DE IMPORTS E FORMAS DE COMPILAÇÃO
    # -------------------------------------------------------------------------
    def test_34_imports_antes_de_modular_compilation_unit(self):
        source = """
        import java.util.List;
        import module java.base;
        module com.app {
            requires java.base;
        }
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, ModularCompilationUnit)
        self.assertEqual(len(unit.imports), 2)
        self.assertIsNotNone(unit.module_declaration)

    def test_35_imports_em_diferentes_formas_de_compilacao(self):
        # 1. Ordinary
        u1 = parse_code("package a; import java.util.*; class X {}")
        self.assertIsInstance(u1, OrdinaryCompilationUnit)
        # 2. Compact
        u2 = parse_code("import java.util.*; void main() {}")
        self.assertIsInstance(u2, CompactCompilationUnit)
        # 3. Modular
        u3 = parse_code("import java.util.*; module X {}")
        self.assertIsInstance(u3, ModularCompilationUnit)

    def test_36_identificadores_contextuais(self):
        # Palavras contextuais de módulo usadas como identificadores comuns em classes
        source = """
        public class Contextuais {
            int module = 1;
            int open = 2;
            int requires = 3;
            int transitive = 4;
            int exports = 5;
            int opens = 6;
            int to = 7;
            int uses = 8;
            int provides = 9;
            int with = 10;

            void module() {}
            void open() {}
        }
        """
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        self.assertEqual(len(cls.members), 12)
        self.assertEqual(cls.members[0].name, "module")
        self.assertEqual(cls.members[1].name, "open")

    def test_37_unidade_de_compilacao_vazia_valida(self):
        unit = parse_code("")
        self.assertIsInstance(unit, OrdinaryCompilationUnit)
        self.assertEqual(unit.pretty(), "Program")

    # -------------------------------------------------------------------------
    # 8. TESTES NEGATIVOS: REJEIÇÃO ESTRUTURADA DE ERROS SINTÁTICOS
    # -------------------------------------------------------------------------
    def test_38_pacote_malformado(self):
        with self.assertRaises(SyntacticError) as cm:
            parse_code("package ;")
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))
        self.assertIn("identificador após 'package'", str(cm.exception))

        with self.assertRaises(SyntacticError) as cm2:
            parse_code("package br..com.exemplo;")
        self.assertIn("[ERRO SINTÁTICO]", str(cm2.exception))
        self.assertIn("identificador após '.'", str(cm2.exception))

    def test_39_import_sem_nome(self):
        with self.assertRaises(SyntacticError) as cm:
            parse_code("import ;")
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))
        self.assertIn("identificador após 'import'", str(cm.exception))

    def test_40_import_sem_ponto_e_virgula(self):
        with self.assertRaises(SyntacticError) as cm:
            parse_code("import java.util.List\nclass A {}")
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))
        self.assertIn("Era esperado ';'", str(cm.exception))

    def test_41_import_module_sem_nome_de_modulo(self):
        with self.assertRaises(SyntacticError) as cm:
            parse_code("import module ;")
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))
        self.assertIn("nome do módulo após 'import module'", str(cm.exception))

    def test_42_diretiva_requires_incompleta(self):
        with self.assertRaises(SyntacticError) as cm:
            parse_code("module com.app { requires ; }")
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))
        self.assertIn("nome do módulo após 'requires'", str(cm.exception))

    def test_43_diretiva_exports_incompleta(self):
        with self.assertRaises(SyntacticError) as cm:
            parse_code("module com.app { exports ; }")
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))
        self.assertIn("nome do pacote após 'exports'", str(cm.exception))

    def test_44_diretiva_opens_incompleta(self):
        with self.assertRaises(SyntacticError) as cm:
            parse_code("module com.app { opens ; }")
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))
        self.assertIn("nome do pacote após 'opens'", str(cm.exception))

    def test_45_diretiva_uses_incompleta(self):
        with self.assertRaises(SyntacticError) as cm:
            parse_code("module com.app { uses ; }")
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))
        self.assertIn("nome do tipo de serviço após 'uses'", str(cm.exception))

    def test_46_diretiva_provides_incompleta(self):
        with self.assertRaises(SyntacticError) as cm:
            parse_code("module com.app { provides Servico ; }")
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))
        self.assertIn("Era esperado 'with'", str(cm.exception))

    def test_47_modulo_sem_abertura_ou_fechamento_de_chaves(self):
        with self.assertRaises(SyntacticError) as cm:
            parse_code("module com.app")
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))
        self.assertIn("Era esperado '{'", str(cm.exception))

        with self.assertRaises(SyntacticError) as cm2:
            parse_code("module com.app { requires java.base;")
        self.assertIn("[ERRO SINTÁTICO]", str(cm2.exception))
        self.assertIn("Era esperado '}'", str(cm2.exception))

    def test_48_unidade_modular_com_tokens_indevidos_depois_do_modulo(self):
        source = "module com.app {} class InvalidoDepoisDoModulo {}"
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source)
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))
        self.assertIn("Tokens indevidos após a declaração do módulo", str(cm.exception))

    # -------------------------------------------------------------------------
    # 9. INTEGRAÇÃO COM S1 E PIPELINE UNIFICADO
    # -------------------------------------------------------------------------
    def test_49_integracao_com_ast_da_s1(self):
        source = """
        import module java.base;
        import java.util.List;

        static <T extends Comparable<T>> T maior(T a, T b) {
            return a;
        }

        void main() {
            List<String> nomes;
        }
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, CompactCompilationUnit)
        metodo = unit.class_members[0]
        self.assertEqual(len(metodo.type_parameters), 1)
        self.assertEqual(metodo.type_parameters[0].name, "T")
        self.assertEqual(metodo.type_parameters[0].bounds[0].name, "Comparable")

    def test_50_integracao_com_analyze_source(self):
        # 1. Unidade Ordinária
        res_ord = analyze_source("package a.b; public class A { int x = 10; }")
        self.assertTrue(res_ord.success)
        self.assertIsInstance(res_ord.ast, OrdinaryCompilationUnit)

        # 2. Unidade Compacta
        res_comp = analyze_source("void main() { int y = 20; }")
        self.assertTrue(res_comp.success)
        self.assertIsInstance(res_comp.ast, CompactCompilationUnit)

        # 3. Unidade Modular
        res_mod = analyze_source("module com.app { requires java.base; }")
        self.assertTrue(res_mod.success)
        self.assertIsInstance(res_mod.ast, ModularCompilationUnit)


if __name__ == "__main__":
    unittest.main()

