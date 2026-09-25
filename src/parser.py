from .token import Token, TokenType
from .ast_nodes import Program, Declaration, Assignment, BinaryOp, Literal, Identifier

class SyntacticError(Exception):
    """Exceção estruturada para erros sintáticos."""
    def __init__(self, message: str, line: int, column: int, expected: str = None, found: str = None):
        self.message = message
        self.line = line
        self.column = column
        self.expected = expected
        self.found = found
        super().__init__(self._format_message())

    def _format_message(self):
        lines = ["[ERRO SINTÁTICO]", f"Linha {self.line}, coluna {self.column}:"]
        if self.expected:
            lines.append(f"Era esperado {self.expected}.")
        else:
            lines.append(f"{self.message}.")
        if self.found is not None:
            if self.found == "EOF" or self.found == "":
                lines.append("Encontrado: fim de arquivo (EOF)")
            else:
                lines.append(f"Encontrado: '{self.found}'")
        return "\n".join(lines)


class Parser:
    """Parser descendente recursivo estritamente alinhado à gramática oficial."""
    def __init__(self, tokens):
        self.tokens = list(tokens) if tokens is not None else []
        self.current = 0
        self.depth = 0
        self.max_depth = 200

    def peek(self):
        if self.current < len(self.tokens):
            return self.tokens[self.current]
        last_line = self.tokens[-1].line if self.tokens else 1
        last_col = self.tokens[-1].column if self.tokens else 1
        return Token(TokenType.EOF, "", last_line, last_col)

    def advance(self):
        token = self.peek()
        if self.current < len(self.tokens):
            self.current += 1
        return token

    def check(self, token_type):
        return self.peek().type == token_type

    def expect(self, token_type, message, expected=None):
        if not self.check(token_type):
            t = self.peek()
            exp = expected if expected is not None else f"'{token_type.name}'"
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message=message,
                line=t.line,
                column=t.column,
                expected=exp,
                found=found_repr,
            )
        return self.advance()

    def parse(self):
        try:
            statements = []
            while not self.check(TokenType.EOF):
                old_current = self.current
                statements.append(self.statement())
                if self.current <= old_current:
                    t = self.peek()
                    raise SyntacticError(
                        message="Loop detectado: parser não avançou tokens no comando",
                        line=t.line,
                        column=t.column,
                        expected="comando válido",
                        found=t.lexeme if t.type != TokenType.EOF else "EOF",
                    )
            return Program(statements)
        except RecursionError:
            t = self.peek()
            raise SyntacticError(
                message="Limite de aninhamento / recursão do sistema excedido na análise sintática",
                line=t.line,
                column=t.column,
                expected="expressão com profundidade suportada",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )

    def statement(self):
        if self.check(TokenType.KEYWORD_INT) or self.check(TokenType.KEYWORD_STRING):
            return self.declaration()
        if self.check(TokenType.IDENTIFIER):
            return self.assignment()
        t = self.peek()
        found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
        raise SyntacticError(
            message=f"Comando inesperado: {found_repr!r}",
            line=t.line,
            column=t.column,
            expected="uma declaração ('int', 'String') ou atribuição",
            found=found_repr,
        )

    def declaration(self):
        type_token = self.advance()
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message=f"Era esperado um identificador após o tipo '{type_token.lexeme}'",
                line=t.line,
                column=t.column,
                expected=f"um identificador após o tipo '{type_token.lexeme}'",
                found=found_repr,
            )
        name_token = self.advance()
        name = name_token.lexeme
        initializer = None
        if self.check(TokenType.ASSIGN):
            self.advance()
            if self.check(TokenType.SEMICOLON) or self.check(TokenType.EOF):
                t = self.peek()
                found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                raise SyntacticError(
                    message="Era esperado uma expressão após '='",
                    line=t.line,
                    column=t.column,
                    expected="uma expressão após '='",
                    found=found_repr,
                )
            initializer = self.expression()

        if not self.check(TokenType.SEMICOLON):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message="Era esperado ';' ao final da declaração",
                line=t.line,
                column=t.column,
                expected="';' ao final da declaração",
                found=found_repr,
            )
        self.advance()
        return Declaration(type_token.lexeme, name, type_token.line, initializer, column=type_token.column)

    def assignment(self):
        name_token = self.advance()
        name = name_token.lexeme
        if not self.check(TokenType.ASSIGN):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message=f"Era esperado '=' após o identificador '{name}'",
                line=t.line,
                column=t.column,
                expected=f"'=' após o identificador '{name}'",
                found=found_repr,
            )
        self.advance()
        if self.check(TokenType.SEMICOLON) or self.check(TokenType.EOF):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message="Era esperado uma expressão após '='",
                line=t.line,
                column=t.column,
                expected="uma expressão após '='",
                found=found_repr,
            )
        expr = self.expression()
        if not self.check(TokenType.SEMICOLON):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message="Era esperado ';' ao final da atribuição",
                line=t.line,
                column=t.column,
                expected="';' ao final da atribuição",
                found=found_repr,
            )
        self.advance()
        return Assignment(name, name_token.line, expr, column=name_token.column)

    def expression(self):
        node = self.term()
        while self.check(TokenType.PLUS) or self.check(TokenType.MINUS):
            op_token = self.advance()
            op = op_token.lexeme
            if self.check(TokenType.SEMICOLON) or self.check(TokenType.EOF) or self.check(TokenType.RPAREN):
                t = self.peek()
                found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                raise SyntacticError(
                    message=f"Era esperado uma expressão após '{op}'",
                    line=t.line,
                    column=t.column,
                    expected=f"uma expressão após '{op}'",
                    found=found_repr,
                )
            right = self.term()
            node = BinaryOp(op, node, right, line=op_token.line, column=op_token.column)
        return node

    def term(self):
        if self.check(TokenType.IDENTIFIER):
            tok = self.advance()
            return Identifier(tok.lexeme, line=tok.line, column=tok.column)
        if self.check(TokenType.NUMBER):
            tok = self.advance()
            return Literal(tok.lexeme, "NUM", line=tok.line, column=tok.column)
        if self.check(TokenType.STRING_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "STRING", line=tok.line, column=tok.column)
        if self.check(TokenType.LPAREN):
            self.depth += 1
            if self.depth > self.max_depth:
                t = self.peek()
                raise SyntacticError(
                    message=f"Limite de aninhamento de parênteses excedido (máximo de {self.max_depth} níveis)",
                    line=t.line,
                    column=t.column,
                    expected=f"expressão dentro do Limite de aninhamento (máximo de {self.max_depth} níveis)",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            try:
                self.advance()
                expr = self.expression()
                if not self.check(TokenType.RPAREN):
                    t = self.peek()
                    found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                    raise SyntacticError(
                        message="Era esperado ')' para fechar a expressão",
                        line=t.line,
                        column=t.column,
                        expected="')'",
                        found=found_repr,
                    )
                self.advance()
                return expr
            finally:
                self.depth -= 1

        t = self.peek()
        found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
        raise SyntacticError(
            message="Era esperado uma expressão",
            line=t.line,
            column=t.column,
            expected="uma expressão",
            found=found_repr,
        )
