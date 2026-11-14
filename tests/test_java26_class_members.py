"""
Suíte de Testes Automatizados para a Etapa S3 da Gramática Java SE 26:
Classes, Campos, Métodos, Construtores, Flexible Constructor Bodies e Inicializadores.
Referência Normativa: JLS Java SE 26, Capítulos 8 e 19, JEP 513.
"""

import unittest
from src.compiler.lexer import Lexer
from src.compiler.parser import Parser, SyntacticError
from src.main import analyze_source
from src.compiler.ast_nodes import (
    CompilationUnit, OrdinaryCompilationUnit, CompactCompilationUnit,
    ClassDeclaration, FieldDeclaration, MethodDeclaration, ConstructorDeclaration,
    ConstructorBody, ExplicitConstructorInvocation, AlternateConstructorInvocation,
    SuperclassConstructorInvocation, Parameter, FormalParameter, VariableArityParameter,
    ReceiverParameter, VariableDeclarator, VariableDeclaratorId,
    InstanceInitializer, StaticInitializer, Block, EmptyStatement
)


def parse_code(source: str, mode: str = None) -> CompilationUnit:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse(mode=mode)


class TestJava26ClassMembersS3(unittest.TestCase):
    """Testes formais da Etapa S3 cobrindo JLS §8, §19 e JEP 513."""

    # =========================================================================
    # 1. CAMPOS (JLS §8.3)
    # =========================================================================
    def test_01_campo_simples(self):
        source = "class A { int x; }"
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        self.assertEqual(len(cls.members), 1)
        f = cls.members[0]
        self.assertIsInstance(f, FieldDeclaration)
        self.assertEqual(f.type_ref.name, "int")
        self.assertEqual(f.name, "x")
        self.assertEqual(len(f.declarators), 1)
        self.assertEqual(f.declarators[0].name, "x")
        self.assertIsNone(f.initializer)

    def test_02_campo_final(self):
        source = "class A { final double PI = 3.14159; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertIsInstance(f, FieldDeclaration)
        self.assertIn("final", f.modifiers)
        self.assertEqual(f.name, "PI")
        self.assertIsNotNone(f.initializer)

    def test_03_campo_static(self):
        source = "class A { static int contador = 0; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertIn("static", f.modifiers)
        self.assertEqual(f.name, "contador")

    def test_04_campo_transient(self):
        source = "class A { transient int temporario; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertIn("transient", f.modifiers)
        self.assertEqual(f.name, "temporario")

    def test_05_campo_volatile(self):
        source = "class A { volatile boolean ativo; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertIn("volatile", f.modifiers)
        self.assertEqual(f.name, "ativo")

    def test_06_campo_com_annotation(self):
        source = "class A { @Deprecated String texto; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertEqual(len(f.annotations), 1)
        self.assertEqual(f.annotations[0].name, "Deprecated")
        self.assertEqual(f.name, "texto")

    def test_07_campos_multiplos_na_mesma_declaracao(self):
        source = "class Pessoa { int idade, altura, peso; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertIsInstance(f, FieldDeclaration)
        self.assertEqual(len(f.declarators), 3)
        self.assertEqual(f.declarators[0].name, "idade")
        self.assertEqual(f.declarators[1].name, "altura")
        self.assertEqual(f.declarators[2].name, "peso")

    def test_08_inicializadores_independentes(self):
        source = "class A { int a = 1, b, c = 2; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertEqual(len(f.declarators), 3)
        self.assertIsNotNone(f.declarators[0].initializer)
        self.assertIsNone(f.declarators[1].initializer)
        self.assertIsNotNone(f.declarators[2].initializer)

    def test_09_arrays_com_dimensoes_no_identificador(self):
        source = "class A { int matriz[][], vetor[]; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertEqual(len(f.declarators), 2)
        self.assertEqual(f.declarators[0].dims, 2)
        self.assertEqual(f.declarators[1].dims, 1)

    def test_10_inicializador_de_array(self):
        source = "class A { int[] valores = {1, 2, 3}; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertIsNotNone(f.initializer)

    def test_11_declaradores_com_dimensoes_diferentes(self):
        source = "class A { int[] valores, outros[]; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertEqual(f.declarators[0].dims, 0) # dimensão está no tipo int[]
        self.assertEqual(f.declarators[1].dims, 1) # dimensão extra no identificador

    def test_12_campo_sem_inicializador(self):
        source = "class A { String descricao; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertIsNone(f.initializer)
        self.assertEqual(f.name, "descricao")

    def test_12_b_campo_com_underscore(self):
        source = "class A { int _ = 10; }"
        unit = parse_code(source)
        f = unit.type_declarations[0].members[0]
        self.assertEqual(f.declarators[0].name, "_")
        self.assertTrue(f.declarators[0].id.is_unnamed)

    # =========================================================================
    # 2. MÉTODOS (JLS §8.4)
    # =========================================================================
    def test_13_metodo_void(self):
        source = "class A { public void executar() {} }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertIsInstance(m, MethodDeclaration)
        self.assertEqual(m.name, "executar")
        self.assertEqual(m.return_type.name, "void")
        self.assertIsNotNone(m.body)

    def test_14_metodo_com_retorno_primitivo(self):
        source = "class A { private int calcular() { return 10; } }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertEqual(m.return_type.name, "int")
        self.assertIn("private", m.modifiers)

    def test_15_metodo_com_retorno_de_referencia(self):
        source = "class A { public String getNome() { return \"teste\"; } }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertEqual(m.return_type.name, "String")

    def test_16_metodo_generico(self):
        source = "class A { public <T> T converter(T valor) { return valor; } }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertEqual(len(m.type_parameters), 1)
        self.assertEqual(m.type_parameters[0].name, "T")
        self.assertEqual(m.return_type.name, "T")

    def test_17_metodo_com_limites_genericos(self):
        source = "class A { public <T extends Number & Comparable<T>> T maior(T a, T b) { return a; } }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        tparam = m.type_parameters[0]
        self.assertEqual(len(tparam.bounds), 2)
        self.assertEqual(tparam.bounds[0].name, "Number")
        self.assertEqual(tparam.bounds[1].name, "Comparable")

    def test_18_metodo_com_varios_parametros(self):
        source = "class A { public void cadastrar(String nome, int idade, boolean ativo) {} }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertEqual(len(m.parameters), 3)
        self.assertEqual(m.parameters[0].name, "nome")
        self.assertEqual(m.parameters[1].name, "idade")
        self.assertEqual(m.parameters[2].name, "ativo")

    def test_19_metodo_varargs(self):
        source = "class A { public void imprimir(String... mensagens) {} }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertEqual(len(m.parameters), 1)
        p = m.parameters[0]
        self.assertIsInstance(p, VariableArityParameter)
        self.assertTrue(p.is_varargs)
        self.assertEqual(p.name, "mensagens")

    def test_20_metodo_com_throws(self):
        source = "class A { public void carregar() throws IOException, SQLException {} }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertEqual(len(m.throws_types), 2)
        self.assertEqual(m.throws_types[0].name, "IOException")
        self.assertEqual(m.throws_types[1].name, "SQLException")

    def test_21_metodo_abstrato_sem_corpo(self):
        source = "abstract class A { public abstract void processar(); }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertIsNone(m.body)
        self.assertIn("abstract", m.modifiers)

    def test_22_metodo_static(self):
        source = "class A { public static int soma(int a, int b) { return a + b; } }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertIn("static", m.modifiers)

    def test_23_metodo_synchronized(self):
        source = "class A { public synchronized void sincronizado() {} }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertIn("synchronized", m.modifiers)

    def test_24_metodo_native(self):
        source = "class A { public native void nativo(); }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertIn("native", m.modifiers)
        self.assertIsNone(m.body)

    def test_25_metodo_com_dimensoes_de_retorno_depois_do_declarador(self):
        source = "class A { public int metodo()[][] { return null; } }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertEqual(m.name, "metodo")
        self.assertEqual(m.dims, 2)

    def test_26_metodo_com_annotations(self):
        source = "class A { @Override public String toString() { return \"\"; } }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertEqual(len(m.annotations), 1)
        self.assertEqual(m.annotations[0].name, "Override")

    def test_27_metodo_com_receiver_parameter(self):
        source = "class Pessoa { void validar(Pessoa this) {} }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertIsNotNone(m.receiver_parameter)
        self.assertEqual(m.receiver_parameter.type_ref.name, "Pessoa")
        self.assertEqual(len(m.parameters), 0)

    def test_28_metodo_com_type_annotations_nos_parametros(self):
        source = "class A { void processar(@NotNull String nome, final int x) {} }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        p1 = m.parameters[0]
        self.assertEqual(len(p1.annotations), 1)
        self.assertEqual(p1.annotations[0].name, "NotNull")
        p2 = m.parameters[1]
        self.assertIn("final", p2.modifiers)

    def test_28_b_rejeicao_receiver_parameter_como_segundo_parametro(self):
        source = "class A { void m(int a, A this) {} }"
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source)
        self.assertTrue(
            "parâmetro receptor" in cm.exception.message or
            "identificador de parâmetro válido" in str(cm.exception)
        )

    # =========================================================================
    # 3. CONSTRUTORES (JLS §8.8)
    # =========================================================================
    def test_29_construtor_vazio(self):
        source = "class Pessoa { Pessoa() {} }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertIsInstance(c, ConstructorDeclaration)
        self.assertEqual(c.name, "Pessoa")
        self.assertEqual(len(c.parameters), 0)

    def test_30_construtor_parametrizado(self):
        source = "class Pessoa { Pessoa(String nome) { this.nome = nome; } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertEqual(len(c.parameters), 1)
        self.assertEqual(c.parameters[0].name, "nome")

    def test_31_construtor_generico(self):
        source = "class Caixa { <U> Caixa(U valor) {} }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertIsInstance(c, ConstructorDeclaration)
        self.assertEqual(len(c.type_parameters), 1)
        self.assertEqual(c.type_parameters[0].name, "U")

    def test_32_construtor_com_varargs(self):
        source = "class Registro { Registro(String... valores) {} }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertTrue(c.parameters[0].is_varargs)

    def test_33_construtor_com_receiver_parameter(self):
        source = "class Externa { class Interna { Interna(Externa Externa.this) {} } }"
        unit = parse_code(source)
        inner = unit.type_declarations[0].members[0]
        c = inner.members[0]
        self.assertIsNotNone(c.receiver_parameter)
        self.assertEqual(c.receiver_parameter.qualifier, "Externa")

    def test_34_invocacao_this(self):
        source = "class Pessoa { Pessoa() { this(\"padrao\"); } Pessoa(String n) {} }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertIsInstance(c.body, ConstructorBody)
        self.assertIsInstance(c.body.constructor_invocation, AlternateConstructorInvocation)
        self.assertEqual(c.body.constructor_invocation.kind, "this")
        self.assertEqual(len(c.body.constructor_invocation.arguments), 1)

    def test_35_invocacao_this_com_argumentos(self):
        source = "class Pessoa { Pessoa(int id) { this(id, \"anonimo\"); } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        inv = c.body.constructor_invocation
        self.assertIsInstance(inv, AlternateConstructorInvocation)
        self.assertEqual(len(inv.arguments), 2)

    def test_36_invocacao_super(self):
        source = "class Pessoa { Pessoa() { super(); } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        inv = c.body.constructor_invocation
        self.assertIsInstance(inv, SuperclassConstructorInvocation)
        self.assertEqual(inv.kind, "super")
        self.assertEqual(len(inv.arguments), 0)

    def test_37_invocacao_super_com_argumentos(self):
        source = "class Pessoa { Pessoa(String nome) { super(nome); } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        inv = c.body.constructor_invocation
        self.assertIsInstance(inv, SuperclassConstructorInvocation)
        self.assertEqual(len(inv.arguments), 1)

    def test_38_invocacao_generica_de_construtor(self):
        source = "class Caixa { Caixa() { <String>super(\"teste\"); } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        inv = c.body.constructor_invocation
        self.assertEqual(len(inv.type_arguments), 1)
        self.assertEqual(inv.type_arguments[0].name, "String")

    def test_39_invocacao_qualificada_de_super(self):
        source = "class Sub { Sub(Enclosing enc) { enc.super(); } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        inv = c.body.constructor_invocation
        self.assertIsInstance(inv, SuperclassConstructorInvocation)
        self.assertIsNotNone(inv.qualifier)
        self.assertEqual(inv.qualifier.name, "enc")

    def test_40_argumentos_complexos_na_invocacao(self):
        source = "class A { A(int a, int b) { super(Math.max(1, a) + b, \"msg\"); } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        inv = c.body.constructor_invocation
        self.assertEqual(len(inv.arguments), 2)

    # =========================================================================
    # 4. FLEXIBLE CONSTRUCTOR BODIES (JEP 513 / JLS §8.8.7)
    # =========================================================================
    def test_41_construtor_com_prologo_vazio(self):
        source = "class A { A() { super(); int x = 1; } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertEqual(len(c.body.prologue), 0)
        self.assertIsNotNone(c.body.constructor_invocation)
        self.assertEqual(len(c.body.epilogue), 1)

    def test_42_construtor_com_prologo_de_variavel_local(self):
        source = "class A { A(int v) { int validado = Math.max(0, v); super(validado); } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertEqual(len(c.body.prologue), 1)
        self.assertIsNotNone(c.body.constructor_invocation)
        self.assertEqual(len(c.body.epilogue), 0)

    def test_43_construtor_com_prologo_contendo_if(self):
        source = """
        class Positivo {
            Positivo(long valor) {
                if (valor <= 0) {
                    throw new IllegalArgumentException();
                }
                super();
            }
        }
        """
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertEqual(len(c.body.prologue), 1)
        self.assertIsNotNone(c.body.constructor_invocation)

    def test_44_construtor_com_prologo_e_invocacao_super(self):
        source = "class A { A() { validar(); super(); } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertEqual(len(c.body.prologue), 1)
        self.assertIsInstance(c.body.constructor_invocation, SuperclassConstructorInvocation)

    def test_45_construtor_com_prologo_e_invocacao_this(self):
        source = "class A { A() { int x = 10; this(x); } A(int x) {} }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertEqual(len(c.body.prologue), 1)
        self.assertIsInstance(c.body.constructor_invocation, AlternateConstructorInvocation)

    def test_46_construtor_com_epilogo(self):
        source = "class A { A() { super(); int a = 1; int b = 2; } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertEqual(len(c.body.epilogue), 2)

    def test_47_construtor_com_prologo_e_epilogo(self):
        source = """
        class Exemplo {
            Exemplo(int valor) {
                int validado = Math.max(0, valor);
                if (validado == 0) {
                    throw new IllegalArgumentException();
                }
                super();
                registrar(validado);
            }
        }
        """
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertEqual(len(c.body.prologue), 2)
        self.assertIsNotNone(c.body.constructor_invocation)
        self.assertEqual(len(c.body.epilogue), 1)

    def test_48_construtor_sem_invocacao_explicita(self):
        source = "class A { A() { int x = 10; } }"
        unit = parse_code(source)
        c = unit.type_declarations[0].members[0]
        self.assertIsNone(c.body.constructor_invocation)
        self.assertEqual(len(c.body.prologue), 1)

    def test_49_rejeicao_de_duas_invocacoes_explicitas(self):
        source = "class A { A() { super(); super(); } }"
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source)
        self.assertTrue(
            "Múltiplas invocações" in cm.exception.message or
            "apenas uma invocação explícita" in str(cm.exception)
        )

    def test_50_rejeicao_de_invocacao_dentro_de_bloco_aninhado(self):
        source = "class A { A() { { super(); } } }"
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source)
        self.assertTrue(
            "nível superior" in cm.exception.message or
            "invocação de construtor proibida" in str(cm.exception)
        )

    def test_51_rejeicao_de_invocacao_dentro_de_condicional(self):
        source = "class A { A(boolean b) { if (b) super(); } }"
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source)
        self.assertTrue(
            "nível superior" in cm.exception.message or
            "invocação de construtor proibida" in str(cm.exception)
        )

    def test_52_rejeicao_de_invocacao_em_posicao_estrutural_invalida(self):
        source = "class A { void metodo() { super(); } }"
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source)
        self.assertTrue(
            "nível superior" in cm.exception.message or
            "invocação de construtor proibida" in str(cm.exception)
        )

    # =========================================================================
    # 5. INICIALIZADORES (JLS §8.6, §8.7)
    # =========================================================================
    def test_53_inicializador_de_instancia(self):
        source = "class Sistema { { inicializarInstancia(); } }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertIsInstance(m, InstanceInitializer)
        self.assertIsInstance(m.block, Block)

    def test_54_inicializador_estatico(self):
        source = "class Sistema { static { inicializarClasse(); } }"
        unit = parse_code(source)
        m = unit.type_declarations[0].members[0]
        self.assertIsInstance(m, StaticInitializer)
        self.assertIsInstance(m.block, Block)

    def test_55_multiplos_inicializadores(self):
        source = """
        class Sistema {
            static { primeiraEtapa(); }
            { preparar(); }
            static { segundaEtapa(); }
        }
        """
        unit = parse_code(source)
        members = unit.type_declarations[0].members
        self.assertEqual(len(members), 3)
        self.assertIsInstance(members[0], StaticInitializer)
        self.assertIsInstance(members[1], InstanceInitializer)
        self.assertIsInstance(members[2], StaticInitializer)

    def test_56_ordem_de_inicializadores(self):
        source = """
        class A {
            int x = 1;
            { x++; }
            int y = 2;
            static { Logger.init(); }
        }
        """
        unit = parse_code(source)
        members = unit.type_declarations[0].members
        self.assertEqual(len(members), 4)
        self.assertIsInstance(members[0], FieldDeclaration)
        self.assertIsInstance(members[1], InstanceInitializer)
        self.assertIsInstance(members[2], FieldDeclaration)
        self.assertIsInstance(members[3], StaticInitializer)

    def test_57_blocos_com_instrucoes(self):
        source = """
        class A {
            static {
                int a = 10;
                int b = 20;
                int c = a + b;
            }
        }
        """
        unit = parse_code(source)
        si = unit.type_declarations[0].members[0]
        self.assertEqual(len(si.block.statements), 3)

    def test_58_blocos_malformados(self):
        source = "class A { static { int x = 1; "
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source)
        self.assertIn("Era esperado '}'", str(cm.exception))

    # =========================================================================
    # 6. INTEGRAÇÃO E CORREÇÃO HERDADA DA S2 (COMPACT COMPILATION UNITS)
    # =========================================================================
    def test_59_classe_com_todos_os_tipos_de_membros(self):
        source = """
        public class Completa {
            private int valor;
            static int total = 0;
            static { total = 10; }
            { valor = 1; }
            public Completa() { super(); }
            public int getValor() { return valor; }
        }
        """
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        self.assertEqual(len(cls.members), 6)
        self.assertIsInstance(cls.members[0], FieldDeclaration)
        self.assertIsInstance(cls.members[1], FieldDeclaration)
        self.assertIsInstance(cls.members[2], StaticInitializer)
        self.assertIsInstance(cls.members[3], InstanceInitializer)
        self.assertIsInstance(cls.members[4], ConstructorDeclaration)
        self.assertIsInstance(cls.members[5], MethodDeclaration)

    def test_60_classe_aninhada(self):
        source = """
        class Externa {
            int x = 1;
            class Interna {
                int y = 2;
                void test() {}
            }
        }
        """
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        self.assertEqual(len(cls.members), 2)
        inner = cls.members[1]
        self.assertIsInstance(inner, ClassDeclaration)
        self.assertEqual(inner.name, "Interna")
        self.assertEqual(len(inner.members), 2)

    def test_61_classe_generica_com_construtor(self):
        source = """
        class Caixa<T> {
            private T item;
            public Caixa(T item) {
                this.item = item;
            }
        }
        """
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        self.assertEqual(len(cls.type_parameters), 1)
        c = cls.members[1]
        self.assertIsInstance(c, ConstructorDeclaration)

    def test_62_classe_com_campos_e_metodos_anotados(self):
        source = """
        class A {
            @Deprecated
            private int velho;

            @Override
            public String toString() {
                return "A";
            }
        }
        """
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        self.assertEqual(len(cls.members[0].annotations), 1)
        self.assertEqual(len(cls.members[1].annotations), 1)

    def test_63_classe_completa_com_package_e_imports(self):
        source = """
        package com.empresa.app;
        import java.util.List;
        import static java.lang.Math.PI;

        public class Circulo {
            private double raio;
            public Circulo(double raio) {
                this.raio = raio;
            }
            public double area() {
                return PI * raio * raio;
            }
        }
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, OrdinaryCompilationUnit)
        self.assertEqual(unit.package.name, "com.empresa.app")
        self.assertEqual(len(unit.imports), 2)
        self.assertEqual(len(unit.type_declarations), 1)

    def test_64_integracao_com_analyze_source(self):
        source = """
        class Teste {
            int a = 1, b = 2;
            Teste() { super(); }
            int somar() { return a + b; }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success)
        self.assertIsInstance(res.ast, OrdinaryCompilationUnit)
        self.assertEqual(len(res.semantic_errors), 0)

    def test_65_compatibilidade_com_unidades_compactas_s2(self):
        # Unidade compacta com campo seguido do método obrigatório
        source = """
        int contador = 0;
        void main() {
            contador = 10;
        }
        """
        unit = parse_code(source)
        self.assertIsInstance(unit, CompactCompilationUnit)
        self.assertEqual(len(unit.class_members), 2)
        self.assertIsInstance(unit.class_members[0], FieldDeclaration)
        self.assertIsInstance(unit.class_members[1], MethodDeclaration)

    def test_66_rejeicao_unidade_compacta_sem_metodo_declarado(self):
        # Arquivo contendo somente campo não pode ser aceito como compact compilation unit
        source = "int contador = 0;"
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source, mode="compact")
        self.assertTrue(
            "exige pelo menos uma declaração de método" in cm.exception.message or
            "ao menos uma declaração de método" in str(cm.exception)
        )

    def test_67_rejeicao_inicializador_antes_do_primeiro_metodo_em_compacta(self):
        # Em compact unit, inicializadores não são permitidos antes do primeiro método
        source = """
        { System.out.println("inicializando"); }
        void main() {}
        """
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source, mode="compact")
        self.assertTrue(
            "não são permitidos antes da primeira declaração de método" in cm.exception.message or
            "declaração de campo, classe, interface ou método" in str(cm.exception)
        )

    def test_68_rejeicao_construtor_em_unidade_compacta(self):
        # Construtor é proibido em classe implicitamente declarada
        source = """
        void main() {}
        Unnamed() {}
        """
        with self.assertRaises(SyntacticError) as cm:
            parse_code(source, mode="compact")
        self.assertIn("[ERRO SINTÁTICO]", str(cm.exception))

    # =========================================================================
    # 7. S3.1: CORREÇÃO DE TIPOS DE DECLARADORES, RETORNOS E UNNAMED VARIABLES
    # =========================================================================
    def test_69_declarador_simples(self):
        source = "class Exemplo { int valor; }"
        res = analyze_source(source)
        self.assertTrue(res.success)
        f = res.ast.type_declarations[0].members[0]
        self.assertEqual(f.declarators[0].effective_type, "int")
        sym = res.symbol_table.get_symbol("valor")
        self.assertIsNotNone(sym)
        self.assertEqual(sym["type"], "int")

    def test_70_multiplos_campos_mesmo_tipo(self):
        source = "class Exemplo { int a, b, c; }"
        res = analyze_source(source)
        self.assertTrue(res.success)
        f = res.ast.type_declarations[0].members[0]
        self.assertEqual(len(f.declarators), 3)
        self.assertEqual([d.effective_type for d in f.declarators], ["int", "int", "int"])
        for name in ("a", "b", "c"):
            self.assertEqual(res.symbol_table.get_symbol(name)["type"], "int")

    def test_71_campo_com_dimensoes_posteriores_ao_identificador(self):
        source = "class Exemplo { int matriz[][], vetor[]; }"
        res = analyze_source(source)
        self.assertTrue(res.success)
        f = res.ast.type_declarations[0].members[0]
        self.assertEqual(f.type_ref.full_name, "int")
        self.assertEqual(f.declarators[0].dims, 2)
        self.assertEqual(f.declarators[0].effective_type, "int[][]")
        self.assertEqual(f.declarators[1].dims, 1)
        self.assertEqual(f.declarators[1].effective_type, "int[]")
        self.assertEqual(res.symbol_table.get_symbol("matriz")["type"], "int[][]")
        self.assertEqual(res.symbol_table.get_symbol("vetor")["type"], "int[]")

    def test_72_campos_com_dimensoes_diferentes_na_mesma_declaracao(self):
        source = "class Exemplo { int[] buffer, historico[]; }"
        res = analyze_source(source)
        self.assertTrue(res.success)
        f = res.ast.type_declarations[0].members[0]
        self.assertEqual(f.type_ref.full_name, "int[]")
        self.assertEqual(f.declarators[0].dims, 0)
        self.assertEqual(f.declarators[0].effective_type, "int[]")
        self.assertEqual(f.declarators[1].dims, 1)
        self.assertEqual(f.declarators[1].effective_type, "int[][]")

    def test_73_tipos_efetivos_na_tabela_de_simbolos(self):
        source = """
        class Exemplo {
            int valor;
            int[] buffer, historico[];
            int matriz[][], vetor[];
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success)
        self.assertEqual(res.symbol_table.get_symbol("valor")["type"], "int")
        self.assertEqual(res.symbol_table.get_symbol("buffer")["type"], "int[]")
        self.assertEqual(res.symbol_table.get_symbol("historico")["type"], "int[][]")
        self.assertEqual(res.symbol_table.get_symbol("matriz")["type"], "int[][]")
        self.assertEqual(res.symbol_table.get_symbol("vetor")["type"], "int[]")

    def test_74_metodo_com_dimensoes_antes_do_nome(self):
        source = "class Exemplo { int[][] primeiro() { return null; } }"
        res = analyze_source(source)
        self.assertTrue(res.success)
        m = res.ast.type_declarations[0].members[0]
        self.assertEqual(m.return_type.full_name, "int[][]")
        self.assertEqual(m.dims, 0)
        self.assertEqual(m.effective_return_type, "int[][]")
        self.assertEqual(res.symbol_table.get_symbol("primeiro")["type"], "int[][]")

    def test_75_metodo_com_dimensoes_depois_dos_parenteses(self):
        source = "class Exemplo { int segundo()[][] { return null; } }"
        res = analyze_source(source)
        self.assertTrue(res.success)
        m = res.ast.type_declarations[0].members[0]
        self.assertEqual(m.return_type.full_name, "int")
        self.assertEqual(m.dims, 2)
        self.assertEqual(m.effective_return_type, "int[][]")
        self.assertEqual(res.symbol_table.get_symbol("segundo")["type"], "int[][]")

    def test_76_metodo_com_dimensoes_antes_e_depois(self):
        source = "class Exemplo { String[] quarto() { return null; } }"
        res = analyze_source(source)
        self.assertTrue(res.success)
        m = res.ast.type_declarations[0].members[0]
        self.assertEqual(m.effective_return_type, "String[]")
        self.assertEqual(res.symbol_table.get_symbol("quarto")["type"], "String[]")

    def test_77_tipo_efetivo_retorno_quatro_dimensoes(self):
        source = "class Exemplo { int[][] terceiro()[][] { return null; } }"
        res = analyze_source(source)
        self.assertTrue(res.success)
        m = res.ast.type_declarations[0].members[0]
        self.assertEqual(m.return_type.full_name, "int[][]")
        self.assertEqual(m.dims, 2)
        self.assertEqual(m.effective_return_type, "int[][][][]")
        self.assertEqual(m.effective_return_type_ref.array_dimensions, 4)
        self.assertEqual(res.symbol_table.get_symbol("terceiro")["type"], "int[][][][]")

    def test_78_preservacao_dimensoes_ast_e_to_dict(self):
        source = "class Exemplo { int matriz[][], vetor[]; int[][] calc()[][]; }"
        unit = parse_code(source)
        cls = unit.type_declarations[0]
        field_node = cls.members[0]
        method_node = cls.members[1]

        self.assertEqual(field_node.type_ref.array_dimensions, 0)
        self.assertEqual(field_node.declarators[0].dims, 2)
        self.assertEqual(field_node.declarators[0].effective_type, "int[][]")
        self.assertEqual(method_node.return_type.array_dimensions, 2)
        self.assertEqual(method_node.dims, 2)
        self.assertEqual(method_node.effective_return_type, "int[][][][]")

        f_dict = field_node.to_dict()
        self.assertIn("effective_types", f_dict)
        self.assertEqual(f_dict["effective_types"], ["int[][]", "int[]"])

        m_dict = method_node.to_dict()
        self.assertEqual(m_dict["effective_return_type"], "int[][][][]")
        self.assertEqual(m_dict["dims"], 2)

    def test_79_rejeicao_semantica_underscore_como_campo(self):
        source = "class Exemplo { int _; }"
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("'_' não pode ser utilizado como nome de campo" in str(e) for e in res.semantic_errors))
        self.assertIsNone(res.symbol_table.get_symbol("_"))

    def test_80_rejeicao_underscore_em_declaracao_multipla(self):
        source = "class Exemplo { int valor = 1, _ = 0; }"
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("'_' não pode ser utilizado como nome de campo" in str(e) for e in res.semantic_errors))
        self.assertIsNotNone(res.symbol_table.get_symbol("valor"))
        self.assertIsNone(res.symbol_table.get_symbol("_"))

    def test_81_preservacao_underscore_variaveis_locais_permitidas(self):
        source = """
        class Exemplo {
            void teste() {
                int _ = 10;
                int _ = 20;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success)
        self.assertEqual(len(res.semantic_errors), 0)
        self.assertIsNone(res.symbol_table.get_symbol("_"))

    def test_82_preservacao_parametros_nao_nomeados_permitidos(self):
        source = """
        class Exemplo {
            void executar(int x) {
                int[] lista = new int[] {1, 2};
                for (int _ : lista) {
                    int y = x;
                }
                try {
                    int z = 1;
                } catch (Exception _) {
                    int w = 2;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success)
        self.assertIsNone(res.symbol_table.get_symbol("_"))

    def test_83_flexible_constructor_body_valido(self):
        source = """
        class Base {
            Base(int x) {}
        }
        class Exemplo extends Base {
            int valor;
            Exemplo(int x) {
                int validado = x * 2;
                if (validado < 0) {
                    validado = 0;
                }
                super(validado);
                this.valor = validado;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success)
        self.assertEqual(len(res.semantic_errors), 0)

    def test_84_uso_invalido_this_early_construction_context(self):
        source = """
        class Base {
            Base(int x) {}
        }
        class Exemplo extends Base {
            int valor;
            Exemplo(int x) {
                this.valor = 10;
                super(x);
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("early construction context" in str(e) for e in res.semantic_errors))

    def test_85_integracao_analyze_source_tipos_e_construtores(self):
        source = """
        package com.teste;

        public class TesteIntegracao {
            private int[] buffer, historico[];
            private int tabela[][], vetor[];

            public TesteIntegracao(int id) {
                int idCalc = id * 10;
                super();
                int _ = 1;
            }

            public int[][] gerarCoordenadas()[][] {
                return null;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success)
        self.assertEqual(res.symbol_table.get_symbol("buffer")["type"], "int[]")
        self.assertEqual(res.symbol_table.get_symbol("historico")["type"], "int[][]")
        self.assertEqual(res.symbol_table.get_symbol("tabela")["type"], "int[][]")
        self.assertEqual(res.symbol_table.get_symbol("vetor")["type"], "int[]")
        self.assertEqual(res.symbol_table.get_symbol("gerarCoordenadas")["type"], "int[][][][]")

    def test_86_uso_invalido_super_early_construction_context(self):
        source = """
        class Base {
            int campoBase = 10;
            Base(int x) {}
            int obter() { return 1; }
        }
        class Exemplo extends Base {
            Exemplo(int x) {
                int y = super.campoBase + super.obter();
                super(x);
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("super" in str(e) and "early construction context" in str(e) for e in res.semantic_errors))

    def test_87_acesso_implicito_campo_instancia_prologo(self):
        source = """
        class Base {
            Base(int x) {}
        }
        class Exemplo extends Base {
            int contador;
            Exemplo() {
                contador = 5;
                super(1);
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("contador" in str(e) and "early construction context" in str(e) for e in res.semantic_errors))

    def test_88_chamada_implicita_metodo_instancia_prologo(self):
        source = """
        class Base {
            Base(int x) {}
        }
        class Exemplo extends Base {
            int calcular() { return 42; }
            Exemplo() {
                int r = calcular();
                super(r);
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("calcular" in str(e) and "early construction context" in str(e) for e in res.semantic_errors))

    def test_89_this_em_argumentos_invocacao_construtor(self):
        source = """
        class Base {
            Base(Object ref) {}
        }
        class Exemplo extends Base {
            int valor;
            Exemplo() {
                super(this);
            }
            Exemplo(int a) {
                this(this.valor);
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        early_errs = [str(e) for e in res.semantic_errors if "early construction context" in str(e)]
        self.assertGreaterEqual(len(early_errs), 2, msg=res.semantic_errors)

    def test_90_referencia_instancia_argumentos_super_e_this(self):
        source = """
        class Base {
            Base(int x) {}
        }
        class Exemplo extends Base {
            int instanciaCampo = 1;
            int instanciaMetodo() { return 2; }
            Exemplo() {
                super(instanciaCampo);
            }
            Exemplo(int a) {
                this(instanciaMetodo());
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("instanciaCampo" in str(e) and "early construction context" in str(e) for e in res.semantic_errors))
        self.assertTrue(any("instanciaMetodo" in str(e) and "early construction context" in str(e) for e in res.semantic_errors))

    def test_91_membros_estaticos_e_locais_validos_no_early_construction_context(self):
        source = """
        class Base {
            Base(int x) {}
        }
        class Exemplo extends Base {
            static final int CONST = 10;
            static int validar(int v) { return v + CONST; }
            int campoNormal;
            Exemplo(int entrada) {
                int ajustado = validar(entrada);
                super(ajustado + CONST);
                this.campoNormal = ajustado;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, f"Erros inesperados: {res.semantic_errors}")
        self.assertEqual(len(res.semantic_errors), 0)


if __name__ == "__main__":
    unittest.main()
