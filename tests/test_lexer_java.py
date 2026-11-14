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

from src.compiler.token import Token, TokenType
from src.compiler.lexer import Lexer, LexicalError


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
        self.assertEqual(
            [t.type for t in tokens[:-1]],
            [TokenType.INT, TokenType.LONG, TokenType.LONG, TokenType.LONG],
        )
        self.assertEqual(tokens[0].lexeme, "1_000_000")
        self.assertEqual(tokens[3].lexeme, "9_999_999L")

    def test_inteiros_hexadecimais(self):
        source = "0x0 0x1A2B 0XFF 0xCAFE_BABE 0x10L"
        tokens = Lexer(source).tokenize()
        self.assertEqual(
            [t.type for t in tokens[:-1]],
            [TokenType.INT, TokenType.INT, TokenType.INT, TokenType.INT, TokenType.LONG],
        )

    def test_inteiros_binarios(self):
        source = "0b0 0b1010 0B11_00 0b1L"
        tokens = Lexer(source).tokenize()
        self.assertEqual(
            [t.type for t in tokens[:-1]],
            [TokenType.INT, TokenType.INT, TokenType.INT, TokenType.LONG],
        )

    def test_inteiros_octais(self):
        source = "0755 0123_456 077L"
        tokens = Lexer(source).tokenize()
        self.assertEqual(
            [t.type for t in tokens[:-1]],
            [TokenType.INT, TokenType.INT, TokenType.LONG],
        )

    def test_pontos_flutuantes_e_doubles(self):
        source = "3.14 .5 10. 1.23f 1.23F 2.718d 2.718D"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertIn(tok.type, (TokenType.DOUBLE, TokenType.FLOAT))
        self.assertEqual(tokens[0].type, TokenType.DOUBLE) # 3.14
        self.assertEqual(tokens[1].type, TokenType.DOUBLE) # .5
        self.assertEqual(tokens[2].type, TokenType.DOUBLE) # 10.
        self.assertEqual(tokens[3].type, TokenType.FLOAT)  # 1.23f
        self.assertEqual(tokens[4].type, TokenType.FLOAT)  # 1.23F
        self.assertEqual(tokens[5].type, TokenType.DOUBLE) # 2.718d
        self.assertEqual(tokens[6].type, TokenType.DOUBLE) # 2.718D

    def test_notacao_cientifica(self):
        source = "1e10 1.5e-3 2E+5 1e4f 3.0e-2d"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertIn(tok.type, (TokenType.DOUBLE, TokenType.FLOAT))
        self.assertEqual(tokens[0].type, TokenType.DOUBLE) # 1e10
        self.assertEqual(tokens[3].type, TokenType.FLOAT)  # 1e4f

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
        source = r"'\n' '\t' '\r' '\"' '\\' '\'' '\s' '\0'"
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].lexeme, "\n")
        self.assertEqual(tokens[1].lexeme, "\t")
        self.assertEqual(tokens[2].lexeme, "\r")
        self.assertEqual(tokens[3].lexeme, '"')
        self.assertEqual(tokens[4].lexeme, "\\")
        self.assertEqual(tokens[5].lexeme, "'")
        self.assertEqual(tokens[6].lexeme, " ")
        self.assertEqual(tokens[7].lexeme, "\0")

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
        source = r'"Linha 1\nLinha 2\t\"Aspas\"\s\u0042"'
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].type, TokenType.STRING_LITERAL)
        self.assertIn("Linha 1\nLinha 2\t\"Aspas\" B", tokens[0].lexeme)

    def test_escapes_genericos_em_char_e_string_sem_erro(self):
        tokens = Lexer(r"""'\s' '\d' "texto \s \q valido" """).tokenize()
        self.assertEqual(tokens[0].type, TokenType.CHAR_LITERAL)
        self.assertEqual(tokens[0].lexeme, " ")
        self.assertEqual(tokens[1].type, TokenType.CHAR_LITERAL)
        self.assertEqual(tokens[1].lexeme, r"\d")
        self.assertEqual(tokens[2].type, TokenType.STRING_LITERAL)
        self.assertIn(r"\q", tokens[2].lexeme)

    def test_text_block_java(self):
        source = '"""\n    linha 1\n    linha 2\n    """'
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].type, TokenType.STRING_LITERAL)
        self.assertIn("linha 1\n    linha 2", tokens[0].lexeme)


class TestLexerCaracteresInvalidosERecuperacao(unittest.TestCase):
    """Garante que caracteres inválidos geram erros registrados com tolerância a falhas."""

    def test_caracteres_estranhos_registrados_e_recuperados(self):
        # Caracteres genuinamente estranhos ao Java (cifrao '$' e underscore '_' sao validos)
        for ch in ['#', '`', '§', '°']:
            source = f"int x = {ch};"
            lexer = Lexer(source)
            tokens = lexer.tokenize()

            # O erro deve ser registrado na lista de erros sem interromper o lexer
            self.assertEqual(len(lexer.errors), 1, f"Deveria registrar 1 erro para {ch}")
            err = lexer.errors[0]
            self.assertEqual(err.character, ch)
            self.assertEqual(err.line, 1)
            self.assertEqual(err.column, 9)
            self.assertIn(f"Caractere inválido: {ch!r}", str(err))

            # Tolerância a falhas: o fluxo continua até EOF e retorna tokens válidos
            self.assertEqual([t.type for t in tokens], [
                TokenType.KEYWORD_INT,
                TokenType.IDENTIFIER,
                TokenType.ASSIGN,
                TokenType.SEMICOLON,
                TokenType.EOF
            ])
            self.assertEqual(tokens[-1].type, TokenType.EOF)

    def test_multiplos_erros_lexicos_recuperados_ate_eof(self):
        source = "int # a = 1 § 2 ` ;"
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        self.assertEqual(len(lexer.errors), 3)
        self.assertEqual(lexer.errors[0].character, '#')
        self.assertEqual(lexer.errors[0].column, 5)
        self.assertEqual(lexer.errors[1].character, '§')
        self.assertEqual(lexer.errors[1].column, 13)
        self.assertEqual(lexer.errors[2].character, '`')
        self.assertEqual(lexer.errors[2].column, 17)

        # Continuidade total até EOF
        lexemes = [t.lexeme for t in tokens]
        self.assertEqual(lexemes, ["int", "a", "=", "1", "2", ";", ""])
        self.assertEqual(tokens[-1].type, TokenType.EOF)

    def test_acesso_propriedades_e_dicionario_erro(self):
        lexer = Lexer("int ? @ # ;")
        lexer.tokenize()
        self.assertEqual(len(lexer.errors), 1)
        err = lexer.errors[0]
        self.assertEqual(err.line, 1)
        self.assertEqual(err.column, 9)
        self.assertEqual(err.character, "#")
        self.assertEqual(err["line"], 1)
        self.assertEqual(err["column"], 9)
        self.assertEqual(err["character"], "#")


class TestLexerIdentificadoresJavaAbrangentes(unittest.TestCase):
    """Testes específicos para identificadores válidos em Java (com '$' e '_')."""

    def test_identificadores_iniciados_por_cifrao(self):
        source = "$ $var $1 $foo_bar $$$"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertEqual(tok.type, TokenType.IDENTIFIER)
        self.assertEqual([t.lexeme for t in tokens[:-1]], ["$", "$var", "$1", "$foo_bar", "$$$"])

    def test_identificadores_iniciados_por_underscore(self):
        source = "_ _var _1 _foo_bar ___"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertEqual(tok.type, TokenType.IDENTIFIER)
        self.assertEqual([t.lexeme for t in tokens[:-1]], ["_", "_var", "_1", "_foo_bar", "___"])

    def test_identificadores_com_cifrao_e_underscore_intermediarios(self):
        source = "var$name my_var$1 Class$Inner total_$$$"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertEqual(tok.type, TokenType.IDENTIFIER)
        self.assertEqual([t.lexeme for t in tokens[:-1]], ["var$name", "my_var$1", "Class$Inner", "total_$$$"])


class TestLexerLiteraisJavaAvancados(unittest.TestCase):
    """Testes para todos os literais da linguagem Java."""

    def test_strings_com_escapes_octais(self):
        source = r'"\0 \033 \377 \7"'
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].type, TokenType.STRING_LITERAL)
        self.assertEqual(tokens[0].lexeme, "\0 \033 \377 \7")

    def test_char_com_escapes_octais(self):
        source = r"'\0' '\033' '\377' '\7'"
        tokens = Lexer(source).tokenize()
        self.assertEqual([t.type for t in tokens[:-1]], [TokenType.CHAR_LITERAL] * 4)
        self.assertEqual([t.lexeme for t in tokens[:-1]], ["\0", "\033", "\377", "\7"])

    def test_numeros_hexadecimais_ponto_flutuante(self):
        source = "0x1.0p0 0x1p-2 0x1.fp3f 0x0.8p1D"
        tokens = Lexer(source).tokenize()
        for tok in tokens[:-1]:
            self.assertIn(tok.type, (TokenType.DOUBLE, TokenType.FLOAT))
        self.assertEqual(tokens[0].type, TokenType.DOUBLE) # 0x1.0p0
        self.assertEqual(tokens[2].type, TokenType.FLOAT)  # 0x1.fp3f
        self.assertEqual([t.lexeme for t in tokens[:-1]], ["0x1.0p0", "0x1p-2", "0x1.fp3f", "0x0.8p1D"])

    def test_erro_octal_com_sufixo_long_e_digito_oito(self):
        with self.assertRaises(LexicalError):
            Lexer("089L").tokenize()

    def test_literais_float_double_completos_nao_quebram_no_ponto(self):
        # Garante que 3.1415 e 2.0 são lidos inteiramente como DOUBLE e não quebrados no ponto
        source = "3.1415 2.0 0.0 123.456789"
        tokens = Lexer(source).tokenize()
        self.assertEqual(len(tokens), 5) # 4 números + EOF
        self.assertEqual(tokens[0].type, TokenType.DOUBLE)
        self.assertEqual(tokens[0].lexeme, "3.1415")
        self.assertEqual(tokens[1].type, TokenType.DOUBLE)
        self.assertEqual(tokens[1].lexeme, "2.0")
        self.assertEqual(tokens[2].type, TokenType.DOUBLE)
        self.assertEqual(tokens[2].lexeme, "0.0")
        self.assertEqual(tokens[3].type, TokenType.DOUBLE)
        self.assertEqual(tokens[3].lexeme, "123.456789")
        self.assertEqual(tokens[4].type, TokenType.EOF)

        # Nenhum token DOT isolado deve existir
        self.assertNotIn(TokenType.DOT, [t.type for t in tokens])

    def test_regex_float_double_compilada(self):
        from src.compiler.lexer import FLOAT_DOUBLE_REGEX
        self.assertIsNotNone(FLOAT_DOUBLE_REGEX.match("3.1415"))
        self.assertIsNotNone(FLOAT_DOUBLE_REGEX.match("2.0"))
        self.assertIsNotNone(FLOAT_DOUBLE_REGEX.match(".5"))
        self.assertIsNotNone(FLOAT_DOUBLE_REGEX.match("1e10"))
        self.assertIsNotNone(FLOAT_DOUBLE_REGEX.match("1.23f"))

    def test_operadores_compostos_e_simples_completos(self):
        source = ">>= >>> >>>= <<= && || ++ -- != == <= >= += -= *= /= %= &= |= ^= << >>"
        tokens = Lexer(source).tokenize()
        esperados = [
            TokenType.RSHIFT_ASSIGN,
            TokenType.URSHIFT,
            TokenType.URSHIFT_ASSIGN,
            TokenType.LSHIFT_ASSIGN,
            TokenType.LOGICAL_AND,
            TokenType.LOGICAL_OR,
            TokenType.INCREMENT,
            TokenType.DECREMENT,
            TokenType.NOT_EQUAL,
            TokenType.EQUAL,
            TokenType.LESS_EQUAL,
            TokenType.GREATER_EQUAL,
            TokenType.PLUS_ASSIGN,
            TokenType.MINUS_ASSIGN,
            TokenType.STAR_ASSIGN,
            TokenType.SLASH_ASSIGN,
            TokenType.PERCENT_ASSIGN,
            TokenType.AND_ASSIGN,
            TokenType.OR_ASSIGN,
            TokenType.XOR_ASSIGN,
            TokenType.LSHIFT,
            TokenType.RSHIFT,
            TokenType.EOF
        ]
        self.assertEqual([t.type for t in tokens], esperados)

    def test_literal_hexadecimal_0x0F_classificado_como_int(self):
        """Verifica que '0x0F' e hexadecimais terminados em 'F'/'f' são classificados como INT/LONG e não float."""
        tokens = Lexer("0x0F 0X0F 0xFF 0x1A2B 0xCAFE_BABE 0x10L").tokenize()
        esperados = [
            TokenType.INT,
            TokenType.INT,
            TokenType.INT,
            TokenType.INT,
            TokenType.INT,
            TokenType.LONG,
        ]
        self.assertEqual([tok.type for tok in tokens[:-1]], esperados)
        for tok in tokens[:-1]:
            self.assertNotEqual(tok.type, TokenType.FLOAT)
            self.assertNotEqual(tok.type, TokenType.DOUBLE)

    def test_regex_hex_int_compilada(self):
        """Valida que HEX_INT_REGEX reconhece inteiros hexadecimais válidos e rejeita floats."""
        from src.compiler.lexer import HEX_INT_REGEX, classify_number
        self.assertIsNotNone(HEX_INT_REGEX.match("0x0F"))
        self.assertIsNotNone(HEX_INT_REGEX.match("0X0F"))
        self.assertIsNotNone(HEX_INT_REGEX.match("0xFF"))
        self.assertIsNotNone(HEX_INT_REGEX.match("0xCAFE_BABE"))
        self.assertIsNotNone(HEX_INT_REGEX.match("0x10L"))
        self.assertIsNone(HEX_INT_REGEX.match("3.1415"))
        self.assertIsNone(HEX_INT_REGEX.match("1.23f"))
        self.assertIsNone(HEX_INT_REGEX.match("0x1.0p0"))

        # Valida que classify_number dá precedência ao hex int sobre float
        self.assertEqual(classify_number("0x0F"), TokenType.INT)
        self.assertEqual(classify_number("0xFF"), TokenType.INT)
        self.assertEqual(classify_number("0x1.0p0"), TokenType.DOUBLE)
        self.assertEqual(classify_number("0x1.fp3f"), TokenType.FLOAT)

    def test_atribuicao_semantica_hexadecimal_int(self):
        """Valida que int x = 0x0F; é semanticamente aceito como int sem disparar falso erro de float."""
        from src.compiler.parser import Parser
        from src.compiler.semantic import SemanticAnalyzer
        from src.compiler.symbol_table import SymbolTable
        tokens = Lexer("int x = 0x0F;").tokenize()
        ast = Parser(tokens).parse()
        symbols = SymbolTable()
        errors = SemanticAnalyzer(symbols).analyze(ast)
        self.assertEqual(errors, [])

    def test_classificacao_long_e_demais_literais_numericos(self):
        """Valida INT, LONG, FLOAT, DOUBLE e alias LONG_LITERAL em todas as bases."""
        from src.compiler.lexer import classify_number
        self.assertIs(TokenType.LONG_LITERAL, TokenType.LONG)

        casos = [
            ("10", TokenType.INT),
            ("10L", TokenType.LONG),
            ("10l", TokenType.LONG),
            ("0x10L", TokenType.LONG),
            ("0b101L", TokenType.LONG),
            ("077L", TokenType.LONG),
            ("1.5f", TokenType.FLOAT),
            ("1.5", TokenType.DOUBLE),
        ]
        for lexema, esperado in casos:
            with self.subTest(lexema=lexema):
                toks = Lexer(lexema).tokenize()
                self.assertEqual(len(toks), 2)
                self.assertEqual(toks[0].type, esperado)
                self.assertEqual(toks[0].lexeme, lexema)
                self.assertEqual(classify_number(lexema), esperado)

    def test_numeros_em_expressoes_sem_espacos(self):
        """Garante que operadores adjacentes a literais numéricos continuam funcionando."""
        toks = Lexer("10+20L-1.5f*2.0").tokenize()
        self.assertEqual(
            [(t.type, t.lexeme) for t in toks[:-1]],
            [
                (TokenType.INT, "10"),
                (TokenType.PLUS, "+"),
                (TokenType.LONG, "20L"),
                (TokenType.MINUS, "-"),
                (TokenType.FLOAT, "1.5f"),
                (TokenType.STAR, "*"),
                (TokenType.DOUBLE, "2.0"),
            ],
        )

    def test_erros_lexicos_sufixos_e_caracteres_invalidos_apos_numero(self):
        """Rejeita sufixos duplicados ou caracteres alfanuméricos inválidos colados a números."""
        invalidos = ["10LL", "10fd", "10abc", "0b12", "0x10LL", "0b101LL", "0x1G", "1.5fx"]
        for codigo in invalidos:
            with self.subTest(codigo=codigo):
                with self.assertRaises(LexicalError):
                    Lexer(codigo).tokenize()


if __name__ == "__main__":
    unittest.main()
