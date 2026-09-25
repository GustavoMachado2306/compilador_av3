from .token import Token, TokenType

KEYWORDS = {
    "int": TokenType.KEYWORD_INT,
    "String": TokenType.KEYWORD_STRING,
}

class LexicalError(Exception):
    """Exceção estruturada para erros léxicos."""
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
    """Analisador léxico para o subconjunto didático da linguagem."""
    def __init__(self, source: str):
        self.source = source if source is not None else ""
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def tokenize(self):
        tokens = []
        while self.pos < len(self.source):
            old_pos = self.pos
            c = self.source[self.pos]

            # Ignora caractere de BOM se presente no meio do fluxo
            if c == '\ufeff':
                self.pos += 1
                continue

            # Suporte a CRLF e quebras de linha
            if c == "\r":
                self.pos += 1
                if self.pos < len(self.source) and self.source[self.pos] == "\n":
                    self.pos += 1
                    self.line += 1
                    self.column = 1
                continue

            # Espaços em branco e tabulações
            if c in " \t":
                self.pos += 1
                self.column += 1
                continue

            # Quebra de linha isolada
            if c == "\n":
                self.line += 1
                self.column = 1
                self.pos += 1
                continue

            # Identificadores e palavras-chave
            if c.isalpha() or c == "_":
                start_pos = self.pos
                start_col = self.column
                start_line = self.line
                while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == "_"):
                    self.pos += 1
                    self.column += 1
                lexeme = self.source[start_pos:self.pos]
                token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
                tokens.append(Token(token_type, lexeme, start_line, start_col))
                continue

            # Números inteiros
            if c.isdigit():
                start_pos = self.pos
                start_col = self.column
                start_line = self.line
                while self.pos < len(self.source) and self.source[self.pos].isdigit():
                    self.pos += 1
                    self.column += 1
                lexeme = self.source[start_pos:self.pos]
                tokens.append(Token(TokenType.NUMBER, lexeme, start_line, start_col))
                continue

            # Strings literais delimitadas por aspas duplas com suporte a escapes
            if c == '"':
                start_line = self.line
                start_col = self.column
                self.pos += 1
                self.column += 1
                chars = []
                closed = False
                while self.pos < len(self.source):
                    ch = self.source[self.pos]
                    if ch == '\\':
                        if self.pos + 1 < len(self.source):
                            next_ch = self.source[self.pos + 1]
                            if next_ch in ('"', '\\', 'n', 't'):
                                escape_map = {'"': '"', '\\': '\\', 'n': '\n', 't': '\t'}
                                chars.append(escape_map[next_ch])
                                self.pos += 2
                                self.column += 2
                                continue
                    if ch == '"':
                        self.pos += 1
                        self.column += 1
                        closed = True
                        break
                    if ch == "\n":
                        self.tokens = list(tokens)
                        raise LexicalError(
                            "String não fechada antes da quebra de linha.",
                            start_line,
                            start_col,
                            tokens=tokens,
                        )
                    chars.append(ch)
                    self.pos += 1
                    self.column += 1

                if not closed:
                    self.tokens = list(tokens)
                    raise LexicalError(
                        "String não fechada (esperado '\"' antes do fim do arquivo).",
                        start_line,
                        start_col,
                        tokens=tokens,
                    )

                value = "".join(chars)
                tokens.append(Token(TokenType.STRING_LITERAL, value, start_line, start_col))
                continue

            # Delimitadores e operadores de caractere único
            single = {
                '=': TokenType.ASSIGN,
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                ';': TokenType.SEMICOLON,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
            }
            if c in single:
                col = self.column
                tokens.append(Token(single[c], c, self.line, col))
                self.pos += 1
                self.column += 1
                continue

            # Caractere inválido com garantia de avanço do cursor
            col = self.column
            self.pos += 1
            self.column += 1
            self.tokens = list(tokens)
            raise LexicalError(
                f"Caractere inválido: {c!r}.",
                self.line,
                col,
                character=c,
                tokens=tokens,
            )

        tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        self.tokens = tokens
        return tokens
