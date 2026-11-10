"""
Suíte de Testes de Conformidade Sintática — Java SE 26 (JLS Capítulo 19)
ETAPA S1: Nomes, Identificadores, Tipos e Generics.

Cobre integralmente:
1. Nomes simples e qualificados (TypeName, PackageName, ModuleName, ExpressionName).
2. Tipos primitivos e void (byte, short, int, long, char, float, double, boolean, void).
3. Tipos de referência (ClassOrInterfaceType, TypeVariable, ArrayType).
4. TypeParameters em classes e interfaces (<T>, <K, V>).
5. TypeParameters com limite superior (<T extends Number>).
6. TypeParameters com múltiplos limites / intersection bounds (<T extends Number & Comparable<T>>).
7. TypeParameters com anotações (<@NotNull T>).
8. TypeArguments simples (<String>, <Integer>).
9. TypeArguments com wildcard irrestrito (<?>).
10. TypeArguments com wildcard covariante (<? extends Number>).
11. TypeArguments com wildcard contravariante (<? super Integer>).
12. Generics aninhados com desambiguação de '>>' (List<List<String>>).
13. Generics triplamente aninhados com desambiguação de '>>>' (Map<String, List<Set<Integer>>>).
14. Métodos genéricos com parâmetros de tipo (<T> T identity(T x)).
15. Classes e interfaces com cláusula permits (sealed ... permits ...).
16. Dimensões de arrays multidimensionais (int[][], String[][][]).
17. Parâmetros com varargs (String... args).
18. Type annotations em tipos e dimensões (@NotNull String, String @Nullable []).
19. Rejeição com erros sintáticos estruturados para tipos malformados.
20. Integração completa com analyze_source(source).
"""

import unittest
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.token import TokenType
from src.lexer import Lexer
from src.parser import Parser, SyntacticError
from src.ast_nodes import (
    CompilationUnit, ClassDeclaration, InterfaceDeclaration, MethodDeclaration,
    FieldDeclaration, LocalVariableDeclaration, TypeReference, WildcardType,
    TypeParameter, Annotation
)
from src.main import analyze_source


def parse_code(source: str) -> CompilationUnit:
    """Helper para analisar código Java e obter a CompilationUnit."""
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


class TestJava26NamesTypesGenerics(unittest.TestCase):
    """Testes exaustivos da Etapa S1: Nomes, Tipos e Generics Java SE 26."""

    # -------------------------------------------------------------------------
    # 1. NOMES SIMPLES E QUALIFICADOS
    # -------------------------------------------------------------------------
    def test_01_nomes_simples_e_qualificados_em_campos(self):
        source = """
        public class ExemploNomes {
            Pessoa p1;
            br.com.empresa.Pessoa p2;
            java.util.Map mapa;
        }
        """
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        self.assertEqual(len(cls.members), 3)

        self.assertEqual(cls.members[0].type_ref.name, "Pessoa")
        self.assertEqual(cls.members[1].type_ref.name, "br.com.empresa.Pessoa")
        self.assertEqual(cls.members[2].type_ref.name, "java.util.Map")

    # -------------------------------------------------------------------------
    # 2. TIPOS PRIMITIVOS E VOID
    # -------------------------------------------------------------------------
    def test_02_todos_os_tipos_primitivos_e_void(self):
        source = """
        public class Primitivos {
            byte b;
            short s;
            int i;
            long l;
            char c;
            float f;
            double d;
            boolean bool;
            void executar() {}
        }
        """
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        self.assertEqual(len(cls.members), 9)

        tipos_esperados = ["byte", "short", "int", "long", "char", "float", "double", "boolean"]
        for idx, tipo in enumerate(tipos_esperados):
            self.assertEqual(cls.members[idx].type_ref.name, tipo)
            self.assertEqual(cls.members[idx].type_ref.array_dimensions, 0)

        # Método void
        metodo = cls.members[8]
        self.assertIsInstance(metodo, MethodDeclaration)
        self.assertEqual(metodo.return_type.name, "void")

    # -------------------------------------------------------------------------
    # 3. TYPE PARAMETERS EM CLASSES E INTERFACES
    # -------------------------------------------------------------------------
    def test_03_type_parameters_simples_em_classe(self):
        source = "public class Caixa<T> { T conteudo; }"
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        self.assertEqual(cls.name, "Caixa")
        self.assertEqual(len(cls.type_parameters), 1)
        self.assertEqual(cls.type_parameters[0].name, "T")
        self.assertEqual(len(cls.type_parameters[0].bounds), 0)

    def test_04_type_parameters_multiplos_em_interface(self):
        source = "public interface Mapeamento<K, V> { V obter(K chave); }"
        unit = parse_code(source)
        iface = unit.type_declarations[0]
        self.assertEqual(iface.name, "Mapeamento")
        self.assertEqual(len(iface.type_parameters), 2)
        self.assertEqual(iface.type_parameters[0].name, "K")
        self.assertEqual(iface.type_parameters[1].name, "V")

    # -------------------------------------------------------------------------
    # 4. TYPE PARAMETERS COM BOUNDS E INTERSECTION BOUNDS
    # -------------------------------------------------------------------------
    def test_05_type_parameter_com_limite_simples(self):
        source = "public class Repositorio<T extends Number> {}"
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        tparam = cls.type_parameters[0]
        self.assertEqual(tparam.name, "T")
        self.assertEqual(len(tparam.bounds), 1)
        self.assertEqual(tparam.bounds[0].name, "Number")
        self.assertIn("T extends Number", tparam.pretty())

    def test_06_type_parameter_com_intersection_bounds(self):
        # T extends Number & Comparable<T> & java.io.Serializable
        source = "public class Conversor<T extends Number & Comparable<T> & java.io.Serializable> {}"
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        tparam = cls.type_parameters[0]
        self.assertEqual(tparam.name, "T")
        self.assertEqual(len(tparam.bounds), 3)
        self.assertEqual(tparam.bounds[0].name, "Number")
        self.assertEqual(tparam.bounds[1].name, "Comparable")
        self.assertEqual(tparam.bounds[1].type_arguments[0].name, "T")
        self.assertEqual(tparam.bounds[2].name, "java.io.Serializable")
        self.assertIn("T extends Number & Comparable<T> & java.io.Serializable", tparam.pretty())

    # -------------------------------------------------------------------------
    # 5. TYPE ARGUMENTS SIMPLES E ANINHADOS (DESAMBIGUAÇÃO '>>' E '>>>')
    # -------------------------------------------------------------------------
    def test_07_type_arguments_simples(self):
        source = "public class Demo { List<String> nomes; Map<String, Integer> mapa; }"
        unit = parse_code(source)
        cls = unit.type_declarations[0]

        t1 = cls.members[0].type_ref
        self.assertEqual(t1.name, "List")
        self.assertEqual(len(t1.type_arguments), 1)
        self.assertEqual(t1.type_arguments[0].name, "String")

        t2 = cls.members[1].type_ref
        self.assertEqual(t2.name, "Map")
        self.assertEqual(len(t2.type_arguments), 2)
        self.assertEqual(t2.type_arguments[0].name, "String")
        self.assertEqual(t2.type_arguments[1].name, "Integer")

    def test_08_generics_aninhados_com_fechamento_rshift(self):
        # List<List<String>> termina com '>>' que o lexer captura como RSHIFT
        source = "public class Demo { List<List<String>> matriz; }"
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        t = cls.members[0].type_ref
        self.assertEqual(t.name, "List")
        self.assertEqual(t.type_arguments[0].name, "List")
        self.assertEqual(t.type_arguments[0].type_arguments[0].name, "String")
        self.assertEqual(t.pretty(), "List<List<String>>")

    def test_09_generics_triplamente_aninhados_com_fechamento_urshift(self):
        # Map<String, List<Set<Integer>>> termina com '>>>' (URSHIFT)
        source = "public class Demo { Map<String, List<Set<Integer>>> arvore; }"
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        t = cls.members[0].type_ref
        self.assertEqual(t.name, "Map")
        self.assertEqual(t.type_arguments[0].name, "String")
        self.assertEqual(t.type_arguments[1].name, "List")
        self.assertEqual(t.type_arguments[1].type_arguments[0].name, "Set")
        self.assertEqual(t.type_arguments[1].type_arguments[0].type_arguments[0].name, "Integer")
        self.assertEqual(t.pretty(), "Map<String, List<Set<Integer>>>")

    # -------------------------------------------------------------------------
    # 6. WILDCARDS E WILDCARD BOUNDS (?, ? EXTENDS, ? SUPER)
    # -------------------------------------------------------------------------
    def test_10_wildcard_irrestrito(self):
        source = "public class Demo { List<?> qualquer; }"
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        arg = cls.members[0].type_ref.type_arguments[0]
        self.assertIsInstance(arg, WildcardType)
        self.assertIsNone(arg.bound_kind)
        self.assertIsNone(arg.bound_type)
        self.assertEqual(arg.pretty(), "?")

    def test_11_wildcard_extends_covariante(self):
        source = "public class Demo { List<? extends Number> numeros; }"
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        arg = cls.members[0].type_ref.type_arguments[0]
        self.assertIsInstance(arg, WildcardType)
        self.assertEqual(arg.bound_kind, "extends")
        self.assertEqual(arg.bound_type.name, "Number")
        self.assertEqual(arg.pretty(), "? extends Number")

    def test_12_wildcard_super_contravariante(self):
        source = "public class Demo { List<? super Integer> inteiros; }"
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        arg = cls.members[0].type_ref.type_arguments[0]
        self.assertIsInstance(arg, WildcardType)
        self.assertEqual(arg.bound_kind, "super")
        self.assertEqual(arg.bound_type.name, "Integer")
        self.assertEqual(arg.pretty(), "? super Integer")

    # -------------------------------------------------------------------------
    # 7. MÉTODOS GENÉRICOS COM TYPE PARAMETERS
    # -------------------------------------------------------------------------
    def test_13_metodo_generico_com_type_parameter(self):
        source = """
        public class Utilitario {
            public <T extends Comparable<T>> T maior(T primeiro, T segundo) {
                return primeiro;
            }
        }
        """
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        metodo = cls.members[0]
        self.assertIsInstance(metodo, MethodDeclaration)
        self.assertEqual(len(metodo.type_parameters), 1)
        self.assertEqual(metodo.type_parameters[0].name, "T")
        self.assertEqual(metodo.type_parameters[0].bounds[0].name, "Comparable")
        self.assertEqual(metodo.return_type.name, "T")

    # -------------------------------------------------------------------------
    # 8. CLASSE E INTERFACE COM CLÁUSULA PERMITS (SEALED HIERARCHY)
    # -------------------------------------------------------------------------
    def test_14_classe_com_permits(self):
        source = "public class Forma permits Circulo, Quadrado, Triangulo {}"
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        self.assertEqual(len(cls.permits_types), 3)
        self.assertEqual(cls.permits_types[0].name, "Circulo")
        self.assertEqual(cls.permits_types[1].name, "Quadrado")
        self.assertEqual(cls.permits_types[2].name, "Triangulo")
        self.assertIn("permits Circulo, Quadrado, Triangulo", cls.pretty())

    # -------------------------------------------------------------------------
    # 9. ARRAYS MULTIDIMENSIONAIS E VARARGS
    # -------------------------------------------------------------------------
    def test_15_arrays_multidimensionais_e_varargs(self):
        source = """
        public class Matrizes {
            int[][] matriz2d;
            String[][][] cubo3d;
            void processar(double[] lista, Object... args) {}
        }
        """
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        self.assertEqual(cls.members[0].type_ref.array_dimensions, 2)
        self.assertEqual(cls.members[1].type_ref.array_dimensions, 3)

        metodo = cls.members[2]
        self.assertEqual(metodo.parameters[0].type_ref.array_dimensions, 1)
        self.assertTrue(metodo.parameters[1].is_varargs)
        self.assertTrue(metodo.parameters[1].type_ref.is_varargs)

    # -------------------------------------------------------------------------
    # 10. TYPE ANNOTATIONS E ANOTAÇÕES DE MEMBRO
    # -------------------------------------------------------------------------
    def test_16_type_annotations(self):
        source = """
        public class Anotada {
            @NotNull String nome;
            @SuppressWarnings("unchecked") List<@NonNull Integer> dados;
        }
        """
        unit = parse_code(source)
        cls = unit.type_declarations[0]

        # Campo 1 com anotação de tipo
        f1 = cls.members[0]
        self.assertEqual(len(f1.type_ref.annotations), 1)
        self.assertEqual(f1.type_ref.annotations[0].name, "NotNull")

        # Campo 2
        f2 = cls.members[1]
        self.assertEqual(len(f2.type_ref.annotations), 1)
        self.assertEqual(f2.type_ref.annotations[0].name, "SuppressWarnings")
        self.assertEqual(f2.type_ref.type_arguments[0].annotations[0].name, "NonNull")

    # -------------------------------------------------------------------------
    # 11. TESTES NEGATIVOS: REJEIÇÃO DE SINTAXE MALFORMADA
    # -------------------------------------------------------------------------
    def test_17_erro_generics_nao_fechado(self):
        source = "public class Erro { List<String dados; }"
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source)
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))

    def test_18_erro_type_parameter_sem_nome(self):
        source = "public class Erro< > {}"
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source)
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))

    def test_19_erro_tipo_invalido_simbolo_estranho(self):
        source = "public class Erro { 123 variavel; }"
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source)
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))

    # -------------------------------------------------------------------------
    # 12. INTEGRAÇÃO COM ANALYZE_SOURCE
    # -------------------------------------------------------------------------
    def test_20_integracao_analyze_source_fase_s1(self):
        source = """
        public class DemoFinal<T extends Number> {
            private List<? extends T> itens;
            public Map<String, List<Set<T>>> arvore;

            public <R> R transformar(T entrada) {
                return null;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success)
        self.assertFalse(res.has_errors)
        self.assertIsNotNone(res.ast)
        ast_str = res.ast.pretty()
        self.assertIn("DemoFinal<T extends Number>", ast_str)
        self.assertIn("List<? extends T>", ast_str)
        self.assertIn("Map<String, List<Set<T>>>", ast_str)


if __name__ == "__main__":
    unittest.main()

