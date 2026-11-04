"""
Suíte de testes dedicada à validação da Fase B (Estrutura Sintática de Arquivos Java).
Cobre os 25 requisitos obrigatórios da especificação:
1. Classe vazia
2. Classe com pacote
3. Classe com imports
4. Imports estáticos
5. Classe com campo simples
6. Campo com inicializador
7. Classe com vários campos
8. Classe com método void
9. Método com tipo de retorno
10. Método com vários parâmetros
11. Construtor vazio
12. Construtor com parâmetros
13. Classe com extends
14. Classe com implements
15. Interface simples
16. Interface genérica simples
17. Enum
18. Vários modificadores
19. Arrays em tipos de campo e parâmetro
20. Varargs
21. Método abstrato ou declaração sem corpo no contexto válido
22. Classe sem chave de fechamento
23. Tipo sem nome
24. Declaração fora do contexto permitido (método solto no nível superior)
25. Múltiplos tipos de erros sintáticos estruturados
"""

import unittest
from pathlib import Path
import sys

# Garante acesso ao pacote src
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.lexer import Lexer
from src.parser import Parser, SyntacticError
from src.ast_nodes import (
    CompilationUnit, PackageDeclaration, ImportDeclaration,
    ClassDeclaration, InterfaceDeclaration, EnumDeclaration,
    FieldDeclaration, MethodDeclaration, ConstructorDeclaration,
    Parameter, TypeReference, Block, ReturnStatement
)
from src.main import analyze_source


class TestEstruturaArquivosJava(unittest.TestCase):
    """Testes obrigatórios da Fase B para reconhecimento de estruturas Java."""

    # 1. Classe vazia
    def test_01_classe_vazia(self):
        source = "public class Pessoa {}"
        unit = Parser(Lexer(source).tokenize()).parse()
        self.assertIsInstance(unit, CompilationUnit)
        self.assertEqual(len(unit.type_declarations), 1)
        cls = unit.type_declarations[0]
        self.assertIsInstance(cls, ClassDeclaration)
        self.assertEqual(cls.name, "Pessoa")
        self.assertEqual(cls.modifiers, ["public"])
        self.assertEqual(len(cls.members), 0)
        self.assertIn("ClassDeclaration: public Pessoa", unit.pretty())

    # 2. Classe com pacote
    def test_02_classe_com_pacote(self):
        source = "package exemplo.modelo;\npublic class Pessoa {}"
        unit = Parser(Lexer(source).tokenize()).parse()
        self.assertIsNotNone(unit.package)
        self.assertIsInstance(unit.package, PackageDeclaration)
        self.assertEqual(unit.package.name, "exemplo.modelo")
        self.assertIn("PackageDeclaration", unit.pretty())
        self.assertIn("exemplo.modelo", unit.pretty())

    # 3. Classe com imports
    def test_03_classe_com_imports(self):
        source = (
            "package exemplo;\n"
            "import java.util.List;\n"
            "import java.util.Map;\n"
            "public class Pessoa {}"
        )
        unit = Parser(Lexer(source).tokenize()).parse()
        self.assertEqual(len(unit.imports), 2)
        self.assertEqual(unit.imports[0].name, "java.util.List")
        self.assertFalse(unit.imports[0].is_static)
        self.assertEqual(unit.imports[1].name, "java.util.Map")

    # 4. Imports estáticos
    def test_04_imports_estaticos(self):
        source = (
            "import static java.lang.Math.PI;\n"
            "import static java.lang.Math.*;\n"
            "public class Calculo {}"
        )
        unit = Parser(Lexer(source).tokenize()).parse()
        self.assertEqual(len(unit.imports), 2)
        self.assertTrue(unit.imports[0].is_static)
        self.assertFalse(unit.imports[0].is_wildcard)
        self.assertEqual(unit.imports[0].name, "java.lang.Math.PI")
        self.assertTrue(unit.imports[1].is_static)
        self.assertTrue(unit.imports[1].is_wildcard)
        self.assertEqual(unit.imports[1].name, "java.lang.Math.*")

    # 5. Classe com campo simples
    def test_05_classe_com_campo_simples(self):
        source = "public class Pessoa {\n    private int idade;\n}"
        unit = Parser(Lexer(source).tokenize()).parse()
        cls = unit.type_declarations[0]
        self.assertEqual(len(cls.members), 1)
        field = cls.members[0]
        self.assertIsInstance(field, FieldDeclaration)
        self.assertEqual(field.name, "idade")
        self.assertEqual(field.type_ref.name, "int")
        self.assertEqual(field.modifiers, ["private"])
        self.assertIsNone(field.initializer)

    # 6. Campo com inicializador
    def test_06_campo_com_inicializador(self):
        source = "public class Config {\n    public static final int LIMITE = 100;\n}"
        unit = Parser(Lexer(source).tokenize()).parse()
        field = unit.type_declarations[0].members[0]
        self.assertEqual(field.name, "LIMITE")
        self.assertEqual(field.modifiers, ["public", "static", "final"])
        self.assertIsNotNone(field.initializer)
        self.assertIn("100", field.initializer.pretty())

    # 7. Classe com vários campos
    def test_07_classe_com_varios_campos(self):
        source = (
            "public class Produto {\n"
            "    private String nome = \"Ana\";\n"
            "    protected double valor = 10.5;\n"
            "    public int codigo;\n"
            "}"
        )
        unit = Parser(Lexer(source).tokenize()).parse()
        members = unit.type_declarations[0].members
        self.assertEqual(len(members), 3)
        self.assertEqual(members[0].name, "nome")
        self.assertEqual(members[0].type_ref.name, "String")
        self.assertEqual(members[1].name, "valor")
        self.assertEqual(members[1].type_ref.name, "double")
        self.assertEqual(members[2].name, "codigo")
        self.assertIsNone(members[2].initializer)

    # 8. Classe com método void
    def test_08_classe_com_metodo_void(self):
        source = "public class Servico {\n    public void executar() {}\n}"
        unit = Parser(Lexer(source).tokenize()).parse()
        method = unit.type_declarations[0].members[0]
        self.assertIsInstance(method, MethodDeclaration)
        self.assertEqual(method.name, "executar")
        self.assertEqual(method.return_type.name, "void")
        self.assertEqual(len(method.parameters), 0)
        self.assertIsNotNone(method.body)
        self.assertIsInstance(method.body, Block)

    # 9. Método com tipo de retorno
    def test_09_metodo_com_tipo_de_retorno(self):
        source = "public class Calc {\n    public int obterTotal() {\n        return 42;\n    }\n}"
        unit = Parser(Lexer(source).tokenize()).parse()
        method = unit.type_declarations[0].members[0]
        self.assertEqual(method.name, "obterTotal")
        self.assertEqual(method.return_type.name, "int")
        self.assertEqual(len(method.body.statements), 1)
        self.assertIsInstance(method.body.statements[0], ReturnStatement)

    # 10. Método com vários parâmetros
    def test_10_metodo_com_varios_parametros(self):
        source = "public class Calc {\n    public int somar(int a, int b) {\n        return a + b;\n    }\n}"
        unit = Parser(Lexer(source).tokenize()).parse()
        method = unit.type_declarations[0].members[0]
        self.assertEqual(len(method.parameters), 2)
        self.assertEqual(method.parameters[0].name, "a")
        self.assertEqual(method.parameters[0].type_ref.name, "int")
        self.assertEqual(method.parameters[1].name, "b")
        self.assertEqual(method.parameters[1].type_ref.name, "int")

    # 11. Construtor vazio
    def test_11_construtor_vazio(self):
        source = "public class Calculadora {\n    public Calculadora() {}\n}"
        unit = Parser(Lexer(source).tokenize()).parse()
        ctor = unit.type_declarations[0].members[0]
        self.assertIsInstance(ctor, ConstructorDeclaration)
        self.assertEqual(ctor.name, "Calculadora")
        self.assertEqual(len(ctor.parameters), 0)
        self.assertEqual(ctor.modifiers, ["public"])

    # 12. Construtor com parâmetros
    def test_12_construtor_com_parametros(self):
        source = (
            "public class Pessoa {\n"
            "    private String nome;\n"
            "    public Pessoa(String nome) {\n"
            "        this.nome = nome;\n"
            "    }\n"
            "}"
        )
        unit = Parser(Lexer(source).tokenize()).parse()
        members = unit.type_declarations[0].members
        self.assertEqual(len(members), 2)
        ctor = members[1]
        self.assertIsInstance(ctor, ConstructorDeclaration)
        self.assertEqual(ctor.name, "Pessoa")
        self.assertEqual(len(ctor.parameters), 1)
        self.assertEqual(ctor.parameters[0].name, "nome")
        self.assertEqual(ctor.parameters[0].type_ref.name, "String")

    # 13. Classe com extends
    def test_13_classe_com_extends(self):
        source = "class Calculadora extends Base {}"
        unit = Parser(Lexer(source).tokenize()).parse()
        cls = unit.type_declarations[0]
        self.assertIsNotNone(cls.extends_type)
        self.assertEqual(cls.extends_type.name, "Base")

    # 14. Classe com implements
    def test_14_classe_com_implements(self):
        source = "public final class Exemplo implements Runnable, Serializable {}"
        unit = Parser(Lexer(source).tokenize()).parse()
        cls = unit.type_declarations[0]
        self.assertEqual(cls.modifiers, ["public", "final"])
        self.assertEqual(len(cls.implements_types), 2)
        self.assertEqual(cls.implements_types[0].name, "Runnable")
        self.assertEqual(cls.implements_types[1].name, "Serializable")

    # 15. Interface simples
    def test_15_interface_simples(self):
        source = "public interface Repositorio {\n    void salvar();\n}"
        unit = Parser(Lexer(source).tokenize()).parse()
        iface = unit.type_declarations[0]
        self.assertIsInstance(iface, InterfaceDeclaration)
        self.assertEqual(iface.name, "Repositorio")
        self.assertEqual(len(iface.members), 1)
        method = iface.members[0]
        self.assertEqual(method.name, "salvar")
        self.assertIsNone(method.body)

    # 16. Interface genérica simples
    def test_16_interface_generica_simples(self):
        source = "public interface Conversor<T> {\n    T converter(T entrada);\n}"
        unit = Parser(Lexer(source).tokenize()).parse()
        iface = unit.type_declarations[0]
        self.assertEqual(iface.type_parameters, ["T"])
        method = iface.members[0]
        self.assertEqual(method.return_type.name, "T")
        self.assertEqual(method.parameters[0].type_ref.name, "T")

    # 17. Enum
    def test_17_enum(self):
        source = "public enum Status {\n    NOVO, EM_ANDAMENTO, CONCLUIDO\n}"
        unit = Parser(Lexer(source).tokenize()).parse()
        enum_decl = unit.type_declarations[0]
        self.assertIsInstance(enum_decl, EnumDeclaration)
        self.assertEqual(enum_decl.name, "Status")
        self.assertEqual(len(enum_decl.constants), 3)
        self.assertEqual([c.name for c in enum_decl.constants], ["NOVO", "EM_ANDAMENTO", "CONCLUIDO"])

    # 18. Vários modificadores
    def test_18_varios_modificadores(self):
        source = (
            "public abstract class Forma {\n"
            "    protected static final double PI = 3.14;\n"
            "    public abstract void desenhar();\n"
            "}"
        )
        unit = Parser(Lexer(source).tokenize()).parse()
        cls = unit.type_declarations[0]
        self.assertEqual(cls.modifiers, ["public", "abstract"])
        field = cls.members[0]
        self.assertEqual(field.modifiers, ["protected", "static", "final"])
        method = cls.members[1]
        self.assertEqual(method.modifiers, ["public", "abstract"])
        self.assertIsNone(method.body)

    # 19. Arrays em tipos de campo e parâmetro
    def test_19_arrays_em_tipos_de_campo_e_parametro(self):
        source = (
            "public class Matriz {\n"
            "    private int[] valores;\n"
            "    public void processar(String[] dados) {}\n"
            "}"
        )
        unit = Parser(Lexer(source).tokenize()).parse()
        field = unit.type_declarations[0].members[0]
        self.assertEqual(field.type_ref.array_dimensions, 1)
        method = unit.type_declarations[0].members[1]
        self.assertEqual(method.parameters[0].type_ref.array_dimensions, 1)

    # 20. Varargs
    def test_20_varargs(self):
        source = "public class Logger {\n    public void log(String... mensagens) {}\n}"
        unit = Parser(Lexer(source).tokenize()).parse()
        method = unit.type_declarations[0].members[0]
        param = method.parameters[0]
        self.assertTrue(param.is_varargs)
        self.assertEqual(param.type_ref.name, "String")

    # 21. Método abstrato ou declaração sem corpo no contexto válido
    def test_21_metodo_sem_corpo_valido(self):
        source = "public abstract class Base {\n    public abstract void acao();\n}"
        unit = Parser(Lexer(source).tokenize()).parse()
        method = unit.type_declarations[0].members[0]
        self.assertIsNone(method.body)
        self.assertIn("sem corpo", method.pretty())

    # 22. Classe sem chave de fechamento
    def test_22_classe_sem_chave_de_fechamento(self):
        source = "public class Pessoa {"
        with self.assertRaises(SyntacticError) as cm:
            Parser(Lexer(source).tokenize()).parse()
        err = cm.exception
        self.assertIn("[ERRO SINTÁTICO]", str(err))
        self.assertIn("Era esperado '}'", str(err))

    # 23. Tipo sem nome
    def test_23_tipo_sem_nome(self):
        source = "public class {}"
        with self.assertRaises(SyntacticError) as cm:
            Parser(Lexer(source).tokenize()).parse()
        err = cm.exception
        self.assertIn("[ERRO SINTÁTICO]", str(err))
        self.assertIn("Era esperado o nome da classe", str(err))

    # 24. Declaração fora do contexto permitido (método no nível superior)
    def test_24_declaracao_fora_do_contexto_permitido(self):
        source = "public int somar() {}"
        with self.assertRaises(SyntacticError) as cm:
            Parser(Lexer(source).tokenize()).parse()
        err = cm.exception
        self.assertIn("[ERRO SINTÁTICO]", str(err))
        self.assertIn("nível superior", str(err))

    # 25. Múltiplos tipos de erros sintáticos estruturados
    def test_25_multiplos_erros_sintaticos_estruturados(self):
        casos_invalidos = [
            ("package exemplo", "';' ao final da declaração de package"),
            ("import ;", "identificador após 'import'"),
            ("public class A extends { }", "um tipo"),
            ("public class A { public void test( { } }", "um tipo"),
            ("public class A { int ; }", "nome do membro"),
        ]
        for src, msg_esperada in casos_invalidos:
            with self.assertRaises(SyntacticError, msg=f"Deveria falhar em: {src}") as cm:
                Parser(Lexer(src).tokenize()).parse()
            err = cm.exception
            self.assertIn("[ERRO SINTÁTICO]", str(err))
            self.assertIn(msg_esperada, str(err))

    # Teste de integração de arquivo Java completo via analyze_source
    def test_26_integracao_api_arquivo_java_completo(self):
        source = (
            "package exemplo;\n\n"
            "import java.util.List;\n\n"
            "public class Pessoa {\n"
            "    private String nome;\n\n"
            "    public Pessoa(String nome) {\n"
            "        this.nome = nome;\n"
            "    }\n\n"
            "    public String getNome() {\n"
            "        return nome;\n"
            "    }\n"
            "}\n"
        )
        res = analyze_source(source)
        self.assertTrue(res.success)
        self.assertFalse(res.has_errors)
        self.assertIsInstance(res.ast, CompilationUnit)
        self.assertEqual(res.ast.package.name, "exemplo")
        self.assertEqual(len(res.ast.imports), 1)
        self.assertEqual(len(res.ast.type_declarations), 1)
        self.assertTrue(res.symbol_table.exists("Pessoa"))
        self.assertTrue(res.symbol_table.exists("nome"))
        self.assertTrue(res.symbol_table.exists("getNome"))


if __name__ == "__main__":
    unittest.main()
