"""
Testes de regressão para serialização (`to_dict()`), representação textual (`pretty()`)
e contratos construtivos da AST em `src/ast_nodes.py` (Etapa 2).
"""

import unittest
from src.compiler.lexer import Lexer
from src.compiler.parser import Parser
from src.compiler.ast_nodes import (
    ASTNode, Program, CompilationUnit, OrdinaryCompilationUnit,
    ModularCompilationUnit, CompactCompilationUnit,
    PackageDeclaration, ImportDeclaration, ModuleDeclaration, RequiresDirective,
    Annotation, MarkerAnnotation, SingleElementAnnotation, NormalAnnotation,
    ElementValue, ElementValueList, ElementValuePair, ElementValuePairList,
    ElementValueArrayInitializer, ClassLiteral,
    TypeReference, WildcardType, TypeParameter,
    ClassDeclaration, InterfaceDeclaration, InterfaceBody, InterfaceConstantDeclaration,
    InterfaceMethodDeclaration, EnumDeclaration, EnumBody, EnumConstantList,
    EnumBodyDeclarations, EnumConstant, EnumConstantBody,
    AnnotationInterfaceDeclaration, AnnotationInterfaceBody,
    AnnotationInterfaceElementDeclaration, AnnotationInterfaceElementModifier,
    AnnotationDefaultValue, DefaultValue,
    RecordDeclaration, RecordHeader, RecordComponentList, RecordComponent,
    VariableArityRecordComponent, RecordBody,
    NormalCanonicalConstructor, CompactConstructorDeclaration, NonCanonicalRecordConstructor,
    FieldDeclaration, MethodDeclaration, ConstructorDeclaration, ConstructorBody,
    Parameter, ReceiverParameter, Block, VariableDeclaratorId, VariableDeclarator,
    Declaration, LocalVariableDeclaration, ReturnStatement, IfStatement,
    SwitchStatement, SwitchExpression, SwitchBlock, SwitchRule,
    SwitchBlockStatementGroup, CaseLabel, DefaultLabel, Guard,
    TypePattern, RecordPattern, MatchAllPattern, PatternVariable,
    BinaryOp, UnaryOp, ConditionalExpression, ArrayCreationExpression,
    ArrayInitializer, LambdaExpression, LambdaParameter, MethodReference,
    MethodCall, ObjectCreationExpression, Literal, Identifier, EmptyStatement,
)


def parse_ast(source: str, mode: str = None) -> CompilationUnit:
    return Parser(Lexer(source).tokenize()).parse(mode=mode)


class TestASTSerializationRegression(unittest.TestCase):
    """Protege equivalência estrita de to_dict() e pretty() antes e após simplificação."""

    def test_to_dict_inherited_equivalents_keys_and_order(self):
        lit1 = Literal(1, "INT", line=2, column=5)
        lit2 = Literal('"ok"', "STRING", line=2, column=8)
        ev1 = ElementValue(value=lit1, line=2, column=5)
        ev2 = ElementValue(value=lit2, line=2, column=8)

        evl_empty = ElementValueList(line=1, column=1)
        self.assertEqual(
            evl_empty.to_dict(),
            {"node": "ElementValueList", "values": [], "line": 1, "column": 1},
        )
        self.assertEqual(list(evl_empty.to_dict().keys()), ["node", "values", "line", "column"])

        evl = ElementValueList(values=[ev1, ev2], line=2, column=5)
        d_evl = evl.to_dict()
        self.assertEqual(len(d_evl["values"]), 2)
        self.assertEqual(d_evl["values"][0]["node"], "ElementValue")

        pair = ElementValuePair(name="value", value=ev1, line=3, column=2)
        self.assertEqual(
            list(pair.to_dict().keys()),
            ["node", "name", "value", "line", "column"],
        )
        self.assertEqual(pair.to_dict()["value"]["node"], "ElementValue")

        pair_list = ElementValuePairList(pairs=[pair], line=3, column=2)
        self.assertEqual(list(pair_list.to_dict().keys()), ["node", "pairs", "line", "column"])
        self.assertEqual(pair_list.to_dict()["pairs"][0]["name"], "value")

        ec = EnumConstant(name="RED", line=4, column=3)
        ecl = EnumConstantList(constants=[ec], has_trailing_comma=True, line=4, column=3)
        self.assertEqual(
            list(ecl.to_dict().keys()),
            ["node", "constants", "has_trailing_comma", "line", "column"],
        )
        self.assertTrue(ecl.to_dict()["has_trailing_comma"])
        self.assertEqual(ecl.to_dict()["constants"][0]["name"], "RED")

        eb_empty = EnumBody(line=5, column=1)
        self.assertEqual(
            eb_empty.to_dict(),
            {"node": "EnumBody", "constant_list": None, "body_declarations": None, "line": 5, "column": 1},
        )
        eb_full = EnumBody(
            constant_list=ecl,
            body_declarations=EnumBodyDeclarations(members=[], has_semicolon=True, line=5, column=20),
            line=5,
            column=1,
        )
        self.assertEqual(list(eb_full.to_dict().keys()), ["node", "constant_list", "body_declarations", "line", "column"])
        self.assertEqual(eb_full.to_dict()["constant_list"]["node"], "EnumConstantList")
        self.assertEqual(eb_full.to_dict()["body_declarations"]["node"], "EnumBodyDeclarations")

        mod = AnnotationInterfaceElementModifier(name="public", line=6, column=4)
        self.assertEqual(
            mod.to_dict(),
            {"node": "AnnotationInterfaceElementModifier", "name": "public", "line": 6, "column": 4},
        )
        self.assertEqual(list(mod.to_dict().keys()), ["node", "name", "line", "column"])

        adv = AnnotationDefaultValue(value=ev1, line=7, column=10)
        self.assertIs(DefaultValue, AnnotationDefaultValue)
        self.assertEqual(list(adv.to_dict().keys()), ["node", "value", "line", "column"])
        self.assertEqual(adv.to_dict()["node"], "AnnotationDefaultValue")
        self.assertEqual(adv.to_dict()["value"]["node"], "ElementValue")

        rc = RecordComponent(type_ref=TypeReference("int"), name="x", line=8, column=2)
        rcl = RecordComponentList(components=[rc], line=8, column=2)
        self.assertEqual(list(rcl.to_dict().keys()), ["node", "components", "line", "column"])
        self.assertEqual(rcl.to_dict()["components"][0]["name"], "x")

    def test_to_dict_kept_custom_overrides_and_omissions(self):
        m = MarkerAnnotation(name="Override", line=1, column=1)
        self.assertEqual(m.to_dict(), {"node": "MarkerAnnotation", "name": "Override", "line": 1, "column": 1})
        self.assertNotIn("arguments", m.to_dict())

        ev = ElementValue(value=Literal(42, "INT"), line=1, column=5)
        se = SingleElementAnnotation(name="Tag", element_value=ev, line=1, column=1)
        self.assertNotIn("arguments", se.to_dict())
        self.assertEqual(se.to_dict()["element_value"]["node"], "ElementValue")

        na = NormalAnnotation(name="Cfg", line=1, column=1)
        self.assertNotIn("arguments", na.to_dict())
        self.assertEqual(na.to_dict()["element_value_pair_list"]["pairs"], [])

        t_int = TypeReference("int", array_dimensions=1, line=2, column=1)
        cl = ClassLiteral(type_ref=t_int, line=2, column=1)
        d_cl = cl.to_dict()
        self.assertEqual(d_cl["type"]["node"], "TypeReference")
        self.assertEqual(d_cl["type_name"], "int[]")
        self.assertFalse(d_cl["is_void"])
        self.assertNotIn("type_ref", d_cl)

        tp = TypePattern(type_ref=TypeReference("String"), name="s", modifiers=["final"], line=3, column=1)
        self.assertEqual(tp.to_dict()["type_name"], "String")
        rp = RecordPattern(type_ref=TypeReference("Point"), components=[tp], line=3, column=1)
        self.assertEqual(rp.to_dict()["type_name"], "Point")

        rh = RecordHeader(components=[RecordComponent(TypeReference("int"), "a")], line=4, column=1)
        self.assertEqual(list(rh.to_dict().keys()), ["node", "component_list", "line", "column"])

        ic = InterfaceConstantDeclaration(
            type_ref=TypeReference("int"),
            declarators=[VariableDeclarator(VariableDeclaratorId("MAX"), Literal(10, "INT"))],
        )
        self.assertEqual(ic.to_dict()["node"], "InterfaceConstantDeclaration")
        self.assertEqual(ic.to_dict()["implicit_modifiers"], ["public", "static", "final"])

        im = InterfaceMethodDeclaration(name="m", return_type=TypeReference("void"))
        self.assertEqual(im.to_dict()["node"], "InterfaceMethodDeclaration")
        self.assertTrue(im.to_dict()["is_abstract"])

    def test_pretty_inherited_and_empty_vs_populated_nodes(self):
        self.assertEqual(Program().pretty(), "Program")
        self.assertEqual(
            Program(statements=[EmptyStatement()]).pretty(),
            "Program\n└── EmptyStatement (;)",
        )

        self.assertEqual(CompilationUnit().pretty(), "Program")
        self.assertEqual(OrdinaryCompilationUnit().pretty(), "Program")
        self.assertEqual(
            OrdinaryCompilationUnit(statements=[EmptyStatement()]).pretty(),
            "Program\n└── EmptyStatement (;)",
        )
        ocu = OrdinaryCompilationUnit(
            package=PackageDeclaration("p.q"),
            imports=[ImportDeclaration("java.util.List")],
            type_declarations=[ClassDeclaration("A")],
        )
        self.assertTrue(ocu.pretty().startswith("OrdinaryCompilationUnit\n"))

        cu_mod = CompilationUnit(module_declaration=ModuleDeclaration("m"))
        self.assertTrue(cu_mod.pretty().startswith("CompilationUnit\n"))

        self.assertEqual(MarkerAnnotation("Override").pretty(), "@Override")
        self.assertEqual(Annotation("Custom", arguments=[Literal(1, "INT")]).pretty(), "@Custom(...)")
        self.assertEqual(Annotation("Bare").pretty(), "@Bare")

        field_no_init = FieldDeclaration(
            type_ref=TypeReference("int"),
            modifiers=["private"],
            declarators=[VariableDeclarator(VariableDeclaratorId("x"))],
        )
        self.assertEqual(field_no_init.pretty(), "FieldDeclaration: private int x")
        field_init = FieldDeclaration(
            type_ref=TypeReference("int"),
            declarators=[VariableDeclarator(VariableDeclaratorId("x"), Literal(1, "INT"))],
        )
        self.assertEqual(field_init.pretty(), "FieldDeclaration: int x = INT (1)\n└── INT (1)")

        iface_const_no_init = InterfaceConstantDeclaration(
            type_ref=TypeReference("int"),
            modifiers=["public"],
            declarators=[VariableDeclarator(VariableDeclaratorId("K"))],
        )
        self.assertEqual(iface_const_no_init.pretty(), "InterfaceConstantDeclaration: public int K")
        iface_const_init = InterfaceConstantDeclaration(
            type_ref=TypeReference("int"),
            declarators=[VariableDeclarator(VariableDeclaratorId("K"), Literal(9, "INT"))],
        )
        self.assertEqual(iface_const_init.pretty(), "InterfaceConstantDeclaration: int K = INT (9)\n└── INT (9)")

        m_abs = MethodDeclaration(
            name="f",
            return_type=TypeReference("void"),
            modifiers=["public"],
            parameters=[Parameter(TypeReference("int"), "a")],
            throws_types=[TypeReference("Exception")],
        )
        self.assertEqual(
            m_abs.pretty(),
            "MethodDeclaration: public void f(Parametro (int) a) throws Exception (abstrato / sem corpo)",
        )
        im_abs = InterfaceMethodDeclaration(
            name="g",
            return_type=TypeReference("int"),
            type_parameters=[TypeParameter("T", bounds=[TypeReference("Number")])],
            dims=1,
            dims_annotations=[[MarkerAnnotation("NonNull")]],
        )
        self.assertEqual(
            im_abs.pretty(),
            "InterfaceMethodDeclaration: <T extends Number> int g() @NonNull [] (abstrato / sem corpo)",
        )
        im_body = InterfaceMethodDeclaration(
            name="h",
            return_type=TypeReference("void"),
            modifiers=["default"],
            body=Block([]),
        )
        self.assertEqual(im_body.pretty(), "InterfaceMethodDeclaration: default void h()\n└── Block")

        self.assertEqual(Block([]).pretty(), "Block")
        self.assertEqual(ClassDeclaration("C").pretty(), "ClassDeclaration: C")
        self.assertEqual(InterfaceBody().pretty(), "InterfaceBody")
        self.assertEqual(InterfaceDeclaration("I").pretty(), "InterfaceDeclaration: I")
        self.assertEqual(EnumConstantBody().pretty(), "EnumConstantBody")
        self.assertEqual(EnumConstant("A").pretty(), "EnumConstant: A")
        self.assertEqual(EnumBodyDeclarations().pretty(), "EnumBodyDeclarations")
        self.assertEqual(EnumBody().pretty(), "EnumBody")
        self.assertEqual(EnumDeclaration("E").pretty(), "EnumDeclaration: E")
        self.assertEqual(ModuleDeclaration("mod").pretty(), "ModuleDeclaration: mod")
        self.assertEqual(ConstructorBody().pretty(), "ConstructorBody")
        self.assertEqual(ConstructorDeclaration("C").pretty(), "ConstructorDeclaration: C()")
        self.assertEqual(NormalCanonicalConstructor("R").pretty(), "NormalCanonicalConstructor: R()")
        self.assertEqual(CompactConstructorDeclaration("R").pretty(), "CompactConstructorDeclaration: R (compacto)")
        self.assertEqual(NonCanonicalRecordConstructor("R").pretty(), "NonCanonicalRecordConstructor: R()")
        self.assertEqual(RecordBody().pretty(), "RecordBody (construtor canônico implícito)")
        self.assertEqual(RecordDeclaration("R", RecordHeader()).pretty(), "RecordDeclaration: R() [canonical implícito]")
        self.assertEqual(LocalVariableDeclaration("int", "v", line=1).pretty(), "LocalVariableDeclaration: int v")
        self.assertEqual(ReturnStatement().pretty(), "ReturnStatement")
        self.assertEqual(CaseLabel(has_default=True).pretty(), "CaseLabel (default)")
        self.assertEqual(ArrayCreationExpression(TypeReference("int"), dimensions=[None]).pretty(), "ArrayCreation: new int[]")

    def test_full_java_structures_to_dict_and_pretty_roundtrip(self):
        source = """
        package demo;
        import java.util.*;

        @interface Info {
            String[] tags() default {"a", "b"};
        }

        interface Service {
            int LIMIT = 5;
            default <T extends Number> T id(T v) {
                return v;
            }
        }

        enum Color {
            RED(1), BLUE(2);
            final int code;
            Color(int code) { this.code = code; }
        }

        record Box<T>(@Info(tags = {"x"}) T value) implements Service {
            Box {
                if (value == null) return;
            }
            static int check(Object obj) {
                return switch (obj) {
                    case Box(String s) when s.length() > 0 -> 1;
                    case Box(_) -> 2;
                    case null, default -> 0;
                };
            }
        }
        """
        cu = parse_ast(source)
        d = cu.to_dict()
        self.assertEqual(d["node"], "OrdinaryCompilationUnit")
        self.assertGreaterEqual(len(d["type_declarations"]), 4)
        p = cu.pretty()
        self.assertIn("OrdinaryCompilationUnit", p)
        self.assertIn("InterfaceConstantDeclaration: int LIMIT = NUM (5)", p)
        self.assertIn("InterfaceMethodDeclaration: default <T extends Number> T id(", p)
        self.assertIn("RecordDeclaration: Box<T>(", p)
        self.assertIn("SwitchExpression", p)
        self.assertIn("MatchAllPattern (_)", p)


if __name__ == "__main__":
    unittest.main()
