from .token import Token, TokenType

KEYWORDS = {
    "int": TokenType.INT,
    "String": TokenType.STRING,
}

class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.line = 1

    def tokenize(self):
        tokens = []
        while self.pos < len(self.source):
            c = self.source[self.pos]

            if c in " \t\r":
                self.pos += 1
                continue
            if c == "\n":
                self.line += 1
                self.pos += 1
                continue

            if c.isalpha() or c == "_":
                start = self.pos
                self.pos += 1
                while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == "_"):
                    self.pos += 1
                lexeme = self.source[start:self.pos]
                token_type = KEYWORDS.get(lexeme, TokenType.ID)
                tokens.append(Token(token_type, lexeme, self.line))
                continue

            if c.isdigit():
                start = self.pos
                self.pos += 1
                while self.pos < len(self.source) and self.source[self.pos].isdigit():
                    self.pos += 1
                tokens.append(Token(TokenType.NUMBER, self.source[start:self.pos], self.line))
                continue

            if c == '"':
                start_line = self.line
                self.pos += 1
                start = self.pos
                while self.pos < len(self.source) and self.source[self.pos] != '"':
                    if self.source[self.pos] == "\n":
                        self.line += 1
                    self.pos += 1
                if self.pos >= len(self.source):
                    raise ValueError(f"[ERRO LÉXICO] String não fechada na linha {start_line}.")
                value = self.source[start:self.pos]
                self.pos += 1
                tokens.append(Token(TokenType.STRING_LITERAL, value, start_line))
                continue

            single = {
                '=': TokenType.ASSIGN,
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                ';': TokenType.SEMICOLON,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
            }
            if c in single:
                tokens.append(Token(single[c], c, self.line))
                self.pos += 1
                continue

            raise ValueError(f"[ERRO LÉXICO] Caractere inesperado {c!r} na linha {self.line}.")

        tokens.append(Token(TokenType.EOF, "", self.line))
        return tokens
