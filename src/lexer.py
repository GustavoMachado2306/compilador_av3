import re
from .token import Token, TokenType


# 3. Dicionário completo de Palavras Reservadas e Literais Reservados do Java
JAVA_KEYWORDS = {
    "abstract": TokenType.KEYWORD,
    "assert": TokenType.KEYWORD,
    "boolean": TokenType.KEYWORD,
    "break": TokenType.KEYWORD,
    "byte": TokenType.KEYWORD,
    "case": TokenType.KEYWORD,
    "catch": TokenType.KEYWORD,
    "char": TokenType.KEYWORD,
    "class": TokenType.KEYWORD,
    "const": TokenType.KEYWORD,
    "continue": TokenType.KEYWORD,
    "default": TokenType.KEYWORD,
    "do": TokenType.KEYWORD,
    "double": TokenType.KEYWORD,
    "else": TokenType.KEYWORD,
    "enum": TokenType.KEYWORD,
    "extends": TokenType.KEYWORD,
    "final": TokenType.KEYWORD,
    "finally": TokenType.KEYWORD,
    "float": TokenType.KEYWORD,
    "for": TokenType.KEYWORD,
    "goto": TokenType.KEYWORD,
    "if": TokenType.KEYWORD,
    "implements": TokenType.KEYWORD,
    "import": TokenType.KEYWORD,
    "instanceof": TokenType.KEYWORD,
    "int": TokenType.KEYWORD_INT,
    "interface": TokenType.KEYWORD,
    "long": TokenType.KEYWORD,
    "native": TokenType.KEYWORD,
    "new": TokenType.KEYWORD,
    "package": TokenType.KEYWORD,
    "private": TokenType.KEYWORD,
    "protected": TokenType.KEYWORD,
    "public": TokenType.KEYWORD,
    "return": TokenType.KEYWORD,
    "short": TokenType.KEYWORD,
    "static": TokenType.KEYWORD,
    "strictfp": TokenType.KEYWORD,
    "super": TokenType.KEYWORD,
    "switch": TokenType.KEYWORD,
    "synchronized": TokenType.KEYWORD,
    "this": TokenType.KEYWORD,
    "throw": TokenType.KEYWORD,
    "throws": TokenType.KEYWORD,
    "transient": TokenType.KEYWORD,
    "try": TokenType.KEYWORD,
    "void": TokenType.KEYWORD,
    "volatile": TokenType.KEYWORD,
    "while": TokenType.KEYWORD,
    "true": TokenType.BOOLEAN_LITERAL,
    "false": TokenType.BOOLEAN_LITERAL,
    "null": TokenType.NULL_LITERAL,
    "String": TokenType.KEYWORD_STRING,
}

# Alias mantido para compatibilidade com importações existentes
KEYWORDS = JAVA_KEYWORDS

# Expressões regulares pré-compiladas respeitando a ordem estrita de precedência
RE_WHITESPACE = re.compile(r"\s+")
RE_LINE_COMMENT = re.compile(r"//[^\r\n]*")
RE_BLOCK_COMMENT = re.compile(r"/\*[\s\S]*?\*/")

RE_STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\\r\n])*"')
RE_CHAR_LITERAL = re.compile(r"'(?:\\u[0-9a-fA-F]{4}|\\[0-7]{1,3}|\\.|[^'\\\r\n])'")
RE_HEX_LITERAL = re.compile(r"0[xX][0-9a-fA-F][0-9a-fA-F_]*[lL]?")
RE_BINARY_LITERAL = re.compile(r"0[bB][01][01_]*[lL]?")
RE_OCTAL_LITERAL = re.compile(r"0[0-7_]+[lL]?(?![0-9.])")
RE_FLOAT_LITERAL = re.compile(
    r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?[fFdD]?|\d[\d_]*(?:[eE][+-]?\d[\d_]*)[fFdD]?|\d[\d_]*[fFdD]"
)
RE_INTEGER_LITERAL = re.compile(r"\d[\d_]*[lL]?")

RE_KEYWORD = re.compile(
    r"(?:"
    + "|".join(sorted(JAVA_KEYWORDS.keys(), key=len, reverse=True))
    + r")(?![a-zA-Z0-9_$])"
)

RE_IDENTIFIER = re.compile(r"[a-zA-Z_$][a-zA-Z0-9_$]*")

# 4. Operadores de 4, 3, 2 e 1 caracteres (do maior para o menor)
OPS_3_CHARS = {
    ">>>=": TokenType.URSHIFT_ASSIGN,
    ">>=": TokenType.RSHIFT_ASSIGN,
    "<<=": TokenType.LSHIFT_ASSIGN,
    ">>>": TokenType.URSHIFT,
    "...": TokenType.ELLIPSIS,
}

OPS_2_CHARS = {
    "==": TokenType.EQ,
    "!=": TokenType.NEQ,
    "<=": TokenType.LTE,
    ">=": TokenType.GTE,
    "&&": TokenType.AND,
    "||": TokenType.OR,
    "++": TokenType.INCREMENT,
    "--": TokenType.DECREMENT,
    "+=": TokenType.PLUS_ASSIGN,
    "-=": TokenType.MINUS_ASSIGN,
    "*=": TokenType.MUL_ASSIGN,
    "/=": TokenType.DIV_ASSIGN,
    "%=": TokenType.MOD_ASSIGN,
    "&=": TokenType.AND_ASSIGN,
    "|=": TokenType.OR_ASSIGN,
    "^=": TokenType.XOR_ASSIGN,
    "<<": TokenType.LSHIFT,
    ">>": TokenType.RSHIFT,
    "::": TokenType.METHOD_REF,
    "->": TokenType.ARROW,
}

OPS_1_CHAR = {
    "=": TokenType.ASSIGN,
    ">": TokenType.GT,
    "<": TokenType.LT,
    "!": TokenType.NOT,
    "~": TokenType.BIT_NOT,
    "?": TokenType.QUESTION,
    ":": TokenType.COLON,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.MULTIPLY,
    "/": TokenType.DIVIDE,
    "%": TokenType.MODULO,
    "&": TokenType.BIT_AND,
    "|": TokenType.BIT_OR,
    "^": TokenType.BIT_XOR,
}

# 5. Pontuação e delimitadores
DELIMITERS = {
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    ";": TokenType.SEMICOLON,
    ",": TokenType.COMMA,
    ".": TokenType.DOT,
    "@": TokenType.AT,
}


class LexicalError(Exception):
    """Exceção/registro estruturado para erros léxicos."""
    def __init__(self, message: str, line: int, column: int, character: str = None, tokens: list = None):
        self.message = message
        self.line = line
        self.column = column
        self.character = character
        self.tokens = list(tokens) if tokens is not None else []
        super().__init__(self._format_message())

    def _format_message(self):
        return f"[ERRO LÉXICO]\nLinha {self.line}, coluna {self.column}:\n{self.message}"


class Lexer:
    """Analisador léxico completo para a linguagem Java com tolerância a falhas."""
    def __init__(self, source: str, raise_on_error: bool = False):
        self.source = source if source is not None else ""
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.errors = []
        self.raise_on_error = raise_on_error

    def _advance_text(self, text: str):
        """Avança o cursor atualizando linha e coluna com precisão."""
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == "\r":
                if i + 1 < n and text[i + 1] == "\n":
                    i += 2
                else:
                    i += 1
                self.line += 1
                self.column = 1
            elif ch == "\n":
                i += 1
                self.line += 1
                self.column = 1
            else:
                i += 1
                self.column += 1
        self.pos += n

    def _unescape_string(self, raw_inner: str) -> str:
        """Processa sequências de escape padrão do Java em literais de String/Char."""
        escape_map = {
            '"': '"',
            "'": "'",
            "\\": "\\",
            "n": "\n",
            "t": "\t",
            "r": "\r",
            "b": "\b",
            "f": "\f",
        }
        chars = []
        i = 0
        while i < len(raw_inner):
            if raw_inner[i] == "\\" and i + 1 < len(raw_inner):
                nxt = raw_inner[i + 1]
                if nxt in escape_map:
                    chars.append(escape_map[nxt])
                    i += 2
                    continue
            chars.append(raw_inner[i])
            i += 1
        return "".join(chars)

    def _record_error(self, message: str, line: int, col: int, character: str, tokens: list):
        err = LexicalError(
            message=message,
            line=line,
            column=col,
            character=character,
            tokens=tokens,
        )
        self.errors.append(err)
        self.tokens = list(tokens)
        if self.raise_on_error:
            raise err

    def tokenize(self):
        tokens = []
        self.errors = []
        length = len(self.source)

        while self.pos < length:
            c = self.source[self.pos]

            # Ignora BOM UTF-8 se presente
            if c == "\ufeff":
                self.pos += 1
                continue

            # =========================================================
            # 1. ESPAÇOS E COMENTÁRIOS (Ignorados / Pulados)
            # =========================================================

            # 1.1 Espaços em branco, tabs e quebras de linha (\s+)
            m_ws = RE_WHITESPACE.match(self.source, self.pos)
            if m_ws:
                self._advance_text(m_ws.group(0))
                continue

            # 1.2 Comentários de linha (//.*)
            m_line_comment = RE_LINE_COMMENT.match(self.source, self.pos)
            if m_line_comment:
                self._advance_text(m_line_comment.group(0))
                continue

            # 1.3 Comentários de bloco e Javadoc (/\*[\s\S]*?\*/) — ANTES de '/'
            if self.source.startswith("/*", self.pos):
                m_block_comment = RE_BLOCK_COMMENT.match(self.source, self.pos)
                if m_block_comment:
                    self._advance_text(m_block_comment.group(0))
                    continue
                else:
                    # Comentário de bloco não fechado: registra erro e avança até EOF
                    start_line, start_col = self.line, self.column
                    self._advance_text(self.source[self.pos:])
                    self._record_error(
                        "Comentário de bloco não fechado (esperado '*/' antes do fim do arquivo).",
                        start_line,
                        start_col,
                        "/*",
                        tokens,
                    )
                    continue

            # =========================================================
            # 2. LITERAIS FORTES
            # =========================================================

            # 2.1 String Literal: "(?:\\.|[^"\\])*"
            if c == '"':
                m_str = RE_STRING_LITERAL.match(self.source, self.pos)
                if m_str:
                    start_line, start_col = self.line, self.column
                    raw_lexeme = m_str.group(0)
                    value = self._unescape_string(raw_lexeme[1:-1])
                    self._advance_text(raw_lexeme)
                    tokens.append(Token(TokenType.STRING_LITERAL, value, start_line, start_col))
                    continue
                else:
                    # String malformada / não fechada: registra erro e avança até o fim da linha
                    start_line, start_col = self.line, self.column
                    end_idx = self.pos + 1
                    while end_idx < length and self.source[end_idx] not in ("\n", "\r"):
                        end_idx += 1
                    msg = (
                        "String não fechada antes da quebra de linha."
                        if end_idx < length
                        else "String não fechada (esperado '\"' antes do fim do arquivo)."
                    )
                    self._advance_text(self.source[self.pos:end_idx])
                    self._record_error(msg, start_line, start_col, '"', tokens)
                    continue

            # 2.2 Char Literal: '(?:\\.|[^'\\])'
            if c == "'":
                m_char = RE_CHAR_LITERAL.match(self.source, self.pos)
                if m_char:
                    start_line, start_col = self.line, self.column
                    raw_lexeme = m_char.group(0)
                    value = self._unescape_string(raw_lexeme[1:-1])
                    self._advance_text(raw_lexeme)
                    tokens.append(Token(TokenType.CHAR_LITERAL, value, start_line, start_col))
                    continue
                else:
                    start_line, start_col = self.line, self.column
                    self.pos += 1
                    self.column += 1
                    self._record_error(
                        "Literal de caractere inválido ou não fechado.",
                        start_line,
                        start_col,
                        "'",
                        tokens,
                    )
                    continue

            # 2.3 Hexadecimal: 0[xX][0-9a-fA-F]+ (Antes de Float/Int)
            m_hex = RE_HEX_LITERAL.match(self.source, self.pos)
            if m_hex:
                start_line, start_col = self.line, self.column
                lexeme = m_hex.group(0)
                self._advance_text(lexeme)
                tokens.append(Token(TokenType.HEX_LITERAL, lexeme, start_line, start_col))
                continue

            # 2.4 Binário: 0[bB][01]+
            m_bin = RE_BINARY_LITERAL.match(self.source, self.pos)
            if m_bin:
                start_line, start_col = self.line, self.column
                lexeme = m_bin.group(0)
                self._advance_text(lexeme)
                tokens.append(Token(TokenType.BINARY_LITERAL, lexeme, start_line, start_col))
                continue

            # 2.5 Octal: 0[0-7]+ (Antes de Integer, sem conflitar com Float 0.x)
            m_oct = RE_OCTAL_LITERAL.match(self.source, self.pos)
            if m_oct:
                start_line, start_col = self.line, self.column
                lexeme = m_oct.group(0)
                self._advance_text(lexeme)
                tokens.append(Token(TokenType.OCTAL_LITERAL, lexeme, start_line, start_col))
                continue

            # 2.6 Float/Double: \d+\.\d+([eE][+-]?\d+)?[fFdD]?
            m_float = RE_FLOAT_LITERAL.match(self.source, self.pos)
            if m_float:
                start_line, start_col = self.line, self.column
                lexeme = m_float.group(0)
                self._advance_text(lexeme)
                tokens.append(Token(TokenType.FLOAT_LITERAL, lexeme, start_line, start_col))
                continue

            # 2.7 Integer: \d+
            m_int = RE_INTEGER_LITERAL.match(self.source, self.pos)
            if m_int:
                start_line, start_col = self.line, self.column
                lexeme = m_int.group(0)
                self._advance_text(lexeme)
                tokens.append(Token(TokenType.NUMBER, lexeme, start_line, start_col))
                continue

            # =========================================================
            # 3. PALAVRAS RESERVADAS (Keywords)
            # =========================================================
            m_kw = RE_KEYWORD.match(self.source, self.pos)
            if m_kw:
                start_line, start_col = self.line, self.column
                lexeme = m_kw.group(0)
                token_type = JAVA_KEYWORDS[lexeme]
                self._advance_text(lexeme)
                tokens.append(Token(token_type, lexeme, start_line, start_col))
                continue

            # =========================================================
            # 4. OPERADORES COMPOSTOS E SIMPLES (Do maior para o menor)
            # =========================================================

            # 4.1 Operadores compostos longos (>>>=, >>=, <<=, >>>, ...)
            for op_len in (4, 3):
                if self.pos + op_len <= length:
                    op_multi = self.source[self.pos:self.pos + op_len]
                    if op_multi in OPS_3_CHARS:
                        start_line, start_col = self.line, self.column
                        self._advance_text(op_multi)
                        tokens.append(Token(OPS_3_CHARS[op_multi], op_multi, start_line, start_col))
                        break
            else:
                op_multi = None
            if op_multi in OPS_3_CHARS:
                continue

            # 4.2 Operadores de 2 caracteres: ==, !=, <=, >=, &&, ||, ++, --, +=, -=, *=, /=, %=, &=, |=, ^=, <<, >>, ::
            if self.pos + 2 <= length:
                op2 = self.source[self.pos:self.pos + 2]
                if op2 in OPS_2_CHARS:
                    start_line, start_col = self.line, self.column
                    self._advance_text(op2)
                    tokens.append(Token(OPS_2_CHARS[op2], op2, start_line, start_col))
                    continue

            # 4.3 Operadores de 1 caractere: =, >, <, !, ~, ?, :, +, -, *, /, %, &, |, ^
            if c in OPS_1_CHAR:
                start_line, start_col = self.line, self.column
                self._advance_text(c)
                tokens.append(Token(OPS_1_CHAR[c], c, start_line, start_col))
                continue

            # =========================================================
            # 5. PONTUAÇÃO E DELIMITADORES
            # =========================================================
            if c in DELIMITERS:
                start_line, start_col = self.line, self.column
                self._advance_text(c)
                tokens.append(Token(DELIMITERS[c], c, start_line, start_col))
                continue

            # =========================================================
            # 6. IDENTIFICADORES: [a-zA-Z_$][a-zA-Z0-9_$]*
            # =========================================================
            m_id = RE_IDENTIFIER.match(self.source, self.pos)
            if m_id:
                start_line, start_col = self.line, self.column
                lexeme = m_id.group(0)
                token_type = JAVA_KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
                self._advance_text(lexeme)
                tokens.append(Token(token_type, lexeme, start_line, start_col))
                continue

            # =========================================================
            # 7. RECUPERAÇÃO DE ERRO LÉXICO (Tolerância a falhas)
            # =========================================================
            start_line, start_col = self.line, self.column
            self.pos += 1
            self.column += 1
            self._record_error(
                f"Caractere inválido: {c!r}.",
                start_line,
                start_col,
                c,
                tokens,
            )

        tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        self.tokens = tokens
        return tokens
