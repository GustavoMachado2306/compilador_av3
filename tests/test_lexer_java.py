"""
Suíte de testes dedicada para o analisador léxico de Java (Fase A).
Cobre:
- Comentários (linha, bloco, Javadoc e erros de fechamento)
- Delimitadores e pontuação
- Operadores e máxima correspondência (maximal munch)
- Palavras-chave completas e literais (true, false, null)
- Números (decimais, hexadecimais, binários, octais, ponto flutuante, notação científica, sufixos, underscores e erros)
- Literais de texto e caracteres (escapes válidos, Unicode e erros de malformação)
"""

import unittest
from pathlib import Path
import sys

# Garante acesso ao pacote src
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.token import Token, TokenType
from src.lexer import Lexer, LexicalError


class TestLexerEspacosEComentarios(unittest.TestCase):
    """Testes para o item 4.1: Espaços, quebras de linha e comentários."""

    def test_comentario_de_linha_simples(self):
        source = "// Este é um comentário\nint x = 10;"
        tokens = Lexer(source).tokenize()
        self.assertEqual(len(tokens), 6)
        self.assertEqual(tokens[0].type, TokenType.KEYWORD_INT)
        self.assertEqual(tokens[0].line, 2)
        self.assertEqual(tokens[0].column, 1)

    def test_comentario_de_linha_no_fim_do_arquivo(self):
        source = "int x = 10; // Fim do comando"
        tokens = Lexer(source).tokenize()
        self.assertEqual(len(tokens), 6)
        self.assertEqual(tokens[4].type, TokenType.SEMICOLON)
        self.assertEqual(tokens[5].type, TokenType.EOF)

    def test_comentario_de_bloco_uma_linha(self):
        source = "int /* comentário inline */ x = 10;"
        tokens = Lexer(source).tokenize()
        self.assertEqual(len(tokens), 6)
        self.assertEqual(tokens[0].type, TokenType.KEYWORD_INT)
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[1].lexeme, "x")

    def test_comentario_de_bloco_multilinha(self):
        source = "/*\n * Comentário de múltiplas linhas\n * Linha 3\n */\nint total = 100;"
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].type, TokenType.KEYWORD_INT)
        self.assertEqual(tokens[0].line, 5)
        self.assertEqual(tokens[0].column, 1)

    def test_comentario_javadoc(self):
        source = "/**\n * Documentação Javadoc da classe\n * @author Gustavo\n */\nclass Teste {}"
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].type, TokenType.KEYWORD_CLASS)
        self.assertEqual(tokens[0].line, 5)

    def test_codigo_dentro_de_comentario_ignorado(self):
        source = "/* int a = 10; @ # $ * / */ int b = 20;"
        tokens = Lexer(source).tokenize()
        self.assertEqual(len(tokens), 6)
        self.assertEqual(tokens[0].type, TokenType.KEYWORD_INT)
        self.assertEqual(tokens[1].lexeme, "b")

    def test_comentario_de_bloco_nao_fechado_lanca_erro(self):
        source = "/* comentário sem fechamento antes do fim"
        with self.assertRaises(LexicalError) as cm:
            Lexer(source).tokenize()
        self.assertIn("Comentário de bloco não fechado", str(cm.exception))


class TestLexerDelimitadores(unittest.TestCase):
    """Testes para o item 4.2: Delimitadores e pontuação."""

    def test_todos_os_delimitadores_individuais(self):
        source = "( ) { } [ ] ; , . @ ? :"
        tokens = Lexer(source).tokenize()
        tipos_esperados = [
            TokenType.LPAREN, TokenType.RPAREN,
            TokenType.LBRACE, TokenType.RBRACE,
            TokenType.LBRACKET, TokenType.RBRACKET,
            TokenType.SEMICOLON, TokenType.COMMA,
            TokenType.DOT, TokenType.AT,
            TokenType.QUESTION, TokenType.COLON,
            TokenType.EOF
        ]
        self.assertEqual([t.type for t in tokens], tipos_esperados)

    def test_delimitadores_contiguos(self):
        source = "(){}[];,.@?:"
        tokens = Lexer(source).tokenize()
        self.assertEqual(len(tokens), 13)
        self.assertEqual(tokens[0].type, TokenType.LPAREN)
        self.assertEqual(tokens[1].type, TokenType.RPAREN)
        self.assertEqual(tokens[9].type, TokenType.AT)


class TestLexerOperadores(unittest.TestCase):
    """Testes para o item 4.3: Operadores e maximal munch."""

    def test_operadores_de_atribuicao_composta(self):
        source = "= += -= *= /= %= &= |= ^= <<= >>= >>>="
        tokens = Lexer(source).tokenize()
        esperados = [
            TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
            TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN, TokenType.PERCENT_ASSIGN,
            TokenType.AND_ASSIGN, TokenType.OR_ASSIGN, TokenType.XOR_ASSIGN,
            TokenType.LSHIFT_ASSIGN, TokenType.RSHIFT_ASSIGN, TokenType.URSHIFT_ASSIGN,
            TokenType.EOF
        ]
        self.assertEqual([t.type for t in tokens], esperados)

    def test_operadores_relacionais_e_igualdade(self):
        source = "== != < <= > >="
        tokens = Lexer(source).tokenize()
        esperados = [
            TokenType.EQUAL, TokenType.NOT_EQUAL,
            TokenType.LESS, TokenType.LESS_EQUAL,
            TokenType.GREATER, TokenType.GREATER_EQUAL,
            TokenType.EOF
        ]
        self.assertEqual([t.type for t in tokens], esperados)

    def test_operadores_logicos_e_bitwise(self):
        source = "&& || ! & | ^ ~"
        tokens = Lexer(source).tokenize()
        esperados = [
            TokenType.LOGICAL_AND, TokenType.LOGICAL_OR, TokenType.LOGICAL_NOT,
            TokenType.BITWISE_AND, TokenType.BITWISE_OR, TokenType.BITWISE_XOR,
            TokenType.BITWISE_NOT, TokenType.EOF
        ]
        self.assertEqual([t.type for t in tokens], esperados)

    def test_shifts_e_operadores_especiais(self):
        source = "<< >> >>> -> :: ..."
        tokens = Lexer(source).tokenize()
        esperados = [
            TokenType.LSHIFT, TokenType.RSHIFT, TokenType.URSHIFT,
            TokenType.ARROW, TokenType.DOUBLE_COLON, TokenType.ELLIPSIS,
            TokenType.EOF
        ]
        self.assertEqual([t.type for t in tokens], esperados)

    def test_incremento_e_decremento(self):
        source = "++ --"
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].type, TokenType.INCREMENT)
        self.assertEqual(tokens[1].type, TokenType.DECREMENT)

    def test_maximal_munch_operadores_adjacentes(self):
        # Em Java, 'a+++b' deve ser 'a' '++' '+' 'b'
        source = "a+++b"
        tokens = Lexer(source).tokenize()
        self.assertEqual([t.type for t in tokens], [
            TokenType.IDENTIFIER,
            TokenType.INCREMENT,
            TokenType.PLUS,
            TokenType.IDENTIFIER,
            TokenType.EOF
        ])

    def test_distincao_entre_maior_e_shift(self):
        source = "x >>> 2 > 1"
        tokens = Lexer(source).tokenize()
        self.assertEqual([t.type for t in tokens], [
            TokenType.IDENTIFIER,
            TokenType.URSHIFT,
            TokenType.NUMBER,
            TokenType.GREATER,
            TokenType.NUMBER,
            TokenType.EOF
        ])


class TestLexerPalavrasChaveELiterais(unittest.TestCase):
    """Testes para o item 4.4: Palavras-chave e literais de Java."""

    def test_todas_as_cinquenta_palavras_chave_java(self):
        keywords_str = (
            "abstract assert boolean break byte "
            "case catch char class const continue "
            "default do double else enum extends "
            "final finally float for if implements "
            "import instanceof int interface long "
            "native new package private protected "
            "public return short static strictfp "
            "super switch synchronized this throw "
            "throws transient try void volatile while"
        )
        tokens = Lexer(keywords_str).tokenize()
        for tok in tokens[:-1]:
            self.assertTrue(tok.type.name.startswith("KEYWORD_"), f"Falha na palavra {tok.lexeme}")

    def test_literais_booleanos_e_nulo(self):
        source = "true false null"
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].type, TokenType.BOOLEAN_LITERAL)
        self.assertEqual(tokens[1].type, TokenType.BOOLEAN_LITERAL)
        self.assertEqual(tokens[2].type, TokenType.NULL_LITERAL)

    def test_identificadores_que_contem_palavras_chave(self):
        source = "classRoom international booleanFlag nullable"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertEqual(tok.type, TokenType.IDENTIFIER)


class TestLexerNumeros(unittest.TestCase):
    """Testes para o item 4.5: Literais numéricos, bases e notação científica."""

    def test_inteiros_decimais(self):
        source = "0 42 123456789"
        tokens = Lexer(source).tokenize()
        self.assertEqual([t.lexeme for t in tokens[:-1]], ["0", "42", "123456789"])

    def test_inteiros_decimais_com_underscores_e_sufixo_long(self):
        source = "1_000_000 100L 50l 9_999_999L"
        tokens = Lexer(source).tokenize()
        self.assertEqual([t.type for t in tokens[:-1]], [TokenType.NUMBER] * 4)
        self.assertEqual(tokens[0].lexeme, "1_000_000")
        self.assertEqual(tokens[3].lexeme, "9_999_999L")

    def test_inteiros_hexadecimais(self):
        source = "0x0 0x1A2B 0XFF 0xCAFE_BABE 0x10L"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertEqual(tok.type, TokenType.NUMBER)

    def test_inteiros_binarios(self):
        source = "0b0 0b1010 0B11_00 0b1L"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertEqual(tok.type, TokenType.NUMBER)

    def test_inteiros_octais(self):
        source = "0755 0123_456 077L"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertEqual(tok.type, TokenType.NUMBER)

    def test_pontos_flutuantes_e_doubles(self):
        source = "3.14 .5 10. 1.23f 1.23F 2.718d 2.718D"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertEqual(tok.type, TokenType.NUMBER)

    def test_notacao_cientifica(self):
        source = "1e10 1.5e-3 2E+5 1e4f 3.0e-2d"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertEqual(tok.type, TokenType.NUMBER)

    def test_erro_hex_sem_digitos(self):
        with self.assertRaises(LexicalError):
            Lexer("0x;").tokenize()

    def test_erro_binario_sem_digitos(self):
        with self.assertRaises(LexicalError):
            Lexer("0b;").tokenize()

    def test_erro_underscore_ao_final_do_numero(self):
        with self.assertRaises(LexicalError):
            Lexer("100_").tokenize()

    def test_erro_underscore_apos_prefixo_hex(self):
        with self.assertRaises(LexicalError):
            Lexer("0x_123").tokenize()

    def test_erro_notacao_cientifica_sem_expoente(self):
        with self.assertRaises(LexicalError):
            Lexer("1e").tokenize()

    def test_erro_sufixo_long_em_float(self):
        with self.assertRaises(LexicalError):
            Lexer("3.14L").tokenize()

    def test_erro_octal_com_digitos_oito_ou_nove(self):
        with self.assertRaises(LexicalError):
            Lexer("089").tokenize()


class TestLexerStringsECaracteres(unittest.TestCase):
    """Testes para o item 4.5: Literais char e strings com escapes."""

    def test_char_literal_simples(self):
        source = "'a' 'Z' '0'"
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].type, TokenType.CHAR_LITERAL)
        self.assertEqual(tokens[0].lexeme, "a")
        self.assertEqual(tokens[1].lexeme, "Z")

    def test_char_literal_com_escapes(self):
        source = r"'\n' '\t' '\\' '\'' '\0'"
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].lexeme, "\n")
        self.assertEqual(tokens[1].lexeme, "\t")
        self.assertEqual(tokens[2].lexeme, "\\")
        self.assertEqual(tokens[3].lexeme, "'")
        self.assertEqual(tokens[4].lexeme, "\0")

    def test_char_literal_unicode(self):
        source = r"'\u0041'"  # 'A'
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].type, TokenType.CHAR_LITERAL)
        self.assertEqual(tokens[0].lexeme, "A")

    def test_erro_char_vazio(self):
        with self.assertRaises(LexicalError) as cm:
            Lexer("''").tokenize()
        self.assertIn("vazio", str(cm.exception))

    def test_erro_char_multiplos_caracteres(self):
        with self.assertRaises(LexicalError):
            Lexer("'ab'").tokenize()

    def test_erro_char_nao_fechado(self):
        with self.assertRaises(LexicalError):
            Lexer("'a\n").tokenize()

    def test_string_com_escapes_e_unicode(self):
        source = r'"Linha 1\nLinha 2\t\"Aspas\" \u0042"'
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].type, TokenType.STRING_LITERAL)
        self.assertIn("Linha 1\nLinha 2\t\"Aspas\" B", tokens[0].lexeme)

    def test_erro_string_escape_invalido(self):
        with self.assertRaises(LexicalError) as cm:
            Lexer(r'"texto \q invalido"').tokenize()
        self.assertIn("Sequência de escape inválida", str(cm.exception))


class TestLexerCaracteresInvalidos(unittest.TestCase):
    """Garante que caracteres genuinamente estranhos ao Java geram erro léxico."""

    def test_caracteres_estranhos_rejeitados(self):
        for ch in ['#', '`', '$', '§', '°']:
            with self.assertRaises(LexicalError):
                Lexer(f"int x = {ch};").tokenize()


if __name__ == "__main__":
    unittest.main()
