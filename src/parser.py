<<<<<<< HEAD
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

=======
"""
Módulo do Analisador Sintático (Parser) do Compilador Java (AV3).
Implementa um analisador descendente recursivo capaz de processar:
- Unidades de compilação completas (CompilationUnit);
- Declarações de package e imports (simples, com wildcard '*' e static);
- Declarações de classes, interfaces e enums;
- Modificadores de acesso e especiais;
- Campos (com ou sem inicializador);
- Construtores e métodos (com parâmetros, tipos de retorno e throws);
- Blocos de métodos ({ ... }) e instruções de retorno;
- Modo de compatibilidade com fragmentos didáticos de comandos.
"""
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a

from typing import List, Optional, Set
from .token import Token, TokenType
from .ast_nodes import (
    ASTNode, Program, CompilationUnit, PackageDeclaration, ImportDeclaration,
    ClassDeclaration, InterfaceDeclaration, EnumDeclaration, EnumConstant,
    FieldDeclaration, MethodDeclaration, ConstructorDeclaration, Parameter,
    TypeReference, Block, ReturnStatement, Declaration, LocalVariableDeclaration,
    Assignment, BinaryOp, UnaryOp, MethodCall, Literal, Identifier,
    ExpressionStatement, EmptyStatement, IfStatement, WhileStatement,
    DoWhileStatement, ForStatement, EnhancedForStatement, BreakStatement,
    ContinueStatement, ThrowStatement, AssertStatement, TryStatement,
    CatchClause, SynchronizedStatement, UnsupportedStatement,
    ConditionalExpression, MemberAccess, ArrayAccess, ObjectCreationExpression,
    ArrayInitializer, ArrayCreationExpression, CastExpression,
    InstanceOfExpression, LambdaExpression, MethodReference
)

# Conjunto de palavras-chave que representam modificadores em Java
MODIFIER_TOKENS: Set[TokenType] = {
    TokenType.KEYWORD_PUBLIC, TokenType.KEYWORD_PROTECTED, TokenType.KEYWORD_PRIVATE,
    TokenType.KEYWORD_STATIC, TokenType.KEYWORD_FINAL, TokenType.KEYWORD_ABSTRACT,
    TokenType.KEYWORD_SYNCHRONIZED, TokenType.KEYWORD_NATIVE, TokenType.KEYWORD_TRANSIENT,
    TokenType.KEYWORD_VOLATILE, TokenType.KEYWORD_STRICTFP,
}

# Conjunto de tipos primitivos e void
PRIMITIVE_TYPE_TOKENS: Set[TokenType] = {
    TokenType.KEYWORD_INT, TokenType.KEYWORD_BOOLEAN, TokenType.KEYWORD_CHAR,
    TokenType.KEYWORD_BYTE, TokenType.KEYWORD_SHORT, TokenType.KEYWORD_LONG,
    TokenType.KEYWORD_FLOAT, TokenType.KEYWORD_DOUBLE, TokenType.KEYWORD_VOID,
}

# Conjunto de operadores de atribuição da linguagem Java
ASSIGNMENT_TOKENS: Set[TokenType] = {
    TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
    TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN, TokenType.PERCENT_ASSIGN,
    TokenType.AND_ASSIGN, TokenType.OR_ASSIGN, TokenType.XOR_ASSIGN,
    TokenType.LSHIFT_ASSIGN, TokenType.RSHIFT_ASSIGN, TokenType.URSHIFT_ASSIGN,
}


# =============================================================================
# SEÇÃO 1: EXCEÇÃO DE ERRO SINTÁTICO ESTRUTURADO
# =============================================================================
class SyntacticError(Exception):
<<<<<<< HEAD
    """Exceção/registro estruturado para erros sintáticos."""
=======
    """
    Exceção estruturada para erros sintáticos.
    Informa linha, coluna, o que era esperado e o símbolo encontrado.
    """
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
    def __init__(self, message: str, line: int, column: int, expected: str = None, found: str = None):
        self.message = message
        self.line = line
        self.column = column
        self.expected = expected
        self.found = found
        super().__init__(self._format_message())

    def _format_message(self) -> str:
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


# =============================================================================
# SEÇÃO 2: CLASSE PRINCIPAL DO PARSER
# =============================================================================
class Parser:
    """
<<<<<<< HEAD
    Analisador Sintático Descendente Recursivo (Recursive Descent Parser) para Java
    com suporte a classes, métodos, blocos, controle de fluxo completo, hierarquia
    completa de expressões e recuperação de erros em modo pânico (Panic Mode).
    """
    def __init__(self, tokens, raise_on_error: bool = False):
=======
    Parser descendente recursivo para arquivos e fragmentos da linguagem Java.
    Reconhece unidades de compilação completas e preserva compatibilidade com
    fragmentos isolados de comandos das etapas anteriores.
    """
    def __init__(self, tokens: List[Token]):
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        self.tokens = list(tokens) if tokens is not None else []
        self.current = 0
        self.depth = 0
        self.max_depth = 200
        self.errors = []
        self.raise_on_error = raise_on_error
        self._pending_statements = []

<<<<<<< HEAD
    def peek(self, offset: int = 0) -> Token:
        idx = self.current + offset
        if 0 <= idx < len(self.tokens):
            return self.tokens[idx]
=======
    # -------------------------------------------------------------------------
    # 2.1 MÉTODOS AUXILIARES DE NAVEGAÇÃO E INSPEÇÃO DE TOKENS
    # -------------------------------------------------------------------------
    def peek(self) -> Token:
        """Retorna o token atual sem consumir."""
        if self.current < len(self.tokens):
            return self.tokens[self.current]
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        last_line = self.tokens[-1].line if self.tokens else 1
        last_col = self.tokens[-1].column if self.tokens else 1
        return Token(TokenType.EOF, "", last_line, last_col)

<<<<<<< HEAD
    def advance(self) -> Token:
        token = self.peek()
=======
    def peek_offset(self, offset: int = 1) -> Token:
        """Retorna o token N posições à frente sem consumir."""
        idx = self.current + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        last_line = self.tokens[-1].line if self.tokens else 1
        last_col = self.tokens[-1].column if self.tokens else 1
        return Token(TokenType.EOF, "", last_line, last_col)

    def advance(self) -> Token:
        """Consome e retorna o token atual."""
        tok = self.peek()
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        if self.current < len(self.tokens):
            self.current += 1
        return tok

    def check(self, token_type: TokenType) -> bool:
<<<<<<< HEAD
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
=======
        """Verifica se o token atual é do tipo esperado."""
        return self.peek().type == token_type

    def expect(self, token_type: TokenType, message: str, expected: str = None) -> Token:
        """
        Exige que o token atual seja do tipo especificado.
        Se não for, lança SyntacticError estruturado com a linha e coluna exatas.
        """
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
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

<<<<<<< HEAD
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
=======
    # -------------------------------------------------------------------------
    # 2.2 PONTO DE ENTRADA: PARSE DE UNIDADE DE COMPILAÇÃO
    # -------------------------------------------------------------------------
    def parse(self) -> CompilationUnit:
        """
        Ponto de entrada principal do parser.
        Constrói a árvore sintática completa (CompilationUnit).
        """
        try:
            unit = CompilationUnit()

            # Se for entrada vazia (apenas EOF)
            if self.check(TokenType.EOF):
                return unit

            # 1. Declaração opcional de pacote
            if self.check(TokenType.KEYWORD_PACKAGE):
                unit.package = self.package_declaration()

            # 2. Declarações de importação (zero ou mais)
            while self.check(TokenType.KEYWORD_IMPORT):
                unit.imports.append(self.import_declaration())

            # 3. Declarações de tipos ou comandos de nível superior
            while not self.check(TokenType.EOF):
                old_current = self.current

                # Captura modificadores no nível superior
                modifiers = self.parse_modifiers()

                if self.check(TokenType.KEYWORD_CLASS):
                    unit.type_declarations.append(self.class_declaration(modifiers))
                elif self.check(TokenType.KEYWORD_INTERFACE):
                    unit.type_declarations.append(self.interface_declaration(modifiers))
                elif self.check(TokenType.KEYWORD_ENUM):
                    unit.type_declarations.append(self.enum_declaration(modifiers))
                elif modifiers:
                    # Modificadores presentes, mas sem class/interface/enum (ex: public int somar() {})
                    t = self.peek()
                    found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                    raise SyntacticError(
                        message="Declarações de métodos e campos não são permitidas no nível superior fora de uma classe, interface ou enum",
                        line=t.line,
                        column=t.column,
                        expected="'class', 'interface' ou 'enum' no nível superior",
                        found=found_repr,
                    )
                else:
                    # Verifica se alguém declarou método sem modificadores no nível superior (ex: int somar() {})
                    if self._is_method_signature():
                        t = self.peek()
                        raise SyntacticError(
                            message="Declarações de métodos não são permitidas no nível superior fora de uma classe ou interface",
                            line=t.line,
                            column=t.column,
                            expected="declaração de classe, interface ou enum",
                            found=t.lexeme if t.type != TokenType.EOF else "EOF",
                        )

                    # Caso contrário, trata como comando didático de nível superior (modo fragmento)
                    stmt = self.statement()
                    unit.statements.append(stmt)

                # Salvaguarda contra loop infinito
                if self.current <= old_current:
                    t = self.peek()
                    raise SyntacticError(
                        message="Loop detectado: parser não avançou tokens na unidade de compilação",
                        line=t.line,
                        column=t.column,
                        expected="declaração de tipo válida",
                        found=t.lexeme if t.type != TokenType.EOF else "EOF",
                    )

            return unit

        except RecursionError:
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
            t = self.peek()
            raise SyntacticError(
                message="Era esperado o nome da classe após 'class'",
                line=t.line,
                column=t.column,
<<<<<<< HEAD
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
=======
                expected="expressão dentro do limite de aninhamento suportado",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )

    # -------------------------------------------------------------------------
    # 2.3 DECLARAÇÃO DE PACOTE E IMPORTS
    # -------------------------------------------------------------------------
    def package_declaration(self) -> PackageDeclaration:
        """Processa: package nome.do.pacote;"""
        pkg_tok = self.advance() # consome 'package'
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado um identificador após 'package'",
                line=t.line,
                column=t.column,
                expected="o nome do pacote",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        name = self.qualified_identifier()
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da declaração de package", expected="';' ao final da declaração de package")
        return PackageDeclaration(name, pkg_tok.line, pkg_tok.column)

    def import_declaration(self) -> ImportDeclaration:
        """Processa: import [static] caminho.[*];"""
        imp_tok = self.advance() # consome 'import'
        is_static = False
        if self.check(TokenType.KEYWORD_STATIC):
            self.advance()
            is_static = True

        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado um identificador após 'import'",
                line=t.line,
                column=t.column,
                expected="um identificador após 'import'",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )

        parts = [self.advance().lexeme]
        is_wildcard = False

        while self.check(TokenType.DOT):
            self.advance() # consome '.'
            if self.check(TokenType.STAR):
                self.advance() # consome '*'
                parts.append("*")
                is_wildcard = True
                break
            elif self.check(TokenType.IDENTIFIER):
                parts.append(self.advance().lexeme)
            else:
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado um identificador ou '*' após '.' no import",
                    line=t.line,
                    column=t.column,
                    expected="identificador ou '*'",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )

        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final do import", expected="';'")
        return ImportDeclaration(".".join(parts), is_static, is_wildcard, imp_tok.line, imp_tok.column)

    def qualified_identifier(self) -> str:
        """Lê identificadores separados por ponto: a.b.c"""
        parts = [self.expect(TokenType.IDENTIFIER, "Era esperado um identificador").lexeme]
        while self.check(TokenType.DOT):
            self.advance()
            parts.append(self.expect(TokenType.IDENTIFIER, "Era esperado um identificador após '.'").lexeme)
        return ".".join(parts)

    def parse_modifiers(self) -> List[str]:
        """Lê modificadores contíguos (public, static, final, etc.)."""
        mods = []
        while self.peek().type in MODIFIER_TOKENS:
            mods.append(self.advance().lexeme)
        return mods

    # -------------------------------------------------------------------------
    # 2.4 DECLARAÇÕES DE CLASSES, INTERFACES E ENUMS
    # -------------------------------------------------------------------------
    def class_declaration(self, modifiers: List[str]) -> ClassDeclaration:
        """Processa a declaração de uma classe Java."""
        class_tok = self.advance() # consome 'class'
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado o nome da classe após 'class'",
                line=t.line,
                column=t.column,
                expected="o nome da classe",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        class_name = self.advance().lexeme

        extends_type = None
        if self.check(TokenType.KEYWORD_EXTENDS):
            self.advance()
            extends_type = self.parse_type_reference()

        implements_types = []
        if self.check(TokenType.KEYWORD_IMPLEMENTS):
            self.advance()
            implements_types.append(self.parse_type_reference())
            while self.check(TokenType.COMMA):
                self.advance()
                implements_types.append(self.parse_type_reference())

        self.expect(TokenType.LBRACE, "Era esperado '{' para abrir o corpo da classe", expected="'{'")

        members = []
        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            members.append(self.class_member(class_name))

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o corpo da classe", expected="'}'")
        return ClassDeclaration(class_name, modifiers, extends_type, implements_types, members, class_tok.line, class_tok.column)

    def interface_declaration(self, modifiers: List[str]) -> InterfaceDeclaration:
        """Processa a declaração de uma interface Java."""
        iface_tok = self.advance() # consome 'interface'
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado o nome da interface após 'interface'",
                line=t.line,
                column=t.column,
                expected="o nome da interface",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        iface_name = self.advance().lexeme

        type_parameters = []
        if self.check(TokenType.LESS):
            self.advance()
            while not self.check(TokenType.GREATER) and not self.check(TokenType.EOF):
                if self.check(TokenType.IDENTIFIER):
                    type_parameters.append(self.advance().lexeme)
                if self.check(TokenType.COMMA):
                    self.advance()
                else:
                    break
            self.expect(TokenType.GREATER, "Era esperado '>' após os parâmetros de tipo da interface", expected="'>'")

        extends_types = []
        if self.check(TokenType.KEYWORD_EXTENDS):
            self.advance()
            extends_types.append(self.parse_type_reference())
            while self.check(TokenType.COMMA):
                self.advance()
                extends_types.append(self.parse_type_reference())

        self.expect(TokenType.LBRACE, "Era esperado '{' para abrir o corpo da interface", expected="'{'")

        members = []
        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            members.append(self.interface_member(iface_name))

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o corpo da interface", expected="'}'")
        return InterfaceDeclaration(iface_name, modifiers, type_parameters, extends_types, members, iface_tok.line, iface_tok.column)

    def enum_declaration(self, modifiers: List[str]) -> EnumDeclaration:
        """Processa a declaração de um enum Java."""
        enum_tok = self.advance() # consome 'enum'
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado o nome do enum após 'enum'",
                line=t.line,
                column=t.column,
                expected="o nome do enum",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        enum_name = self.advance().lexeme

        implements_types = []
        if self.check(TokenType.KEYWORD_IMPLEMENTS):
            self.advance()
            implements_types.append(self.parse_type_reference())
            while self.check(TokenType.COMMA):
                self.advance()
                implements_types.append(self.parse_type_reference())

        self.expect(TokenType.LBRACE, "Era esperado '{' para abrir o corpo do enum", expected="'{'")

        constants = []
        while not self.check(TokenType.SEMICOLON) and not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            if self.check(TokenType.IDENTIFIER):
                c_tok = self.advance()
                args = []
                if self.check(TokenType.LPAREN):
                    self.advance()
                    while not self.check(TokenType.RPAREN) and not self.check(TokenType.EOF):
                        args.append(self.expression())
                        if self.check(TokenType.COMMA):
                            self.advance()
                    self.expect(TokenType.RPAREN, "Era esperado ')' após argumentos da constante do enum", expected="')'")
                constants.append(EnumConstant(c_tok.lexeme, args, c_tok.line, c_tok.column))
                if self.check(TokenType.COMMA):
                    self.advance()
                else:
                    break
            else:
                break

        members = []
        if self.check(TokenType.SEMICOLON):
            self.advance()
            while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
                members.append(self.class_member(enum_name))

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o corpo do enum", expected="'}'")
        return EnumDeclaration(enum_name, modifiers, implements_types, constants, members, enum_tok.line, enum_tok.column)

    # -------------------------------------------------------------------------
    # 2.5 MEMBROS DE CLASSE (CAMPOS, CONSTRUTORES, MÉTODOS)
    # -------------------------------------------------------------------------
    def class_member(self, class_name: str) -> ASTNode:
        """Processa um membro dentro de uma classe."""
        mods = self.parse_modifiers()

        # Tipos aninhados
        if self.check(TokenType.KEYWORD_CLASS):
            return self.class_declaration(mods)
        if self.check(TokenType.KEYWORD_INTERFACE):
            return self.interface_declaration(mods)
        if self.check(TokenType.KEYWORD_ENUM):
            return self.enum_declaration(mods)

        # Construtor: identificador igual ao nome da classe seguido de '('
        if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == class_name and self.peek_offset(1).type == TokenType.LPAREN:
            ctor_tok = self.advance()
            params = self.parse_parameter_list()
            throws_types = self.parse_throws_clause()
            body = self.parse_block()
            return ConstructorDeclaration(ctor_tok.lexeme, params, mods, throws_types, body, ctor_tok.line, ctor_tok.column)

        # Campo ou Método: inicia com o tipo
        type_ref = self.parse_type_reference()
        name_tok = self.expect(TokenType.IDENTIFIER, "Era esperado o nome do membro (método ou campo)", expected="o nome do membro (método ou campo)")

        # Método
        if self.check(TokenType.LPAREN):
            params = self.parse_parameter_list()
            throws_types = self.parse_throws_clause()
            if self.check(TokenType.SEMICOLON):
                self.advance()
                body = None # método abstrato ou assinatura sem corpo
            else:
                body = self.parse_block()
            return MethodDeclaration(name_tok.lexeme, type_ref, params, mods, throws_types, body, name_tok.line, name_tok.column)

        # Campo
        initializer = None
        if self.check(TokenType.ASSIGN):
            self.advance()
            initializer = self.expression()

        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da declaração do campo", expected="';'")
        return FieldDeclaration(type_ref, name_tok.lexeme, mods, initializer, name_tok.line, name_tok.column)

    def interface_member(self, interface_name: str) -> ASTNode:
        """Processa um membro dentro de uma interface."""
        mods = self.parse_modifiers()
        type_ref = self.parse_type_reference()
        name_tok = self.expect(TokenType.IDENTIFIER, "Era esperado o nome do método ou constante da interface")

        if self.check(TokenType.LPAREN):
            params = self.parse_parameter_list()
            throws_types = self.parse_throws_clause()
            if self.check(TokenType.SEMICOLON):
                self.advance()
                body = None
            else:
                body = self.parse_block() # default method
            return MethodDeclaration(name_tok.lexeme, type_ref, params, mods, throws_types, body, name_tok.line, name_tok.column)

        initializer = None
        if self.check(TokenType.ASSIGN):
            self.advance()
            initializer = self.expression()
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da declaração", expected="';'")
        return FieldDeclaration(type_ref, name_tok.lexeme, mods, initializer, name_tok.line, name_tok.column)

    # -------------------------------------------------------------------------
    # 2.6 REFERÊNCIA DE TIPO E PARÂMETROS
    # -------------------------------------------------------------------------
    def parse_type_reference(self) -> TypeReference:
        """Processa tipos primitivos, nomes qualificados, generics e dimensões de arrays."""
        tok = self.peek()
        if tok.type in PRIMITIVE_TYPE_TOKENS:
            self.advance()
            type_name = tok.lexeme
        elif tok.type == TokenType.IDENTIFIER:
            type_name = self.qualified_identifier()
        else:
            raise SyntacticError(
                message=f"Tipo inválido: '{tok.lexeme}'",
                line=tok.line,
                column=tok.column,
                expected="um tipo primitivo ou identificador de classe",
                found=tok.lexeme if tok.type != TokenType.EOF else "EOF",
            )

        # Parâmetros genéricos simples (<T>, <K, V>)
        type_arguments = []
        if self.check(TokenType.LESS):
            self.advance()
            while not self.check(TokenType.GREATER) and not self.check(TokenType.EOF):
                type_arguments.append(self.parse_type_reference())
                if self.check(TokenType.COMMA):
                    self.advance()
                else:
                    break
            self.expect(TokenType.GREATER, "Era esperado '>' para fechar argumentos de tipo genérico", expected="'>'")

        # Dimensões de array (ex: int[], String[][])
        array_dimensions = 0
        while self.check(TokenType.LBRACKET) and self.peek_offset(1).type == TokenType.RBRACKET:
            self.advance() # [
            self.advance() # ]
            array_dimensions += 1

        is_varargs = False
        if self.check(TokenType.ELLIPSIS):
            self.advance()
            is_varargs = True

        return TypeReference(type_name, array_dimensions, type_arguments, is_varargs, tok.line, tok.column)

    def parse_parameter_list(self) -> List[Parameter]:
        """Processa a lista de parâmetros entre parênteses: (Tipo a, Tipo... b)"""
        self.expect(TokenType.LPAREN, "Era esperado '(' para iniciar parâmetros", expected="'('")
        params = []
        while not self.check(TokenType.RPAREN) and not self.check(TokenType.EOF):
            t_ref = self.parse_type_reference()
            is_var = t_ref.is_varargs
            if self.check(TokenType.ELLIPSIS):
                self.advance()
                is_var = True
            p_name_tok = self.expect(TokenType.IDENTIFIER, "Era esperado o nome do parâmetro")
            params.append(Parameter(t_ref, p_name_tok.lexeme, is_var, p_name_tok.line, p_name_tok.column))
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
            if self.check(TokenType.COMMA):
                self.advance()
            else:
                break
<<<<<<< HEAD
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

=======
        self.expect(TokenType.RPAREN, "Era esperado ')' para fechar os parâmetros", expected="')'")
        return params

    def parse_throws_clause(self) -> List[TypeReference]:
        """Processa a cláusula throws Excecao1, Excecao2."""
        exceptions = []
        if self.check(TokenType.KEYWORD_THROWS):
            self.advance()
            exceptions.append(self.parse_type_reference())
            while self.check(TokenType.COMMA):
                self.advance()
                exceptions.append(self.parse_type_reference())
        return exceptions

    # -------------------------------------------------------------------------
    # 2.7 BLOCOS E INSTRUÇÕES (FASE C)
    # -------------------------------------------------------------------------
    def parse_block(self) -> Block:
        """Processa o bloco { ... } verificando o balanceamento de chaves."""
        start_tok = self.expect(TokenType.LBRACE, "Era esperado '{' para iniciar o bloco", expected="'{'")
        statements = []

        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            statements.append(self.parse_statement())

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o bloco", expected="'}'")
        return Block(statements, start_tok.line, start_tok.column)

    def block_statement(self) -> ASTNode:
        """Processa uma instrução dentro de um bloco (compatibilidade com métodos)."""
        return self.parse_statement()

    def parse_statement(self) -> ASTNode:
        """
        Processa uma instrução Java (Fase C) ou bloco.
        Reconhece:
        - Blocos aninhados { ... }
        - Instrução vazia ;
        - Declarações de variáveis locais (com e sem inicializador)
        - Atribuições simples e compostas
        - if, if/else, if/else if/else (com e sem chaves)
        - while e do/while
        - for tradicional e for aprimorado (for-each)
        - break e continue (com e sem rótulo)
        - return (com e sem expressão)
        - throw
        - try/catch/finally e try-with-resources
        - assert
        - synchronized
        - Chamadas de método e expressões como instruções
        """
        # 1. Instrução vazia ';'
        if self.check(TokenType.SEMICOLON):
            tok = self.advance()
            return EmptyStatement(tok.line, tok.column)

        # 2. Bloco aninhado '{ ... }'
        if self.check(TokenType.LBRACE):
            return self.parse_block()

        # 3. Retorno: 'return [expr];'
        if self.check(TokenType.KEYWORD_RETURN):
            return self.parse_return_statement()

        # 4. Condicional: 'if (cond) ... else ...'
        if self.check(TokenType.KEYWORD_IF):
            return self.parse_if_statement()

        # 5. Laço while: 'while (cond) ...'
        if self.check(TokenType.KEYWORD_WHILE):
            return self.parse_while_statement()

        # 6. Laço do-while: 'do ... while (cond);'
        if self.check(TokenType.KEYWORD_DO):
            return self.parse_do_while_statement()

        # 7. Laço for (tradicional ou aprimorado): 'for (...) ...'
        if self.check(TokenType.KEYWORD_FOR):
            return self.parse_for_statement()

        # 8. Comandos de desvio: 'break [rotulo];' e 'continue [rotulo];'
        if self.check(TokenType.KEYWORD_BREAK):
            return self.parse_break_statement()
        if self.check(TokenType.KEYWORD_CONTINUE):
            return self.parse_continue_statement()

        # 9. Lançamento de exceção: 'throw expr;'
        if self.check(TokenType.KEYWORD_THROW):
            return self.parse_throw_statement()

        # 10. Asserção: 'assert cond [: msg];'
        if self.check(TokenType.KEYWORD_ASSERT):
            return self.parse_assert_statement()

        # 11. Tratamento de exceções: 'try ... catch ... finally'
        if self.check(TokenType.KEYWORD_TRY):
            return self.parse_try_statement()

        # 12. Bloco sincronizado: 'synchronized (lock) { ... }'
        if self.check(TokenType.KEYWORD_SYNCHRONIZED):
            return self.parse_synchronized_statement()

        # 13. Declaração local de variável (ex: int x = 10; String nome; final int y;)
        if self._is_local_declaration():
            return self.parse_local_variable_declaration()

        # 14. Atribuição simples ou qualificada (ex: x = 10; this.nome = nome; x += 1;)
        if (self.check(TokenType.IDENTIFIER) or self.check(TokenType.KEYWORD_THIS)) and self._is_assignment_ahead():
            return self.assignment()

        # 15. Instrução de expressão (ex: System.out.println("Olá"); contador++; matriz[i] = 10;)
        expr = self.expression()
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final do comando", expected="';'")
        if isinstance(expr, Assignment):
            return expr
        return ExpressionStatement(expr, line=expr.line, column=expr.column)

    # -------------------------------------------------------------------------
    # 2.8 COMANDOS ESPECÍFICOS DE CONTROLE DE FLUXO (FASE C)
    # -------------------------------------------------------------------------
    def parse_if_statement(self) -> IfStatement:
        """Processa if (condicao) ramo_verdadeiro [else ramo_falso]."""
        if_tok = self.advance() # consome 'if'
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'if'", expected="'('")
        if self.check(TokenType.RPAREN):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado uma condição entre parênteses no 'if'",
                line=t.line,
                column=t.column,
                expected="uma condição",
                found=")",
            )
        condition = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' após a condição do 'if'", expected="')'")
        then_branch = self.parse_statement()
        else_branch = None
        if self.check(TokenType.KEYWORD_ELSE):
            self.advance() # consome 'else'
            else_branch = self.parse_statement()
        return IfStatement(condition, then_branch, else_branch, if_tok.line, if_tok.column)

    def parse_while_statement(self) -> WhileStatement:
        """Processa while (condicao) corpo."""
        while_tok = self.advance() # consome 'while'
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'while'", expected="'('")
        if self.check(TokenType.RPAREN):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado uma condição entre parênteses no 'while'",
                line=t.line,
                column=t.column,
                expected="uma condição",
                found=")",
            )
        condition = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' após a condição do 'while'", expected="')'")
        body = self.parse_statement()
        return WhileStatement(condition, body, while_tok.line, while_tok.column)

    def parse_do_while_statement(self) -> DoWhileStatement:
        """Processa do corpo while (condicao);"""
        do_tok = self.advance() # consome 'do'
        body = self.parse_statement()
        self.expect(TokenType.KEYWORD_WHILE, "Era esperado 'while' após o corpo do 'do'", expected="'while'")
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'while'", expected="'('")
        if self.check(TokenType.RPAREN):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado uma condição entre parênteses no 'while'",
                line=t.line,
                column=t.column,
                expected="uma condição",
                found=")",
            )
        condition = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' após a condição do 'while'", expected="')'")
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final do comando 'do-while'", expected="';'")
        return DoWhileStatement(body, condition, do_tok.line, do_tok.column)

    def parse_for_statement(self) -> ASTNode:
        """Processa for tradicional ou for aprimorado (for-each)."""
        for_tok = self.advance() # consome 'for'
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'for'", expected="'('")

        if self.check(TokenType.RPAREN):
            t = self.peek()
            raise SyntacticError(
                message="Cabeçalho do 'for' incompleto ou vazio",
                line=t.line,
                column=t.column,
                expected="cláusulas do 'for'",
                found=")",
            )

        # Distinção entre for tradicional e for aprimorado via lookahead
        if self._is_enhanced_for_ahead():
            return self._parse_enhanced_for(for_tok)
        else:
            return self._parse_traditional_for(for_tok)

    def _is_enhanced_for_ahead(self) -> bool:
        """Verifica se há um ':' antes de ';' no cabeçalho do 'for' (desconsiderando ternários ? :)."""
        idx = self.current
        paren_depth = 0
        bracket_depth = 0
        question_depth = 0
        while idx < len(self.tokens):
            tok = self.tokens[idx]
            if tok.type == TokenType.LPAREN:
                paren_depth += 1
            elif tok.type == TokenType.RPAREN:
                if paren_depth == 0:
                    break
                paren_depth -= 1
            elif tok.type == TokenType.LESS:
                bracket_depth += 1
            elif tok.type == TokenType.GREATER:
                if bracket_depth > 0:
                    bracket_depth -= 1
            elif paren_depth == 0 and bracket_depth == 0:
                if tok.type == TokenType.QUESTION:
                    question_depth += 1
                elif tok.type == TokenType.COLON:
                    if question_depth > 0:
                        question_depth -= 1
                    else:
                        return True
                elif tok.type == TokenType.SEMICOLON:
                    return False
            idx += 1
        return False

    def _parse_enhanced_for(self, for_tok: Token) -> EnhancedForStatement:
        """Processa for aprimorado: for (Tipo var : colecao) corpo."""
        mods = self.parse_modifiers()
        type_ref = self.parse_type_reference()
        var_tok = self.expect(TokenType.IDENTIFIER, "Era esperado o nome da variável no 'for' aprimorado", expected="o nome da variável")
        var_decl = LocalVariableDeclaration(
            type_name=type_ref.name,
            name=var_tok.lexeme,
            line=var_tok.line,
            column=var_tok.column,
            type_ref=type_ref,
            modifiers=mods,
        )
        self.expect(TokenType.COLON, "Era esperado ':' após a variável no 'for' aprimorado", expected="':'")
        iterable = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' para fechar o cabeçalho do 'for' aprimorado", expected="')'")
        body = self.parse_statement()
        return EnhancedForStatement(var_decl, iterable, body, for_tok.line, for_tok.column)

    def _parse_traditional_for(self, for_tok: Token) -> ForStatement:
        """Processa for tradicional: for ([init]; [cond]; [update]) corpo."""
        # 1. Inicialização
        init = None
        if self.check(TokenType.SEMICOLON):
            self.advance() # init vazio
        else:
            if self._is_local_declaration():
                init = self.parse_local_variable_declaration_in_for()
            else:
                init = self.expression()
            self.expect(TokenType.SEMICOLON, "Era esperado ';' após a inicialização do 'for'", expected="';'")

        # 2. Condição
        condition = None
        if self.check(TokenType.SEMICOLON):
            self.advance() # condicao vazia
        else:
            condition = self.expression()
            self.expect(TokenType.SEMICOLON, "Era esperado ';' após a condição do 'for'", expected="';'")

        # 3. Atualização
        update = None
        if not self.check(TokenType.RPAREN):
            update = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' para fechar o cabeçalho do 'for'", expected="')'")

        # 4. Corpo
        body = self.parse_statement()
        return ForStatement(init, condition, update, body, for_tok.line, for_tok.column)

    def parse_local_variable_declaration_in_for(self) -> LocalVariableDeclaration:
        """Processa declaração de variável local no cabeçalho do 'for' (sem ponto e vírgula final)."""
        mods = self.parse_modifiers()
        type_ref = self.parse_type_reference()
        name_tok = self.expect(TokenType.IDENTIFIER, "Era esperado o nome da variável no 'for'", expected="o nome da variável")
        name = name_tok.lexeme
        initializer = None
        if self.check(TokenType.ASSIGN):
            self.advance()
            initializer = self.expression()
        return LocalVariableDeclaration(
            type_name=type_ref.name,
            name=name,
            line=name_tok.line,
            initializer=initializer,
            column=name_tok.column,
            type_ref=type_ref,
            modifiers=mods,
        )

    def parse_break_statement(self) -> BreakStatement:
        """Processa break [rotulo];"""
        break_tok = self.advance() # consome 'break'
        label = None
        if self.check(TokenType.IDENTIFIER):
            label = self.advance().lexeme
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final do comando 'break'", expected="';'")
        return BreakStatement(label, break_tok.line, break_tok.column)

    def parse_continue_statement(self) -> ContinueStatement:
        """Processa continue [rotulo];"""
        cont_tok = self.advance() # consome 'continue'
        label = None
        if self.check(TokenType.IDENTIFIER):
            label = self.advance().lexeme
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final do comando 'continue'", expected="';'")
        return ContinueStatement(label, cont_tok.line, cont_tok.column)

    def parse_return_statement(self) -> ReturnStatement:
        """Processa return [expressao];"""
        ret_tok = self.advance() # consome 'return'
        expr = None
        if not self.check(TokenType.SEMICOLON):
            expr = self.expression()
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final do return", expected="';'")
        return ReturnStatement(expr, ret_tok.line, ret_tok.column)

    def parse_throw_statement(self) -> ThrowStatement:
        """Processa throw expressao;"""
        throw_tok = self.advance() # consome 'throw'
        expr = self.expression()
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final do throw", expected="';'")
        return ThrowStatement(expr, throw_tok.line, throw_tok.column)

    def parse_assert_statement(self) -> AssertStatement:
        """Processa assert condicao [: mensagem];"""
        assert_tok = self.advance() # consome 'assert'
        cond = self.expression()
        msg = None
        if self.check(TokenType.COLON):
            self.advance() # consome ':'
            msg = self.expression()
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final do assert", expected="';'")
        return AssertStatement(cond, msg, assert_tok.line, assert_tok.column)

    def parse_try_statement(self) -> TryStatement:
        """Processa try [(recursos)] { corpo } catch... finally..."""
        try_tok = self.advance() # consome 'try'
        resources = []

        # try com recursos: try (...)
        if self.check(TokenType.LPAREN):
            self.advance() # consome '('
            while not self.check(TokenType.RPAREN) and not self.check(TokenType.EOF):
                if self._is_local_declaration():
                    res = self.parse_local_variable_declaration_in_resource()
                else:
                    res = self.expression()
                resources.append(res)
                if self.check(TokenType.SEMICOLON):
                    self.advance()
                else:
                    break
            self.expect(TokenType.RPAREN, "Era esperado ')' para fechar os recursos do 'try'", expected="')'")

        body = self.parse_block()

        catches = []
        while self.check(TokenType.KEYWORD_CATCH):
            catch_tok = self.advance() # consome 'catch'
            self.expect(TokenType.LPAREN, "Era esperado '(' após 'catch'", expected="'('")
            p_type = self.parse_type_reference()
            p_name = self.expect(TokenType.IDENTIFIER, "Era esperado o nome do parâmetro da exceção no 'catch'", expected="nome do parâmetro da exceção")
            param = Parameter(p_type, p_name.lexeme, line=p_name.line, column=p_name.column)
            self.expect(TokenType.RPAREN, "Era esperado ')' após o parâmetro do 'catch'", expected="')'")
            c_body = self.parse_block()
            catches.append(CatchClause(param, c_body, catch_tok.line, catch_tok.column))

        finally_block = None
        if self.check(TokenType.KEYWORD_FINALLY):
            self.advance() # consome 'finally'
            finally_block = self.parse_block()

        if not resources and not catches and not finally_block:
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message="Instrução 'try' deve ter ao menos uma cláusula 'catch' ou 'finally'",
                line=try_tok.line,
                column=try_tok.column,
                expected="'catch' ou 'finally'",
                found=found_repr,
            )

        return TryStatement(resources, body, catches, finally_block, try_tok.line, try_tok.column)

    def parse_local_variable_declaration_in_resource(self) -> LocalVariableDeclaration:
        """Processa declaração de variável dentro dos recursos do try: [var|Tipo] id = expr."""
        mods = self.parse_modifiers()
        type_ref = self.parse_type_reference()
        name_tok = self.expect(TokenType.IDENTIFIER, "Era esperado o nome da variável do recurso", expected="nome da variável")
        self.expect(TokenType.ASSIGN, "Era esperado '=' na inicialização do recurso do 'try'", expected="'='")
        init_expr = self.expression()
        return LocalVariableDeclaration(
            type_name=type_ref.name,
            name=name_tok.lexeme,
            line=name_tok.line,
            initializer=init_expr,
            column=name_tok.column,
            type_ref=type_ref,
            modifiers=mods,
        )

    def parse_synchronized_statement(self) -> SynchronizedStatement:
        """Processa synchronized (lock) { corpo }."""
        sync_tok = self.advance() # consome 'synchronized'
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'synchronized'", expected="'('")
        lock = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' após a expressão de lock do 'synchronized'", expected="')'")
        body = self.parse_block()
        return SynchronizedStatement(lock, body, sync_tok.line, sync_tok.column)

    def parse_local_variable_declaration(self) -> LocalVariableDeclaration:
        """Processa declaração local: [final] Tipo nome [= expressao];"""
        mods = self.parse_modifiers()
        type_ref = self.parse_type_reference()
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            base_type = type_name.replace("[]", "")
            raise SyntacticError(
<<<<<<< HEAD
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

=======
                message=f"Era esperado um identificador após o tipo '{type_ref.name}'",
                line=t.line,
                column=t.column,
                expected=f"um identificador após o tipo '{type_ref.name}'",
                found=found_repr,
            )
        name_token = self.advance()
        name = name_token.lexeme
        if name == type_ref.name:
            raise SyntacticError(
                message=f"Nome de variável inválido: o identificador não pode ser igual ao nome do tipo '{name}'",
                line=name_token.line,
                column=name_token.column,
                expected="um identificador diferente do tipo",
                found=name,
            )
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
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

<<<<<<< HEAD
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
=======
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da declaração", expected="';'")
        return LocalVariableDeclaration(
            type_name=type_ref.name,
            name=name,
            line=name_token.line,
            initializer=initializer,
            column=name_token.column,
            type_ref=type_ref,
            modifiers=mods,
        )

    # -------------------------------------------------------------------------
    # 2.9 COMANDOS E MODO FRAGMENTO DIDÁTICO
    # -------------------------------------------------------------------------
    def statement(self) -> ASTNode:
        """Processa declarações e atribuições didáticas de nível superior."""
        if self.peek().type in PRIMITIVE_TYPE_TOKENS or (
            self.check(TokenType.IDENTIFIER) and self._is_local_declaration()
        ):
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

    def declaration(self) -> Declaration:
        """Processa declarações simples didáticas: Tipo id [= expr];"""
        type_token = self.advance()
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
<<<<<<< HEAD
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
=======
                message=f"Era esperado um identificador após o tipo '{type_token.lexeme}'",
                line=t.line,
                column=t.column,
                expected=f"um identificador após o tipo '{type_token.lexeme}'",
                found=found_repr,
            )
        name_token = self.advance()
        name = name_token.lexeme
        if name == type_token.lexeme:
            raise SyntacticError(
                message=f"Nome de variável inválido: o identificador não pode ser igual ao nome do tipo '{name}'",
                line=name_token.line,
                column=name_token.column,
                expected="um identificador diferente do tipo",
                found=name,
            )
        initializer = None
        if self.check(TokenType.ASSIGN):
            self.advance()
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
            if self.check(TokenType.SEMICOLON) or self.check(TokenType.EOF):
                t = self.peek()
                found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                raise SyntacticError(
<<<<<<< HEAD
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
=======
                    message="Era esperado uma expressão após '='",
                    line=t.line,
                    column=t.column,
                    expected="uma expressão após '='",
                    found=found_repr,
                )
            initializer = self.expression()

        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da declaração", expected="';'")
        return Declaration(type_token.lexeme, name, type_token.line, initializer, column=type_token.column)

    def assignment(self) -> Assignment:
        """Processa atribuição: id = expressao; ou this.id = expressao;"""
        start_tok = self.peek()
        # Suporte a 'this.nome' ou identificador comum
        if self.check(TokenType.KEYWORD_THIS):
            self.advance()
            self.expect(TokenType.DOT, "Era esperado '.' após 'this'")
            name_token = self.expect(TokenType.IDENTIFIER, "Era esperado o nome do campo após 'this.'")
            name = f"this.{name_token.lexeme}"
            target_node = MemberAccess(Identifier("this", line=start_tok.line, column=start_tok.column), name_token.lexeme, line=name_token.line, column=name_token.column)
        else:
            name_token = self.advance()
            name = name_token.lexeme
            target_node = Identifier(name, line=name_token.line, column=name_token.column)

        # Verifica operador de atribuição
        if self.peek().type in ASSIGNMENT_TOKENS:
            op_tok = self.advance()
            op = op_tok.lexeme
        else:
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message=f"Era esperado '=' após o identificador '{var_name}'",
                line=t.line,
                column=t.column,
                expected=f"'=' após o identificador '{var_name}'",
                found=found_repr,
            )

<<<<<<< HEAD
        self.advance()  # '='
=======
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
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
<<<<<<< HEAD
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
=======
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da atribuição", expected="';'")
        return Assignment(name, start_tok.line, expr, operator=op, column=start_tok.column, target=target_node)

    # -------------------------------------------------------------------------
    # 2.10 EXPRESSÕES E OPERADORES (FASE D)
    # -------------------------------------------------------------------------
    def expression(self) -> ASTNode:
        """Ponto de entrada de expressões: inicia pela avaliação de expressões lambda."""
        return self.lambda_expression()

    def lambda_expression(self) -> ASTNode:
        """
        Nível 1: Expressões lambda '->'.
        Suporta:
        - Parâmetro único sem parênteses: x -> x * 2
        - Parâmetros entre parênteses: (a, b) -> a + b ou () -> executar()
        - Corpo como expressão ou bloco: x -> { return x + 1; }
        """
        # Caso 1: identificador único seguido de '->' (ex: x -> ...)
        if self.check(TokenType.IDENTIFIER) and self.peek_offset(1).type == TokenType.ARROW:
            param_tok = self.advance()
            self.advance() # consome '->'
            if self.check(TokenType.LBRACE):
                body = self.parse_block()
                is_block = True
            else:
                body = self.expression()
                is_block = False
            return LambdaExpression(
                parameters=[param_tok.lexeme],
                body=body,
                is_block_body=is_block,
                line=param_tok.line,
                column=param_tok.column
            )

        # Caso 2: parâmetros entre parênteses seguidos de '->' (ex: () -> ..., (a, b) -> ...)
        if self.check(TokenType.LPAREN) and self._is_lambda_parameters_ahead():
            start_tok = self.advance() # consome '('
            params = []
            while not self.check(TokenType.RPAREN) and not self.check(TokenType.EOF):
                while self.peek().type in MODIFIER_TOKENS:
                    self.advance()
                first_tok = self.expect(TokenType.IDENTIFIER, "Era esperado nome de parâmetro na expressão lambda", expected="nome de parâmetro")
                if self.check(TokenType.IDENTIFIER):
                    second_tok = self.advance()
                    params.append(second_tok.lexeme)
                else:
                    params.append(first_tok.lexeme)

                if self.check(TokenType.COMMA):
                    self.advance()
                else:
                    break
            self.expect(TokenType.RPAREN, "Era esperado ')' para fechar os parâmetros da lambda", expected="')'")
            self.expect(TokenType.ARROW, "Era esperado '->' na expressão lambda", expected="'->'")
            if self.check(TokenType.LBRACE):
                body = self.parse_block()
                is_block = True
            else:
                body = self.expression()
                is_block = False
            return LambdaExpression(
                parameters=params,
                body=body,
                is_block_body=is_block,
                line=start_tok.line,
                column=start_tok.column
            )

        return self.assignment_expression()

    def _is_lambda_parameters_ahead(self) -> bool:
        """Verifica se os parênteses à frente contêm parâmetros de lambda seguidos de '->'."""
        idx = self.current + 1
        paren_depth = 1
        while idx < len(self.tokens):
            tok = self.tokens[idx]
            if tok.type == TokenType.LPAREN:
                paren_depth += 1
            elif tok.type == TokenType.RPAREN:
                paren_depth -= 1
                if paren_depth == 0:
                    if idx + 1 < len(self.tokens) and self.tokens[idx + 1].type == TokenType.ARROW:
                        return True
                    return False
            idx += 1
        return False

    def assignment_expression(self) -> ASTNode:
        """
        Nível 2: Atribuições simples e compostas (=, +=, -=, etc.), associativas à direita.
        Ex: a = b = c -> a = (b = c)
        """
        node = self.ternary_expression()
        if self.peek().type in ASSIGNMENT_TOKENS:
            op_tok = self.advance()
            op = op_tok.lexeme
            self._check_missing_operand(op)
            right = self.assignment_expression()

            # Extrai nome representativo para retrocompatibilidade
            if isinstance(node, Identifier):
                target_name = node.name
            elif isinstance(node, MemberAccess):
                target_name = f"{node.target.pretty() if hasattr(node.target, 'name') else 'target'}.{node.member_name}"
            elif isinstance(node, ArrayAccess):
                target_name = f"{node.array.name}[...]" if isinstance(node.array, Identifier) else "array[...]"
            else:
                target_name = "target"

            return Assignment(
                name=target_name,
                line=op_tok.line,
                expression=right,
                operator=op,
                column=op_tok.column,
                target=node
            )
        return node

    def ternary_expression(self) -> ASTNode:
        """
        Nível 3: Operador condicional ternário (?:), associativo à direita.
        Ex: cond ? val1 : cond2 ? val2 : val3
        """
        node = self.logical_or()
        if self.check(TokenType.QUESTION):
            q_tok = self.advance() # consome '?'
            self._check_missing_operand("?")
            then_expr = self.expression()
            self.expect(TokenType.COLON, "Era esperado ':' na expressão condicional ternária", expected="':'")
            self._check_missing_operand(":")
            else_expr = self.ternary_expression()
            return ConditionalExpression(node, then_expr, else_expr, q_tok.line, q_tok.column)
        return node

    def logical_or(self) -> ASTNode:
        """Nível 4: OR lógico (||)."""
        return self._parse_binary(self.logical_and, {TokenType.LOGICAL_OR})

    def logical_and(self) -> ASTNode:
        """Nível 5: AND lógico (&&)."""
        return self._parse_binary(self.bitwise_or, {TokenType.LOGICAL_AND})

    def bitwise_or(self) -> ASTNode:
        """Nível 6: OR bit a bit (|)."""
        return self._parse_binary(self.bitwise_xor, {TokenType.BITWISE_OR})

    def bitwise_xor(self) -> ASTNode:
        """Nível 7: XOR bit a bit (^)."""
        return self._parse_binary(self.bitwise_and, {TokenType.BITWISE_XOR})

    def bitwise_and(self) -> ASTNode:
        """Nível 8: AND bit a bit (&)."""
        return self._parse_binary(self.equality, {TokenType.BITWISE_AND})

    def equality(self) -> ASTNode:
        """Nível 9: Igualdade (==, !=)."""
        return self._parse_binary(self.relational, {TokenType.EQUAL, TokenType.NOT_EQUAL})

    def relational(self) -> ASTNode:
        """Nível 10: Relacionais (<, <=, >, >=) e verificação de tipo (instanceof)."""
        node = self.shift()
        rel_tokens = {
            TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER,
            TokenType.GREATER_EQUAL, TokenType.KEYWORD_INSTANCEOF
        }
        while self.peek().type in rel_tokens:
            if self.check(TokenType.KEYWORD_INSTANCEOF):
                op_tok = self.advance()
                self._check_missing_operand("instanceof")
                target_type = self.parse_type_reference()
                node = InstanceOfExpression(node, target_type, op_tok.line, op_tok.column)
            else:
                op_tok = self.advance()
                op = op_tok.lexeme
                self._check_missing_operand(op)
                right = self.shift()
                node = BinaryOp(op, node, right, line=op_tok.line, column=op_tok.column)
        return node

    def shift(self) -> ASTNode:
        """Nível 11: Deslocamentos de bits (<<, >>, >>>)."""
        return self._parse_binary(self.additive, {TokenType.LSHIFT, TokenType.RSHIFT, TokenType.URSHIFT})

    def additive(self) -> ASTNode:
        """Nível 12: Adição e subtração (+, -)."""
        return self._parse_binary(self.multiplicative, {TokenType.PLUS, TokenType.MINUS})

    def multiplicative(self) -> ASTNode:
        """Nível 13: Multiplicação, divisão e resto (*, /, %)."""
        return self._parse_binary(self.unary, {TokenType.STAR, TokenType.SLASH, TokenType.PERCENT})

    def _parse_binary(self, next_fn, token_types: Set[TokenType]) -> ASTNode:
        """Helper para expressões binárias associativas à esquerda com validação."""
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        node = next_fn()
        while self.peek().type in token_types:
            op_token = self.advance()
            op = op_token.lexeme
<<<<<<< HEAD
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
=======
            self._check_missing_operand(op)
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
            right = next_fn()
            node = BinaryOp(op, node, right, line=op_token.line, column=op_token.column)
        return node

<<<<<<< HEAD
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
=======
    def _check_missing_operand(self, op: str):
        """Verifica se o operando direito de uma operação está ausente ou inválido."""
        if (
            self.check(TokenType.SEMICOLON) or self.check(TokenType.EOF) or
            self.check(TokenType.RPAREN) or self.check(TokenType.COMMA) or
            self.check(TokenType.COLON) or self.check(TokenType.RBRACKET) or
            self.check(TokenType.RBRACE)
        ):
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message=f"Era esperado uma expressão após '{op}'",
                line=t.line,
                column=t.column,
                expected=f"uma expressão após '{op}'",
                found=found_repr,
            )
        # Operadores binários duplicados sem operando (ex: a + * b ou a + / b)
        dup_binaries = {
            TokenType.STAR, TokenType.SLASH, TokenType.PERCENT,
            TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.LOGICAL_AND,
            TokenType.LOGICAL_OR, TokenType.BITWISE_OR, TokenType.BITWISE_AND,
            TokenType.BITWISE_XOR, TokenType.LSHIFT, TokenType.RSHIFT, TokenType.URSHIFT,
        }
        if self.peek().type in dup_binaries:
            t = self.peek()
            raise SyntacticError(
                message=f"Era esperado uma expressão após '{op}'",
                line=t.line,
                column=t.column,
                expected=f"uma expressão após '{op}'",
                found=t.lexeme,
            )

    def unary(self) -> ASTNode:
        """
        Nível 14: Operadores unários prefixados (!, ~, ++, --, +, -) e conversões explícitas (casts).
        """
        # 1. Cast explícito: (Tipo) expressao
        if self.check(TokenType.LPAREN) and self._is_cast_ahead():
            return self.parse_cast_expression()

        # 2. Operadores unários prefixados: ++, --, +, -, !, ~
        if self.peek().type in {
            TokenType.LOGICAL_NOT, TokenType.BITWISE_NOT,
            TokenType.INCREMENT, TokenType.DECREMENT,
            TokenType.PLUS, TokenType.MINUS,
        }:
            op_tok = self.advance()
            self._check_missing_operand(op_tok.lexeme)
            operand = self.unary()
            return UnaryOp(op_tok.lexeme, operand, is_postfix=False, line=op_tok.line, column=op_tok.column)

        return self.postfix()

    def _is_cast_ahead(self) -> bool:
        """
        Determina se a abertura de parênteses à frente representa um cast: (Tipo) expressao
        em oposição a uma expressão agrupada: (expr).
        """
        idx = self.current + 1
        if idx >= len(self.tokens):
            return False

        first = self.tokens[idx]

        # 1. Tipos primitivos: (int) x, (double[]) arr
        if first.type in PRIMITIVE_TYPE_TOKENS and first.type != TokenType.KEYWORD_VOID:
            idx += 1
            while idx + 1 < len(self.tokens) and self.tokens[idx].type == TokenType.LBRACKET and self.tokens[idx+1].type == TokenType.RBRACKET:
                idx += 2
            return idx < len(self.tokens) and self.tokens[idx].type == TokenType.RPAREN

        # 2. Tipos de referência: (String) obj, (List<T>) list
        if first.type == TokenType.IDENTIFIER:
            idx += 1
            # Pula qualificadores: (java.lang.String)
            while idx + 1 < len(self.tokens) and self.tokens[idx].type == TokenType.DOT and self.tokens[idx+1].type == TokenType.IDENTIFIER:
                idx += 2

            # Pula generics: < ... >
            if idx < len(self.tokens) and self.tokens[idx].type == TokenType.LESS:
                idx += 1
                g_depth = 1
                while idx < len(self.tokens) and g_depth > 0:
                    if self.tokens[idx].type == TokenType.LESS:
                        g_depth += 1
                    elif self.tokens[idx].type == TokenType.GREATER:
                        g_depth -= 1
                    idx += 1

            # Pula dimensões de array: []
            while idx + 1 < len(self.tokens) and self.tokens[idx].type == TokenType.LBRACKET and self.tokens[idx+1].type == TokenType.RBRACKET:
                idx += 2

            if idx < len(self.tokens) and self.tokens[idx].type == TokenType.RPAREN:
                if idx + 1 < len(self.tokens):
                    after = self.tokens[idx + 1]
                    valid_cast_starters = {
                        TokenType.IDENTIFIER, TokenType.INT, TokenType.NUMBER, TokenType.DOUBLE, TokenType.FLOAT,
                        TokenType.STRING_LITERAL,
                        TokenType.CHAR_LITERAL, TokenType.BOOLEAN_LITERAL, TokenType.NULL_LITERAL,
                        TokenType.KEYWORD_THIS, TokenType.KEYWORD_SUPER, TokenType.KEYWORD_NEW,
                        TokenType.LPAREN, TokenType.LOGICAL_NOT, TokenType.BITWISE_NOT,
                    }
                    return after.type in valid_cast_starters
        return False

    def parse_cast_expression(self) -> CastExpression:
        """Processa conversão de tipo: (Tipo) expressao."""
        start_tok = self.advance() # consome '('
        target_type = self.parse_type_reference()
        self.expect(TokenType.RPAREN, "Era esperado ')' para fechar o tipo no cast", expected="')'")
        self._check_missing_operand(f"({target_type.name})")
        expr = self.unary()
        return CastExpression(target_type=target_type, expression=expr, line=start_tok.line, column=start_tok.column)

    def postfix(self) -> ASTNode:
        """
        Nível 15: Operações pós-fixadas e encadeamento:
        - Acesso a membros: alvo.campo
        - Chamada de método: alvo.metodo(args) ou metodo(args)
        - Acesso a array: array[indice]
        - Referência a método: alvo::metodo ou Tipo::new
        - Pós-fixados: expr++, expr--
        """
        node = self.primary()

        while True:
            # 1. Ponto '.' para membro ou chamada
            if self.check(TokenType.DOT):
                self.advance() # consome '.'
                if self.check(TokenType.KEYWORD_CLASS) or self.check(TokenType.KEYWORD_THIS) or self.check(TokenType.KEYWORD_SUPER):
                    member_tok = self.advance()
                else:
                    member_tok = self.expect(TokenType.IDENTIFIER, "Era esperado um identificador após '.'", expected="identificador após '.'")

                if self.check(TokenType.LPAREN):
                    self.advance() # consome '('
                    args = self.parse_arguments()
                    self.expect(TokenType.RPAREN, "Era esperado ')' para fechar argumentos", expected="')'")
                    node = MethodCall(method_name=member_tok.lexeme, target=node, arguments=args, line=member_tok.line, column=member_tok.column)
                else:
                    node = MemberAccess(target=node, member_name=member_tok.lexeme, line=member_tok.line, column=member_tok.column)

            # 2. Chamada direta de método após identificador: id(args)
            elif self.check(TokenType.LPAREN) and isinstance(node, Identifier):
                self.advance() # consome '('
                args = self.parse_arguments()
                self.expect(TokenType.RPAREN, "Era esperado ')' para fechar argumentos", expected="')'")
                node = MethodCall(method_name=node.name, target=None, arguments=args, line=node.line, column=node.column)

            # 3. Indexação de array: expr[indice]
            elif self.check(TokenType.LBRACKET):
                bracket_tok = self.advance() # consome '['
                if self.check(TokenType.RBRACKET):
                    raise SyntacticError(
                        message="Era esperado um índice entre colchetes",
                        line=bracket_tok.line,
                        column=bracket_tok.column,
                        expected="expressão de índice entre colchetes",
                        found="]",
                    )
                index_expr = self.expression()
                self.expect(TokenType.RBRACKET, "Era esperado ']' para fechar o índice do array", expected="']'")
                node = ArrayAccess(array=node, index=index_expr, line=bracket_tok.line, column=bracket_tok.column)

            # 4. Referência de método: alvo::metodo ou Tipo::new
            elif self.check(TokenType.DOUBLE_COLON):
                col_tok = self.advance() # consome '::'
                if self.check(TokenType.KEYWORD_NEW):
                    m_tok = self.advance()
                    method_name = m_tok.lexeme
                elif self.check(TokenType.IDENTIFIER):
                    m_tok = self.advance()
                    method_name = m_tok.lexeme
                else:
                    t = self.peek()
                    found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                    raise SyntacticError(
                        message="Era esperado um nome de método ou 'new' após '::'",
                        line=t.line,
                        column=t.column,
                        expected="nome de método ou 'new'",
                        found=found_repr,
                    )
                node = MethodReference(target=node, method_name=method_name, line=col_tok.line, column=col_tok.column)

            # 5. Operadores pós-fixados: expr++ ou expr--
            elif self.check(TokenType.INCREMENT) or self.check(TokenType.DECREMENT):
                op_tok = self.advance()
                node = UnaryOp(op=op_tok.lexeme, operand=node, is_postfix=True, line=op_tok.line, column=op_tok.column)

            else:
                break

        return node

    def parse_arguments(self) -> List[ASTNode]:
        """Processa lista de argumentos separados por vírgula dentro de parênteses."""
        args = []
        while not self.check(TokenType.RPAREN) and not self.check(TokenType.EOF):
            args.append(self.expression())
            if self.check(TokenType.COMMA):
                self.advance()
            else:
                break
        return args

    def primary(self) -> ASTNode:
        """Processa operandos primários, literais, instanciações e parênteses."""
        # 1. Instanciação com 'new': objetos ou arrays
        if self.check(TokenType.KEYWORD_NEW):
            return self.parse_new_expression()

        # 2. Inicializador de array literal: { 1, 2, 3 }
        if self.check(TokenType.LBRACE):
            return self.parse_array_initializer()

        # 3. Identificador ou 'this'/'super'
        if self.check(TokenType.IDENTIFIER) or self.check(TokenType.KEYWORD_THIS) or self.check(TokenType.KEYWORD_SUPER):
            tok = self.advance()
            return Identifier(tok.lexeme, line=tok.line, column=tok.column)

        # 4. Literais numéricos (inteiros, double, float), string, caractere, booleano e nulo
        if self.check(TokenType.INT) or self.check(TokenType.NUMBER):
            tok = self.advance()
            return Literal(tok.lexeme, "NUM", line=tok.line, column=tok.column)

        if self.check(TokenType.DOUBLE):
            tok = self.advance()
            return Literal(tok.lexeme, "DOUBLE", line=tok.line, column=tok.column)

        if self.check(TokenType.FLOAT):
            tok = self.advance()
            return Literal(tok.lexeme, "FLOAT", line=tok.line, column=tok.column)

        if self.check(TokenType.STRING_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "STRING", line=tok.line, column=tok.column)

        if self.check(TokenType.CHAR_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "CHAR", line=tok.line, column=tok.column)

        if self.check(TokenType.BOOLEAN_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "BOOLEAN", line=tok.line, column=tok.column)

>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
        if self.check(TokenType.NULL_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "NULL", line=tok.line, column=tok.column)

<<<<<<< HEAD
        # Agrupamento com parênteses: ( expressao )
=======
        # 5. Expressões entre parênteses com controle de profundidade
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
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
                self.expect(TokenType.RPAREN, "Era esperado ')' para fechar a expressão", expected="')'")
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

<<<<<<< HEAD
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
=======
    def parse_new_expression(self) -> ASTNode:
        """Processa instanciação de objeto 'new Tipo(args)' ou criação de array 'new Tipo[dim]'."""
        new_tok = self.advance() # consome 'new'
        tok = self.peek()
        if tok.type in PRIMITIVE_TYPE_TOKENS:
            self.advance()
            type_name = tok.lexeme
        elif tok.type == TokenType.IDENTIFIER:
            type_name = self.qualified_identifier()
        else:
            raise SyntacticError(
                message=f"Tipo inválido após 'new': '{tok.lexeme}'",
                line=tok.line,
                column=tok.column,
                expected="um tipo primitivo ou identificador de classe",
                found=tok.lexeme if tok.type != TokenType.EOF else "EOF",
            )

        type_args = []
        if self.check(TokenType.LESS):
            self.advance()
            while not self.check(TokenType.GREATER) and not self.check(TokenType.EOF):
                type_args.append(self.parse_type_reference())
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
                if self.check(TokenType.COMMA):
                    self.advance()
                else:
                    break
<<<<<<< HEAD
        if self.check(TokenType.RBRACE):
            self.advance()
        return Literal("{...}", "NUM", line=brace_tok.line, column=brace_tok.column)
=======
            self.expect(TokenType.GREATER, "Era esperado '>' para fechar argumentos genéricos", expected="'>'")

        base_type = TypeReference(type_name, array_dimensions=0, type_arguments=type_args, line=tok.line, column=tok.column)

        # Caso A: Criação de array: new Tipo[10] ou new Tipo[] { ... }
        if self.check(TokenType.LBRACKET):
            dimensions = []
            while self.check(TokenType.LBRACKET):
                self.advance() # consome '['
                if self.check(TokenType.RBRACKET):
                    self.advance() # consome ']'
                    dimensions.append(None)
                else:
                    dim_expr = self.expression()
                    self.expect(TokenType.RBRACKET, "Era esperado ']' para fechar dimensão do array", expected="']'")
                    dimensions.append(dim_expr)
            initializer = None
            if self.check(TokenType.LBRACE):
                initializer = self.parse_array_initializer()
            base_type.array_dimensions = len(dimensions)
            return ArrayCreationExpression(base_type, dimensions, initializer, new_tok.line, new_tok.column)

        # Caso B: Instanciação de classe: new Classe(args)
        self.expect(TokenType.LPAREN, "Era esperado '(' após tipo na instanciação com 'new'", expected="'('")
        args = self.parse_arguments()
        self.expect(TokenType.RPAREN, "Era esperado ')' após argumentos da instanciação", expected="')'")
        return ObjectCreationExpression(base_type, args, line=new_tok.line, column=new_tok.column)

    def parse_array_initializer(self) -> ArrayInitializer:
        """Processa inicializador literal de array: { 1, 2, 3 } ou { {1}, {2} }."""
        brace_tok = self.advance() # consome '{'
        elements = []
        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            elements.append(self.expression())
            if self.check(TokenType.COMMA):
                self.advance()
            else:
                break
        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar inicializador de array", expected="'}'")
        return ArrayInitializer(elements=elements, line=brace_tok.line, column=brace_tok.column)

    # -------------------------------------------------------------------------
    # 2.11 PREDICADOS DE DECISÃO SINTÁTICA (LOOKAHEAD)
    # -------------------------------------------------------------------------
    def _is_local_declaration(self) -> bool:
        """Determina se os próximos tokens representam uma declaração local de variável."""
        offset = 0
        if self.peek_offset(offset).type == TokenType.KEYWORD_FINAL:
            offset += 1

        t = self.peek_offset(offset)
        if t.type in PRIMITIVE_TYPE_TOKENS and t.type != TokenType.KEYWORD_VOID:
            return True

        if t.type == TokenType.IDENTIFIER:
            next_t = self.peek_offset(offset + 1)
            # Ex: String nome
            if next_t.type == TokenType.IDENTIFIER:
                return True
            # Ex: String[] nomes
            if next_t.type == TokenType.LBRACKET and self.peek_offset(offset + 2).type == TokenType.RBRACKET:
                return True
            # Ex: List<String> nomes
            if next_t.type == TokenType.LESS:
                return True

        return False

    def _is_assignment_ahead(self) -> bool:
        """Determina se o comando à frente é uma atribuição simples ou composta."""
        if self.check(TokenType.KEYWORD_THIS):
            if self.peek_offset(1).type == TokenType.DOT and self.peek_offset(3).type in ASSIGNMENT_TOKENS:
                return True
        if self.check(TokenType.IDENTIFIER) and self.peek_offset(1).type in ASSIGNMENT_TOKENS:
            return True
        return False

    def _is_method_signature(self) -> bool:
        """Determina se os tokens à frente representam uma assinatura de método (ex: int somar(...))."""
        t = self.peek()
        if t.type in PRIMITIVE_TYPE_TOKENS or t.type == TokenType.IDENTIFIER:
            next_t = self.peek_offset(1)
            if next_t.type == TokenType.IDENTIFIER and self.peek_offset(2).type == TokenType.LPAREN:
                return True
        return False
>>>>>>> ba7ca9076e818d78e8d714d5e78ed7c05ebef71a
