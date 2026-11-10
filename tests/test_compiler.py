import os
import sys
import tempfile
import unittest
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.token import Token, TokenType
from src.lexer import Lexer, LexicalError
from src.parser import Parser, SyntacticError
from src.ast_nodes import Program, Declaration, Assignment, BinaryOp, Literal, Identifier
from src.symbol_table import SymbolTable
from src.semantic import SemanticAnalyzer, SemanticError
from src.main import read_source_file, run_file, analyze_source, AnalysisResult


class TestCompiladorOficial(unittest.TestCase):
    """Suíte oficial de testes da Etapa 2 (regressão obrigatória: Casos 1 a 26)."""

    def test_01_declaracao_simples_int(self):
        source = "int x;"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(ast.statements), 1)
        self.assertIsInstance(ast.statements[0], Declaration)
        self.assertEqual(ast.statements[0].name, "x")
        self.assertEqual(ast.statements[0].type_name, "int")
        self.assertIsNone(ast.statements[0].initializer)
        self.assertTrue(symbols.exists("x"))
        self.assertEqual(symbols.lookup("x")["type"], "int")

    def test_02_declaracao_com_inicializacao_int(self):
        source = "int x = 10;"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(ast.statements), 1)
        self.assertIsNotNone(ast.statements[0].initializer)

    def test_03_declaracao_simples_string(self):
        source = "String nome;"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 0)
        self.assertTrue(symbols.exists("nome"))
        self.assertEqual(symbols.lookup("nome")["type"], "String")

    def test_04_declaracao_com_inicializacao_string(self):
        source = 'String nome = "Gustavo";'
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 0)
        self.assertTrue(symbols.exists("nome"))
        self.assertEqual(symbols.lookup("nome")["type"], "String")

    def test_05_expressao_soma(self):
        source = "int x = 10 + 5;"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 0)
        self.assertIsInstance(ast.statements[0].initializer, BinaryOp)
        self.assertEqual(ast.statements[0].initializer.op, "+")

    def test_06_expressao_parenteses_e_subtracao(self):
        source = "int x = (10 + 5) - 2;"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 0)
        self.assertIsInstance(ast.statements[0].initializer, BinaryOp)
        self.assertEqual(ast.statements[0].initializer.op, "-")

    def test_07_uso_de_variavel_em_expressao(self):
        source = "int a = 10;\nint b = a + 5;"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 0)
        self.assertTrue(symbols.exists("a"))
        self.assertTrue(symbols.exists("b"))

    def test_08_atribuicao_pos_declaracao(self):
        source = "int x = 10;\nx = x - 2;"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(ast.statements), 2)
        self.assertIsInstance(ast.statements[1], Assignment)

    def test_09_caractere_invalido(self):
        source = "int x = 10 # 5;"
        lexer = Lexer(source)
        tokens = lexer.tokenize()

<<<<<<< HEAD
        # Tolerância a falhas: não interrompe com exceção, registra erro e continua até EOF
=======
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        self.assertEqual(len(lexer.errors), 1)
        err = lexer.errors[0]
        self.assertEqual(err.line, 1)
        self.assertEqual(err.column, 12)
        self.assertEqual(err.character, "#")
        self.assertIn("[ERRO LÉXICO]", str(err))
        self.assertIn("Caractere inválido: '#'", str(err))
<<<<<<< HEAD
=======

        # Tolerância a falhas: continua processando até EOF
        self.assertEqual([t.lexeme for t in tokens], ["int", "x", "=", "10", "5", ";", ""])
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        self.assertEqual(tokens[-1].type, TokenType.EOF)

    def test_10_string_nao_fechada(self):
        source = 'String nome = "Gustavo;'
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        self.assertEqual(len(lexer.errors), 1)
        err = lexer.errors[0]
        self.assertEqual(err.line, 1)
        self.assertEqual(err.column, 15)
        self.assertIn("[ERRO LÉXICO]", str(err))
        self.assertIn("String não fechada", str(err))
        self.assertEqual(tokens[-1].type, TokenType.EOF)

    def test_11_declaracao_sem_expressao(self):
        source = "int x = ;"
        tokens = Lexer(source).tokenize()
        parser = Parser(tokens)
        parser.parse()

        self.assertGreaterEqual(len(parser.errors), 1)
        err = parser.errors[0]
        self.assertEqual(err.line, 1)
        self.assertEqual(err.column, 9)
        self.assertEqual(err.found, ";")
        self.assertIn("[ERRO SINTÁTICO]", str(err))
        self.assertIn("Era esperado uma expressão após '='.", str(err))

    def test_12_atribuicao_sem_expressao(self):
        source = "x = ;"
        tokens = Lexer(source).tokenize()
        parser = Parser(tokens)
        parser.parse()

        self.assertGreaterEqual(len(parser.errors), 1)
        err = parser.errors[0]
        self.assertEqual(err.line, 1)
        self.assertEqual(err.column, 5)
        self.assertEqual(err.found, ";")
        self.assertIn("[ERRO SINTÁTICO]", str(err))
        self.assertIn("Era esperado uma expressão após '='.", str(err))

    def test_13_expressao_incompleta_no_eof(self):
        source = "x = 10 +"
        tokens = Lexer(source).tokenize()
        parser = Parser(tokens)
        parser.parse()

        self.assertGreaterEqual(len(parser.errors), 1)
        err = parser.errors[0]
        self.assertEqual(err.line, 1)
        self.assertEqual(err.found, "EOF")
        self.assertIn("Era esperado uma expressão após '+'.", str(err))

    def test_14_declaracao_sem_identificador(self):
        source = "int = 10;"
        tokens = Lexer(source).tokenize()
        parser = Parser(tokens)
        parser.parse()

        self.assertGreaterEqual(len(parser.errors), 1)
        err = parser.errors[0]
        self.assertEqual(err.line, 1)
        self.assertEqual(err.column, 5)
        self.assertEqual(err.found, "=")
        self.assertIn("Era esperado um identificador após o tipo 'int'.", str(err))

    def test_15_parentese_nao_fechado(self):
        source = "int x = (10 + 2;"
        tokens = Lexer(source).tokenize()
        parser = Parser(tokens)
        parser.parse()

        self.assertGreaterEqual(len(parser.errors), 1)
        err = parser.errors[0]
        self.assertEqual(err.line, 1)
        self.assertEqual(err.column, 16)
        self.assertEqual(err.found, ";")
        self.assertIn("Era esperado ')'.", str(err))

    def test_16_atribuicao_sem_igual(self):
        source = "x 10;"
        tokens = Lexer(source).tokenize()
        parser = Parser(tokens)
        parser.parse()

        self.assertGreaterEqual(len(parser.errors), 1)
        err = parser.errors[0]
        self.assertEqual(err.line, 1)
        self.assertEqual(err.column, 3)
        self.assertEqual(err.found, "10")
        self.assertIn("Era esperado '=' após o identificador 'x'.", str(err))

    def test_17_variavel_nao_declarada(self):
        source = "x = 10;"
        ast = Parser(Lexer(source).tokenize()).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 1)
        self.assertIn("[ERRO SEMÂNTICO]", str(errors[0]))
        self.assertIn("Variável 'x' não foi declarada.", str(errors[0]))
        self.assertEqual(errors[0].line, 1)

    def test_18_declaracao_duplicada(self):
        source = "int x;\nint x;"
        ast = Parser(Lexer(source).tokenize()).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 1)
        self.assertIn("[ERRO SEMÂNTICO]", str(errors[0]))
        self.assertIn("Variável 'x' declarada novamente", str(errors[0]))
        self.assertEqual(errors[0].line, 2)

    def test_19_atribuicao_incompativel(self):
        source = 'int x = "texto";'
        ast = Parser(Lexer(source).tokenize()).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 1)
        self.assertIn("Incompatibilidade de tipos", str(errors[0]))
        self.assertIn("não é possível atribuir String a 'x' do tipo int", str(errors[0]))

    def test_20_inicializacao_incompativel(self):
        source = "String nome = 10;"
        ast = Parser(Lexer(source).tokenize()).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertEqual(len(errors), 1)
        self.assertIn("Incompatibilidade de tipos", str(errors[0]))
        self.assertIn("não é possível atribuir int a 'nome' do tipo String", str(errors[0]))

    def test_21_operacao_aritmetica_incompativel_com_string(self):
        source = 'String nome = "abc";\nint x = nome + 10;'
        ast = Parser(Lexer(source).tokenize()).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertGreaterEqual(len(errors), 1)
        mensagens = "\n".join(str(e) for e in errors)
        self.assertIn("tipo 'String' não é suportado em operações aritméticas", mensagens)

    def test_22_multiplos_erros_na_mesma_entrada(self):
        source = (
            'int resultado = "texto";\n'
            'total = 10;\n'
            'x = y + 1;\n'
        )
        ast = Parser(Lexer(source).tokenize()).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)

        self.assertGreaterEqual(len(errors), 3)
        mensagens = "\n".join(str(e) for e in errors)
        self.assertIn("Incompatibilidade de tipos", mensagens)
        self.assertIn("total", mensagens)
        self.assertIn("x", mensagens)
        self.assertIn("y", mensagens)

    def test_23_arquivo_vazio(self):
        tokens = Lexer("").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)

        ast = Parser(tokens).parse()
        self.assertEqual(len(ast.statements), 0)
        self.assertEqual(ast.pretty(), "Program")

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".java") as tmp:
            tmp_path = tmp.name

        try:
            content, err = read_source_file(tmp_path)
            self.assertIsNone(err)
            self.assertEqual(content, "")
            exit_code = run_file(tmp_path)
            self.assertEqual(exit_code, 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_24_arquivo_inexistente(self):
        caminho = "arquivo_totalmente_inexistente_9999.java"
        content, err = read_source_file(caminho)
        self.assertIsNone(content)
        self.assertIn("[ERRO DE ENTRADA]", err)
        self.assertEqual(run_file(caminho), 1)

    def test_25_arquivo_encoding_invalido(self):
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".java") as tmp:
            tmp.write(b"\xff\xfe\x00\x80\x81\x92")
            tmp_path = tmp.name

        try:
            content, err = read_source_file(tmp_path)
            self.assertIsNone(content)
            self.assertIn("[ERRO DE ENTRADA]", err)
            self.assertEqual(run_file(tmp_path), 1)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_26_tabela_de_simbolos_atributos(self):
        st = SymbolTable()
        st.declare("x", "int", 1)
        st.declare("nome", "String", 2)

        # Palavras reservadas pré-carregadas conforme Barema AV3
        sym_int = st.lookup("int")
        self.assertIsNotNone(sym_int)
        self.assertEqual(sym_int["name"], "int")
        self.assertEqual(sym_int["category"], "palavra_reservada")
        self.assertEqual(sym_int["type"], "tipo")
        self.assertEqual(sym_int["line"], "-")
        self.assertEqual(sym_int["order"], 1)

        sym_str = st.lookup("String")
        self.assertIsNotNone(sym_str)
        self.assertEqual(sym_str["name"], "String")
        self.assertEqual(sym_str["category"], "tipo")
        self.assertEqual(sym_str["type"], "tipo")
        self.assertEqual(sym_str["line"], "-")
        self.assertEqual(sym_str["order"], 2)

        # Variáveis declaradas em seguida
        sym_x = st.lookup("x")
        self.assertEqual(sym_x["name"], "x")
        self.assertEqual(sym_x["category"], "variavel")
        self.assertEqual(sym_x["type"], "int")
        self.assertEqual(sym_x["line"], 1)
        self.assertEqual(sym_x["order"], 3)

        sym_nome = st.lookup("nome")
        self.assertEqual(sym_nome["order"], 4)


class TestEstresseERobustez(unittest.TestCase):
    """Testes exaustivos da Etapa 3: Estresse, entradas extremas, falhas e limites."""

    # -------------------------------------------------------------
    # 2. ENTRADAS EXTREMAS
    # -------------------------------------------------------------

    def test_27_apenas_espacos(self):
        tokens = Lexer("    \t  \t ").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)

    def test_28_apenas_quebras_de_linha(self):
        tokens = Lexer("\n\n\n\n\n").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)
        self.assertEqual(tokens[0].line, 6)

    def test_29_milhares_de_espacos_e_tabs(self):
        source = (" " * 5000) + ("\t" * 5000) + "int x = 10;"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        self.assertEqual(len(ast.statements), 1)

    def test_30_milhares_de_quebras_de_linha(self):
        source = ("\n" * 5000) + "int x = 10;"
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].line, 5001)
        ast = Parser(tokens).parse()
        self.assertEqual(len(ast.statements), 1)

    def test_31_identificador_gigante(self):
        nome_gigante = "var_" + ("a" * 3000)
        source = f"int {nome_gigante} = 10;\n{nome_gigante} = {nome_gigante} + 1;"
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[1].lexeme, nome_gigante)
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)
        self.assertEqual(len(errors), 0)
        self.assertTrue(symbols.exists(nome_gigante))

    def test_32_numero_gigante(self):
        num_gigante = "9" * 3000
        source = f"int x = {num_gigante};"
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[3].lexeme, num_gigante)
        ast = Parser(tokens).parse()
        self.assertEqual(len(ast.statements), 1)

    def test_33_string_gigante(self):
        str_gigante = "x" * 3000
        source = f'String s = "{str_gigante}";'
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[3].lexeme, str_gigante)
        ast = Parser(tokens).parse()
        self.assertEqual(len(ast.statements), 1)

    def test_34_string_vazia(self):
        source = 'String s = "";'
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[3].type, TokenType.STRING_LITERAL)
        self.assertEqual(tokens[3].lexeme, "")
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)
        self.assertEqual(len(errors), 0)

    def test_35_string_com_caracteres_especiais(self):
        chars = '!@#$%^&*()_+-=[]{}|;:,./<>?~`'
        source = f'String s = "{chars}";'
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[3].lexeme, chars)
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)
        self.assertEqual(len(errors), 0)

    def test_36_string_com_escapes(self):
        source = r'String s = "linha1\nlinha2\t\"aspas\"\\barra";'
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[3].type, TokenType.STRING_LITERAL)
        self.assertIn("linha1\nlinha2\t\"aspas\"\\barra", tokens[3].lexeme)
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)
        self.assertEqual(len(errors), 0)

    def test_37_expressao_muito_longa(self):
        partes = ["1"] * 500
        source = "int x = " + " + ".join(partes) + ";"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(ast.statements), 1)

    def test_38_muitas_declaracoes_sequenciais(self):
        linhas = [f"int v{i} = {i};" for i in range(1000)]
        source = "\n".join(linhas)
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(ast.statements), 1000)
        self.assertEqual(len([s for s in symbols.all() if s["category"] == "variavel"]), 1000)
        self.assertEqual(len(symbols.all()), 1002)

    # -------------------------------------------------------------
    # 3. TESTES DE CARACTERES INVÁLIDOS INDIVIDUAIS
    # -------------------------------------------------------------

    def test_39_caracteres_invalidos_individuais(self):
<<<<<<< HEAD
        chars_invalidos = ['#', '\\', '`']
=======
        # Caracteres que não pertencem ao léxico da linguagem Java
        chars_invalidos = ['#', '`', '\\', '§', '°']
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        for ch in chars_invalidos:
            source = f"int a = 1 {ch} 2;"
            lexer = Lexer(source)
            tokens = lexer.tokenize()
<<<<<<< HEAD
            self.assertEqual(len(lexer.errors), 1, msg=f"Falha ao registrar erro em '{ch}'")
=======
            self.assertEqual(len(lexer.errors), 1, msg=f"Falha ao registrar erro para '{ch}'")
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
            err = lexer.errors[0]
            self.assertEqual(err.character, ch)
            self.assertEqual(err.line, 1)
            self.assertEqual(err.column, 11)
            self.assertIn(f"Caractere inválido: {ch!r}", str(err))
            self.assertEqual(tokens[-1].type, TokenType.EOF)

<<<<<<< HEAD
    def test_39d_identificadores_com_cifrao_e_sublinhado(self):
        source = "int $orcamentoGlobal = 100;\nint _contador = $orcamentoGlobal + 1;\nint var$1_2 = _contador;"
        tokens = Lexer(source).tokenize()
        ids = [t.lexeme for t in tokens if t.type == TokenType.IDENTIFIER]
        self.assertEqual(ids, ["$orcamentoGlobal", "_contador", "$orcamentoGlobal", "var$1_2", "_contador"])
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)
        self.assertEqual(len(errors), 0)
        self.assertTrue(symbols.exists("$orcamentoGlobal"))
        self.assertTrue(symbols.exists("_contador"))
        self.assertTrue(symbols.exists("var$1_2"))

    def test_39e_char_literal_e_string_literal(self):
        source = r"""'Z' '\n' '\t' '\'' '\\' "texto" """
        tokens = Lexer(source).tokenize()
        self.assertEqual([t.type for t in tokens], [
            TokenType.CHAR_LITERAL,
            TokenType.CHAR_LITERAL,
            TokenType.CHAR_LITERAL,
            TokenType.CHAR_LITERAL,
            TokenType.CHAR_LITERAL,
            TokenType.STRING_LITERAL,
            TokenType.EOF,
        ])
        self.assertEqual(tokens[0].lexeme, "Z")
        self.assertEqual(tokens[1].lexeme, "\n")
        self.assertEqual(tokens[2].lexeme, "\t")
        self.assertEqual(tokens[3].lexeme, "'")
        self.assertEqual(tokens[4].lexeme, "\\")
        self.assertEqual(tokens[5].lexeme, "texto")

        # Literais de char inválidos registram erro sem interromper a execução
        for invalido in ["''", "'ab'", "'a", "'\\'"]:
            lexer = Lexer(invalido)
            lexer.tokenize()
            self.assertGreater(len(lexer.errors), 0, msg=f"Deveria registrar erro em: {invalido!r}")

    def test_39c_delimitadores_e_pontuacao_java(self):
        source = "{ ( [ ; , . @ ] ) } System.out.println 3.14 0xFF 0b1010 077"
        tokens = Lexer(source).tokenize()
        self.assertEqual([t.type for t in tokens], [
            TokenType.LBRACE,
            TokenType.LPAREN,
            TokenType.LBRACKET,
            TokenType.SEMICOLON,
            TokenType.COMMA,
            TokenType.DOT,
            TokenType.AT,
            TokenType.RBRACKET,
            TokenType.RPAREN,
            TokenType.RBRACE,
            TokenType.IDENTIFIER,
            TokenType.DOT,
            TokenType.IDENTIFIER,
            TokenType.DOT,
            TokenType.IDENTIFIER,
            TokenType.FLOAT_LITERAL,
            TokenType.HEX_LITERAL,
            TokenType.BINARY_LITERAL,
            TokenType.OCTAL_LITERAL,
            TokenType.EOF,
        ])
        self.assertEqual(tokens[15].lexeme, "3.14")
        self.assertEqual(tokens[16].lexeme, "0xFF")
        self.assertEqual(tokens[17].lexeme, "0b1010")
        self.assertEqual(tokens[18].lexeme, "077")

    def test_39b_comentarios_e_operador_divisao(self):
        # 1. Comentário de linha
        source_linha = "// Comentario inicial\nint x = 10; // Comentario no fim da linha\n"
        tokens_linha = Lexer(source_linha).tokenize()
        self.assertEqual([t.type for t in tokens_linha], [
            TokenType.KEYWORD_INT,
            TokenType.IDENTIFIER,
            TokenType.ASSIGN,
            TokenType.NUMBER,
            TokenType.SEMICOLON,
            TokenType.EOF,
        ])
        self.assertEqual(tokens_linha[0].line, 2)

        # 2. Comentário de bloco (múltiplas linhas)
        source_bloco = "/* Bloco\nde multiplas\nlinhas */\nint y = 20 /* inline */ / 2;"
        tokens_bloco = Lexer(source_bloco).tokenize()
        self.assertEqual([t.type for t in tokens_bloco], [
            TokenType.KEYWORD_INT,
            TokenType.IDENTIFIER,
            TokenType.ASSIGN,
            TokenType.NUMBER,
            TokenType.DIVIDE,
            TokenType.NUMBER,
            TokenType.SEMICOLON,
            TokenType.EOF,
        ])
        self.assertEqual(tokens_bloco[0].line, 4)
        self.assertEqual(tokens_bloco[4].lexeme, "/")

        # 3. Comentário de bloco não fechado registra erro léxico controlado sem interromper
        lexer_bloco = Lexer("int x = 10; /* comentario sem fim")
        lexer_bloco.tokenize()
        self.assertEqual(len(lexer_bloco.errors), 1)
=======
    def test_39_b_identificadores_com_cifrao_e_underscore(self):
        source = "int $var = 1; int _aux = 2; int x$y_z = 3; int $ = 4; int _ = 5;"
        tokens = Lexer(source).tokenize()
        ids = [t.lexeme for t in tokens if t.type == TokenType.IDENTIFIER]
        self.assertEqual(ids, ["$var", "_aux", "x$y_z", "$", "_"])
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a

    # -------------------------------------------------------------
    # 4. TESTES DE STRINGS MALFORMADAS
    # -------------------------------------------------------------

    def test_40_aspas_isoladas_e_incompletas(self):
        casos = [
            '"',
            '"\n"',
            'abc"',
            '"abc',
            '"abc\nint x = 10;',
            '"abc\nxyz',
            '"texto sem fim',
        ]
        for caso in casos:
            lexer = Lexer(caso)
            tokens = lexer.tokenize()
            self.assertGreater(len(lexer.errors), 0, msg=f"Deveria registrar erro em: {caso!r}")
            self.assertEqual(tokens[-1].type, TokenType.EOF)

    # -------------------------------------------------------------
    # 5. TESTES DE PARSER MALFORMADO (COMBINAÇÕES EXTREMAS)
    # -------------------------------------------------------------

    def test_41_combinacoes_sintaticas_malformadas(self):
        entradas_invalidas = [
            "=",
            "+",
            "-",
            "(",
            ")",
            "int",
            "String",
            "int ;",
            "String ;",
            "int =",
            "String =",
            "int x",
            "String nome",
            "x",
            "x =",
            "x = ;",
            "x = +",
            "x = -",
            "x = (",
            "x = (1",
            "x = 1)",
            "x = 1 2;",
            "x + 10;",
            "int x x;",
            "int x = 10 20;",
            "int int;",
            "String String;",
        ]
        for caso in entradas_invalidas:
            tokens = Lexer(caso).tokenize()
            parser = Parser(tokens)
            parser.parse()
            self.assertGreater(len(parser.errors), 0, msg=f"Deveria registrar erro sintático em: {caso!r}")

    # -------------------------------------------------------------
    # 6. TESTES SEMÂNTICOS DE MALFORMAÇÃO E TIPOS
    # -------------------------------------------------------------

    def test_42_combinacoes_semanticas_invalidas(self):
        casos = [
            ("x = 1;", "não foi declarada"),
            ("x = y + 1;", "não foi declarada"),
            ("int x = y;", "não foi declarada"),
            ("String nome = x;", "não foi declarada"),
            ('int x = "abc";', "Incompatibilidade de tipos"),
            ("String nome = 123;", "Incompatibilidade de tipos"),
            ("int x;\nint x;", "declarada novamente"),
            ("String nome;\nString nome;", "declarada novamente"),
            ('int x = 1;\nString s = "a";\nx = s;', "Incompatibilidade de tipos"),
            ('int x = 1;\nString s = "a";\ns = x;', "Incompatibilidade de tipos"),
            ('String nome = "abc";\nint x = nome - 10;', "não é suportado em operações aritméticas"),
            ('String nome = "abc";\nint x = nome + 10;', "não é suportado em operações aritméticas"),
        ]
        for source, esperado in casos:
            ast = Parser(Lexer(source).tokenize()).parse()
            symbols = SymbolTable()
            errors = SemanticAnalyzer(symbols).analyze(ast)
            self.assertGreater(len(errors), 0, msg=f"Esperava erro em: {source}")
            mensagens = "\n".join(str(e) for e in errors)
            self.assertIn(esperado, mensagens, msg=f"Esperava '{esperado}' em {mensagens}")

    # -------------------------------------------------------------
    # 7. PROGRESSO DO LEXER E PARSER (GARANTIA CONTRA LOOPS)
    # -------------------------------------------------------------

    def test_43_progresso_do_lexer(self):
        lexer = Lexer("int a = 10; @ ;")
        pos_anteriores = []
        try:
            tokens = []
            while lexer.pos < len(lexer.source):
                pos_anteriores.append(lexer.pos)
                if len(pos_anteriores) > 1:
                    self.assertGreater(pos_anteriores[-1], pos_anteriores[-2], "Lexer não avançou o cursor!")
                lexer.tokenize()
        except LexicalError:
            pass  # Encerrou com erro controlado, sem loop

    def test_44_progresso_do_parser(self):
        # Parser nunca deve entrar em loop infinito mesmo com tokens inesperados
        tokens = [
            Token(TokenType.NUMBER, "123", 1, 1),
            Token(TokenType.PLUS, "+", 1, 5),
            Token(TokenType.EOF, "", 1, 6)
        ]
        parser = Parser(tokens)
        parser.parse()
        self.assertGreater(len(parser.errors), 0)

    # -------------------------------------------------------------
    # 8. TESTES DE ARQUIVO E FORMATOS (CRLF, BOM, PERMISSÕES)
    # -------------------------------------------------------------

    def test_45_arquivo_caminho_vazio_ou_nulo(self):
        content, err = read_source_file("")
        self.assertIsNone(content)
        self.assertIn("Caminho do arquivo não pode ser vazio", err)

        content, err = read_source_file("   ")
        self.assertIsNone(content)
        self.assertIn("Caminho do arquivo não pode ser vazio", err)

    def test_46_arquivo_diretorio(self):
        content, err = read_source_file(".")
        self.assertIsNone(content)
        self.assertIn("O caminho informado é um diretório", err)

    def test_47_arquivo_com_bom(self):
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".java") as tmp:
            # UTF-8 BOM seguido de código válido
            tmp.write(b"\xef\xbb\xbfint x = 42;")
            tmp_path = tmp.name

        try:
            content, err = read_source_file(tmp_path)
            self.assertIsNone(err)
            self.assertIn("int x = 42;", content)
            exit_code = run_file(tmp_path)
            self.assertEqual(exit_code, 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_48_arquivo_com_crlf_e_lf(self):
        source = "int a = 10;\r\nint b = 20;\nint c = a + b;\r\n"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(ast.statements), 3)

    # -------------------------------------------------------------
    # 9. CLI EXECUÇÃO E SAÍDAS LIMPAS
    # -------------------------------------------------------------

    def test_49_cli_arquivo_valido(self):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".java") as tmp:
            tmp.write("int x = 10;\n")
            tmp_path = tmp.name
        try:
            code = run_file(tmp_path)
            self.assertEqual(code, 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_50_cli_arquivo_invalido(self):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".java") as tmp:
            tmp.write("int x = ;\n")
            tmp_path = tmp.name
        try:
            code = run_file(tmp_path)
            self.assertEqual(code, 1)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # -------------------------------------------------------------
    # 10. TESTE DE ISOLAMENTO ENTRE EXECUÇÕES CONSECUTIVAS
    # -------------------------------------------------------------

    def test_51_isolamento_entre_execucoes(self):
        codigos = [
            ("int x = 10;", True),
            ('String nome = "A";', True),
            ("x = 20;", False),  # 'x' não foi declarado nesta execução!
            ("int y = 30;", True),
        ]
        for codigo, esperado_sucesso in codigos:
            tokens = Lexer(codigo).tokenize()
            ast = Parser(tokens).parse()
            symbols = SymbolTable()
            errors = SemanticAnalyzer(symbols).analyze(ast)
            if esperado_sucesso:
                self.assertEqual(len(errors), 0, msg=f"Falhou em código que deveria ser válido: {codigo}")
            else:
                self.assertGreater(len(errors), 0, msg=f"Deveria falhar por isolamento: {codigo}")

    # -------------------------------------------------------------
    # 11. LIMITE DE RECURSÃO E ANINHAMENTO
    # -------------------------------------------------------------

    def test_52_limite_recursao_parenteses_profundos(self):
        # 250 parênteses aninhados excede o limite defensivo configurado (200)
        expr = ("(" * 250) + "10" + (")" * 250)
        source = f"int x = {expr};"
        tokens = Lexer(source).tokenize()
        parser = Parser(tokens)
        parser.parse()
        self.assertGreater(len(parser.errors), 0)
        err = parser.errors[0]
        self.assertIn("limite de aninhamento", str(err).lower())

    # -------------------------------------------------------------
    # 12. AST PRETTY PRINTING ROBUSTO
    # -------------------------------------------------------------

    def test_53_ast_pretty_estruturas_diversas(self):
        # Declaração sem inicialização
        d1 = Declaration("int", "x", 1)
        self.assertIn("Declaracao (int)", d1.pretty())

        # Declaração com inicialização
        d2 = Declaration("String", "s", 1, Literal("ola", "STRING"))
        self.assertIn("Declaracao (String)", d2.pretty())
        self.assertIn("Inicializador", d2.pretty())

        # Atribuição
        a = Assignment("x", 1, BinaryOp("+", Identifier("x"), Literal("1", "NUM")))
        self.assertIn("Atribuicao", a.pretty())
        self.assertIn("Expressao (+)", a.pretty())

        # Nós corrompidos ou com campos None não devem falhar
        d_corrupt = Declaration("int", "x", 1, initializer="invalido")
        self.assertIsInstance(d_corrupt.pretty(), str)

        prog = Program([d1, d2, a])
        self.assertIn("Program", prog.pretty())

    # -------------------------------------------------------------
    # 13. TESTES AUTOMATIZADOS EM LOTE (200+ COMBINAÇÕES DE STRESS)
    # -------------------------------------------------------------

    def test_54_lote_entradas_malformadas_fuzzing(self):
        elementos = [
            "int", "String", "x", "y1", "_abc", "10", "0", '"texto"', '""',
            "=", "+", "-", ";", "(", ")", "@", "#", "$", " ", "\n", "\t"
        ]
        # Gera mais de 220 combinações variadas de tokens e fragmentos
        entradas_geradas = []
        for e1 in ["int", "x", "=", "+", "(", "@", '"a"']:
            for e2 in [";", "10", "y", ")", "-", "String", ""]:
                for e3 in ["", " = 5;", " + ", "(10)", " @", " \n "]:
                    entradas_geradas.append(f"{e1} {e2}{e3}")

        self.assertGreaterEqual(len(entradas_geradas), 200)

        for entrada in entradas_geradas:
            try:
                tokens = Lexer(entrada).tokenize()
                parser = Parser(tokens)
                ast = parser.parse()
                symbols = SymbolTable()
                SemanticAnalyzer(symbols).analyze(ast)
            except (LexicalError, SyntacticError):
                # Erro esperado e controlado
                pass
            except Exception as e:
                self.fail(f"Exceção não tratada na entrada {entrada!r}: {type(e).__name__}: {e}")


class TestIntegracaoGUIEAPI(unittest.TestCase):
    """Testes de integração para a API do compilador (analyze_source) e camada GUI."""

    def test_55_analyze_source_api_sucesso(self):
        source = "int a = 10;\nString s = \"ok\";\n"
        res = analyze_source(source)
        self.assertTrue(res.success)
        self.assertFalse(res.has_errors)
        self.assertEqual(len(res.tokens), 11)
        self.assertIsNotNone(res.ast)
        self.assertIsNotNone(res.symbol_table)
        self.assertEqual(len(res.symbol_table.all()), 4)
        self.assertEqual(len(res.semantic_errors), 0)

    def test_56_analyze_source_api_erro_lexico(self):
        source = "int a = 10 # 5;"
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(res.has_errors)
        self.assertIsNotNone(res.lexical_error)
        self.assertIsNone(res.ast)
        self.assertGreater(len(res.tokens), 0)

    def test_57_analyze_source_api_erro_sintatico(self):
        source = "x = ;"
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(res.has_errors)
        self.assertIsNotNone(res.syntactic_error)
        self.assertIsNone(res.ast)

    def test_58_analyze_source_api_erro_semantico(self):
        source = "int a = \"texto\";"
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(res.has_errors)
        self.assertIsNotNone(res.ast)
        self.assertIsNotNone(res.symbol_table)
        self.assertGreater(len(res.semantic_errors), 0)

    def test_59_analyze_source_api_vazio(self):
        res = analyze_source("")
        self.assertTrue(res.success)
        self.assertFalse(res.has_errors)
        self.assertEqual(len(res.tokens), 1)
        self.assertEqual(res.tokens[0].type, TokenType.EOF)

    def test_60_gui_instancia_e_ciclo_completo(self):
        # Testa instanciação da GUI e execução de métodos sem abrir janela modal
        try:
            import tkinter as tk
            from src.gui import CompiladorGUI
            app = CompiladorGUI()
            app.update_idletasks()

            # 0. Verifica estado inicial completamente vazio
            self.assertEqual(app.editor.get("1.0", tk.END).strip(), "")
            self.assertEqual(len(app.tokens_tree.get_children()), 0)
            self.assertEqual(len(app.symbols_tree.get_children()), 0)
            self.assertEqual(app.ast_text.get("1.0", tk.END).strip(), "")
            self.assertIn("Aguardando análise", app.semantic_text.get("1.0", tk.END))
            self.assertIn("Aguardando análise", app.errors_text.get("1.0", tk.END))
            self.assertEqual(app.status_var.get(), "Pronto")

            # 1. Análise válida
            app.editor.delete("1.0", tk.END)
            app.editor.insert("1.0", 'int a = 10;\nString s = "teste";\n')
            app.on_analyze()
            self.assertEqual(len(app.tokens_tree.get_children()), 11)
            self.assertEqual(len(app.symbols_tree.get_children()), 4)
            self.assertIn("Program", app.ast_text.get("1.0", tk.END))

            # 1.1 Copiar Tudo
            copied = app.on_copy_all()
            self.assertIn("=== CÓDIGO FONTE ===", copied)
            self.assertIn("=== TOKENS ===", copied)
            self.assertIn("=== TABELA DE SÍMBOLOS ===", copied)
            self.assertIn("=== AST ===", copied)
            self.assertIn("=== SEMÂNTICA ===", copied)
            self.assertIn("=== ERROS ===", copied)
            self.assertEqual(app.status_var.get(), "Tudo copiado para a área de transferência!")

            # 2. Re-análise sem vazamento ou acúmulo de estado
            app.on_analyze()
            self.assertEqual(len(app.tokens_tree.get_children()), 11)
            self.assertEqual(len(app.symbols_tree.get_children()), 4)

            # 3. Análise com erro léxico
            app.editor.delete("1.0", tk.END)
            app.editor.insert("1.0", "int x = 10 # 5;")
            app.on_analyze()
            self.assertIn("[ERRO LÉXICO]", app.errors_text.get("1.0", tk.END))

            # 4. Análise com erro sintático
            app.editor.delete("1.0", tk.END)
            app.editor.insert("1.0", "x = ;")
            app.on_analyze()
            self.assertIn("[ERRO SINTÁTICO]", app.errors_text.get("1.0", tk.END))

            # 5. Análise com erro semântico
            app.editor.delete("1.0", tk.END)
            app.editor.insert("1.0", 'int x = "texto";')
            app.on_analyze()
            self.assertIn("[ERRO SEMÂNTICO]", app.errors_text.get("1.0", tk.END))

            # 6. Limpar
            app.on_clear()
            self.assertEqual(len(app.tokens_tree.get_children()), 0)
            self.assertEqual(len(app.symbols_tree.get_children()), 0)

            app.destroy()
        except tk.TclError:
            # Em ambientes sem display/X11 disponível
            pass

    def test_61_tabela_de_simbolos_sem_duplicacao_palavra_reservada(self):
        source = 'int x = 10;\nint y = 20;\nString s1 = "a";\nString s2 = "b";\n'
        res = analyze_source(source)
        self.assertTrue(res.success)
        names = [s["name"] for s in res.symbol_table.all()]
        self.assertEqual(names.count("int"), 1)
        self.assertEqual(names.count("String"), 1)
        self.assertEqual(len(res.symbol_table.all()), 6)

    def test_62_tabela_de_simbolos_barema_completo(self):
        source = 'int x = 10;\nString nome = "Gustavo";\n'
        res = analyze_source(source)
        all_syms = res.symbol_table.all()
        self.assertEqual(len(all_syms), 4)

        # Ordem 1: int
        self.assertEqual(all_syms[0]["order"], 1)
        self.assertEqual(all_syms[0]["name"], "int")
        self.assertEqual(all_syms[0]["category"], "palavra_reservada")
        self.assertEqual(all_syms[0]["type"], "tipo")
        self.assertEqual(all_syms[0]["line"], "-")

        # Ordem 2: String
        self.assertEqual(all_syms[1]["order"], 2)
        self.assertEqual(all_syms[1]["name"], "String")
        self.assertEqual(all_syms[1]["category"], "tipo")
        self.assertEqual(all_syms[1]["type"], "tipo")
        self.assertEqual(all_syms[1]["line"], "-")

        # Ordem 3: x
        self.assertEqual(all_syms[2]["order"], 3)
        self.assertEqual(all_syms[2]["name"], "x")
        self.assertEqual(all_syms[2]["category"], "variavel")
        self.assertEqual(all_syms[2]["type"], "int")
        self.assertEqual(all_syms[2]["line"], 1)

        # Ordem 4: nome
        self.assertEqual(all_syms[3]["order"], 4)
        self.assertEqual(all_syms[3]["name"], "nome")
        self.assertEqual(all_syms[3]["category"], "variavel")
        self.assertEqual(all_syms[3]["type"], "String")
        self.assertEqual(all_syms[3]["line"], 2)

    def test_63_estrutura_java_completa_com_skip_no_parser(self):
        source = """
        // Comentário de cabeçalho
        package br.edu.compilador;
        import java.util.*;

        /* Comentário de bloco
           em múltiplas linhas */
        public class TesteManual {
            public static void main(String[] args) {
                int _contador = 10;
                double $orcamentoGlobal = 1500.75;
                char status = 'Z';
                String nome = "Gustavo";

                if (_contador > 0) {
                    _contador = _contador + 5;
                    System.out.println(nome);
                }

                while (_contador < 20) {
                    _contador++;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros inesperados: {res.lexical_error} | {res.syntactic_error} | {res.semantic_errors}")
        self.assertIsNotNone(res.ast)
        self.assertEqual(len(res.ast.statements), 3)  # PackageNode, ImportNode, ClassNode
        self.assertIn("Classe (public class TesteManual)", res.ast.pretty())
        self.assertIn("Metodo (public static void main(String[] args))", res.ast.pretty())
        self.assertTrue(res.symbol_table.exists("_contador"))
        self.assertTrue(res.symbol_table.exists("$orcamentoGlobal"))
        self.assertTrue(res.symbol_table.exists("status"))
        self.assertTrue(res.symbol_table.exists("nome"))

    def test_64_precedencia_expressoes_e_panic_mode(self):
        source = """
        public class Calculadora {
            public static int executar(int base) {
                int x = 10 + 2 * 3;
                int y = (x << 1) & 0xFF | 0b1010 ^ 077;
                boolean ativo = x >= 10 && y != 0 || !false;
                do {
                    x += 1;
                } while (x < 20);
                for (int i = 0; i < 5; i++) {
                    y -= i;
                }
                return x + y + base;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.syntactic_error} | {res.semantic_errors}")
        self.assertTrue(res.symbol_table.exists("x"))
        self.assertTrue(res.symbol_table.exists("y"))
        self.assertTrue(res.symbol_table.exists("ativo"))
        self.assertTrue(res.symbol_table.exists("i"))

    def test_65_switch_try_catch_arrays_e_concatenacao(self):
        source = """
        package app.core;
        import java.io.*;

        public class ProcessadorDados extends Base implements Runnable {
            public static void main(String args[]) {
                int[] valores = new int[5];
                valores[0] = 10;
                int primeiro = valores[0];
                double convertido = (double) primeiro;
                String msg = "Valor: " + primeiro;
                msg += " pronto";

                switch (primeiro) {
                    case 10:
                        valores[0] += 5;
                        break;
                    default:
                        valores[0] = 0;
                        break;
                }

                try {
                    System.out.println("Processando: " + msg);
                } catch (Exception e) {
                    System.out.println(e);
                } finally {
                    primeiro--;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.lexical_error} | {res.syntactic_error} | {res.semantic_errors}")
        pretty_ast = res.ast.pretty()
        self.assertIn("Switch", pretty_ast)
        self.assertIn("Try", pretty_ast)
        self.assertIn("Catch (Exception e)", pretty_ast)
        self.assertIn("Finally", pretty_ast)
        self.assertIn("AcessoArray", pretty_ast)
        self.assertIn("Atribuicao (+=)", pretty_ast)

    def test_66_ast_nodes_completos_e_panic_mode_parcial(self):
        from src.ast_nodes import (
            ClassDecl,
            MethodDecl,
            Block,
            IfStmt,
            WhileStmt,
            ForStmt,
            DoWhileStmt,
            ReturnStmt,
            BreakStmt,
            ContinueStmt,
            MethodCall,
            UnaryOp,
            CompoundAssign,
            ArrayAccess,
        )
        # Verifica exportação de todos os nós solicitados e recuperação em Modo Pânico
        source = """
        public class Demo {
            public void rodar() {
                int validoAntes = 10;
                int erroSintatico = ;
                int validoDepois = 20;
                validoDepois += validoAntes;
            }
        }
        """
        tokens = Lexer(source).tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        self.assertEqual(len(parser.errors), 1)
        # Mesmo com erro na linha intermediária, a AST parcial contém a classe, método e comandos válidos
        cls_node = ast.statements[0]
        self.assertIsInstance(cls_node, ClassDecl)
        method_node = cls_node.members[0]
        self.assertIsInstance(method_node, MethodDecl)
        self.assertIsInstance(method_node.body, Block)
        # 'validoAntes', 'validoDepois' e 'validoDepois += validoAntes' foram preservados na AST parcial
        self.assertGreaterEqual(len(method_node.body.statements), 2)
        self.assertTrue(any(isinstance(s, CompoundAssign) for s in method_node.body.statements))


class TestPromocaoImplicitaWidening(unittest.TestCase):
    """Testes específicos para promoção implícita (widening) e literais double/float."""

    def test_atribuicao_int_para_double_aceita(self):
        source = "double x = 10; double y = 42; y = 100;"
        res = analyze_source(source)
        self.assertEqual(len(res.semantic_errors), 0, f"Erros inesperados: {res.semantic_errors}")
        self.assertTrue(res.success)

    def test_atribuicao_literal_double_aceita(self):
        source = "double pi = 3.1415; double d = 2.0;"
        res = analyze_source(source)
        self.assertEqual(len(res.semantic_errors), 0, f"Erros inesperados: {res.semantic_errors}")
        self.assertTrue(res.success)

    def test_operacoes_mistas_int_double_promovidas_para_double(self):
        source = """
        int a = 10;
        double b = 2.5;
        double soma = a + b;
        double sub = b - a;
        double mult = a * b;
        double div = a / b;
        """
        res = analyze_source(source)
        self.assertEqual(len(res.semantic_errors), 0, f"Erros inesperados: {res.semantic_errors}")
        self.assertTrue(res.success)

    def test_atribuicao_invalida_double_para_int_rejeitada(self):
        source = "double d = 3.1415;\nint x = d;"
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("não é possível atribuir double a 'x' do tipo int" in err for err in res.semantic_errors))

    def test_operacao_mista_atribuida_a_int_rejeitada(self):
        source = "int a = 10;\ndouble b = 2.5;\nint c = a + b;"
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("não é possível atribuir double a 'c' do tipo int" in err for err in res.semantic_errors))


if __name__ == "__main__":
    unittest.main()
