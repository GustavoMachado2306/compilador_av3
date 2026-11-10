from .token import Token, TokenType
from .ast_nodes import (
    ASTNode,
    Program,
    PackageNode,
    ImportNode,
    Block,
    BlockNode,
    ParameterNode,
    MethodDecl,
    MethodNode,
    ClassDecl,
    ClassNode,
    Declaration,
    Assignment,
    CompoundAssign,
    ArrayAccess,
    IfStmt,
    IfNode,
    WhileStmt,
    WhileNode,
    DoWhileStmt,
    DoWhileNode,
    ForStmt,
    ForNode,
    SwitchStmt,
    CaseClause,
    TryStmt,
    CatchClause,
    ThrowStmt,
    ReturnStmt,
    ReturnNode,
    BreakStmt,
    BreakNode,
    ContinueStmt,
    ContinueNode,
    MethodCall,
    MethodCallNode,
    UnaryOp,
    UnaryOpNode,
    BinaryOp,
    Literal,
    Identifier,
)


TYPE_KEYWORDS = {
    "int",
    "String",
    "double",
    "float",
    "boolean",
    "char",
    "long",
    "short",
    "byte",
}

MODIFIER_KEYWORDS = {
    "public",
    "private",
    "protected",
    "static",
    "final",
    "abstract",
    "synchronized",
    "volatile",
    "transient",
    "native",
    "strictfp",
    "default",
}

COMPOUND_ASSIGN_TOKENS = {
    TokenType.PLUS_ASSIGN: "+",
    TokenType.MINUS_ASSIGN: "-",
    TokenType.MUL_ASSIGN: "*",
    TokenType.DIV_ASSIGN: "/",
    TokenType.MOD_ASSIGN: "%",
    TokenType.LSHIFT_ASSIGN: "<<",
    TokenType.RSHIFT_ASSIGN: ">>",
    TokenType.URSHIFT_ASSIGN: ">>>",
    TokenType.AND_ASSIGN: "&",
    TokenType.OR_ASSIGN: "|",
    TokenType.XOR_ASSIGN: "^",
}


class SyntacticError(Exception):
    """Exceção/registro estruturado para erros sintáticos."""
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
    """
    Analisador Sintático Descendente Recursivo (Recursive Descent Parser) para Java
    com suporte a classes, métodos, blocos, controle de fluxo completo, hierarquia
    completa de expressões e recuperação de erros em modo pânico (Panic Mode).
    """
    def __init__(self, tokens, raise_on_error: bool = False):
        self.tokens = list(tokens) if tokens is not None else []
        self.current = 0
        self.depth = 0
        self.max_depth = 200
        self.errors = []
        self.raise_on_error = raise_on_error
        self._pending_statements = []

    def peek(self, offset: int = 0) -> Token:
        idx = self.current + offset
        if 0 <= idx < len(self.tokens):
            return self.tokens[idx]
        last_line = self.tokens[-1].line if self.tokens else 1
        last_col = self.tokens[-1].column if self.tokens else 1
        return Token(TokenType.EOF, "", last_line, last_col)

    def advance(self) -> Token:
        token = self.peek()
        if self.current < len(self.tokens):
            self.current += 1
        return token

    def check(self, token_type: TokenType) -> bool:
        return self.peek().type == token_type

    def check_keyword(self, word: str) -> bool:
        t = self.peek()
        if word == "int" and t.type == TokenType.KEYWORD_INT:
            return True
        if word == "String" and t.type == TokenType.KEYWORD_STRING:
            return True
        return t.type == TokenType.KEYWORD and t.lexeme == word

    def _is_primitive_or_builtin_type(self, tok: Token) -> bool:
        return (
            tok.type in (TokenType.KEYWORD_INT, TokenType.KEYWORD_STRING)
            or (tok.type == TokenType.KEYWORD and tok.lexeme in TYPE_KEYWORDS)
        )

    def _is_modifier(self, tok: Token) -> bool:
        return tok.type == TokenType.KEYWORD and tok.lexeme in MODIFIER_KEYWORDS

    def expect(self, token_type: TokenType, message: str, expected: str = None) -> Token:
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

    def _record_error(self, err: SyntacticError):
        self.errors.append(err)
        if self.raise_on_error:
            raise err

    def _synchronize(self):
        """
        Modo Pânico (Panic Mode): avança tokens até encontrar um ponto seguro de
        sincronização (';' ou '}') para continuar construindo a AST do restante do arquivo.
        """
        while not self.check(TokenType.EOF):
            tok = self.advance()
            if tok.type in (TokenType.SEMICOLON, TokenType.RBRACE):
                return
            nxt = self.peek()
            if nxt.type in (TokenType.KEYWORD_INT, TokenType.KEYWORD_STRING):
                return
            if nxt.type == TokenType.KEYWORD and nxt.lexeme in (
                "class", "public", "private", "protected", "static", "void",
                "int", "double", "float", "boolean", "char", "long", "short", "byte",
                "if", "for", "while", "do", "switch", "try", "return", "break", "continue", "throw",
            ):
                return

    def _skip_annotations(self):
        """Consome anotações Java como @Override ou @SuppressWarnings(...)."""
        while self.check(TokenType.AT):
            self.advance()
            if self.check(TokenType.IDENTIFIER) or self.check(TokenType.KEYWORD):
                self.advance()
                while self.check(TokenType.DOT):
                    self.advance()
                    if self.check(TokenType.IDENTIFIER):
                        self.advance()
                if self.check(TokenType.LPAREN):
                    depth = 0
                    while not self.check(TokenType.EOF):
                        tk = self.advance()
                        if tk.type == TokenType.LPAREN:
                            depth += 1
                        elif tk.type == TokenType.RPAREN:
                            depth -= 1
                            if depth <= 0:
                                break

    def _collect_modifiers(self):
        """Consome anotações e modificadores (public, static, final, etc.)."""
        modifiers = []
        while True:
            self._skip_annotations()
            if self._is_modifier(self.peek()):
                modifiers.append(self.advance().lexeme)
            else:
                break
        return modifiers

    def _parse_qualified_name(self) -> str:
        """Lê um nome qualificado separado por pontos (ex: java.util.* ou System.out.println)."""
        parts = []
        if self.check(TokenType.IDENTIFIER) or self.check(TokenType.KEYWORD) or self._is_primitive_or_builtin_type(self.peek()):
            parts.append(self.advance().lexeme)
        while self.check(TokenType.DOT):
            self.advance()
            if self.check(TokenType.MULTIPLY):
                parts.append(self.advance().lexeme)
                break
            elif self.check(TokenType.IDENTIFIER) or self.check(TokenType.KEYWORD):
                parts.append(self.advance().lexeme)
            else:
                break
        return ".".join(parts)

    def _parse_type_specifier(self) -> str:
        """Lê um especificador de tipo incluindo genéricos <...> e colchetes de array []."""
        tok = self.advance()
        type_name = tok.lexeme
        while self.check(TokenType.DOT) and self.peek(1).type == TokenType.IDENTIFIER:
            self.advance()
            type_name += "." + self.advance().lexeme

        # Suporte opcional a genéricos ex: List<String>
        if self.check(TokenType.LT):
            depth = 0
            while not self.check(TokenType.EOF):
                tk = self.advance()
                if tk.type == TokenType.LT:
                    depth += 1
                elif tk.type == TokenType.GT:
                    depth -= 1
                    if depth <= 0:
                        break
                elif tk.type == TokenType.RSHIFT:
                    depth -= 2
                    if depth <= 0:
                        break

        # Suporte a colchetes de array ex: String[] ou int[][]
        while self.check(TokenType.LBRACKET) and self.peek(1).type == TokenType.RBRACKET:
            self.advance()
            self.advance()
            type_name += "[]"

        return type_name

    # =========================================================================
    # 1. ESTRUTURA DO PROGRAMA, PACKAGE, IMPORT, CLASSES E MÉTODOS
    # =========================================================================

    def parse(self) -> Program:
        statements = []
        self.errors = []
        self._pending_statements = []

        while not self.check(TokenType.EOF) or self._pending_statements:
            if self._pending_statements:
                statements.append(self._pending_statements.pop(0))
                continue

            old_current = self.current
            try:
                self._skip_annotations()
                if self.check(TokenType.EOF):
                    break

                # Ignora ';' ou '}' soltos para manter tolerância a falhas
                if self.check(TokenType.SEMICOLON) or self.check(TokenType.RBRACE):
                    self.advance()
                    continue

                if self.check_keyword("package"):
                    statements.append(self.parse_package())
                elif self.check_keyword("import"):
                    statements.append(self.parse_import())
                else:
                    node = self.parse_top_level_or_statement()
                    if node is not None:
                        statements.append(node)

                while self._pending_statements:
                    statements.append(self._pending_statements.pop(0))

                if self.current <= old_current and not self.check(TokenType.EOF):
                    t = self.peek()
                    raise SyntacticError(
                        message=f"Token inesperado: {t.lexeme!r}",
                        line=t.line,
                        column=t.column,
                        expected="declaração ou comando válido",
                        found=t.lexeme,
                    )

            except RecursionError:
                t = self.peek()
                err = SyntacticError(
                    message="Limite de aninhamento / recursão do sistema excedido na análise sintática",
                    line=t.line,
                    column=t.column,
                    expected="expressão dentro do limite de aninhamento suportado",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
                self._record_error(err)
                break
            except SyntacticError as err:
                self._record_error(err)
                self._synchronize()

        return Program(statements)

    def parse_package(self) -> PackageNode:
        pkg_tok = self.advance()  # 'package'
        name = self._parse_qualified_name()
        if self.check(TokenType.SEMICOLON):
            self.advance()
        return PackageNode(name=name, line=pkg_tok.line, column=pkg_tok.column)

    def parse_import(self) -> ImportNode:
        imp_tok = self.advance()  # 'import'
        if self.check_keyword("static"):
            self.advance()
        name = self._parse_qualified_name()
        if self.check(TokenType.SEMICOLON):
            self.advance()
        return ImportNode(name=name, line=imp_tok.line, column=imp_tok.column)

    def parse_top_level_or_statement(self) -> ASTNode:
        """Analisa classes, métodos ou comandos soltos."""
        saved_pos = self.current
        modifiers = self._collect_modifiers()

        if self.check_keyword("class") or self.check_keyword("interface") or self.check_keyword("enum"):
            return self.parse_class_declaration(modifiers)

        # Verifica se é declaração de método ou variável precedida por modificadores
        if modifiers:
            if self.check_keyword("void") or self._is_primitive_or_builtin_type(self.peek()) or self.check(TokenType.IDENTIFIER):
                return self.parse_member_after_modifiers(modifiers)

        # Sem modificadores, mas pode ser método solto (ex: void teste() { ... })
        if self.check_keyword("void"):
            return self.parse_member_after_modifiers([])

        # Caso contrário, restaura posição se necessário e analisa comando padrão
        self.current = saved_pos
        return self.statement()

    def parse_class_declaration(self, modifiers: list) -> ClassDecl:
        class_tok = self.advance()  # 'class', 'interface' ou 'enum'
        if self.check(TokenType.IDENTIFIER):
            name_tok = self.advance()
            class_name = name_tok.lexeme
        else:
            t = self.peek()
            raise SyntacticError(
                message="Era esperado o nome da classe após 'class'",
                line=t.line,
                column=t.column,
                expected="identificador da classe",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )

        # Parâmetros genéricos opcionais na declaração da classe (ex: class Caixa<T>)
        if self.check(TokenType.LT):
            depth = 0
            while not self.check(TokenType.EOF):
                tk = self.advance()
                if tk.type == TokenType.LT:
                    depth += 1
                elif tk.type == TokenType.GT:
                    depth -= 1
                    if depth <= 0:
                        break
                elif tk.type == TokenType.RSHIFT:
                    depth -= 2
                    if depth <= 0:
                        break

        superclass = None
        interfaces = []

        if self.check_keyword("extends"):
            self.advance()
            superclass = self._parse_type_specifier()

        if self.check_keyword("implements"):
            self.advance()
            interfaces.append(self._parse_type_specifier())
            while self.check(TokenType.COMMA):
                self.advance()
                interfaces.append(self._parse_type_specifier())

        self.expect(TokenType.LBRACE, "Era esperado '{' para iniciar o corpo da classe", expected="'{'")

        members = []
        while not self.check(TokenType.EOF) and not self.check(TokenType.RBRACE):
            if self._pending_statements:
                members.append(self._pending_statements.pop(0))
                continue

            old_pos = self.current
            try:
                self._skip_annotations()
                if self.check(TokenType.RBRACE) or self.check(TokenType.EOF):
                    break
                if self.check(TokenType.SEMICOLON):
                    self.advance()
                    continue

                member_mods = self._collect_modifiers()

                # Classe interna
                if self.check_keyword("class") or self.check_keyword("interface") or self.check_keyword("enum"):
                    members.append(self.parse_class_declaration(member_mods))
                # Bloco estático/instância ou método/atributo
                elif self.check(TokenType.LBRACE):
                    members.append(self.parse_block())
                elif (
                    member_mods
                    or self.check_keyword("void")
                    or self._is_primitive_or_builtin_type(self.peek())
                    or self._looks_like_member_or_constructor()
                ):
                    member = self.parse_member_after_modifiers(member_mods)
                    if member is not None:
                        members.append(member)
                else:
                    stmt = self.statement()
                    if stmt is not None:
                        members.append(stmt)

                while self._pending_statements:
                    members.append(self._pending_statements.pop(0))

                if self.current <= old_pos and not self.check(TokenType.EOF):
                    self.advance()
            except SyntacticError as err:
                self._record_error(err)
                self._synchronize()

        if self.check(TokenType.RBRACE):
            self.advance()

        return ClassDecl(
            name=class_name,
            members=members,
            modifiers=modifiers,
            superclass=superclass,
            interfaces=interfaces,
            line=class_tok.line,
            column=class_tok.column,
        )

    def _looks_like_member_or_constructor(self) -> bool:
        """Verifica se os próximos tokens formam um construtor NomeClasse(...) ou atributo/método."""
        if not self.check(TokenType.IDENTIFIER):
            return False
        nxt = self.peek(1)
        if nxt.type == TokenType.LPAREN:
            return True
        if nxt.type == TokenType.IDENTIFIER:
            return True
        if nxt.type == TokenType.LBRACKET and self.peek(2).type == TokenType.RBRACKET and self.peek(3).type == TokenType.IDENTIFIER:
            return True
        return False

    def parse_member_after_modifiers(self, modifiers: list) -> ASTNode:
        """Analisa um método, construtor ou atributo de classe após os modificadores."""
        start_tok = self.peek()

        # Construtor: NomeDaClasse(parametros) { ... }
        if self.check(TokenType.IDENTIFIER) and self.peek(1).type == TokenType.LPAREN:
            ctor_tok = self.advance()
            params = self.parse_parameter_list()
            self._skip_throws_clause()
            body = self.parse_block() if self.check(TokenType.LBRACE) else Block()
            if self.check(TokenType.SEMICOLON):
                self.advance()
            return MethodDecl(
                name=ctor_tok.lexeme,
                return_type="construtor",
                parameters=params,
                body=body,
                modifiers=modifiers,
                line=ctor_tok.line,
                column=ctor_tok.column,
            )

        # Tipo de retorno ou tipo de variável
        return_or_var_type = self._parse_type_specifier()

        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message=f"Era esperado um identificador após o tipo '{return_or_var_type}'",
                line=t.line,
                column=t.column,
                expected=f"um identificador após o tipo '{return_or_var_type}'",
                found=found_repr,
            )

        name_tok = self.advance()
        member_name = name_tok.lexeme

        # Se vier '(' após o nome, é uma Declaração de Método
        if self.check(TokenType.LPAREN):
            params = self.parse_parameter_list()
            while self.check(TokenType.LBRACKET) and self.peek(1).type == TokenType.RBRACKET:
                self.advance()
                self.advance()
            self._skip_throws_clause()
            if self.check(TokenType.LBRACE):
                body = self.parse_block()
            else:
                if self.check(TokenType.SEMICOLON):
                    self.advance()
                body = Block()
            return MethodDecl(
                name=member_name,
                return_type=return_or_var_type,
                parameters=params,
                body=body,
                modifiers=modifiers,
                line=start_tok.line,
                column=start_tok.column,
            )

        # Caso contrário, é uma Declaração de Variável / Atributo
        return self._finish_variable_declaration(return_or_var_type, name_tok, start_tok)

    def _skip_throws_clause(self):
        if self.check_keyword("throws"):
            self.advance()
            self._parse_qualified_name()
            while self.check(TokenType.COMMA):
                self.advance()
                self._parse_qualified_name()

    def parse_parameter_list(self) -> list:
        """Analisa a lista de parâmetros '(Tipo1 p1, String[] args, String args[])'."""
        self.expect(TokenType.LPAREN, "Era esperado '(' na lista de parâmetros", expected="'('")
        params = []
        while not self.check(TokenType.EOF) and not self.check(TokenType.RPAREN):
            self._collect_modifiers()
            if self.check(TokenType.RPAREN):
                break
            param_line = self.peek().line
            param_col = self.peek().column
            param_type = self._parse_type_specifier()
            if self.check(TokenType.ELLIPSIS):
                self.advance()
                param_type += "..."
            if self.check(TokenType.IDENTIFIER):
                param_name = self.advance().lexeme
            else:
                param_name = "param"
            # Suporta colchetes após o nome do parâmetro (ex: String args[])
            while self.check(TokenType.LBRACKET) and self.peek(1).type == TokenType.RBRACKET:
                self.advance()
                self.advance()
                param_type += "[]"
            params.append(ParameterNode(type_name=param_type, name=param_name, line=param_line, column=param_col))
            if self.check(TokenType.COMMA):
                self.advance()
            else:
                break
        self.expect(TokenType.RPAREN, "Era esperado ')' ao final dos parâmetros", expected="')'")
        return params

    def parse_block(self) -> Block:
        lbrace = self.expect(TokenType.LBRACE, "Era esperado '{' para iniciar bloco", expected="'{'")
        stmts = []
        while not self.check(TokenType.EOF) and not self.check(TokenType.RBRACE):
            if self._pending_statements:
                stmts.append(self._pending_statements.pop(0))
                continue

            old_pos = self.current
            try:
                if self.check(TokenType.SEMICOLON):
                    self.advance()
                    continue
                stmt = self.statement()
                if stmt is not None:
                    stmts.append(stmt)
                while self._pending_statements:
                    stmts.append(self._pending_statements.pop(0))
                if self.current <= old_pos and not self.check(TokenType.EOF):
                    self.advance()
            except SyntacticError as err:
                self._record_error(err)
                self._synchronize()

        if self.check(TokenType.RBRACE):
            self.advance()
        return Block(statements=stmts, line=lbrace.line, column=lbrace.column)

    # =========================================================================
    # 2. DECLARAÇÕES E COMANDOS (STATEMENTS)
    # =========================================================================

    def statement(self) -> ASTNode:
        self._skip_annotations()
        t = self.peek()

        # Bloco aninhado '{ ... }'
        if self.check(TokenType.LBRACE):
            return self.parse_block()

        # Estruturas condicionais, repetição e exceções
        if self.check_keyword("if"):
            return self.parse_if_statement()
        if self.check_keyword("while"):
            return self.parse_while_statement()
        if self.check_keyword("do"):
            return self.parse_do_while_statement()
        if self.check_keyword("for"):
            return self.parse_for_statement()
        if self.check_keyword("switch"):
            return self.parse_switch_statement()
        if self.check_keyword("try"):
            return self.parse_try_statement()
        if self.check_keyword("throw"):
            return self.parse_throw_statement()

        # Comandos de controle e retorno
        if self.check_keyword("return"):
            return self.parse_return_statement()
        if self.check_keyword("break"):
            tok = self.advance()
            if self.check(TokenType.IDENTIFIER):
                self.advance()
            self.expect(TokenType.SEMICOLON, "Era esperado ';' após 'break'", expected="';'")
            return BreakStmt(line=tok.line, column=tok.column)
        if self.check_keyword("continue"):
            tok = self.advance()
            if self.check(TokenType.IDENTIFIER):
                self.advance()
            self.expect(TokenType.SEMICOLON, "Era esperado ';' após 'continue'", expected="';'")
            return ContinueStmt(line=tok.line, column=tok.column)

        # Declaração local com modificador (ex: final int MAX = 10;)
        if self._is_modifier(t):
            mods = self._collect_modifiers()
            return self.parse_member_after_modifiers(mods)

        # Declaração de variável de tipo primitivo/String
        if self._is_primitive_or_builtin_type(t):
            return self.declaration()

        # Declaração de variável do tipo Objeto/Classe (ex: Scanner sc = ...; ou MiClasse[] arr;)
        if self._looks_like_object_variable_declaration():
            return self.declaration()

        # Pré-incremento / Pré-decremento como comando isolado (++i; --i;)
        if t.type in (TokenType.INCREMENT, TokenType.DECREMENT):
            return self.parse_prefix_inc_dec_statement()

        # Identificador: pode ser Atribuição, Pós-incremento/decremento ou Chamada de Método
        if self.check(TokenType.IDENTIFIER) or self.check_keyword("this") or self.check_keyword("super"):
            return self.parse_identifier_statement()

        found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
        raise SyntacticError(
            message=f"Comando inesperado: {found_repr!r}",
            line=t.line,
            column=t.column,
            expected="uma declaração ('int', 'String') ou atribuição",
            found=found_repr,
        )

    def _looks_like_object_variable_declaration(self) -> bool:
        """Verifica se 'Identificador Identificador' ou 'Identificador[] Identificador' é declaração de variável."""
        if not self.check(TokenType.IDENTIFIER):
            return False
        idx = 1
        # Suporta genéricos em tipos locais: Ex: List<String> lista = ...
        if self.peek(idx).type == TokenType.LT:
            depth = 0
            while idx < len(self.tokens):
                tk = self.peek(idx)
                idx += 1
                if tk.type == TokenType.LT:
                    depth += 1
                elif tk.type == TokenType.GT:
                    depth -= 1
                    if depth <= 0:
                        break
                elif tk.type == TokenType.RSHIFT:
                    depth -= 2
                    if depth <= 0:
                        break
                elif tk.type in (TokenType.SEMICOLON, TokenType.LBRACE, TokenType.RBRACE, TokenType.EOF):
                    return False
        while self.peek(idx).type == TokenType.LBRACKET and self.peek(idx + 1).type == TokenType.RBRACKET:
            idx += 2
        if self.peek(idx).type == TokenType.IDENTIFIER:
            after_name = self.peek(idx + 1).type
            if after_name in (TokenType.ASSIGN, TokenType.SEMICOLON, TokenType.COMMA, TokenType.LBRACKET, TokenType.COLON):
                return True
        return False

    def declaration(self, require_semicolon: bool = True) -> Declaration:
        start_tok = self.peek()
        type_name = self._parse_type_specifier()

        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            base_type = type_name.replace("[]", "")
            raise SyntacticError(
                message=f"Era esperado um identificador após o tipo '{base_type}'",
                line=t.line,
                column=t.column,
                expected=f"um identificador após o tipo '{base_type}'",
                found=found_repr,
            )

        name_tok = self.advance()
        return self._finish_variable_declaration(type_name, name_tok, start_tok, require_semicolon=require_semicolon)

    def _finish_variable_declaration(
        self,
        type_name: str,
        name_tok: Token,
        start_tok: Token,
        require_semicolon: bool = True,
    ) -> Declaration:
        var_type = type_name
        while self.check(TokenType.LBRACKET) and self.peek(1).type == TokenType.RBRACKET:
            self.advance()
            self.advance()
            if not var_type.endswith("[]"):
                var_type += "[]"

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

        base_type_for_ast = var_type.replace("[]", "") if var_type.startswith(("int", "String", "double", "float", "boolean", "char", "long", "short", "byte")) else var_type
        first_decl = Declaration(base_type_for_ast, name_tok.lexeme, start_tok.line, initializer, column=start_tok.column)

        # Múltiplas variáveis na mesma instrução (ex: int a = 1, b = 2;)
        while self.check(TokenType.COMMA):
            self.advance()
            if not self.check(TokenType.IDENTIFIER):
                t = self.peek()
                found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                raise SyntacticError(
                    message="Era esperado um identificador após ',' na declaração",
                    line=t.line,
                    column=t.column,
                    expected="um identificador após ','",
                    found=found_repr,
                )
            extra_tok = self.advance()
            while self.check(TokenType.LBRACKET) and self.peek(1).type == TokenType.RBRACKET:
                self.advance()
                self.advance()
            extra_init = None
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
                extra_init = self.expression()
            self._pending_statements.append(
                Declaration(base_type_for_ast, extra_tok.lexeme, extra_tok.line, extra_init, column=extra_tok.column)
            )

        if require_semicolon:
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

        return first_decl

    def parse_prefix_inc_dec_statement(self, require_semicolon: bool = True) -> Assignment:
        op_tok = self.advance()
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message=f"Era esperado um identificador após '{op_tok.lexeme}'",
                line=t.line,
                column=t.column,
                expected=f"um identificador após '{op_tok.lexeme}'",
                found=found_repr,
            )
        name_tok = self.advance()
        if require_semicolon:
            self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final do comando", expected="';'")
        base_op = "+" if op_tok.type == TokenType.INCREMENT else "-"
        expr = BinaryOp(
            base_op,
            Identifier(name_tok.lexeme, line=name_tok.line, column=name_tok.column),
            Literal("1", "NUM", line=op_tok.line, column=op_tok.column),
            line=op_tok.line,
            column=op_tok.column,
        )
        return Assignment(name_tok.lexeme, name_tok.line, expr, column=name_tok.column, operator=op_tok.lexeme)

    def parse_identifier_statement(self, require_semicolon: bool = True) -> ASTNode:
        """Analisa atribuições (simples/compostas), pós-incremento/decremento ou chamadas de método."""
        first_tok = self.advance()
        target_parts = [first_tok.lexeme]

        # Suporte a acesso encadeado por ponto (ex: System.out.println ou this.campo)
        while self.check(TokenType.DOT):
            self.advance()
            if self.check(TokenType.IDENTIFIER) or self.check(TokenType.KEYWORD):
                target_parts.append(self.advance().lexeme)
            else:
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado um identificador após '.'",
                    line=t.line,
                    column=t.column,
                    expected="identificador de membro ou método",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )

        # Chamada de método/função (ex: System.out.println(msg); ou calcular(a, b);)
        if self.check(TokenType.LPAREN):
            args = self.parse_argument_list()
            # Permite encadeamento pós-chamada ex: builder.append(a).append(b);
            while self.check(TokenType.DOT):
                self.advance()
                if self.check(TokenType.IDENTIFIER):
                    target_parts.append(self.advance().lexeme)
                if self.check(TokenType.LPAREN):
                    args = self.parse_argument_list()
            if require_semicolon:
                self.expect(TokenType.SEMICOLON, "Era esperado ';' após chamada de método", expected="';'")
            return MethodCall(
                target=".".join(target_parts),
                arguments=args,
                line=first_tok.line,
                column=first_tok.column,
            )

        var_name = target_parts[-1] if target_parts[0] == "this" and len(target_parts) > 1 else ".".join(target_parts)
        target_ast: ASTNode = Identifier(var_name, line=first_tok.line, column=first_tok.column)

        # Indexação de array no lado esquerdo da atribuição (ex: vetor[i] = 10;)
        while self.check(TokenType.LBRACKET):
            lb_tok = self.advance()
            idx_expr = self.expression() if not self.check(TokenType.RBRACKET) else Literal("0", "NUM", line=lb_tok.line, column=lb_tok.column)
            self.expect(TokenType.RBRACKET, "Era esperado ']' após índice do array", expected="']'")
            target_ast = ArrayAccess(array=target_ast, index=idx_expr, line=lb_tok.line, column=lb_tok.column)

        # Pós-incremento / Pós-decremento (ex: i++; i--;)
        if self.check(TokenType.INCREMENT) or self.check(TokenType.DECREMENT):
            op_tok = self.advance()
            if require_semicolon:
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
            base_op = "+" if op_tok.type == TokenType.INCREMENT else "-"
            expr = BinaryOp(
                base_op,
                target_ast,
                Literal("1", "NUM", line=op_tok.line, column=op_tok.column),
                line=op_tok.line,
                column=op_tok.column,
            )
            return Assignment(var_name, first_tok.line, expr, column=first_tok.column, operator=op_tok.lexeme)

        # Atribuições compostas (+=, -=, *=, /=, %=, <<=, >>=, >>>=, &=, |=, ^=)
        if self.peek().type in COMPOUND_ASSIGN_TOKENS:
            op_tok = self.advance()
            base_op = COMPOUND_ASSIGN_TOKENS[op_tok.type]
            if self.check(TokenType.SEMICOLON) or self.check(TokenType.EOF):
                t = self.peek()
                found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                raise SyntacticError(
                    message=f"Era esperado uma expressão após '{op_tok.lexeme}'",
                    line=t.line,
                    column=t.column,
                    expected=f"uma expressão após '{op_tok.lexeme}'",
                    found=found_repr,
                )
            rhs = self.expression()
            if require_semicolon:
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
            expr = BinaryOp(
                base_op,
                target_ast,
                rhs,
                line=op_tok.line,
                column=op_tok.column,
            )
            return CompoundAssign(
                name=var_name,
                line=first_tok.line,
                expression=expr,
                column=first_tok.column,
                operator=op_tok.lexeme,
                target_node=target_ast,
                value=rhs,
            )

        # Atribuição simples (=)
        if not self.check(TokenType.ASSIGN):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message=f"Era esperado '=' após o identificador '{var_name}'",
                line=t.line,
                column=t.column,
                expected=f"'=' após o identificador '{var_name}'",
                found=found_repr,
            )

        self.advance()  # '='
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
        if require_semicolon:
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

        return Assignment(var_name, first_tok.line, expr, column=first_tok.column)

    def assignment(self) -> ASTNode:
        return self.parse_identifier_statement(require_semicolon=True)

    def parse_if_statement(self) -> IfStmt:
        if_tok = self.advance()  # 'if'
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'if'", expected="'('")
        condition = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' após a condição do 'if'", expected="')'")

        then_branch = self.parse_block() if self.check(TokenType.LBRACE) else self.statement()
        else_branch = None
        if self.check_keyword("else"):
            self.advance()
            if self.check_keyword("if"):
                else_branch = self.parse_if_statement()
            elif self.check(TokenType.LBRACE):
                else_branch = self.parse_block()
            else:
                else_branch = self.statement()

        return IfStmt(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            line=if_tok.line,
            column=if_tok.column,
        )

    def parse_while_statement(self) -> WhileStmt:
        w_tok = self.advance()  # 'while'
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'while'", expected="'('")
        condition = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' após a condição do 'while'", expected="')'")
        body = self.parse_block() if self.check(TokenType.LBRACE) else self.statement()
        return WhileStmt(condition=condition, body=body, line=w_tok.line, column=w_tok.column)

    def parse_do_while_statement(self) -> DoWhileStmt:
        do_tok = self.advance()  # 'do'
        body = self.parse_block() if self.check(TokenType.LBRACE) else self.statement()
        if self.check_keyword("while"):
            self.advance()
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'while' no 'do-while'", expected="'('")
        condition = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' após a condição do 'do-while'", expected="')'")
        if self.check(TokenType.SEMICOLON):
            self.advance()
        return DoWhileStmt(body=body, condition=condition, line=do_tok.line, column=do_tok.column)

    def parse_for_statement(self) -> ForStmt:
        for_tok = self.advance()  # 'for'
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'for'", expected="'('")

        init_node = None
        cond_node = None
        update_node = None

        if not self.check(TokenType.SEMICOLON):
            if self._is_modifier(self.peek()):
                self._collect_modifiers()
            if self._is_primitive_or_builtin_type(self.peek()) or self._looks_like_object_variable_declaration():
                type_tok = self.peek()
                t_name = self._parse_type_specifier()
                id_tok = self.expect(TokenType.IDENTIFIER, "Era esperado identificador no 'for'", expected="identificador")
                # Suporte a enhanced for (for-each): for (Tipo item : colecao)
                if self.check(TokenType.COLON):
                    self.advance()
                    iterable_expr = self.expression()
                    init_node = Declaration(t_name.replace("[]", ""), id_tok.lexeme, type_tok.line, None, column=type_tok.column)
                    cond_node = iterable_expr
                    self.expect(TokenType.RPAREN, "Era esperado ')' no 'for'", expected="')'")
                    body = self.parse_block() if self.check(TokenType.LBRACE) else self.statement()
                    return ForStmt(init=init_node, condition=cond_node, update=None, body=body, line=for_tok.line, column=for_tok.column)
                else:
                    init_node = self._finish_variable_declaration(t_name, id_tok, type_tok, require_semicolon=False)
            elif self.peek().type in (TokenType.INCREMENT, TokenType.DECREMENT):
                init_node = self.parse_prefix_inc_dec_statement(require_semicolon=False)
            elif self.check(TokenType.IDENTIFIER):
                init_node = self.parse_identifier_statement(require_semicolon=False)
            else:
                init_node = self.expression()

        if self.check(TokenType.SEMICOLON):
            self.advance()

        if not self.check(TokenType.SEMICOLON) and not self.check(TokenType.RPAREN):
            cond_node = self.expression()

        if self.check(TokenType.SEMICOLON):
            self.advance()

        if not self.check(TokenType.RPAREN):
            if self.peek().type in (TokenType.INCREMENT, TokenType.DECREMENT):
                update_node = self.parse_prefix_inc_dec_statement(require_semicolon=False)
            elif self.check(TokenType.IDENTIFIER):
                update_node = self.parse_identifier_statement(require_semicolon=False)
            else:
                update_node = self.expression()
            while self.check(TokenType.COMMA):
                self.advance()
                if self.peek().type in (TokenType.INCREMENT, TokenType.DECREMENT):
                    self.parse_prefix_inc_dec_statement(require_semicolon=False)
                elif self.check(TokenType.IDENTIFIER):
                    self.parse_identifier_statement(require_semicolon=False)
                else:
                    self.expression()

        self.expect(TokenType.RPAREN, "Era esperado ')' ao final do cabeçalho do 'for'", expected="')'")
        body = self.parse_block() if self.check(TokenType.LBRACE) else self.statement()
        return ForStmt(
            init=init_node,
            condition=cond_node,
            update=update_node,
            body=body,
            line=for_tok.line,
            column=for_tok.column,
        )

    def parse_switch_statement(self) -> SwitchStmt:
        sw_tok = self.advance()  # 'switch'
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'switch'", expected="'('")
        expr = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' após expressão do 'switch'", expected="')'")
        self.expect(TokenType.LBRACE, "Era esperado '{' para abrir o 'switch'", expected="'{'")

        cases = []
        while not self.check(TokenType.EOF) and not self.check(TokenType.RBRACE):
            if self.check_keyword("case"):
                c_tok = self.advance()
                case_val = self.expression()
                self.expect(TokenType.COLON, "Era esperado ':' após 'case'", expected="':'")
                stmts = []
                while (
                    not self.check(TokenType.EOF)
                    and not self.check(TokenType.RBRACE)
                    and not self.check_keyword("case")
                    and not self.check_keyword("default")
                ):
                    if self.check(TokenType.SEMICOLON):
                        self.advance()
                        continue
                    stmts.append(self.statement())
                    while self._pending_statements:
                        stmts.append(self._pending_statements.pop(0))
                cases.append(CaseClause(value=case_val, statements=stmts, line=c_tok.line, column=c_tok.column))
            elif self.check_keyword("default"):
                d_tok = self.advance()
                self.expect(TokenType.COLON, "Era esperado ':' após 'default'", expected="':'")
                stmts = []
                while (
                    not self.check(TokenType.EOF)
                    and not self.check(TokenType.RBRACE)
                    and not self.check_keyword("case")
                    and not self.check_keyword("default")
                ):
                    if self.check(TokenType.SEMICOLON):
                        self.advance()
                        continue
                    stmts.append(self.statement())
                    while self._pending_statements:
                        stmts.append(self._pending_statements.pop(0))
                cases.append(CaseClause(value=None, statements=stmts, line=d_tok.line, column=d_tok.column))
            else:
                # Sincroniza token inesperado dentro do switch
                self.advance()

        if self.check(TokenType.RBRACE):
            self.advance()
        return SwitchStmt(expression=expr, cases=cases, line=sw_tok.line, column=sw_tok.column)

    def parse_try_statement(self) -> TryStmt:
        try_tok = self.advance()  # 'try'
        resource_decls = []
        # Suporte opcional a try-with-resources: try (Recurso r = ...) { ... }
        if self.check(TokenType.LPAREN):
            self.advance()
            while not self.check(TokenType.EOF) and not self.check(TokenType.RPAREN):
                if self._is_modifier(self.peek()):
                    self._collect_modifiers()
                if self._is_primitive_or_builtin_type(self.peek()) or self._looks_like_object_variable_declaration():
                    resource_decls.append(self.declaration(require_semicolon=False))
                else:
                    self.expression()
                if self.check(TokenType.SEMICOLON):
                    self.advance()
            if self.check(TokenType.RPAREN):
                self.advance()

        try_block = self.parse_block()
        if resource_decls:
            try_block.statements = resource_decls + try_block.statements

        catches = []
        while self.check_keyword("catch"):
            c_tok = self.advance()
            self.expect(TokenType.LPAREN, "Era esperado '(' após 'catch'", expected="'('")
            self._collect_modifiers()
            exc_type = self._parse_type_specifier()
            while self.check(TokenType.BIT_OR):
                self.advance()
                exc_type += " | " + self._parse_type_specifier()
            exc_name = self.advance().lexeme if self.check(TokenType.IDENTIFIER) else "e"
            self.expect(TokenType.RPAREN, "Era esperado ')' após parâmetro do 'catch'", expected="')'")
            c_body = self.parse_block()
            catches.append(
                CatchClause(
                    exception_type=exc_type,
                    exception_name=exc_name,
                    body=c_body,
                    line=c_tok.line,
                    column=c_tok.column,
                )
            )

        finally_block = None
        if self.check_keyword("finally"):
            self.advance()
            finally_block = self.parse_block()

        return TryStmt(
            try_block=try_block,
            catches=catches,
            finally_block=finally_block,
            line=try_tok.line,
            column=try_tok.column,
        )

    def parse_throw_statement(self) -> ThrowStmt:
        th_tok = self.advance()  # 'throw'
        expr = self.expression()
        self.expect(TokenType.SEMICOLON, "Era esperado ';' após 'throw'", expected="';'")
        return ThrowStmt(expression=expr, line=th_tok.line, column=th_tok.column)

    def parse_return_statement(self) -> ReturnStmt:
        ret_tok = self.advance()  # 'return'
        expr = None
        if not self.check(TokenType.SEMICOLON) and not self.check(TokenType.EOF):
            expr = self.expression()
        self.expect(TokenType.SEMICOLON, "Era esperado ';' após 'return'", expected="';'")
        return ReturnStmt(expression=expr, line=ret_tok.line, column=ret_tok.column)

    def parse_argument_list(self) -> list:
        self.expect(TokenType.LPAREN, "Era esperado '(' nos argumentos", expected="'('")
        args = []
        if not self.check(TokenType.RPAREN):
            args.append(self.expression())
            while self.check(TokenType.COMMA):
                self.advance()
                args.append(self.expression())
        self.expect(TokenType.RPAREN, "Era esperado ')' ao fechar argumentos", expected="')'")
        return args

    # =========================================================================
    # 3. EXPRESSÕES COMPLETAS COM HIERARQUIA DE PRECEDÊNCIA
    # =========================================================================

    def expression(self) -> ASTNode:
        node = self.logical_or()
        # Operador ternário (? :)
        if self.check(TokenType.QUESTION):
            q_tok = self.advance()
            true_expr = self.expression()
            self.expect(TokenType.COLON, "Era esperado ':' no operador ternário", expected="':'")
            false_expr = self.expression()
            return BinaryOp("?:", true_expr, false_expr, line=q_tok.line, column=q_tok.column)
        return node

    def _parse_binary_level(self, next_fn, token_types: tuple) -> ASTNode:
        node = next_fn()
        while self.peek().type in token_types:
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
            right = next_fn()
            node = BinaryOp(op, node, right, line=op_token.line, column=op_token.column)
        return node

    def logical_or(self) -> ASTNode:
        return self._parse_binary_level(self.logical_and, (TokenType.OR,))

    def logical_and(self) -> ASTNode:
        return self._parse_binary_level(self.bitwise_or, (TokenType.AND,))

    def bitwise_or(self) -> ASTNode:
        return self._parse_binary_level(self.bitwise_xor, (TokenType.BIT_OR,))

    def bitwise_xor(self) -> ASTNode:
        return self._parse_binary_level(self.bitwise_and, (TokenType.BIT_XOR,))

    def bitwise_and(self) -> ASTNode:
        return self._parse_binary_level(self.equality, (TokenType.BIT_AND,))

    def equality(self) -> ASTNode:
        return self._parse_binary_level(self.relational, (TokenType.EQ, TokenType.NEQ))

    def relational(self) -> ASTNode:
        node = self.shift()
        while (
            self.peek().type in (TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE)
            or self.check_keyword("instanceof")
        ):
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
            if op == "instanceof":
                type_str = self._parse_type_specifier()
                right = Identifier(type_str, line=op_token.line, column=op_token.column)
            else:
                right = self.shift()
            node = BinaryOp(op, node, right, line=op_token.line, column=op_token.column)
        return node

    def shift(self) -> ASTNode:
        return self._parse_binary_level(
            self.additive,
            (TokenType.LSHIFT, TokenType.RSHIFT, TokenType.URSHIFT),
        )

    def additive(self) -> ASTNode:
        return self._parse_binary_level(self.multiplicative, (TokenType.PLUS, TokenType.MINUS))

    def multiplicative(self) -> ASTNode:
        return self._parse_binary_level(
            self.unary,
            (TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO),
        )

    def unary(self) -> ASTNode:
        # Operadores unários de prefixo: !, -, +, ~, ++, --
        if self.peek().type in (
            TokenType.NOT,
            TokenType.MINUS,
            TokenType.PLUS,
            TokenType.BIT_NOT,
            TokenType.INCREMENT,
            TokenType.DECREMENT,
        ):
            op_tok = self.advance()
            if self.check(TokenType.SEMICOLON) or self.check(TokenType.EOF) or self.check(TokenType.RPAREN):
                t = self.peek()
                found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                raise SyntacticError(
                    message=f"Era esperado uma expressão após '{op_tok.lexeme}'",
                    line=t.line,
                    column=t.column,
                    expected=f"uma expressão após '{op_tok.lexeme}'",
                    found=found_repr,
                )
            operand = self.unary()
            return UnaryOp(op=op_tok.lexeme, operand=operand, is_postfix=False, line=op_tok.line, column=op_tok.column)

        # Type Cast: (int) expr, (double) expr, (int[]) expr
        if self.check(TokenType.LPAREN) and self._is_primitive_or_builtin_type(self.peek(1)):
            # Verifica se fecha ')' logo após o tipo ou colchetes []
            idx = 2
            while self.peek(idx).type == TokenType.LBRACKET and self.peek(idx + 1).type == TokenType.RBRACKET:
                idx += 2
            if self.peek(idx).type == TokenType.RPAREN:
                lp_tok = self.advance()
                cast_type = self._parse_type_specifier()
                self.advance()  # ')'
                operand = self.unary()
                return UnaryOp(op=f"({cast_type})", operand=operand, is_postfix=False, line=lp_tok.line, column=lp_tok.column)

        return self.postfix()

    def postfix(self) -> ASTNode:
        node = self.primary()
        while self.peek().type in (TokenType.INCREMENT, TokenType.DECREMENT):
            op_tok = self.advance()
            node = UnaryOp(
                op=op_tok.lexeme,
                operand=node,
                is_postfix=True,
                line=op_tok.line,
                column=op_tok.column,
            )
        return node

    def primary(self) -> ASTNode:
        # Instanciação de objetos ou arrays: new Tipo(...) ou new int[...]
        if self.check_keyword("new"):
            new_tok = self.advance()
            type_lex = self._parse_type_specifier()
            if self.check(TokenType.LPAREN):
                args = self.parse_argument_list()
                return MethodCall(target=f"new {type_lex}", arguments=args, line=new_tok.line, column=new_tok.column)
            while self.check(TokenType.LBRACKET):
                self.advance()
                if not self.check(TokenType.RBRACKET):
                    self.expression()
                if self.check(TokenType.RBRACKET):
                    self.advance()
            if self.check(TokenType.LBRACE):
                self._consume_array_initializer()
            kind = "STRING" if type_lex.startswith("String") else "NUM"
            return Literal(f"new {type_lex}", kind, line=new_tok.line, column=new_tok.column)

        # Inicializador de array literal: {1, 2, 3}
        if self.check(TokenType.LBRACE):
            return self._consume_array_initializer()

        # Identificadores, acessos encadeados por ponto, chamadas de método e acesso a arrays
        if self.check(TokenType.IDENTIFIER) or self.check_keyword("this") or self.check_keyword("super"):
            tok = self.advance()
            parts = [tok.lexeme]
            is_call = False
            call_args = []
            array_indices = []

            while self.peek().type in (TokenType.DOT, TokenType.LPAREN, TokenType.LBRACKET):
                if self.check(TokenType.DOT):
                    self.advance()
                    if self.check(TokenType.IDENTIFIER) or self.check(TokenType.KEYWORD):
                        parts.append(self.advance().lexeme)
                elif self.check(TokenType.LPAREN):
                    is_call = True
                    call_args = self.parse_argument_list()
                elif self.check(TokenType.LBRACKET):
                    lb_tok = self.advance()
                    idx_expr = self.expression() if not self.check(TokenType.RBRACKET) else Literal("0", "NUM", line=lb_tok.line, column=lb_tok.column)
                    self.expect(TokenType.RBRACKET, "Era esperado ']' após índice", expected="']'")
                    array_indices.append((idx_expr, lb_tok))

            full_name = parts[-1] if parts[0] == "this" and len(parts) == 2 and not is_call else ".".join(parts)
            if is_call:
                node: ASTNode = MethodCall(target=full_name, arguments=call_args, line=tok.line, column=tok.column)
            else:
                node = Identifier(full_name, line=tok.line, column=tok.column)

            for idx_expr, lb_tok in array_indices:
                node = ArrayAccess(array=node, index=idx_expr, line=lb_tok.line, column=lb_tok.column)
            return node

        # Literais numéricos, textuais, booleanos e null
        if self.check(TokenType.NUMBER):
            tok = self.advance()
            return Literal(tok.lexeme, "NUM", line=tok.line, column=tok.column)
        if self.check(TokenType.FLOAT_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "FLOAT", line=tok.line, column=tok.column)
        if self.check(TokenType.HEX_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "HEX", line=tok.line, column=tok.column)
        if self.check(TokenType.BINARY_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "BINARY", line=tok.line, column=tok.column)
        if self.check(TokenType.OCTAL_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "OCTAL", line=tok.line, column=tok.column)
        if self.check(TokenType.STRING_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "STRING", line=tok.line, column=tok.column)
        if self.check(TokenType.CHAR_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "CHAR", line=tok.line, column=tok.column)
        if self.check(TokenType.BOOLEAN_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "BOOLEAN", line=tok.line, column=tok.column)
        if self.check(TokenType.NULL_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "NULL", line=tok.line, column=tok.column)

        # Agrupamento com parênteses: ( expressao )
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

    def term(self) -> ASTNode:
        """Alias mantido para compatibilidade direta."""
        return self.primary()

    def _consume_array_initializer(self) -> Literal:
        brace_tok = self.advance()  # '{'
        if not self.check(TokenType.RBRACE):
            while not self.check(TokenType.EOF) and not self.check(TokenType.RBRACE):
                if self.check(TokenType.LBRACE):
                    self._consume_array_initializer()
                else:
                    self.expression()
                if self.check(TokenType.COMMA):
                    self.advance()
                else:
                    break
        if self.check(TokenType.RBRACE):
            self.advance()
        return Literal("{...}", "NUM", line=brace_tok.line, column=brace_tok.column)
