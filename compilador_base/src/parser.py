from .token import TokenType
from .ast_nodes import Program, Declaration, Assignment, BinaryOp, Literal, Identifier

class Parser:
    """Parser descendente recursivo para um subconjunto didático de Java."""
    def __init__(self, tokens):
        self.tokens = tokens
        self.current = 0

    def peek(self):
        return self.tokens[self.current]

    def advance(self):
        token = self.peek()
        self.current += 1
        return token

    def check(self, token_type):
        return self.peek().type == token_type

    def expect(self, token_type, message):
        if not self.check(token_type):
            t = self.peek()
            raise ValueError(f"[ERRO SINTÁTICO] {message} na linha {t.line}. Recebido: {t.lexeme!r}.")
        return self.advance()

    def parse(self):
        statements = []
        while not self.check(TokenType.EOF):
            statements.append(self.statement())
        return Program(statements)

    def statement(self):
        if self.check(TokenType.INT) or self.check(TokenType.STRING):
            return self.declaration()
        if self.check(TokenType.ID):
            return self.assignment()
        t = self.peek()
        raise ValueError(f"[ERRO SINTÁTICO] Comando inesperado na linha {t.line}: {t.lexeme!r}.")

    def declaration(self):
        type_token = self.advance()
        name = self.expect(TokenType.ID, "Identificador esperado após o tipo").lexeme
        initializer = None
        if self.check(TokenType.ASSIGN):
            self.advance()
            initializer = self.expression()
        self.expect(TokenType.SEMICOLON, "Esperado ';' ao final da declaração")
        return Declaration(type_token.lexeme, name, type_token.line, initializer)

    def assignment(self):
        name_token = self.advance()
        name = name_token.lexeme
        self.expect(TokenType.ASSIGN, "Esperado '=' após o identificador")
        expr = self.expression()
        self.expect(TokenType.SEMICOLON, "Esperado ';' ao final da atribuição")
        return Assignment(name, name_token.line, expr)

    def expression(self):
        node = self.term()
        while self.check(TokenType.PLUS) or self.check(TokenType.MINUS):
            op = self.advance().lexeme
            right = self.term()
            node = BinaryOp(op, node, right)
        return node

    def term(self):
        if self.check(TokenType.ID):
            return Identifier(self.advance().lexeme)
        if self.check(TokenType.NUMBER):
            return Literal(self.advance().lexeme, "NUM")
        if self.check(TokenType.STRING_LITERAL):
            return Literal(self.advance().lexeme, "STRING")
        t = self.peek()
        raise ValueError(f"[ERRO SINTÁTICO] Esperado identificador ou número/string na linha {t.line}.")
