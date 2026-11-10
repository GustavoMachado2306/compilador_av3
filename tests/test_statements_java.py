"""
Suíte de testes dedicada à validação da Fase C (Instruções e Controle de Fluxo da Linguagem Java).
Cobre todos os 24 requisitos obrigatórios da especificação:
1. Declarações de variáveis locais e atribuições
2. Chamadas de métodos dentro de blocos
3. if e if/else
4. else if e condicionais aninhadas
5. while e do/while
6. for tradicional
7. for aprimorado
8. break e continue
9. return com e sem expressão
10. throw
11. try/catch/finally
12. Múltiplos catch
13. try com recursos
14. assert
15. synchronized
16. Blocos e laços aninhados
17. Instruções sem chaves quando a gramática permitir
18. Parênteses ou chaves não fechados
19. Cabeçalho de for incompleto
20. Condições ausentes ou malformadas
21. Separadores obrigatórios ausentes
22. Integração com classes e métodos completos da Fase B
23. Integração com analyze_source(source)
24. Ausência de regressões nos testes anteriores
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
    CompilationUnit, ClassDeclaration, MethodDeclaration, ConstructorDeclaration,
    Block, LocalVariableDeclaration, Assignment, ExpressionStatement, EmptyStatement,
    IfStatement, WhileStatement, DoWhileStatement, ForStatement, EnhancedForStatement,
    SwitchStatement, SwitchCase, BreakStatement, ContinueStatement, ReturnStatement,
    ThrowStatement, AssertStatement, TryStatement, CatchClause, SynchronizedStatement,
    MethodCall, UnaryOp, BinaryOp, Literal, Identifier
)
from src.main import analyze_source


def parse_java(source: str) -> CompilationUnit:
    """Helper para tokenizar e analisar sintaticamente código Java."""
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


class TestInstrucoesEControleDeFluxoJava(unittest.TestCase):
    """Testes exaustivos da Fase C: Instruções e Controle de Fluxo."""

    # -------------------------------------------------------------------------
    # 1. DECLARAÇÕES DE VARIÁVEIS LOCAIS E ATRIBUIÇÕES
    # -------------------------------------------------------------------------
    def test_01_declaracoes_locais_e_atribuicoes(self):
        source = (
            "public class Teste {\n"
            "    void executar() {\n"
            "        int idade = 20;\n"
            "        String nome;\n"
            "        final double pi = 3.14;\n"
            "        nome = \"Ana\";\n"
            "        idade += 1;\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        body = unit.type_declarations[0].members[0].body
        self.assertIsInstance(body, Block)
        stmts = body.statements
        self.assertEqual(len(stmts), 5)

        # 1.1 int idade = 20;
        self.assertIsInstance(stmts[0], LocalVariableDeclaration)
        self.assertEqual(stmts[0].name, "idade")
        self.assertEqual(stmts[0].type_name, "int")
        self.assertIsInstance(stmts[0].initializer, Literal)
        self.assertEqual(stmts[0].initializer.value, "20")

        # 1.2 String nome;
        self.assertIsInstance(stmts[1], LocalVariableDeclaration)
        self.assertEqual(stmts[1].name, "nome")
        self.assertEqual(stmts[1].type_name, "String")
        self.assertIsNone(stmts[1].initializer)

        # 1.3 final double pi = 3.14;
        self.assertIsInstance(stmts[2], LocalVariableDeclaration)
        self.assertEqual(stmts[2].modifiers, ["final"])
        self.assertEqual(stmts[2].name, "pi")

        # 1.4 nome = "Ana";
        self.assertIsInstance(stmts[3], Assignment)
        self.assertEqual(stmts[3].name, "nome")
        self.assertEqual(stmts[3].operator, "=")
        self.assertIsInstance(stmts[3].expression, Literal)

        # 1.5 idade += 1;
        self.assertIsInstance(stmts[4], Assignment)
        self.assertEqual(stmts[4].name, "idade")
        self.assertEqual(stmts[4].operator, "+=")

    # -------------------------------------------------------------------------
    # 2. CHAMADAS DE MÉTODOS DENTRO DE BLOCOS
    # -------------------------------------------------------------------------
    def test_02_chamadas_de_metodos_em_blocos(self):
        source = (
            "public class Teste {\n"
            "    void log() {\n"
            "        System.out.println(\"Olá\");\n"
            "        executarOperacao();\n"
            "        recurso.executar();\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        stmts = unit.type_declarations[0].members[0].body.statements
        self.assertEqual(len(stmts), 3)

        # 2.1 System.out.println("Olá");
        self.assertIsInstance(stmts[0], ExpressionStatement)
        call1 = stmts[0].expression
        self.assertIsInstance(call1, MethodCall)
        self.assertEqual(call1.method_name, "println")
        self.assertEqual(len(call1.arguments), 1)

        # 2.2 executarOperacao();
        self.assertIsInstance(stmts[1], ExpressionStatement)
        call2 = stmts[1].expression
        self.assertIsInstance(call2, MethodCall)
        self.assertEqual(call2.method_name, "executarOperacao")
        self.assertEqual(len(call2.arguments), 0)

        # 2.3 recurso.executar();
        self.assertIsInstance(stmts[2], ExpressionStatement)
        call3 = stmts[2].expression
        self.assertIsInstance(call3, MethodCall)
        self.assertEqual(call3.method_name, "executar")

    # -------------------------------------------------------------------------
    # 3. IF E IF/ELSE
    # -------------------------------------------------------------------------
    def test_03_if_e_if_else(self):
        source = (
            "public class Teste {\n"
            "    void checar(int idade) {\n"
            "        if (idade >= 18) {\n"
            "            aprovado = true;\n"
            "        }\n"
            "        if (idade < 12) {\n"
            "            tarifa = 0;\n"
            "        } else {\n"
            "            tarifa = 10;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        stmts = unit.type_declarations[0].members[0].body.statements
        self.assertEqual(len(stmts), 2)

        # 3.1 if simples
        if1 = stmts[0]
        self.assertIsInstance(if1, IfStatement)
        self.assertIsInstance(if1.condition, BinaryOp)
        self.assertEqual(if1.condition.op, ">=")
        self.assertIsInstance(if1.then_branch, Block)
        self.assertIsNone(if1.else_branch)

        # 3.2 if/else
        if2 = stmts[1]
        self.assertIsInstance(if2, IfStatement)
        self.assertIsInstance(if2.condition, BinaryOp)
        self.assertEqual(if2.condition.op, "<")
        self.assertIsInstance(if2.then_branch, Block)
        self.assertIsInstance(if2.else_branch, Block)

    # -------------------------------------------------------------------------
    # 4. ELSE IF E CONDICIONAIS ANINHADAS
    # -------------------------------------------------------------------------
    def test_04_else_if_e_condicionais_aninhadas(self):
        source = (
            "public class Teste {\n"
            "    void avaliar(int idade) {\n"
            "        if (idade >= 18) {\n"
            "            aprovado = true;\n"
            "        } else if (idade >= 16) {\n"
            "            aprovado = false;\n"
            "        } else {\n"
            "            aprovado = false;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        stmts = unit.type_declarations[0].members[0].body.statements
        if_root = stmts[0]
        self.assertIsInstance(if_root, IfStatement)
        self.assertIsInstance(if_root.else_branch, IfStatement)
        self.assertIsInstance(if_root.else_branch.else_branch, Block)
        self.assertIn("IfStatement", if_root.pretty())
        self.assertIn("Senao", if_root.pretty())

    # -------------------------------------------------------------------------
    # 5. WHILE E DO/WHILE
    # -------------------------------------------------------------------------
    def test_05_while_e_do_while(self):
        source = (
            "public class Teste {\n"
            "    void laco() {\n"
            "        while (contador < 10) {\n"
            "            contador++;\n"
            "        }\n"
            "        do {\n"
            "            contador--;\n"
            "        } while (contador > 0);\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        stmts = unit.type_declarations[0].members[0].body.statements
        self.assertEqual(len(stmts), 2)

        # 5.1 while
        wh = stmts[0]
        self.assertIsInstance(wh, WhileStatement)
        self.assertIsInstance(wh.condition, BinaryOp)
        self.assertEqual(wh.condition.op, "<")
        self.assertIsInstance(wh.body, Block)

        # 5.2 do-while
        dw = stmts[1]
        self.assertIsInstance(dw, DoWhileStatement)
        self.assertIsInstance(dw.condition, BinaryOp)
        self.assertEqual(dw.condition.op, ">")
        self.assertIsInstance(dw.body, Block)

    # -------------------------------------------------------------------------
    # 6. FOR TRADICIONAL
    # -------------------------------------------------------------------------
    def test_06_for_tradicional(self):
        source = (
            "public class Teste {\n"
            "    void iterar() {\n"
            "        for (int i = 0; i < 10; i++) {\n"
            "            System.out.println(i);\n"
            "        }\n"
            "        for (;;) {\n"
            "            break;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        stmts = unit.type_declarations[0].members[0].body.statements
        self.assertEqual(len(stmts), 2)

        # 6.1 for completo
        f1 = stmts[0]
        self.assertIsInstance(f1, ForStatement)
        self.assertIsInstance(f1.init, LocalVariableDeclaration)
        self.assertEqual(f1.init.name, "i")
        self.assertIsInstance(f1.condition, BinaryOp)
        self.assertIsInstance(f1.update, UnaryOp)
        self.assertIsInstance(f1.body, Block)

        # 6.2 for infinito for (;;)
        f2 = stmts[1]
        self.assertIsInstance(f2, ForStatement)
        self.assertIsNone(f2.init)
        self.assertIsNone(f2.condition)
        self.assertIsNone(f2.update)

    # -------------------------------------------------------------------------
    # 7. FOR APRIMORADO (FOR-EACH)
    # -------------------------------------------------------------------------
    def test_07_for_aprimorado(self):
        source = (
            "public class Teste {\n"
            "    void listar() {\n"
            "        for (String nome : nomes) {\n"
            "            System.out.println(nome);\n"
            "        }\n"
            "        for (final int valor : valores) {\n"
            "            total += valor;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        stmts = unit.type_declarations[0].members[0].body.statements
        self.assertEqual(len(stmts), 2)

        # 7.1 for (String nome : nomes)
        ef1 = stmts[0]
        self.assertIsInstance(ef1, EnhancedForStatement)
        self.assertEqual(ef1.variable.name, "nome")
        self.assertEqual(ef1.variable.type_name, "String")
        self.assertIsInstance(ef1.iterable, Identifier)
        self.assertEqual(ef1.iterable.name, "nomes")
        self.assertIsInstance(ef1.body, Block)

        # 7.2 for (final int valor : valores)
        ef2 = stmts[1]
        self.assertIsInstance(ef2, EnhancedForStatement)
        self.assertEqual(ef2.variable.modifiers, ["final"])
        self.assertEqual(ef2.variable.name, "valor")

    # -------------------------------------------------------------------------
    # 8. BREAK E CONTINUE (COM E SEM RÓTULO)
    # -------------------------------------------------------------------------
    def test_08_break_e_continue(self):
        source = (
            "public class Teste {\n"
            "    void saltos() {\n"
            "        break;\n"
            "        break externo;\n"
            "        continue;\n"
            "        continue externo;\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        stmts = unit.type_declarations[0].members[0].body.statements
        self.assertEqual(len(stmts), 4)

        self.assertIsInstance(stmts[0], BreakStatement)
        self.assertIsNone(stmts[0].label)

        self.assertIsInstance(stmts[1], BreakStatement)
        self.assertEqual(stmts[1].label, "externo")

        self.assertIsInstance(stmts[2], ContinueStatement)
        self.assertIsNone(stmts[2].label)

        self.assertIsInstance(stmts[3], ContinueStatement)
        self.assertEqual(stmts[3].label, "externo")

    # -------------------------------------------------------------------------
    # 9. RETURN COM E SEM EXPRESSÃO
    # -------------------------------------------------------------------------
    def test_09_return_com_e_sem_expressao(self):
        source = (
            "public class Teste {\n"
            "    void sair() {\n"
            "        return;\n"
            "    }\n"
            "    int calcular() {\n"
            "        return 10 + 5;\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        m1 = unit.type_declarations[0].members[0]
        m2 = unit.type_declarations[0].members[1]

        r1 = m1.body.statements[0]
        self.assertIsInstance(r1, ReturnStatement)
        self.assertIsNone(r1.expression)

        r2 = m2.body.statements[0]
        self.assertIsInstance(r2, ReturnStatement)
        self.assertIsInstance(r2.expression, BinaryOp)

    # -------------------------------------------------------------------------
    # 10. THROW
    # -------------------------------------------------------------------------
    def test_10_throw(self):
        source = (
            "public class Teste {\n"
            "    void falhar() {\n"
            "        throw new RuntimeException(\"Erro grave\");\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        stmt = unit.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(stmt, ThrowStatement)
        self.assertIsInstance(stmt.expression, MethodCall)
        self.assertIn("ThrowStatement", stmt.pretty())

    # -------------------------------------------------------------------------
    # 11. TRY/CATCH/FINALLY
    # -------------------------------------------------------------------------
    def test_11_try_catch_finally(self):
        source = (
            "public class Teste {\n"
            "    void executar() {\n"
            "        try {\n"
            "            operacao();\n"
            "        } catch (IllegalArgumentException e) {\n"
            "            System.out.println(e.getMessage());\n"
            "        } finally {\n"
            "            liberar();\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        try_stmt = unit.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(try_stmt, TryStatement)
        self.assertIsInstance(try_stmt.body, Block)
        self.assertEqual(len(try_stmt.catches), 1)
        self.assertEqual(try_stmt.catches[0].parameter.name, "e")
        self.assertEqual(try_stmt.catches[0].parameter.type_ref.name, "IllegalArgumentException")
        self.assertIsInstance(try_stmt.finally_block, Block)

    # -------------------------------------------------------------------------
    # 12. MÚLTIPLOS CATCH
    # -------------------------------------------------------------------------
    def test_12_multiplos_catch(self):
        source = (
            "public class Teste {\n"
            "    void tratar() {\n"
            "        try {\n"
            "            ler();\n"
            "        } catch (IOException e) {\n"
            "            log(e);\n"
            "        } catch (Exception e) {\n"
            "            throw e;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        try_stmt = unit.type_declarations[0].members[0].body.statements[0]
        self.assertEqual(len(try_stmt.catches), 2)
        self.assertEqual(try_stmt.catches[0].parameter.type_ref.name, "IOException")
        self.assertEqual(try_stmt.catches[1].parameter.type_ref.name, "Exception")
        self.assertIsNone(try_stmt.finally_block)

    # -------------------------------------------------------------------------
    # 13. TRY COM RECURSOS (TRY-WITH-RESOURCES)
    # -------------------------------------------------------------------------
    def test_13_try_com_recursos(self):
        source = (
            "public class Teste {\n"
            "    void gerenciar() {\n"
            "        try (var recurso = abrirRecurso()) {\n"
            "            recurso.executar();\n"
            "        } catch (Exception e) {\n"
            "            throw new RuntimeException(e);\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        try_stmt = unit.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(try_stmt, TryStatement)
        self.assertEqual(len(try_stmt.resources), 1)
        res = try_stmt.resources[0]
        self.assertIsInstance(res, LocalVariableDeclaration)
        self.assertEqual(res.name, "recurso")
        self.assertIn("TryStatement (with resources)", try_stmt.pretty())

    # -------------------------------------------------------------------------
    # 14. ASSERT
    # -------------------------------------------------------------------------
    def test_14_assert(self):
        source = (
            "public class Teste {\n"
            "    void validar(int valor) {\n"
            "        assert valor > 0;\n"
            "        assert valor <= 100 : \"Valor fora do limite\";\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        stmts = unit.type_declarations[0].members[0].body.statements
        self.assertEqual(len(stmts), 2)

        # 14.1 assert simples
        a1 = stmts[0]
        self.assertIsInstance(a1, AssertStatement)
        self.assertIsInstance(a1.condition, BinaryOp)
        self.assertIsNone(a1.message)

        # 14.2 assert com mensagem
        a2 = stmts[1]
        self.assertIsInstance(a2, AssertStatement)
        self.assertIsInstance(a2.condition, BinaryOp)
        self.assertIsInstance(a2.message, Literal)

    # -------------------------------------------------------------------------
    # 15. SYNCHRONIZED
    # -------------------------------------------------------------------------
    def test_15_synchronized(self):
        source = (
            "public class Teste {\n"
            "    void sync(Object lock) {\n"
            "        synchronized (lock) {\n"
            "            contador++;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        sync_stmt = unit.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(sync_stmt, SynchronizedStatement)
        self.assertIsInstance(sync_stmt.lock, Identifier)
        self.assertEqual(sync_stmt.lock.name, "lock")
        self.assertIsInstance(sync_stmt.body, Block)
        self.assertIn("SynchronizedStatement", sync_stmt.pretty())

    # -------------------------------------------------------------------------
    # 16. BLOCOS E LAÇOS ANINHADOS
    # -------------------------------------------------------------------------
    def test_16_blocos_e_lacos_aninhados(self):
        source = (
            "public class Teste {\n"
            "    void aninhar() {\n"
            "        {\n"
            "            int a = 10;\n"
            "            while (a > 0) {\n"
            "                for (int b = 0; b < 2; b++) {\n"
            "                    a--;\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        outer_block = unit.type_declarations[0].members[0].body
        inner_block = outer_block.statements[0]
        self.assertIsInstance(inner_block, Block)
        self.assertIsInstance(inner_block.statements[0], LocalVariableDeclaration)
        wh = inner_block.statements[1]
        self.assertIsInstance(wh, WhileStatement)
        f = wh.body.statements[0]
        self.assertIsInstance(f, ForStatement)

    # -------------------------------------------------------------------------
    # 17. INSTRUÇÕES SEM CHAVES QUANDO A GRAMÁTICA PERMITIR
    # -------------------------------------------------------------------------
    def test_17_instrucoes_sem_chaves(self):
        source = (
            "public class Teste {\n"
            "    void compacta(int x) {\n"
            "        if (x > 0) x = 1; else x = 2;\n"
            "        while (x < 10) x++;\n"
            "        for (int i = 0; i < 5; i++) x += i;\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        stmts = unit.type_declarations[0].members[0].body.statements
        self.assertEqual(len(stmts), 3)

        # 17.1 if/else sem chaves
        if_stmt = stmts[0]
        self.assertIsInstance(if_stmt, IfStatement)
        self.assertIsInstance(if_stmt.then_branch, Assignment)
        self.assertIsInstance(if_stmt.else_branch, Assignment)

        # 17.2 while sem chaves
        wh_stmt = stmts[1]
        self.assertIsInstance(wh_stmt, WhileStatement)
        self.assertIsInstance(wh_stmt.body, ExpressionStatement)

        # 17.3 for sem chaves
        for_stmt = stmts[2]
        self.assertIsInstance(for_stmt, ForStatement)
        self.assertIsInstance(for_stmt.body, Assignment)

    # -------------------------------------------------------------------------
    # 18. PARÊNTESES OU CHAVES NÃO FECHADOS (ERROS NEGATIVOS)
    # -------------------------------------------------------------------------
    def test_18_parenteses_ou_chaves_nao_fechados(self):
        casos = [
            # if com parentese nao fechado
            "public class Teste { void f() { if (x > 0 { x = 1; } } }",
            # while com parentese nao fechado
            "public class Teste { void f() { while (x > 0 { x = 1; } } }",
            # bloco sem chave de fechamento
            "public class Teste { void f() { { int x = 10; } }",
        ]
        for caso in casos:
            with self.assertRaises(SyntacticError, msg=f"Deveria falhar em: {caso}"):
                parse_java(caso)

    # -------------------------------------------------------------------------
    # 19. CABEÇALHO DE FOR INCOMPLETO (ERROS NEGATIVOS)
    # -------------------------------------------------------------------------
    def test_19_cabecalho_de_for_incompleto(self):
        casos = [
            # for vazio
            "public class Teste { void f() { for () {} } }",
            # for tradicional sem segundo ';'
            "public class Teste { void f() { for (int i = 0; i < 10) {} } }",
            # for aprimorado sem iteravel
            "public class Teste { void f() { for (String s :) {} } }",
        ]
        for caso in casos:
            with self.assertRaises(SyntacticError, msg=f"Deveria falhar em: {caso}"):
                parse_java(caso)

    # -------------------------------------------------------------------------
    # 20. CONDIÇÕES AUSENTES OU MALFORMADAS (ERROS NEGATIVOS)
    # -------------------------------------------------------------------------
    def test_20_condicoes_ausentes_ou_malformadas(self):
        casos = [
            "public class Teste { void f() { if () {} } }",
            "public class Teste { void f() { while () {} } }",
            "public class Teste { void f() { do {} while (); } }",
        ]
        for caso in casos:
            with self.assertRaises(SyntacticError, msg=f"Deveria falhar em: {caso}"):
                parse_java(caso)

    # -------------------------------------------------------------------------
    # 21. SEPARADORES OBRIGATÓRIOS AUSENTES (ERROS NEGATIVOS)
    # -------------------------------------------------------------------------
    def test_21_separadores_obrigatorios_ausentes(self):
        casos = [
            "public class Teste { void f() { int x = 10 } }",
            "public class Teste { void f() { return } }",
            "public class Teste { void f() { throw e } }",
            "public class Teste { void f() { assert cond } }",
            "public class Teste { void f() { do {} while (x > 0) } }",
        ]
        for caso in casos:
            with self.assertRaises(SyntacticError, msg=f"Deveria falhar em: {caso}"):
                parse_java(caso)

    # -------------------------------------------------------------------------
    # 22. INTEGRAÇÃO COM CLASSES E MÉTODOS COMPLETOS DA FASE B
    # -------------------------------------------------------------------------
    def test_22_integracao_classes_e_metodos_completos(self):
        source = (
            "package br.com.exemplo;\n"
            "import java.util.List;\n"
            "public class Calculadora {\n"
            "    private int total = 0;\n"
            "    public Calculadora(int inicial) {\n"
            "        this.total = inicial;\n"
            "    }\n"
            "    public int somar(int valor) {\n"
            "        if (valor > 0) {\n"
            "            this.total += valor;\n"
            "        } else {\n"
            "            System.out.println(\"Valor não positivo\");\n"
            "        }\n"
            "        return this.total;\n"
            "    }\n"
            "}\n"
        )
        unit = parse_java(source)
        self.assertEqual(unit.package.name, "br.com.exemplo")
        self.assertEqual(len(unit.imports), 1)
        cls = unit.type_declarations[0]
        self.assertEqual(cls.name, "Calculadora")
        self.assertEqual(len(cls.members), 3)

        ctor = cls.members[1]
        self.assertIsInstance(ctor, ConstructorDeclaration)
        self.assertEqual(len(ctor.body.statements), 1)

        metodo = cls.members[2]
        self.assertIsInstance(metodo, MethodDeclaration)
        self.assertEqual(len(metodo.body.statements), 2)
        self.assertIsInstance(metodo.body.statements[0], IfStatement)
        self.assertIsInstance(metodo.body.statements[1], ReturnStatement)

    # -------------------------------------------------------------------------
    # 23. INTEGRAÇÃO COM ANALYZE_SOURCE(SOURCE)
    # -------------------------------------------------------------------------
    def test_23_integracao_analyze_source(self):
        source = (
            "public class Processador {\n"
            "    public void executar(int limite) {\n"
            "        int total = 0;\n"
            "        for (int i = 0; i < limite; i++) {\n"
            "            total += i;\n"
            "        }\n"
            "        return;\n"
            "    }\n"
            "}\n"
        )
        res = analyze_source(source)
        self.assertTrue(res.success)
        self.assertFalse(res.has_errors)
        self.assertIsInstance(res.ast, CompilationUnit)
        self.assertTrue(res.symbol_table.exists("Processador"))
        self.assertTrue(res.symbol_table.exists("executar"))
        self.assertTrue(res.symbol_table.exists("total"))

    # -------------------------------------------------------------------------
    # 24. AUSÊNCIA DE REGRESSÕES NOS TESTES ANTERIORES
    # -------------------------------------------------------------------------
    def test_24_ausencia_regressoes(self):
        # 24.1 Unidade vazia
        u1 = parse_java("")
        self.assertIsInstance(u1, CompilationUnit)
        self.assertEqual(u1.pretty(), "Program")

        # 24.2 Modo didático de fragmento
        u2 = parse_java("int x = 10; x = 20;")
        self.assertEqual(len(u2.statements), 2)

        # 24.3 Instrução vazia dentro de bloco
        source_empty = "public class A { void m() { ; } }"
        u3 = parse_java(source_empty)
        stmt = u3.type_declarations[0].members[0].body.statements[0]
        self.assertIsInstance(stmt, EmptyStatement)

    # -------------------------------------------------------------------------
    # 25. SWITCH / CASE / DEFAULT E VALIDAÇÃO SEMÂNTICA INTERNA
    # -------------------------------------------------------------------------
    def test_25_switch_case_e_default_com_analise_semantica(self):
        source = (
            "public class AvaliadorMenu {\n"
            "    public void processar(int opcao) {\n"
            "        int resultado = 0;\n"
            "        switch (opcao) {\n"
            "            case 1:\n"
            "                int bonus = 10;\n"
            "                resultado = opcao + bonus;\n"
            "                break;\n"
            "            case 2:\n"
            "                resultado = 20;\n"
            "                break;\n"
            "            default:\n"
            "                resultado = -1;\n"
            "                break;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros inesperados: {res.syntactic_error} | {res.semantic_errors}")
        stmt_switch = res.ast.type_declarations[0].members[0].body.statements[1]
        self.assertIsInstance(stmt_switch, SwitchStatement)
        self.assertEqual(len(stmt_switch.cases), 2)
        self.assertIsInstance(stmt_switch.cases[0], SwitchCase)
        self.assertIsNotNone(stmt_switch.default_block)
        self.assertIn("SwitchStatement", stmt_switch.pretty())
        self.assertIn("SwitchCase", stmt_switch.pretty())
        self.assertIn("Default", stmt_switch.pretty())

        # Verifica detecção semântica de variável não declarada dentro de um case
        source_invalido = (
            "public class AvaliadorErro {\n"
            "    public void processar(int opcao) {\n"
            "        switch (opcao) {\n"
            "            case 1:\n"
            "                naoDeclarada = 10;\n"
            "                break;\n"
            "            default:\n"
            "                outraNaoDeclarada = 20;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        res_err = analyze_source(source_invalido)
        self.assertFalse(res_err.success)
        self.assertEqual(len(res_err.semantic_errors), 2)
        erros_str = "\n".join(str(e) for e in res_err.semantic_errors)
        self.assertIn("naoDeclarada", erros_str)
        self.assertIn("outraNaoDeclarada", erros_str)


if __name__ == "__main__":
    unittest.main()
