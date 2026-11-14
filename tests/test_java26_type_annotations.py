"""
Suíte de Testes Automatizados para a Etapa S5 da Gramática Java SE 26:
Type Annotations (JLS §4.11, §9.7.4), Arrays Multidimensionais Anotados, Generics, Casts, Instanceof, New, Receiver e Separação Pré/Pós-Modificadores.
Referência Normativa: JLS Java SE 26, Capítulos 4, 8, 9, 15 e 19.
"""

import unittest
from src.compiler.lexer import Lexer
from src.compiler.parser import Parser, SyntacticError
from src.main import analyze_source
from src.compiler.ast_nodes import (
    CompilationUnit, ClassDeclaration, InterfaceDeclaration, RecordDeclaration,
    FieldDeclaration, MethodDeclaration, ConstructorDeclaration,
    TypeReference, WildcardType, TypeParameter, ReceiverParameter,
    FormalParameter, VariableArityParameter, VariableDeclaratorId,
    CastExpression, InstanceOfExpression, ObjectCreationExpression,
    ArrayCreationExpression, LocalVariableDeclaration, MarkerAnnotation,
    SingleElementAnnotation, MarkerAnnotation as MA
)


def parse_code(source: str, mode: str = None) -> CompilationUnit:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse(mode=mode)


class TestJava26TypeAnnotationsS5(unittest.TestCase):
    """Testes formais da Etapa S5 para Type Annotations (JLS §4.11 & §9.7.4)."""

    def test_01_type_annotations_antes_do_tipo_em_campos_metodos_e_locais(self):
        source = """
        @interface NotNull {}
        @interface Readonly {}

        class Cliente {
            private @NotNull String nome;

            public @NotNull String getNome(@NotNull String prefixo) {
                @Readonly String local = prefixo;
                return local;
            }
        }
        """
        ast = parse_code(source)
        cls = ast.type_declarations[2]
        field = cls.members[0]
        mtd = cls.members[1]

        self.assertIsInstance(field, FieldDeclaration)
        self.assertEqual([a.name for a in field.type_ref.annotations], ["NotNull"])

        self.assertIsInstance(mtd, MethodDeclaration)
        self.assertEqual([a.name for a in mtd.return_type.annotations], ["NotNull"])
        self.assertEqual([a.name for a in mtd.parameters[0].type_ref.annotations], ["NotNull"])

        local = mtd.body.statements[0]
        self.assertIsInstance(local, LocalVariableDeclaration)
        self.assertEqual([a.name for a in local.type_ref.annotations], ["Readonly"])

    def test_02_separacao_pre_e_pos_modificadores_declaration_vs_type_use(self):
        source = """
        class Base {
            @Override
            public String toString() {
                return "Base";
            }

            public @TypeUse String metodoComTypeUse() {
                return "ok";
            }

            @DeclOnly public @TypeUse int campo = 1;
        }
        """
        ast = parse_code(source)
        cls = ast.type_declarations[0]

        to_str = cls.members[0]
        self.assertEqual([a.name for a in to_str.annotations], ["Override"])
        self.assertEqual(to_str.return_type.annotations, [])

        m_type_use = cls.members[1]
        self.assertIn("TypeUse", [a.name for a in m_type_use.return_type.annotations])

        campo = cls.members[2]
        self.assertIn("DeclOnly", [a.name for a in campo.annotations])
        self.assertIn("TypeUse", [a.name for a in campo.type_ref.annotations])
        self.assertNotIn("DeclOnly", [a.name for a in campo.type_ref.annotations])

    def test_03_generics_e_wildcards_com_type_annotations(self):
        source = """
        import java.util.List;
        import java.util.Map;

        class Repositorio {
            Map<@Key String, List<@Val Integer>> indice;
            List<? extends @Upper Number> superiores;
            List<? super @Lower Integer> inferiores;
            List<@Wild ?> curinga;
        }
        """
        ast = parse_code(source)
        cls = ast.type_declarations[0]
        indice_t = cls.members[0].type_ref
        self.assertEqual(indice_t.name, "Map")
        self.assertEqual([a.name for a in indice_t.type_arguments[0].annotations], ["Key"])
        inner_list = indice_t.type_arguments[1]
        self.assertEqual([a.name for a in inner_list.type_arguments[0].annotations], ["Val"])

        sup_wc = cls.members[1].type_ref.type_arguments[0]
        self.assertIsInstance(sup_wc, WildcardType)
        self.assertEqual([a.name for a in sup_wc.bound_type.annotations], ["Upper"])

        inf_wc = cls.members[2].type_ref.type_arguments[0]
        self.assertIsInstance(inf_wc, WildcardType)
        self.assertEqual([a.name for a in inf_wc.bound_type.annotations], ["Lower"])

        wild_wc = cls.members[3].type_ref.type_arguments[0]
        self.assertIsInstance(wild_wc, WildcardType)
        self.assertEqual([a.name for a in wild_wc.annotations], ["Wild"])

    def test_04_superclasses_interfaces_e_throws_com_type_annotations(self):
        source = """
        class Servico extends @ExtBase Base implements @ImpA ContratoA, @ImpB ContratoB {
            public void executar() throws @ExA MinhaExcecao, @ExB OutraExcecao {}
        }

        interface ContratoFilho extends @SuperI ContratoBase {}

        record Dados(int x) implements @RecInt ContratoA {}
        """
        ast = parse_code(source)
        svc = ast.type_declarations[0]
        self.assertEqual([a.name for a in svc.extends_type.annotations], ["ExtBase"])
        self.assertEqual([a.name for a in svc.implements_types[0].annotations], ["ImpA"])
        self.assertEqual([a.name for a in svc.implements_types[1].annotations], ["ImpB"])

        mtd = svc.members[0]
        self.assertEqual([a.name for a in mtd.throws_types[0].annotations], ["ExA"])
        self.assertEqual([a.name for a in mtd.throws_types[1].annotations], ["ExB"])

        iface = ast.type_declarations[1]
        self.assertEqual([a.name for a in iface.extends_types[0].annotations], ["SuperI"])

        rec = ast.type_declarations[2]
        self.assertEqual([a.name for a in rec.implements_types[0].annotations], ["RecInt"])

    def test_05_dimensoes_array_anotadas_e_pos_identificador_ou_metodo(self):
        source = """
        class Vetores {
            @Elem int @Dim1 [] @Dim2 [] matriz;
            int vetorPosIdent @PosDim1 [] @PosDim2 [];
            String[] posMetodo(int n) @RetDim [] {
                return null;
            }
        }
        """
        ast = parse_code(source)
        cls = ast.type_declarations[0]

        f_matriz = cls.members[0]
        self.assertEqual(f_matriz.type_ref.array_dimensions, 2)
        self.assertEqual([a.name for a in f_matriz.type_ref.annotations], ["Elem"])
        self.assertEqual([a.name for a in f_matriz.type_ref.dims_annotations[0]], ["Dim1"])
        self.assertEqual([a.name for a in f_matriz.type_ref.dims_annotations[1]], ["Dim2"])

        f_pos = cls.members[1]
        v_id = f_pos.declarators[0].id
        self.assertIsInstance(v_id, VariableDeclaratorId)
        self.assertEqual(v_id.dims, 2)
        self.assertEqual([a.name for a in v_id.dims_annotations[0]], ["PosDim1"])
        self.assertEqual([a.name for a in v_id.dims_annotations[1]], ["PosDim2"])

        m_pos = cls.members[2]
        self.assertEqual(m_pos.dims, 1)
        self.assertEqual([a.name for a in m_pos.dims_annotations[0]], ["RetDim"])

    def test_06_tipos_aninhados_qualificados_outer_ann_inner(self):
        source = """
        class UsoAninhado {
            @A Outer.@B Inner campo;
            Outer.@B Middle<@X String>.@C Leaf<@Y Integer> profundo;
        }
        """
        ast = parse_code(source)
        cls = ast.type_declarations[0]
        f0 = cls.members[0].type_ref
        self.assertEqual(f0.name, "Outer.Inner")
        self.assertEqual(len(f0.segment_annotations), 2)
        self.assertEqual([a.name for a in f0.segment_annotations[0]], ["A"])
        self.assertEqual([a.name for a in f0.segment_annotations[1]], ["B"])

        f1 = cls.members[1].type_ref
        self.assertEqual(f1.name, "Outer.Middle.Leaf")
        self.assertEqual(len(f1.segment_annotations), 3)
        self.assertEqual(f1.segment_annotations[0], [])
        self.assertEqual([a.name for a in f1.segment_annotations[1]], ["B"])
        self.assertEqual([a.name for a in f1.segment_annotations[2]], ["C"])

    def test_07_casts_e_instanceof_com_type_annotations(self):
        source = """
        class Conversoes {
            void testar(Object obj, Object arr) {
                String s = (@NonNull String) obj;
                int[][] m = (int @DimA [] @DimB []) arr;
                boolean ok = obj instanceof @NonNull String;
                boolean okArr = arr instanceof String @ArrAnn [];
            }
        }
        """
        ast = parse_code(source)
        stmts = ast.type_declarations[0].members[0].body.statements

        cast_s = stmts[0].initializer
        self.assertIsInstance(cast_s, CastExpression)
        self.assertEqual([a.name for a in cast_s.target_type.annotations], ["NonNull"])

        cast_m = stmts[1].initializer
        self.assertIsInstance(cast_m, CastExpression)
        self.assertEqual([a.name for a in cast_m.target_type.dims_annotations[0]], ["DimA"])
        self.assertEqual([a.name for a in cast_m.target_type.dims_annotations[1]], ["DimB"])

        inst_s = stmts[2].initializer
        self.assertIsInstance(inst_s, InstanceOfExpression)
        self.assertEqual([a.name for a in inst_s.target_type.annotations], ["NonNull"])

        inst_a = stmts[3].initializer
        self.assertIsInstance(inst_a, InstanceOfExpression)
        self.assertEqual([a.name for a in inst_a.target_type.dims_annotations[0]], ["ArrAnn"])

    def test_08_varargs_receiver_parameter_e_type_parameters_anotados(self):
        source = """
        class Caixa<@TP T extends @Bound Number> {
            void imprimir(@Readonly Caixa<T> this, String @VarArgs ... itens) {}
            <@MTP E extends @MBound Comparable<E>> void ordenar(E @MVar ... valores) {}
        }

        record Pacote(String @RecVar ... tags) {}
        """
        ast = parse_code(source)
        cls = ast.type_declarations[0]
        tp = cls.type_parameters[0]
        self.assertIsInstance(tp, TypeParameter)
        self.assertEqual(tp.name, "T")
        self.assertEqual([a.name for a in tp.annotations], ["TP"])
        self.assertEqual([a.name for a in tp.bounds[0].annotations], ["Bound"])

        mtd = cls.members[0]
        self.assertIsInstance(mtd.receiver_parameter, ReceiverParameter)
        self.assertEqual([a.name for a in mtd.receiver_parameter.annotations], ["Readonly"])
        var_param = mtd.parameters[0]
        self.assertIsInstance(var_param, VariableArityParameter)
        self.assertEqual([a.name for a in var_param.ellipsis_annotations], ["VarArgs"])

        mtd2 = cls.members[1]
        self.assertEqual([a.name for a in mtd2.type_parameters[0].annotations], ["MTP"])
        self.assertEqual([a.name for a in mtd2.type_parameters[0].bounds[0].annotations], ["MBound"])

        rec = ast.type_declarations[1]
        self.assertEqual([a.name for a in rec.components[0].ellipsis_annotations], ["RecVar"])

    def test_09_expressoes_new_com_type_annotations(self):
        source = """
        import java.util.ArrayList;
        class Fabrica {
            void criar() {
                Object lista = new @NonNull ArrayList<>();
                Object interno = new @A Outer.@B Inner();
                int[][] grade = new int @Dim1 [5] @Dim2 [];
                String[] nomes = new @Elem String @DimArr [] { "a", "b" };
            }
        }
        """
        ast = parse_code(source)
        stmts = ast.type_declarations[0].members[0].body.statements

        obj1 = stmts[0].initializer
        self.assertIsInstance(obj1, ObjectCreationExpression)
        self.assertEqual([a.name for a in obj1.type_ref.annotations], ["NonNull"])

        obj2 = stmts[1].initializer
        self.assertIsInstance(obj2, ObjectCreationExpression)
        self.assertEqual(obj2.type_ref.name, "Outer.Inner")
        self.assertEqual([a.name for a in obj2.type_ref.segment_annotations[0]], ["A"])
        self.assertEqual([a.name for a in obj2.type_ref.segment_annotations[1]], ["B"])

        arr1 = stmts[2].initializer
        self.assertIsInstance(arr1, ArrayCreationExpression)
        self.assertEqual([a.name for a in arr1.type_ref.dims_annotations[0]], ["Dim1"])
        self.assertEqual([a.name for a in arr1.type_ref.dims_annotations[1]], ["Dim2"])

        arr2 = stmts[3].initializer
        self.assertIsInstance(arr2, ArrayCreationExpression)
        self.assertEqual([a.name for a in arr2.type_ref.annotations], ["Elem"])
        self.assertEqual([a.name for a in arr2.type_ref.dims_annotations[0]], ["DimArr"])

    # --- TESTES NEGATIVOS SINTÁTICOS PARA TYPE ANNOTATIONS ---

    def test_10_erro_sintatico_type_annotations_malformadas(self):
        casos = [
            "class A { void f() { Object o = new String @A (); } }",
            "class B { void f(java.util.List<String @A> l) {} }",
            "class C { int x = ((@) 1); }",
        ]
        for src in casos:
            with self.subTest(src=src):
                with self.assertRaises(SyntacticError) as ctx:
                    parse_code(src)
                self.assertEqual(ctx.exception.line, 1)


if __name__ == "__main__":
    unittest.main()
