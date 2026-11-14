"""
Módulo do Analisador Léxico (Lexer) do Compilador Java (AV3).
Responsável por transformar o código-fonte em um fluxo de tokens,
reconhecendo comentários, delimitadores, operadores, palavras-chave,
literais booleanos/nulos, números inteiros/reais e literais de texto/char.
"""

import re
from typing import List, Optional
from .token import Token, TokenType

# =============================================================================
# EXPRESSÕES REGULARES DE LITERAIS NUMÉRICOS JAVA
# A regra de validação de hexadecimal (HEX_INT_REGEX) é definida e executada
# ANTES da regra de float/double para garantir que sufixos/dígitos como 'F'/'f'
# ou 'D'/'d' (ex: '0x0F', '0xFF') não acionem a tipagem de ponto flutuante por engano.
# =============================================================================

# Regra 1: Literais inteiros hexadecimais (iniciam com 0x ou 0X, seguidos de 0-9 e a-f/A-F)
HEX_INT_REGEX = re.compile(
    r"^0[xX][0-9a-fA-F]+(?:_[0-9a-fA-F]+)*[lL]?$"
)
HEX_REGEX = HEX_INT_REGEX
HEX_INTEGER_REGEX = HEX_INT_REGEX
HEXADECIMAL_REGEX = HEX_INT_REGEX

# Regra 2: Literais de ponto flutuante (float / double)
FLOAT_DOUBLE_REGEX = re.compile(
    r"""
    ^ (
        # Formato decimal com ponto (ex: 3.1415, 2.0, 10.)
        \d+(?:_\d+)* \. (?:\d+(?:_\d+)*)? (?:[eE][+-]?\d+(?:_\d+)*)? [fFdD]?
        |
        # Formato iniciado diretamente por ponto (ex: .5, .5f, .5e-3)
        \. \d+(?:_\d+)* (?:[eE][+-]?\d+(?:_\d+)*)? [fFdD]?
        |
        # Notação científica sem ponto (ex: 1e10, 2E+5)
        \d+(?:_\d+)* [eE][+-]?\d+(?:_\d+)* [fFdD]?
        |
        # Inteiro com sufixo explícito float/double (ex: 10f, 10d)
        \d+(?:_\d+)* [fFdD]
        |
        # Hexadecimal de ponto flutuante com expoente binário obrigatório (ex: 0x1.0p0, 0x1p-2, 0x1.fp3f)
        0[xX] (?:
            [0-9a-fA-F]+(?:_[0-9a-fA-F]+)* \. (?:[0-9a-fA-F]+(?:_[0-9a-fA-F]+)*)?
            |
            [0-9a-fA-F]+(?:_[0-9a-fA-F]+)*
            |
            \. [0-9a-fA-F]+(?:_[0-9a-fA-F]+)*
        ) [pP][+-]?\d+(?:_\d+)* [fFdD]?
    ) $
    """,
    re.VERBOSE
)
FLOAT_REGEX = FLOAT_DOUBLE_REGEX
DOUBLE_REGEX = FLOAT_DOUBLE_REGEX


def classify_number(lexeme: str) -> TokenType:
    """
    Classifica um lexema numérico de acordo com a precedência estrita de regras Java.
    A validação da regra de hexadecimal (HEX_INT_REGEX) ocorre ANTES da regra de float/double,
    assegurando que literais como '0x0F' sejam tipados como INT e não como float.
    """
    # 1. Regra de Hexadecimal Inteiro ANTES de float/double
    if HEX_INT_REGEX.match(lexeme):
        return TokenType.LONG if lexeme.endswith(('l', 'L')) else TokenType.INT
    # 2. Regra de Ponto Flutuante (Float / Double)
    if FLOAT_DOUBLE_REGEX.match(lexeme):
        return TokenType.FLOAT if lexeme.endswith(('f', 'F')) else TokenType.DOUBLE
    # 3. Demais inteiros (decimais, binários, octais)
    return TokenType.LONG if lexeme.endswith(('l', 'L')) else TokenType.INT

# =============================================================================
# SEÇÃO 1: MAPEAMENTO DE PALAVRAS-CHAVE E LITERAIS JAVA
# =============================================================================
KEYWORDS = {
    # Palavras-chave originais do subconjunto didático
    "int": TokenType.KEYWORD_INT,

    # Palavras-chave completas do Java (Fase A)
    "abstract": TokenType.KEYWORD_ABSTRACT,
    "assert": TokenType.KEYWORD_ASSERT,
    "boolean": TokenType.KEYWORD_BOOLEAN,
    "break": TokenType.KEYWORD_BREAK,
    "byte": TokenType.KEYWORD_BYTE,
    "case": TokenType.KEYWORD_CASE,
    "catch": TokenType.KEYWORD_CATCH,
    "char": TokenType.KEYWORD_CHAR,
    "class": TokenType.KEYWORD_CLASS,
    "const": TokenType.KEYWORD_CONST,
    "continue": TokenType.KEYWORD_CONTINUE,
    "default": TokenType.KEYWORD_DEFAULT,
    "do": TokenType.KEYWORD_DO,
    "double": TokenType.KEYWORD_DOUBLE,
    "else": TokenType.KEYWORD_ELSE,
    "enum": TokenType.KEYWORD_ENUM,
    "extends": TokenType.KEYWORD_EXTENDS,
    "final": TokenType.KEYWORD_FINAL,
    "finally": TokenType.KEYWORD_FINALLY,
    "float": TokenType.KEYWORD_FLOAT,
    "for": TokenType.KEYWORD_FOR,
    "if": TokenType.KEYWORD_IF,
    "implements": TokenType.KEYWORD_IMPLEMENTS,
    "import": TokenType.KEYWORD_IMPORT,
    "instanceof": TokenType.KEYWORD_INSTANCEOF,
    "interface": TokenType.KEYWORD_INTERFACE,
    "long": TokenType.KEYWORD_LONG,
    "native": TokenType.KEYWORD_NATIVE,
    "new": TokenType.KEYWORD_NEW,
    "package": TokenType.KEYWORD_PACKAGE,
    "private": TokenType.KEYWORD_PRIVATE,
    "protected": TokenType.KEYWORD_PROTECTED,
    "public": TokenType.KEYWORD_PUBLIC,
    "return": TokenType.KEYWORD_RETURN,
    "short": TokenType.KEYWORD_SHORT,
    "static": TokenType.KEYWORD_STATIC,
    "strictfp": TokenType.KEYWORD_STRICTFP,
    "super": TokenType.KEYWORD_SUPER,
    "switch": TokenType.KEYWORD_SWITCH,
    "synchronized": TokenType.KEYWORD_SYNCHRONIZED,
    "this": TokenType.KEYWORD_THIS,
    "throw": TokenType.KEYWORD_THROW,
    "throws": TokenType.KEYWORD_THROWS,
    "transient": TokenType.KEYWORD_TRANSIENT,
    "try": TokenType.KEYWORD_TRY,
    "void": TokenType.KEYWORD_VOID,
    "volatile": TokenType.KEYWORD_VOLATILE,
    "while": TokenType.KEYWORD_WHILE,
}

# Literais especiais tratados na fase léxica
SPECIAL_LITERALS = {
    "true": TokenType.BOOLEAN_LITERAL,
    "false": TokenType.BOOLEAN_LITERAL,
    "null": TokenType.NULL_LITERAL,
}


# =============================================================================
# SEÇÃO 2: ESTRUTURA DE ERRO LÉXICO PADRONIZADA
# =============================================================================
class LexicalError(Exception):
    """
    Exceção estruturada para falhas na análise léxica.
    Preserva a mensagem, linha, coluna, caractere problemático e tokens obtidos até o erro.
    """
    def __init__(self, message: str, line: int, column: int, character: Optional[str] = None, tokens: Optional[list] = None):
        self.message = message
        self.line = line
        self.column = column
        self.character = character
        self.tokens = list(tokens) if tokens is not None else []
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        return f"[ERRO LÉXICO]\nLinha {self.line}, coluna {self.column}:\n{self.message}"

    def __getitem__(self, key: str):
        if key in ("line", "column", "character", "message", "tokens"):
            return getattr(self, key)
        raise KeyError(key)

    def keys(self):
        return ("line", "column", "character", "message", "tokens")

    def __iter__(self):
        yield from ("line", "column", "character", "message", "tokens")

    def to_dict(self):
        return {
            "line": self.line,
            "column": self.column,
            "character": self.character,
            "message": self.message,
        }


# =============================================================================
# SEÇÃO 3: CLASSE PRINCIPAL DO ANALISADOR LÉXICO (LEXER)
# =============================================================================
class Lexer:
    """
    Analisador léxico para Java incremental (Fase A).
    Suporta espaços, quebras de linha (CRLF e LF), comentários de linha, bloco e Javadoc,
    delimitadores, operadores de tamanho variável (longest match), números e textos.
    Possui recuperação e tolerância a falhas para caracteres inválidos.
    """
    HEX_INT_REGEX = HEX_INT_REGEX
    FLOAT_DOUBLE_REGEX = FLOAT_DOUBLE_REGEX
    classify_number = staticmethod(classify_number)

    def __init__(self, source: str):
        self.source = source if source is not None else ""
        self.pos = 0          # Posição absoluta do ponteiro no texto
        self.line = 1         # Linha atual (inicia em 1)
        self.column = 1       # Coluna atual (inicia em 1)
        self.tokens = []      # Lista de tokens acumulados
        self.errors = []      # Lista de erros léxicos acumulados

    # -------------------------------------------------------------------------
    # 3.1 MÉTODOS AUXILIARES DE NAVEGAÇÃO E INSPEÇÃO
    # -------------------------------------------------------------------------
    def _is_at_end(self) -> bool:
        """Verifica se o cursor atingiu o final do código-fonte."""
        return self.pos >= len(self.source)

    def _peek(self, offset: int = 0) -> str:
        """Olha o caractere à frente sem consumir o ponteiro."""
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return ""

    def _match(self, expected: str) -> bool:
        """Verifica se a sequência esperada coincide com os próximos caracteres."""
        if self.source.startswith(expected, self.pos):
            self.pos += len(expected)
            self.column += len(expected)
            return True
        return False

    # -------------------------------------------------------------------------
    # 3.2 FLUXO PRINCIPAL DE TOKENIZAÇÃO
    # -------------------------------------------------------------------------
    def tokenize(self) -> List[Token]:
        """
        Executa a varredura completa da entrada e retorna a lista de tokens até EOF.
        Ao esbarrar em um caractere inválido, salva o erro (com linha, coluna
        e o caractere problemático), avança o ponteiro ignorando o caractere inválido
        e continua processando o restante do código até o final (EOF).
        """
        tokens = []
        self.errors = []
        self.tokens = []

        while not self._is_at_end():
            c = self._peek()

            # -----------------------------------------------------------------
            # 3.2.1 Caractere BOM (Byte Order Mark) UTF-8
            # -----------------------------------------------------------------
            if c == '\ufeff':
                self.pos += 1
                continue

            # -----------------------------------------------------------------
            # 3.2.2 Quebras de linha e CRLF
            # -----------------------------------------------------------------
            if c == '\r':
                self.pos += 1
                if not self._is_at_end() and self._peek() == '\n':
                    self.pos += 1
                self.line += 1
                self.column = 1
                continue

            if c == '\n':
                self.pos += 1
                self.line += 1
                self.column = 1
                continue

            # -----------------------------------------------------------------
            # 3.2.3 Espaços em branco e tabulações
            # -----------------------------------------------------------------
            if c in ' \t':
                self.pos += 1
                self.column += 1
                continue

            # -----------------------------------------------------------------
            # 3.2.4 Comentários: de linha (//), de bloco (/* */) e Javadoc (/** */)
            # -----------------------------------------------------------------
            if c == '/' and self._peek(1) == '/':
                # Comentário de linha: consome até o fim da linha ou EOF
                self.pos += 2
                self.column += 2
                while not self._is_at_end() and self._peek() not in ('\r', '\n'):
                    self.pos += 1
                    self.column += 1
                continue

            if c == '/' and self._peek(1) == '*':
                # Comentário de bloco ou Javadoc
                start_line = self.line
                start_col = self.column
                self.pos += 2
                self.column += 2
                closed = False

                while not self._is_at_end():
                    ch = self._peek()
                    if ch == '\r':
                        self.pos += 1
                        if not self._is_at_end() and self._peek() == '\n':
                            self.pos += 1
                        self.line += 1
                        self.column = 1
                    elif ch == '\n':
                        self.pos += 1
                        self.line += 1
                        self.column = 1
                    elif ch == '*' and self._peek(1) == '/':
                        self.pos += 2
                        self.column += 2
                        closed = True
                        break
                    else:
                        self.pos += 1
                        self.column += 1

                if not closed:
                    self.tokens = list(tokens)
                    raise LexicalError(
                        "Comentário de bloco não fechado (esperado '*/' antes do fim do arquivo).",
                        start_line,
                        start_col,
                        tokens=tokens
                    )
                continue

            # -----------------------------------------------------------------
            # 3.2.5 Identificadores e Palavras-chave (permite '$' e '_')
            # -----------------------------------------------------------------
            if c.isalpha() or c in ('_', '$'):
                start_line = self.line
                start_col = self.column
                start_pos = self.pos

                while not self._is_at_end() and (self._peek().isalnum() or self._peek() in ('_', '$')):
                    self.pos += 1
                    self.column += 1

                lexeme = self.source[start_pos:self.pos]

                # Classificação entre palavra-chave, literal especial ou identificador comum
                if lexeme in SPECIAL_LITERALS:
                    token_type = SPECIAL_LITERALS[lexeme]
                elif lexeme in KEYWORDS:
                    token_type = KEYWORDS[lexeme]
                else:
                    token_type = TokenType.IDENTIFIER

                tokens.append(Token(token_type, lexeme, start_line, start_col))
                continue

            # -----------------------------------------------------------------
            # 3.2.6 Números (Inteiros, Hex, Bin, Oct, Reais com ponto/expoente)
            # -----------------------------------------------------------------
            if c.isdigit() or (c == '.' and self._peek(1).isdigit()):
                tok = self._lex_number(tokens)
                tokens.append(tok)
                continue

            # -----------------------------------------------------------------
            # 3.2.7 Literais de Texto (Strings delimitadas por aspas duplas)
            # -----------------------------------------------------------------
            if c == '"':
                tok = self._lex_string(tokens)
                tokens.append(tok)
                continue

            # -----------------------------------------------------------------
            # 3.2.8 Literais de Caractere (Chars delimitados por aspas simples)
            # -----------------------------------------------------------------
            if c == "'":
                tok = self._lex_char(tokens)
                tokens.append(tok)
                continue

            # -----------------------------------------------------------------
            # 3.2.9 Operadores e Delimitadores com Correspondência do Mais Longo
            # -----------------------------------------------------------------
            start_col = self.column
            start_line = self.line

            # Operadores de 4 caracteres
            if self._match(">>>="):
                tokens.append(Token(TokenType.URSHIFT_ASSIGN, ">>>=", start_line, start_col))
                continue

            # Operadores de 3 caracteres
            if self._match(">>>"):
                tokens.append(Token(TokenType.URSHIFT, ">>>", start_line, start_col))
                continue
            if self._match("<<="):
                tokens.append(Token(TokenType.LSHIFT_ASSIGN, "<<=", start_line, start_col))
                continue
            if self._match(">>="):
                tokens.append(Token(TokenType.RSHIFT_ASSIGN, ">>=", start_line, start_col))
                continue
            if self._match("..."):
                tokens.append(Token(TokenType.ELLIPSIS, "...", start_line, start_col))
                continue

            # Operadores de 2 caracteres
            two_char_ops = {
                "++": TokenType.INCREMENT,
                "--": TokenType.DECREMENT,
                "+=": TokenType.PLUS_ASSIGN,
                "-=": TokenType.MINUS_ASSIGN,
                "*=": TokenType.STAR_ASSIGN,
                "/=": TokenType.SLASH_ASSIGN,
                "%=": TokenType.PERCENT_ASSIGN,
                "&=": TokenType.AND_ASSIGN,
                "|=": TokenType.OR_ASSIGN,
                "^=": TokenType.XOR_ASSIGN,
                "==": TokenType.EQUAL,
                "!=": TokenType.NOT_EQUAL,
                "<=": TokenType.LESS_EQUAL,
                ">=": TokenType.GREATER_EQUAL,
                "&&": TokenType.LOGICAL_AND,
                "||": TokenType.LOGICAL_OR,
                "<<": TokenType.LSHIFT,
                ">>": TokenType.RSHIFT,
                "->": TokenType.ARROW,
                "::": TokenType.DOUBLE_COLON,
            }
            matched_two = False
            for op_str, op_type in two_char_ops.items():
                if self._match(op_str):
                    tokens.append(Token(op_type, op_str, start_line, start_col))
                    matched_two = True
                    break
            if matched_two:
                continue

            # Delimitadores e Operadores de 1 caractere
            one_char_symbols = {
                '=': TokenType.ASSIGN,
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                '*': TokenType.STAR,
                '/': TokenType.SLASH,
                '%': TokenType.PERCENT,
                '<': TokenType.LESS,
                '>': TokenType.GREATER,
                '!': TokenType.LOGICAL_NOT,
                '&': TokenType.BITWISE_AND,
                '|': TokenType.BITWISE_OR,
                '^': TokenType.BITWISE_XOR,
                '~': TokenType.BITWISE_NOT,
                '?': TokenType.QUESTION,
                ':': TokenType.COLON,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                '{': TokenType.LBRACE,
                '}': TokenType.RBRACE,
                '[': TokenType.LBRACKET,
                ']': TokenType.RBRACKET,
                ';': TokenType.SEMICOLON,
                ',': TokenType.COMMA,
                '.': TokenType.DOT,
                '@': TokenType.AT,
            }
            if c in one_char_symbols:
                tokens.append(Token(one_char_symbols[c], c, start_line, start_col))
                self.pos += 1
                self.column += 1
                continue

            # -----------------------------------------------------------------
            # 3.2.10 Caractere Inválido (Tolerância a Falhas / Recuperação de Erro)
            # -----------------------------------------------------------------
            col = self.column
            problem_char = c
            self.pos += 1
            self.column += 1

            err = LexicalError(
                f"Caractere inválido: {problem_char!r}.",
                self.line,
                col,
                character=problem_char,
                tokens=list(tokens)
            )
            self.errors.append(err)
            continue

        # Token final de encerramento do arquivo
        tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        self.tokens = tokens
        return tokens

    # -------------------------------------------------------------------------
    # 3.3 RECONHECIMENTO DE NÚMEROS E VALIDAÇÃO DE SUFIXOS E UNDERSCORES
    # -------------------------------------------------------------------------
    def _validate_number_boundary(
        self, current_tokens: list, lexeme: str, start_line: int
    ) -> None:
        """Garante que não haja sufixos ou caracteres alfanuméricos inválidos colados ao literal numérico."""
        if not self._is_at_end():
            next_ch = self._peek()
            if next_ch.isalnum() or next_ch == '_':
                self.tokens = list(current_tokens)
                raise LexicalError(
                    f"Literal numérico malformado: caractere/sufixo inválido '{next_ch}' após '{lexeme}'.",
                    start_line,
                    self.column,
                    tokens=current_tokens,
                )

    def _lex_number(self, current_tokens: list) -> Token:
        """
        Processa inteiros decimais, hexadecimais (0x), binários (0b), octais (0),
        números reais (float/double), notação científica e underscores numéricos.
        """
        start_line = self.line
        start_col = self.column
        start_pos = self.pos

        # Caso 1: Hexadecimal (0x / 0X)
        if self._peek() == '0' and self._peek(1) in ('x', 'X'):
            self.pos += 2
            self.column += 2

            # Underscore não pode vir logo após o prefixo (0x_...)
            if self._peek() == '_':
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "Underscore não permitido imediatamente após prefixo '0x'.",
                    start_line,
                    start_col + 2,
                    tokens=current_tokens
                )

            hex_digits = 0
            last_was_underscore = False
            has_hex_dot = False
            has_hex_p = False

            while not self._is_at_end():
                ch = self._peek()
                if ch in "0123456789abcdefABCDEF":
                    hex_digits += 1
                    last_was_underscore = False
                    self.pos += 1
                    self.column += 1
                elif ch == '_':
                    last_was_underscore = True
                    self.pos += 1
                    self.column += 1
                elif ch == '.' and not has_hex_dot and not has_hex_p:
                    if self._peek(1) == '.' and self._peek(2) == '.':
                        break
                    if last_was_underscore:
                        self.tokens = list(current_tokens)
                        raise LexicalError(
                            "Underscore não permitido antes do ponto decimal.",
                            start_line,
                            self.column - 1,
                            tokens=current_tokens
                        )
                    has_hex_dot = True
                    self.pos += 1
                    self.column += 1
                    if self._peek() == '_':
                        self.tokens = list(current_tokens)
                        raise LexicalError(
                            "Underscore não permitido após o ponto decimal.",
                            start_line,
                            self.column,
                            tokens=current_tokens
                        )
                elif ch in ('p', 'P') and not has_hex_p:
                    if last_was_underscore:
                        self.tokens = list(current_tokens)
                        raise LexicalError(
                            "Underscore não permitido antes do indicador de expoente 'p'.",
                            start_line,
                            self.column - 1,
                            tokens=current_tokens
                        )
                    has_hex_p = True
                    self.pos += 1
                    self.column += 1
                    if self._peek() in ('+', '-'):
                        self.pos += 1
                        self.column += 1
                    exp_digits = 0
                    while not self._is_at_end() and self._peek().isdigit():
                        exp_digits += 1
                        self.pos += 1
                        self.column += 1
                    if exp_digits == 0:
                        self.tokens = list(current_tokens)
                        raise LexicalError(
                            "Notação científica malformada: esperado ao menos um dígito no expoente.",
                            start_line,
                            self.column,
                            tokens=current_tokens
                        )
                    break
                else:
                    break

            if hex_digits == 0:
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "Literal hexadecimal malformado: nenhum dígito após '0x'.",
                    start_line,
                    start_col,
                    tokens=current_tokens
                )

            if last_was_underscore:
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "Underscore não permitido ao final do literal hexadecimal.",
                    start_line,
                    self.column - 1,
                    tokens=current_tokens
                )

            if has_hex_dot and not has_hex_p:
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "Ponto flutuante hexadecimal deve conter expoente binário 'p' ou 'P'.",
                    start_line,
                    start_col,
                    tokens=current_tokens
                )

            if has_hex_p:
                if self._peek() in ('f', 'F', 'd', 'D'):
                    self.pos += 1
                    self.column += 1
                elif self._peek() in ('l', 'L'):
                    self.tokens = list(current_tokens)
                    raise LexicalError(
                        "Sufixo 'L' não é permitido em literais de ponto flutuante.",
                        start_line,
                        self.column,
                        tokens=current_tokens
                    )
            else:
                # Sufixo opcional de Long (L ou l)
                if self._peek() in ('L', 'l'):
                    self.pos += 1
                    self.column += 1

            lexeme = self.source[start_pos:self.pos]
            self._validate_number_boundary(current_tokens, lexeme, start_line)

            # -----------------------------------------------------------------
            # REGRA 1: Validação de Hexadecimal Inteiro ANTES de Float/Double.
            # Garante que '0x0F', '0xFF', etc. sejam classificados como INT/LONG,
            # impedindo que o dígito ou sufixo 'F'/'f' acione tipagem float por engano.
            # -----------------------------------------------------------------
            if HEX_INT_REGEX.match(lexeme):
                tok_type = TokenType.LONG if lexeme.endswith(('l', 'L')) else TokenType.INT
                return Token(tok_type, lexeme, start_line, start_col)

            if has_hex_p or FLOAT_DOUBLE_REGEX.match(lexeme):
                tok_type = TokenType.FLOAT if lexeme.endswith(('f', 'F')) else TokenType.DOUBLE
                return Token(tok_type, lexeme, start_line, start_col)

            tok_type = TokenType.LONG if lexeme.endswith(('l', 'L')) else TokenType.INT
            return Token(tok_type, lexeme, start_line, start_col)

        # Caso 2: Binário (0b / 0B)
        if self._peek() == '0' and self._peek(1) in ('b', 'B'):
            self.pos += 2
            self.column += 2

            # Underscore não pode vir logo após o prefixo (0b_...)
            if self._peek() == '_':
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "Underscore não permitido imediatamente após prefixo '0b'.",
                    start_line,
                    start_col + 2,
                    tokens=current_tokens
                )

            bin_digits = 0
            last_was_underscore = False
            while not self._is_at_end():
                ch = self._peek()
                if ch in ('0', '1'):
                    bin_digits += 1
                    last_was_underscore = False
                    self.pos += 1
                    self.column += 1
                elif ch == '_':
                    last_was_underscore = True
                    self.pos += 1
                    self.column += 1
                else:
                    break

            if bin_digits == 0:
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "Literal binário malformado: nenhum dígito após '0b'.",
                    start_line,
                    start_col,
                    tokens=current_tokens
                )

            if last_was_underscore:
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "Underscore não permitido ao final do literal binário.",
                    start_line,
                    self.column - 1,
                    tokens=current_tokens
                )

            # Sufixo opcional de Long (L ou l)
            if self._peek() in ('L', 'l'):
                self.pos += 1
                self.column += 1

            lexeme = self.source[start_pos:self.pos]
            self._validate_number_boundary(current_tokens, lexeme, start_line)
            tok_type = TokenType.LONG if lexeme.endswith(('l', 'L')) else TokenType.INT
            return Token(tok_type, lexeme, start_line, start_col)

        # Caso 3: Decimal, Octal ou Ponto Flutuante
        has_dot = False
        has_exp = False
        last_was_underscore = False

        # Se começou diretamente com ponto decimal (.5)
        if self._peek() == '.':
            has_dot = True
            self.pos += 1
            self.column += 1
            if self._peek() == '_':
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "Underscore não permitido imediatamente após o ponto decimal.",
                    start_line,
                    self.column,
                    tokens=current_tokens
                )

        while not self._is_at_end():
            ch = self._peek()

            if ch.isdigit():
                last_was_underscore = False
                self.pos += 1
                self.column += 1

            elif ch == '_':
                # Underscore não pode seguir outro ponto ou expoente diretamente
                last_was_underscore = True
                self.pos += 1
                self.column += 1

            elif ch == '.' and not has_dot and not has_exp:
                if last_was_underscore:
                    self.tokens = list(current_tokens)
                    raise LexicalError(
                        "Underscore não permitido antes do ponto decimal.",
                        start_line,
                        self.column - 1,
                        tokens=current_tokens
                    )
                # Verifica se não é reticências (...)
                if self._peek(1) == '.' and self._peek(2) == '.':
                    break
                has_dot = True
                self.pos += 1
                self.column += 1
                if self._peek() == '_':
                    self.tokens = list(current_tokens)
                    raise LexicalError(
                        "Underscore não permitido após o ponto decimal.",
                        start_line,
                        self.column,
                        tokens=current_tokens
                    )

            elif ch in ('e', 'E') and not has_exp:
                if last_was_underscore:
                    self.tokens = list(current_tokens)
                    raise LexicalError(
                        "Underscore não permitido antes do indicador de expoente 'e'.",
                        start_line,
                        self.column - 1,
                        tokens=current_tokens
                    )
                has_exp = True
                self.pos += 1
                self.column += 1
                if self._peek() in ('+', '-'):
                    self.pos += 1
                    self.column += 1
                # Deve haver ao menos um dígito no expoente
                if not self._peek().isdigit():
                    self.tokens = list(current_tokens)
                    raise LexicalError(
                        "Notação científica malformada: esperado ao menos um dígito no expoente.",
                        start_line,
                        self.column,
                        tokens=current_tokens
                    )
            else:
                break

        if last_was_underscore:
            self.tokens = list(current_tokens)
            raise LexicalError(
                "Underscore não permitido ao final do número.",
                start_line,
                self.column - 1,
                tokens=current_tokens
            )

        # Sufixos de tipo: float (f, F), double (d, D) ou long (l, L)
        ch_suffix = self._peek()
        if ch_suffix in ('f', 'F', 'd', 'D'):
            self.pos += 1
            self.column += 1
        elif ch_suffix in ('l', 'L'):
            if has_dot or has_exp:
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "Sufixo 'L' não é permitido em literais de ponto flutuante.",
                    start_line,
                    self.column,
                    tokens=current_tokens
                )
            self.pos += 1
            self.column += 1

        lexeme = self.source[start_pos:self.pos]
        self._validate_number_boundary(current_tokens, lexeme, start_line)

        # Validação de literais octais inválidos (ex: 088 ou 088L sem ponto ou expoente)
        clean_lexeme = lexeme.rstrip('lL')
        is_float = has_dot or has_exp or lexeme.endswith(('f', 'F', 'd', 'D'))
        if (
            not is_float
            and len(clean_lexeme) > 1
            and clean_lexeme.startswith('0')
            and any(c in ('8', '9') for c in clean_lexeme)
        ):
            self.tokens = list(current_tokens)
            raise LexicalError(
                f"Número octal malformado: dígitos '8' e '9' não são permitidos na base 8 ({lexeme}).",
                start_line,
                start_col,
                tokens=current_tokens
            )

        # -----------------------------------------------------------------
        # REGRA 2: Ponto Flutuante (Float / Double)
        # -----------------------------------------------------------------
        if is_float or FLOAT_DOUBLE_REGEX.match(lexeme):
            tok_type = TokenType.FLOAT if lexeme.endswith(('f', 'F')) else TokenType.DOUBLE
            return Token(tok_type, lexeme, start_line, start_col)

        tok_type = TokenType.LONG if lexeme.endswith(('l', 'L')) else TokenType.INT
        return Token(tok_type, lexeme, start_line, start_col)

    # -------------------------------------------------------------------------
    # 3.4 RECONHECIMENTO DE STRINGS E TEXT BLOCKS COM ESCAPES
    # -------------------------------------------------------------------------
    def _lex_string(self, current_tokens: list) -> Token:
        """Processa literais de string delimitados por aspas duplas e text blocks (\"\"\")."""
        if self.source.startswith('"""', self.pos):
            return self._lex_text_block(current_tokens)

        start_line = self.line
        start_col = self.column
        self.pos += 1
        self.column += 1

        chars = []
        closed = False

        while not self._is_at_end():
            ch = self._peek()

            # Escape com barra invertida
            if ch == '\\':
                esc_col = self.column
                self.pos += 1
                self.column += 1
                if self._is_at_end():
                    break
                next_ch = self._peek()

                if next_ch in ('"', '\\', 'n', 't', 'r', 'b', 'f', "'", 's'):
                    escape_map = {
                        '"': '"', '\\': '\\', 'n': '\n', 't': '\t',
                        'r': '\r', 'b': '\b', 'f': '\f', "'": "'", 's': ' '
                    }
                    chars.append(escape_map[next_ch])
                    self.pos += 1
                    self.column += 1
                    continue
                elif next_ch in "01234567":
                    octal_digits = [next_ch]
                    self.pos += 1
                    self.column += 1
                    max_extra = 2 if next_ch in "0123" else 1
                    for _ in range(max_extra):
                        if not self._is_at_end() and self._peek() in "01234567":
                            octal_digits.append(self._peek())
                            self.pos += 1
                            self.column += 1
                        else:
                            break
                    chars.append(chr(int("".join(octal_digits), 8)))
                    continue
                elif next_ch == 'u':
                    # Suporte a escape Unicode \uXXXX (inclui múltiplos 'u' conforme especificação Java)
                    while not self._is_at_end() and self._peek() == 'u':
                        self.pos += 1
                        self.column += 1
                    hex_code = self.source[self.pos:self.pos + 4]
                    if len(hex_code) == 4 and all(c in "0123456789abcdefABCDEF" for c in hex_code):
                        chars.append(chr(int(hex_code, 16)))
                        self.pos += 4
                        self.column += 4
                        continue
                    else:
                        chars.append("\\u")
                        continue
                elif next_ch not in ('\r', '\n'):
                    # Aceita o caractere de escape como parte do literal sem lançar erro de sequência inválida
                    chars.append(f"\\{next_ch}")
                    self.pos += 1
                    self.column += 1
                    continue
                else:
                    self.tokens = list(current_tokens)
                    raise LexicalError(
                        "String não fechada antes da quebra de linha.",
                        start_line,
                        start_col,
                        tokens=current_tokens
                    )

            if ch == '"':
                self.pos += 1
                self.column += 1
                closed = True
                break

            if ch == '\n' or ch == '\r':
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "String não fechada antes da quebra de linha.",
                    start_line,
                    start_col,
                    tokens=current_tokens
                )

            chars.append(ch)
            self.pos += 1
            self.column += 1

        if not closed:
            self.tokens = list(current_tokens)
            raise LexicalError(
                "String não fechada (esperado '\"' antes do fim do arquivo).",
                start_line,
                start_col,
                tokens=current_tokens
            )

        value = "".join(chars)
        return Token(TokenType.STRING_LITERAL, value, start_line, start_col)

    def _lex_text_block(self, current_tokens: list) -> Token:
        """Processa text blocks delimitados por aspas triplas (\"\"\"...\"\"\") do Java."""
        start_line = self.line
        start_col = self.column
        self.pos += 3
        self.column += 3

        while not self._is_at_end() and self._peek() in (' ', '\t'):
            self.pos += 1
            self.column += 1

        if self._is_at_end() or self._peek() not in ('\r', '\n'):
            self.tokens = list(current_tokens)
            raise LexicalError(
                "Abertura de text block deve ser seguida por quebra de linha.",
                start_line,
                start_col,
                tokens=current_tokens
            )

        if self._peek() == '\r':
            self.pos += 1
            if not self._is_at_end() and self._peek() == '\n':
                self.pos += 1
            self.line += 1
            self.column = 1
        elif self._peek() == '\n':
            self.pos += 1
            self.line += 1
            self.column = 1

        chars = []
        closed = False
        while not self._is_at_end():
            if self.source.startswith('"""', self.pos):
                self.pos += 3
                self.column += 3
                closed = True
                break

            ch = self._peek()
            if ch == '\r':
                self.pos += 1
                if not self._is_at_end() and self._peek() == '\n':
                    self.pos += 1
                self.line += 1
                self.column = 1
                chars.append('\n')
                continue
            elif ch == '\n':
                self.pos += 1
                self.line += 1
                self.column = 1
                chars.append('\n')
                continue
            elif ch == '\\':
                self.pos += 1
                self.column += 1
                if not self._is_at_end():
                    next_ch = self._peek()
                    if next_ch in ('"', '\\', 'n', 't', 'r', 'b', 'f', "'", 's'):
                        escape_map = {
                            '"': '"', '\\': '\\', 'n': '\n', 't': '\t',
                            'r': '\r', 'b': '\b', 'f': '\f', "'": "'", 's': ' '
                        }
                        chars.append(escape_map[next_ch])
                        self.pos += 1
                        self.column += 1
                        continue
                    elif next_ch in ('\r', '\n'):
                        if next_ch == '\r':
                            self.pos += 1
                            if not self._is_at_end() and self._peek() == '\n':
                                self.pos += 1
                        else:
                            self.pos += 1
                        self.line += 1
                        self.column = 1
                        continue
                    else:
                        chars.append(f"\\{next_ch}")
                        self.pos += 1
                        self.column += 1
                        continue
            else:
                chars.append(ch)
                self.pos += 1
                self.column += 1

        if not closed:
            self.tokens = list(current_tokens)
            raise LexicalError(
                "Text block não fechado (esperado '\"\"\"' antes do fim do arquivo).",
                start_line,
                start_col,
                tokens=current_tokens
            )

        value = "".join(chars)
        return Token(TokenType.STRING_LITERAL, value, start_line, start_col)

    # -------------------------------------------------------------------------
    # 3.5 RECONHECIMENTO DE CHARS COM ESCAPES
    # -------------------------------------------------------------------------
    def _lex_char(self, current_tokens: list) -> Token:
        """Processa literais de caractere delimitados por aspas simples ('c')."""
        start_line = self.line
        start_col = self.column
        self.pos += 1
        self.column += 1

        # Caractere vazio '' é erro em Java
        if not self._is_at_end() and self._peek() == "'":
            self.pos += 1
            self.column += 1
            self.tokens = list(current_tokens)
            raise LexicalError(
                "Literal de caractere vazio: '' não é permitido em Java.",
                start_line,
                start_col,
                tokens=current_tokens
            )

        char_val = ""
        if self._is_at_end() or self._peek() in ('\r', '\n'):
            self.tokens = list(current_tokens)
            raise LexicalError(
                "Literal de caractere não fechado.",
                start_line,
                start_col,
                tokens=current_tokens
            )

        ch = self._peek()
        if ch == '\\':
            esc_col = self.column
            self.pos += 1
            self.column += 1
            if self._is_at_end():
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "Literal de caractere não fechado após escape.",
                    start_line,
                    start_col,
                    tokens=current_tokens
                )
            next_ch = self._peek()
            if next_ch in ("'", '"', '\\', 'n', 't', 'r', 'b', 'f', 's'):
                escape_map = {
                    "'": "'", '"': '"', '\\': '\\', 'n': '\n',
                    't': '\t', 'r': '\r', 'b': '\b', 'f': '\f', 's': ' '
                }
                char_val = escape_map[next_ch]
                self.pos += 1
                self.column += 1
            elif next_ch in "01234567":
                octal_digits = [next_ch]
                self.pos += 1
                self.column += 1
                max_extra = 2 if next_ch in "0123" else 1
                for _ in range(max_extra):
                    if not self._is_at_end() and self._peek() in "01234567":
                        octal_digits.append(self._peek())
                        self.pos += 1
                        self.column += 1
                    else:
                        break
                char_val = chr(int("".join(octal_digits), 8))
            elif next_ch == 'u':
                while not self._is_at_end() and self._peek() == 'u':
                    self.pos += 1
                    self.column += 1
                hex_code = self.source[self.pos:self.pos + 4]
                if len(hex_code) == 4 and all(c in "0123456789abcdefABCDEF" for c in hex_code):
                    char_val = chr(int(hex_code, 16))
                    self.pos += 4
                    self.column += 4
                else:
                    char_val = "\\u"
            elif next_ch not in ('\r', '\n'):
                # Aceita o caractere de escape como parte do token de literal sem lançar erro
                char_val = f"\\{next_ch}"
                self.pos += 1
                self.column += 1
            else:
                self.tokens = list(current_tokens)
                raise LexicalError(
                    "Literal de caractere não fechado após escape.",
                    start_line,
                    start_col,
                    tokens=current_tokens
                )
        else:
            char_val = ch
            self.pos += 1
            self.column += 1

        # Deve fechar imediatamente com aspas simples (')
        if self._is_at_end() or self._peek() != "'":
            self.tokens = list(current_tokens)
            raise LexicalError(
                "Literal de caractere inválido: deve conter exatamente um caractere.",
                start_line,
                start_col,
                tokens=current_tokens
            )

        self.pos += 1
        self.column += 1
        return Token(TokenType.CHAR_LITERAL, char_val, start_line, start_col)
