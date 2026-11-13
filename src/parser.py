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

from typing import List, Optional, Set, Any, Tuple
from .token import Token, TokenType
from .ast_nodes import (
    ASTNode, Program, CompilationUnit, PackageDeclaration, ImportDeclaration,
    ClassDeclaration, InterfaceDeclaration, EnumDeclaration, EnumConstant,
    FieldDeclaration, MethodDeclaration, ConstructorDeclaration, Parameter,
    TypeReference, Block, ReturnStatement, Declaration, LocalVariableDeclaration,
    Assignment, BinaryOp, UnaryOp, MethodCall, Literal, Identifier,
    ExpressionStatement, EmptyStatement, IfStatement, WhileStatement,
    DoWhileStatement, ForStatement, EnhancedForStatement, SwitchStatement,
    SwitchCase, BreakStatement, ContinueStatement, ThrowStatement,
    AssertStatement, TryStatement, CatchClause, SynchronizedStatement,
    UnsupportedStatement,
    BlockStatement, LocalClassOrInterfaceDeclaration, Statement,
    LocalVariableType, LocalVariableDeclarationStatement, LabeledStatement,
    StatementExpressionList, SwitchLabel, CaseConstantList, CaseLabel,
    DefaultLabel, SwitchBlockStatementGroup, SwitchRule, SwitchBlock,
    SwitchExpression, YieldStatement, CatchType, Resource,
    ResourceSpecification,
    ConditionalExpression, MemberAccess, ArrayAccess, ObjectCreationExpression,
    ArrayInitializer, ArrayCreationExpression, CastExpression,
    InstanceOfExpression, PatternInstanceOfExpression, LambdaExpression, LambdaParameter, MethodReference,
    ComponentPattern, Pattern, PatternVariable, TypePattern, ComponentPatternList,
    RecordPattern, MatchAllPattern, Guard, PatternCaseLabel,
    Annotation, MarkerAnnotation, SingleElementAnnotation, NormalAnnotation,
    ElementValue, ElementValueList, ElementValueArrayInitializer,
    ElementValuePair, ElementValuePairList, ClassLiteral,
    AnnotationInterfaceElementModifier, AnnotationDefaultValue,
    AnnotationInterfaceMemberDeclaration, AnnotationInterfaceElementDeclaration,
    AnnotationInterfaceBody, AnnotationInterfaceDeclaration,
    WildcardType, TypeParameter,
    OrdinaryCompilationUnit, ModularCompilationUnit, CompactCompilationUnit,
    SingleTypeImport, TypeImportOnDemand, SingleStaticImport, StaticImportOnDemand,
    SingleModuleImport, ModuleDirective, RequiresDirective, ExportsDirective,
    OpensDirective, UsesDirective, ProvidesDirective, ModuleDeclaration,
    VariableDeclaratorId, VariableDeclarator, ReceiverParameter, FormalParameter,
    VariableArityParameter, ExplicitConstructorInvocation, AlternateConstructorInvocation,
    SuperclassConstructorInvocation, ConstructorBody, InstanceInitializer, StaticInitializer,
    InterfaceExtends, InterfacePermits, InterfaceBody, InterfaceMemberDeclaration,
    InterfaceConstantDeclaration, InterfaceMethodDeclaration,
    EnumConstantBody, EnumConstantList, EnumBodyDeclarations, EnumBody,
    RecordComponentModifier, RecordComponent, VariableArityRecordComponent,
    RecordComponentList, RecordHeader, RecordBodyDeclaration,
    NormalCanonicalConstructor, CompactConstructorDeclaration, NonCanonicalRecordConstructor,
    RecordBody, RecordDeclaration
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
    """
    Exceção estruturada para erros sintáticos.
    Informa linha, coluna, o que era esperado e o símbolo encontrado.
    """
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
    Parser descendente recursivo para arquivos e fragmentos da linguagem Java.
    Reconhece unidades de compilação completas e preserva compatibilidade com
    fragmentos isolados de comandos das etapas anteriores.
    """
    def __init__(self, tokens: List[Token], enable_preview_primitive_patterns: bool = False):
        self.tokens = list(tokens) if tokens is not None else []
        self.current = 0
        self.depth = 0
        self.max_depth = 200
        self._pattern_depth = 0
        self.max_pattern_depth = 128
        self.enable_preview_primitive_patterns = enable_preview_primitive_patterns

    # -------------------------------------------------------------------------
    # 2.1 MÉTODOS AUXILIARES DE NAVEGAÇÃO E INSPEÇÃO DE TOKENS
    # -------------------------------------------------------------------------
    def peek(self) -> Token:
        """Retorna o token atual sem consumir."""
        if self.current < len(self.tokens):
            return self.tokens[self.current]
        last_line = self.tokens[-1].line if self.tokens else 1
        last_col = self.tokens[-1].column if self.tokens else 1
        return Token(TokenType.EOF, "", last_line, last_col)

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
        if self.current < len(self.tokens):
            self.current += 1
        return tok

    def check(self, token_type: TokenType) -> bool:
        """Verifica se o token atual é do tipo esperado."""
        return self.peek().type == token_type

    def expect(self, token_type: TokenType, message: str, expected: str = None) -> Token:
        """
        Exige que o token atual seja do tipo especificado.
        Se não for, lança SyntacticError estruturado com a linha e coluna exatas.
        """
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

    # -------------------------------------------------------------------------
    # 2.2 PONTO DE ENTRADA: PARSE DE UNIDADE DE COMPILAÇÃO (JAVA SE 26 / JLS §7.3)
    # -------------------------------------------------------------------------
    def parse(self, mode: Optional[str] = None) -> CompilationUnit:
        """
        Ponto de entrada principal do parser (JLS §7.3).
        Reconhece as 3 modalidades normativas de unidades de compilação:
        - ModularCompilationUnit: {ImportDeclaration} ModuleDeclaration
        - CompactCompilationUnit: {ImportDeclaration} {ClassBodyDeclaration}
        - OrdinaryCompilationUnit: [PackageDeclaration] {ImportDeclaration} {TypeDeclaration}
        """
        try:
            # Se for entrada vazia (apenas EOF)
            if self.check(TokenType.EOF):
                return OrdinaryCompilationUnit()

            # 1. Declaração opcional de pacote (com possíveis anotações precedentes)
            pkg_decl = None
            has_package = False
            if self._is_package_declaration_ahead():
                pkg_annos = self._parse_optional_annotations()
                pkg_decl = self.package_declaration(modifiers=pkg_annos)
                has_package = True

            # 2. Declarações de importação (zero ou mais)
            imports: List[ImportDeclaration] = []
            while self.check(TokenType.KEYWORD_IMPORT):
                imports.append(self.import_declaration())

            # 3. Unidade Modular (JLS §7.3 / §7.7)
            if not has_package and self._is_module_declaration_ahead():
                mod_annos = self._parse_optional_annotations()
                mod_decl = self.parse_module_declaration(leading_annotations=mod_annos)
                if not self.check(TokenType.EOF):
                    t = self.peek()
                    raise SyntacticError(
                        message="Tokens indevidos após a declaração do módulo na unidade de compilação modular",
                        line=t.line,
                        column=t.column,
                        expected="fim de arquivo (EOF). Tokens indevidos após a declaração do módulo",
                        found=t.lexeme if t.type != TokenType.EOF else "EOF",
                    )
                return ModularCompilationUnit(imports=imports, module_declaration=mod_decl, line=mod_decl.line, column=mod_decl.column)

            if has_package and self._is_module_declaration_ahead():
                t = self.peek()
                raise SyntacticError(
                    message="Declarações de módulo não são permitidas após declaração de pacote",
                    line=t.line,
                    column=t.column,
                    expected="declaração de classe, interface ou enum",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )

            # 4. Unidade Compacta (JLS §7.3)
            # Sem package, e com membros de corpo de classe declarados no nível superior
            if not has_package and (mode == "compact" or self._is_compact_compilation_unit()):
                return self.parse_compact_compilation_unit(imports)

            # 5. Unidade Ordinária (JLS §7.3) ou modo de comandos didáticos
            unit = OrdinaryCompilationUnit(package=pkg_decl, imports=imports)

            while not self.check(TokenType.EOF):
                old_current = self.current

                # Captura annotations e modificadores no nível superior
                annos, modifiers = self._parse_annotations_and_modifiers()

                if self._is_annotation_interface_declaration_ahead():
                    decl = self.annotation_interface_declaration(modifiers, annotations=annos)
                    unit.type_declarations.append(decl)
                elif self.check(TokenType.KEYWORD_CLASS):
                    decl = self.class_declaration(modifiers)
                    decl.annotations = annos
                    unit.type_declarations.append(decl)
                elif self.check(TokenType.KEYWORD_INTERFACE):
                    decl = self.interface_declaration(modifiers, annotations=annos)
                    unit.type_declarations.append(decl)
                elif self.check(TokenType.KEYWORD_ENUM):
                    decl = self.enum_declaration(modifiers, annotations=annos)
                    unit.type_declarations.append(decl)
                elif self._is_record_declaration_ahead(allow_missing_name=True):
                    decl = self.record_declaration(modifiers, annotations=annos)
                    unit.type_declarations.append(decl)
                elif modifiers:
                    # Modificadores presentes, mas sem class/interface/enum/record
                    t = self.peek()
                    found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                    raise SyntacticError(
                        message="Declarações de métodos e campos não são permitidas no nível superior fora de uma classe, interface, enum ou record",
                        line=t.line,
                        column=t.column,
                        expected="'class', 'interface', 'enum' ou 'record' no nível superior",
                        found=found_repr,
                    )
                else:
                    if self._is_method_signature():
                        t = self.peek()
                        raise SyntacticError(
                            message="Declarações de métodos não são permitidas no nível superior fora de uma classe ou interface",
                            line=t.line,
                            column=t.column,
                            expected="declaração de classe, interface ou enum",
                            found=t.lexeme if t.type != TokenType.EOF else "EOF",
                        )

                    # Modo fragmento didático
                    stmt = self.statement()
                    unit.statements.append(stmt)

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
            t = self.peek()
            raise SyntacticError(
                message="Limite de aninhamento / recursão do sistema excedido na análise sintática",
                line=t.line,
                column=t.column,
                expected="expressão dentro do limite de aninhamento suportado",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )

    # -------------------------------------------------------------------------
    # 2.3 DECLARAÇÃO DE PACOTE E IMPORTS (JLS §7.4, §7.5)
    # -------------------------------------------------------------------------
    def package_declaration(self, modifiers: List[ASTNode] = None) -> PackageDeclaration:
        """Processa: [annotations] package nome.do.pacote;"""
        if modifiers is None:
            modifiers = self._parse_optional_annotations()
        pkg_tok = self.advance() # consome 'package'
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado um identificador após 'package'",
                line=t.line,
                column=t.column,
                expected="identificador após 'package'",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        name = self.qualified_identifier()
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da declaração de package", expected="';' ao final da declaração de package")
        return PackageDeclaration(name=name, line=pkg_tok.line, column=pkg_tok.column, modifiers=modifiers)

    def import_declaration(self) -> ImportDeclaration:
        """
        Processa declarações de importação da JLS §7.5:
        - SingleTypeImport: import TypeName;
        - TypeImportOnDemand: import PackageOrTypeName.*;
        - SingleStaticImport: import static TypeName.Identifier;
        - StaticImportOnDemand: import static TypeName.*;
        - SingleModuleImport: import module ModuleName;
        """
        imp_tok = self.advance() # consome 'import'

        if self.check(TokenType.SEMICOLON):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado um identificador após 'import'",
                line=t.line,
                column=t.column,
                expected="identificador após 'import'",
                found=";",
            )

        # SingleModuleImport (Java 23+ / 26): import module ModuleName;
        if (
            self.check(TokenType.IDENTIFIER)
            and self.peek().lexeme == "module"
            and self.peek_offset(1).type != TokenType.DOT
        ):
            self.advance() # consome 'module'
            if not self.check(TokenType.IDENTIFIER):
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado o nome do módulo após 'import module'",
                    line=t.line,
                    column=t.column,
                    expected="nome do módulo após 'import module'",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            mod_name = self.qualified_identifier()
            self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final do import de módulo", expected="';'")
            return SingleModuleImport(name=mod_name, line=imp_tok.line, column=imp_tok.column)

        # Static imports: import static ...
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
        full_name = ".".join(parts)

        if is_static:
            if is_wildcard:
                return StaticImportOnDemand(name=full_name, line=imp_tok.line, column=imp_tok.column)
            else:
                return SingleStaticImport(name=full_name, line=imp_tok.line, column=imp_tok.column)
        else:
            if is_wildcard:
                return TypeImportOnDemand(name=full_name, line=imp_tok.line, column=imp_tok.column)
            else:
                return SingleTypeImport(name=full_name, line=imp_tok.line, column=imp_tok.column)

    def qualified_identifier(self) -> str:
        """Lê identificadores separados por ponto: a.b.c"""
        parts = [self.expect(TokenType.IDENTIFIER, "Era esperado um identificador").lexeme]
        while self.check(TokenType.DOT):
            self.advance()
            parts.append(self.expect(TokenType.IDENTIFIER, "Era esperado um identificador após '.'", expected="identificador após '.'").lexeme)
        return ".".join(parts)

    def _is_non_sealed_ahead(self, offset: int = 0) -> bool:
        """Verifica se há o modificador contextual 'non-sealed' (3 tokens contíguos)."""
        t1 = self.peek_offset(offset)
        t2 = self.peek_offset(offset + 1)
        t3 = self.peek_offset(offset + 2)
        return (
            t1.type == TokenType.IDENTIFIER
            and t1.lexeme == "non"
            and t2.type == TokenType.MINUS
            and t3.type == TokenType.IDENTIFIER
            and t3.lexeme == "sealed"
            and t1.line == t2.line == t3.line
            and t2.column == t1.column + 3
            and t3.column == t2.column + 1
        )

    def _is_sealed_modifier_ahead(self, offset: int = 0) -> bool:
        """Verifica se o token 'sealed' atua como modificador contextual (e não identificador comum)."""
        t = self.peek_offset(offset)
        if t.type != TokenType.IDENTIFIER or t.lexeme != "sealed":
            return False
        nxt = self.peek_offset(offset + 1)
        return nxt.type not in (
            TokenType.ASSIGN,
            TokenType.LPAREN,
            TokenType.SEMICOLON,
            TokenType.COMMA,
            TokenType.DOT,
            TokenType.LBRACKET,
            TokenType.RPAREN,
            TokenType.DOUBLE_COLON,
            TokenType.EOF,
        )

    def _is_record_declaration_ahead(self, offset: int = 0, allow_missing_name: bool = False) -> bool:
        """Verifica se há o início de uma declaração de record (JLS §8.10)."""
        t = self.peek_offset(offset)
        if t.type != TokenType.IDENTIFIER or t.lexeme != "record":
            return False
        nxt = self.peek_offset(offset + 1)
        if nxt.type == TokenType.IDENTIFIER or nxt.type == TokenType.LESS:
            return True
        if allow_missing_name and nxt.type in (TokenType.LPAREN, TokenType.LBRACE):
            return True
        return False

    def parse_modifiers(self, allow_default: bool = False, allow_sealed: bool = True) -> List[str]:
        """Lê modificadores contíguos (public, static, final, default, sealed, non-sealed, etc.)."""
        mods = []
        while True:
            if self.peek().type in MODIFIER_TOKENS:
                mods.append(self.advance().lexeme)
            elif allow_default and self.check(TokenType.KEYWORD_DEFAULT):
                mods.append(self.advance().lexeme)
            elif allow_sealed and self._is_non_sealed_ahead():
                self.advance() # non
                self.advance() # -
                self.advance() # sealed
                mods.append("non-sealed")
            elif allow_sealed and self._is_sealed_modifier_ahead():
                mods.append(self.advance().lexeme)
            else:
                break
        return mods

    def _parse_annotations_and_modifiers(self, allow_default: bool = False, allow_sealed: bool = True) -> Tuple[List[ASTNode], List[str]]:
        """Lê anotações e modificadores possivelmente intercalados."""
        annos, _pre, _post, mods = self._parse_annotations_and_modifiers_detailed(
            allow_default=allow_default,
            allow_sealed=allow_sealed,
        )
        return annos, mods

    # -------------------------------------------------------------------------
    # 2.4 DECLARAÇÕES DE CLASSES, INTERFACES, ENUMS E RECORDS
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

        type_parameters = []
        if self.check(TokenType.LESS):
            type_parameters = self.parse_type_parameters()

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

        permits_types = []
        if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "permits":
            self.advance()
            permits_types.append(self.parse_type_reference())
            while self.check(TokenType.COMMA):
                self.advance()
                permits_types.append(self.parse_type_reference())

        self.expect(TokenType.LBRACE, "Era esperado '{' para abrir o corpo da classe", expected="'{'")

        members = []
        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            members.append(self.class_member(class_name))

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o corpo da classe", expected="'}'")
        return ClassDeclaration(
            name=class_name,
            modifiers=modifiers,
            extends_type=extends_type,
            implements_types=implements_types,
            members=members,
            line=class_tok.line,
            column=class_tok.column,
            type_parameters=type_parameters,
            permits_types=permits_types
        )

    def interface_declaration(self, modifiers: List[str], annotations: List[ASTNode] = None) -> InterfaceDeclaration:
        """Processa a declaração de uma interface normal Java (JLS §9.1)."""
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
            type_parameters = self.parse_type_parameters()

        extends_types = []
        if self.check(TokenType.KEYWORD_EXTENDS):
            self.advance()
            extends_types.append(self.parse_type_reference())
            while self.check(TokenType.COMMA):
                self.advance()
                extends_types.append(self.parse_type_reference())

        if self.check(TokenType.KEYWORD_IMPLEMENTS):
            t = self.peek()
            raise SyntacticError(
                message="Interfaces não podem possuir cláusula 'implements'; utilize 'extends' para superinterfaces (JLS §9.1.3)",
                line=t.line,
                column=t.column,
                expected="'permits' ou '{' (interfaces não permitem 'implements')",
                found="implements",
            )

        permits_types = []
        if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "permits":
            self.advance()
            permits_types.append(self.parse_type_reference())
            while self.check(TokenType.COMMA):
                self.advance()
                permits_types.append(self.parse_type_reference())

        lbrace_tok = self.expect(TokenType.LBRACE, "Era esperado '{' para abrir o corpo da interface", expected="'{'")

        members = []
        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            members.append(self.interface_member(iface_name))

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o corpo da interface", expected="'}'")
        iface_body = InterfaceBody(members=members, line=lbrace_tok.line, column=lbrace_tok.column)
        return InterfaceDeclaration(
            name=iface_name,
            modifiers=modifiers,
            type_parameters=type_parameters,
            extends_types=extends_types,
            members=members,
            line=iface_tok.line,
            column=iface_tok.column,
            permits_types=permits_types,
            annotations=annotations or [],
            body=iface_body,
        )

    def enum_declaration(self, modifiers: List[str], annotations: List[ASTNode] = None) -> EnumDeclaration:
        """Processa a declaração de um enum Java (JLS §8.9)."""
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

        if self.check(TokenType.KEYWORD_EXTENDS):
            t = self.peek()
            raise SyntacticError(
                message="Enums não podem possuir cláusula 'extends' explícita (JLS §8.9)",
                line=t.line,
                column=t.column,
                expected="'implements' ou '{' (enums não permitem 'extends')",
                found="extends",
            )

        implements_types = []
        if self.check(TokenType.KEYWORD_IMPLEMENTS):
            self.advance()
            implements_types.append(self.parse_type_reference())
            while self.check(TokenType.COMMA):
                self.advance()
                implements_types.append(self.parse_type_reference())

        lbrace_tok = self.expect(TokenType.LBRACE, "Era esperado '{' para abrir o corpo do enum", expected="'{'")

        constants: List[EnumConstant] = []
        has_trailing_comma = False

        # Comma solta sem nenhuma constante inicial é malformação da lista de constantes
        if self.check(TokenType.COMMA):
            t = self.peek()
            raise SyntacticError(
                message="Lista de constantes do enum malformada: ',' inesperada antes de qualquer constante",
                line=t.line,
                column=t.column,
                expected="nome de constante do enum, ';' ou '}'",
                found=",",
            )

        while not self.check(TokenType.SEMICOLON) and not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            c_annos = self._parse_optional_annotations()
            if not self.check(TokenType.IDENTIFIER):
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado o nome da constante na lista de constantes do enum",
                    line=t.line,
                    column=t.column,
                    expected="nome de constante do enum",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            c_tok = self.advance()
            args: List[ASTNode] = []
            if self.check(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.expression())
                    while self.check(TokenType.COMMA):
                        self.advance()
                        args.append(self.expression())
                self.expect(TokenType.RPAREN, "Era esperado ')' após argumentos da constante do enum", expected="')'")

            c_body: Optional[EnumConstantBody] = None
            if self.check(TokenType.LBRACE):
                cb_tok = self.advance()
                cb_members = []
                while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
                    cb_members.append(self.class_member(c_tok.lexeme))
                self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o corpo específico da constante do enum", expected="'}'")
                c_body = EnumConstantBody(members=cb_members, line=cb_tok.line, column=cb_tok.column)

            constants.append(
                EnumConstant(
                    name=c_tok.lexeme,
                    arguments=args,
                    line=c_tok.line,
                    column=c_tok.column,
                    annotations=c_annos,
                    body=c_body,
                )
            )

            if self.check(TokenType.COMMA):
                self.advance()
                has_trailing_comma = True
                if self.check(TokenType.COMMA):
                    t = self.peek()
                    raise SyntacticError(
                        message="Lista de constantes do enum malformada: vírgula duplicada ',,'",
                        line=t.line,
                        column=t.column,
                        expected="nome de constante, ';' ou '}' após ','",
                        found=",",
                    )
            elif self.check(TokenType.SEMICOLON) or self.check(TokenType.RBRACE):
                has_trailing_comma = False
                break
            else:
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado ',', ';' ou '}' após constante do enum",
                    line=t.line,
                    column=t.column,
                    expected="',', ';' ou '}'",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )

        members: List[ASTNode] = []
        has_semicolon = False
        body_declarations: Optional[EnumBodyDeclarations] = None
        if self.check(TokenType.SEMICOLON):
            sem_tok = self.advance()
            has_semicolon = True
            while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
                members.append(self.class_member(enum_name))
            body_declarations = EnumBodyDeclarations(members=members, has_semicolon=True, line=sem_tok.line, column=sem_tok.column)

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o corpo do enum", expected="'}'")
        const_list = EnumConstantList(constants=constants, has_trailing_comma=has_trailing_comma, line=lbrace_tok.line, column=lbrace_tok.column)
        enum_body = EnumBody(constant_list=const_list, body_declarations=body_declarations, line=lbrace_tok.line, column=lbrace_tok.column)
        return EnumDeclaration(
            name=enum_name,
            modifiers=modifiers,
            implements_types=implements_types,
            constants=constants,
            members=members,
            line=enum_tok.line,
            column=enum_tok.column,
            annotations=annotations or [],
            body=enum_body,
            has_trailing_comma=has_trailing_comma,
            has_semicolon=has_semicolon,
        )

    def record_declaration(self, modifiers: List[str], annotations: List[ASTNode] = None) -> RecordDeclaration:
        """
        Processa a declaração de um record Java (JLS §8.10):
        {ClassModifier} record TypeIdentifier [TypeParameters] RecordHeader [ClassImplements] RecordBody
        """
        rec_tok = self.advance() # consome 'record'
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado o nome do record após 'record'",
                line=t.line,
                column=t.column,
                expected="o nome do record",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        rec_name = self.advance().lexeme

        type_parameters: List[TypeParameter] = []
        if self.check(TokenType.LESS):
            type_parameters = self.parse_type_parameters()

        hdr_tok = self.expect(TokenType.LPAREN, "Era esperado '(' para iniciar o cabeçalho do record (RecordHeader)", expected="'(' para o RecordHeader")
        components: List[RecordComponent] = []
        while not self.check(TokenType.RPAREN) and not self.check(TokenType.EOF):
            if components and components[-1].is_varargs:
                t = self.peek()
                raise SyntacticError(
                    message="Componente varargs ('...') deve ser obrigatoriamente o último componente do record (JLS §8.10.1)",
                    line=t.line,
                    column=t.column,
                    expected="')' após componente varargs",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )

            c_annos = self._parse_optional_annotations()
            if self.check(TokenType.KEYWORD_VOID):
                t = self.peek()
                raise SyntacticError(
                    message="Componente de record não pode possuir tipo 'void'",
                    line=t.line,
                    column=t.column,
                    expected="tipo válido do componente do record",
                    found="void",
                )
            c_type = self.parse_type_reference(leading_annotations=c_annos)
            ellipsis_annos: List[ASTNode] = []
            if self.check(TokenType.AT):
                ellipsis_annos = self._parse_optional_annotations()
            if not c_type.is_varargs and self.check(TokenType.ELLIPSIS):
                self.advance()
                c_type.is_varargs = True

            if not self.check(TokenType.IDENTIFIER):
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado o nome do componente após o tipo no cabeçalho do record",
                    line=t.line,
                    column=t.column,
                    expected="nome do componente do record",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            comp_tok = self.advance()

            if c_type.is_varargs:
                comp = VariableArityRecordComponent(
                    type_ref=c_type,
                    name=comp_tok.lexeme,
                    annotations=c_annos,
                    is_varargs=True,
                    ellipsis_annotations=ellipsis_annos,
                    line=comp_tok.line,
                    column=comp_tok.column,
                )
            else:
                comp = RecordComponent(
                    type_ref=c_type,
                    name=comp_tok.lexeme,
                    annotations=c_annos,
                    is_varargs=False,
                    line=comp_tok.line,
                    column=comp_tok.column,
                )
            components.append(comp)

            if self.check(TokenType.COMMA):
                self.advance()
                if self.check(TokenType.RPAREN):
                    t = self.peek()
                    raise SyntacticError(
                        message="Era esperado outro componente de record após ','",
                        line=t.line,
                        column=t.column,
                        expected="componente de record após ','",
                        found=")",
                    )
            else:
                break

        self.expect(TokenType.RPAREN, "Era esperado ')' para fechar o cabeçalho do record", expected="')'")
        comp_list = RecordComponentList(components=components, line=hdr_tok.line, column=hdr_tok.column)
        rec_header = RecordHeader(component_list=comp_list, line=hdr_tok.line, column=hdr_tok.column)

        if self.check(TokenType.KEYWORD_EXTENDS):
            t = self.peek()
            raise SyntacticError(
                message="Records não podem possuir cláusula 'extends' explícita (JLS §8.10)",
                line=t.line,
                column=t.column,
                expected="'implements' ou '{' (records não permitem 'extends')",
                found="extends",
            )

        implements_types: List[TypeReference] = []
        if self.check(TokenType.KEYWORD_IMPLEMENTS):
            self.advance()
            implements_types.append(self.parse_type_reference())
            while self.check(TokenType.COMMA):
                self.advance()
                implements_types.append(self.parse_type_reference())

        lbrace_tok = self.expect(TokenType.LBRACE, "Era esperado '{' para abrir o corpo do record", expected="'{'")
        declarations: List[ASTNode] = []
        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            declarations.append(self.record_member(rec_name, components))

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o corpo do record", expected="'}'")
        rec_body = RecordBody(declarations=declarations, line=lbrace_tok.line, column=lbrace_tok.column)
        return RecordDeclaration(
            name=rec_name,
            header=rec_header,
            modifiers=modifiers,
            type_parameters=type_parameters,
            implements_types=implements_types,
            body=rec_body,
            annotations=annotations or [],
            line=rec_tok.line,
            column=rec_tok.column,
        )

    def _record_params_match_types(self, params: List[Parameter], components: List[RecordComponent]) -> bool:
        """Verifica se os parâmetros formais correspondem em quantidade, tipo e requisito de varargs aos componentes."""
        if len(params) != len(components):
            return False
        for p, c in zip(params, components):
            p_varargs = bool(getattr(p, "is_varargs", False) or (p.type_ref and p.type_ref.is_varargs))
            c_varargs = bool(c.is_varargs)
            if p_varargs != c_varargs:
                return False
            p_type = p.type_ref.get_effective_type(getattr(p, "dims", 0)) if p.type_ref else ""
            c_type = c.type_ref.full_name if c.type_ref else ""
            if p_type != c_type:
                return False
        return True

    def record_member(self, rec_name: str, header_components: List[RecordComponent]) -> ASTNode:
        """Processa uma declaração membro no corpo de um record (JLS §8.10.2 / §8.10.4)."""
        if self.check(TokenType.SEMICOLON):
            sem_tok = self.advance()
            return EmptyStatement(line=sem_tok.line, column=sem_tok.column)

        annos, _pre_annos, post_annos, mods = self._parse_annotations_and_modifiers_detailed(allow_sealed=True)

        # Inicializador de instância (sintaticamente reconhecido para diagnóstico semântico) ou estático
        if not mods and not annos and self.check(TokenType.LBRACE):
            block = self.parse_block()
            return InstanceInitializer(block=block, line=block.line, column=block.column)

        if mods == ["static"] and not annos and self.check(TokenType.LBRACE):
            block = self.parse_block()
            return StaticInitializer(block=block, line=block.line, column=block.column)

        # Tipos aninhados
        if self._is_annotation_interface_declaration_ahead():
            return self.annotation_interface_declaration(mods, annotations=annos)
        if self.check(TokenType.KEYWORD_CLASS):
            decl = self.class_declaration(mods)
            decl.annotations = annos
            return decl
        if self.check(TokenType.KEYWORD_INTERFACE):
            return self.interface_declaration(mods, annotations=annos)
        if self.check(TokenType.KEYWORD_ENUM):
            return self.enum_declaration(mods, annotations=annos)
        if self._is_record_declaration_ahead(allow_missing_name=True):
            return self.record_declaration(mods, annotations=annos)

        type_params: List[TypeParameter] = []
        if self.check(TokenType.LESS):
            type_params = self.parse_type_parameters()

        # Construtor canônico compacto (JLS §8.10.4.2): {ConstructorModifier} SimpleTypeName ConstructorBody
        if (
            not type_params
            and self.check(TokenType.IDENTIFIER)
            and self.peek().lexeme == rec_name
            and self.peek_offset(1).type == TokenType.LBRACE
        ):
            ctor_tok = self.advance()
            body = self.parse_constructor_body(ctor_tok.lexeme)
            return CompactConstructorDeclaration(
                name=ctor_tok.lexeme,
                parameters=[],
                modifiers=mods,
                throws_types=[],
                body=body,
                line=ctor_tok.line,
                column=ctor_tok.column,
                annotations=annos,
                derived_parameters=list(header_components),
                has_formal_parameter_list=False,
            )

        # Construtor com lista formal de parâmetros (normal canônico ou não canônico)
        if self.check(TokenType.IDENTIFIER) and self.peek_offset(1).type == TokenType.LPAREN:
            if type_params or self.peek().lexeme == rec_name or not any(m in ("static", "abstract", "native", "synchronized") for m in mods):
                ctor_tok = self.advance()
                recv_param, params = self.parse_formal_parameters()
                throws_types = self.parse_throws_clause()
                body = self.parse_constructor_body(ctor_tok.lexeme)

                has_alt_ctor = isinstance(body, ConstructorBody) and isinstance(body.constructor_invocation, AlternateConstructorInvocation)
                types_match = self._record_params_match_types(params, header_components)
                names_match = len(params) == len(header_components) and all(p.name == c.name for p, c in zip(params, header_components))

                if types_match and names_match:
                    return NormalCanonicalConstructor(
                        name=ctor_tok.lexeme,
                        parameters=params,
                        modifiers=mods,
                        throws_types=throws_types,
                        body=body,
                        line=ctor_tok.line,
                        column=ctor_tok.column,
                        receiver_parameter=recv_param,
                        type_parameters=type_params,
                        annotations=annos,
                    )
                if types_match and not has_alt_ctor:
                    return NormalCanonicalConstructor(
                        name=ctor_tok.lexeme,
                        parameters=params,
                        modifiers=mods,
                        throws_types=throws_types,
                        body=body,
                        line=ctor_tok.line,
                        column=ctor_tok.column,
                        receiver_parameter=recv_param,
                        type_parameters=type_params,
                        annotations=annos,
                    )
                return NonCanonicalRecordConstructor(
                    name=ctor_tok.lexeme,
                    parameters=params,
                    modifiers=mods,
                    throws_types=throws_types,
                    body=body,
                    line=ctor_tok.line,
                    column=ctor_tok.column,
                    receiver_parameter=recv_param,
                    type_parameters=type_params,
                    annotations=annos,
                )

        # Método ou Campo dentro do Record
        return self._parse_method_or_field_after_prefix(annos, mods, type_params, post_annos=post_annos)

    # -------------------------------------------------------------------------
    # 2.5 MEMBROS DE CLASSE (CAMPOS, CONSTRUTORES, MÉTODOS, INICIALIZADORES - ETAPA S3)
    # -------------------------------------------------------------------------
    def parse_variable_declarator_id(self) -> VariableDeclaratorId:
        """
        Processa identificador de variável com dimensões opcionais (JLS §8.3):
        (Identifier | _) [Dims]
        """
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado um identificador de variável",
                line=t.line,
                column=t.column,
                expected="identificador de variável",
                found=t.lexeme if t.type != TokenType.EOF else "EOF"
            )
        id_tok = self.advance()
        dims, dims_annos = self._parse_trailing_dims_with_annotations()
        return VariableDeclaratorId(
            name=id_tok.lexeme,
            dims=dims,
            dims_annotations=dims_annos,
            line=id_tok.line,
            column=id_tok.column,
        )

    def variable_initializer(self) -> ASTNode:
        """Processa inicializador de variável (expressão ou inicializador de array literal)."""
        if self.check(TokenType.LBRACE):
            return self.parse_array_initializer()
        return self.expression()

    def _is_constructor_invocation_ahead(self) -> bool:
        """Verifica se os próximos tokens iniciam uma invocação explícita de construtor (JLS §8.8.7.1)."""
        if self.check(TokenType.KEYWORD_THIS) and self.peek_offset(1).type == TokenType.LPAREN:
            return True
        if self.check(TokenType.KEYWORD_SUPER) and self.peek_offset(1).type == TokenType.LPAREN:
            return True
        if self.check(TokenType.LESS):
            depth = 1
            idx = 1
            while depth > 0 and self.peek_offset(idx).type != TokenType.EOF:
                if self.peek_offset(idx).type == TokenType.LESS:
                    depth += 1
                elif self.peek_offset(idx).type in (TokenType.GREATER, TokenType.RSHIFT, TokenType.URSHIFT):
                    depth -= 1
                idx += 1
            if self.peek_offset(idx).type in (TokenType.KEYWORD_THIS, TokenType.KEYWORD_SUPER) and self.peek_offset(idx + 1).type == TokenType.LPAREN:
                return True

        # Qualified: busca '. super (' na mesma instrução (antes de ';')
        idx = 0
        while self.peek_offset(idx).type not in (TokenType.SEMICOLON, TokenType.LBRACE, TokenType.RBRACE, TokenType.EOF):
            if self.peek_offset(idx).type == TokenType.DOT:
                next_idx = idx + 1
                if self.peek_offset(next_idx).type == TokenType.LESS:
                    depth = 1
                    next_idx += 1
                    while depth > 0 and self.peek_offset(next_idx).type != TokenType.EOF:
                        if self.peek_offset(next_idx).type == TokenType.LESS:
                            depth += 1
                        elif self.peek_offset(next_idx).type in (TokenType.GREATER, TokenType.RSHIFT, TokenType.URSHIFT):
                            depth -= 1
                        next_idx += 1
                if self.peek_offset(next_idx).type == TokenType.KEYWORD_SUPER and self.peek_offset(next_idx + 1).type == TokenType.LPAREN:
                    return True
            idx += 1

        return False

    def parse_explicit_constructor_invocation(self) -> ExplicitConstructorInvocation:
        """
        Processa uma invocação explícita de construtor (JLS §8.8.7.1):
        - this(...)
        - super(...)
        - <TypeArgs>this(...)
        - <TypeArgs>super(...)
        - qualifier.super(...)
        - qualifier.<TypeArgs>super(...)
        """
        type_args = []
        if self.check(TokenType.LESS):
            type_args = self.parse_type_arguments()
            if self.check(TokenType.KEYWORD_THIS):
                t_tok = self.advance()
                self.expect(TokenType.LPAREN, "Era esperado '(' após 'this'")
                args = self.parse_arguments()
                self.expect(TokenType.RPAREN, "Era esperado ')' após argumentos do construtor")
                self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da invocação do construtor", expected="';'")
                return AlternateConstructorInvocation(arguments=args, type_arguments=type_args, line=t_tok.line, column=t_tok.column)
            elif self.check(TokenType.KEYWORD_SUPER):
                s_tok = self.advance()
                self.expect(TokenType.LPAREN, "Era esperado '(' após 'super'")
                args = self.parse_arguments()
                self.expect(TokenType.RPAREN, "Era esperado ')' após argumentos do construtor")
                self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da invocação do construtor", expected="';'")
                return SuperclassConstructorInvocation(arguments=args, type_arguments=type_args, qualifier=None, line=s_tok.line, column=s_tok.column)

        if self.check(TokenType.KEYWORD_THIS) and self.peek_offset(1).type == TokenType.LPAREN:
            t_tok = self.advance()
            self.expect(TokenType.LPAREN, "Era esperado '(' após 'this'")
            args = self.parse_arguments()
            self.expect(TokenType.RPAREN, "Era esperado ')' após argumentos do construtor")
            self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da invocação do construtor", expected="';'")
            return AlternateConstructorInvocation(arguments=args, type_arguments=[], line=t_tok.line, column=t_tok.column)

        if self.check(TokenType.KEYWORD_SUPER) and self.peek_offset(1).type == TokenType.LPAREN:
            s_tok = self.advance()
            self.expect(TokenType.LPAREN, "Era esperado '(' após 'super'")
            args = self.parse_arguments()
            self.expect(TokenType.RPAREN, "Era esperado ')' após argumentos do construtor")
            self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da invocação do construtor", expected="';'")
            return SuperclassConstructorInvocation(arguments=args, type_arguments=[], qualifier=None, line=s_tok.line, column=s_tok.column)

        # Qualified: expr.super(...) ou expr.<T>super(...)
        qualifier = self.primary()
        while self.check(TokenType.DOT) and not (self.peek_offset(1).type == TokenType.KEYWORD_SUPER or self.peek_offset(1).type == TokenType.LESS):
            self.advance() # consome '.'
            m_tok = self.expect(TokenType.IDENTIFIER, "Era esperado um identificador")
            if self.check(TokenType.LPAREN):
                self.advance()
                args = self.parse_arguments()
                self.expect(TokenType.RPAREN, "Era esperado ')'")
                qualifier = MethodCall(method_name=m_tok.lexeme, target=qualifier, arguments=args, line=m_tok.line, column=m_tok.column)
            else:
                qualifier = MemberAccess(target=qualifier, member_name=m_tok.lexeme, line=m_tok.line, column=m_tok.column)

        self.expect(TokenType.DOT, "Era esperado '.' antes de 'super' na invocação qualificada de construtor")
        type_args = []
        if self.check(TokenType.LESS):
            type_args = self.parse_type_arguments()

        s_tok = self.expect(TokenType.KEYWORD_SUPER, "Era esperado 'super' na invocação de construtor")
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'super'")
        args = self.parse_arguments()
        self.expect(TokenType.RPAREN, "Era esperado ')' após argumentos do construtor")
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da invocação do construtor", expected="';'")
        return SuperclassConstructorInvocation(arguments=args, type_arguments=type_args, qualifier=qualifier, line=s_tok.line, column=s_tok.column)

    def parse_constructor_body(self, class_name: str) -> ConstructorBody:
        """
        Processa o corpo de um construtor com suporte a Flexible Constructor Bodies (JEP 513 / JLS §8.8.7):
        { [BlockStatements] ConstructorInvocation [BlockStatements] }
        { [BlockStatements] }
        """
        start_tok = self.expect(TokenType.LBRACE, "Era esperado '{' para abrir o corpo do construtor", expected="'{'")
        prologue: List[ASTNode] = []
        ctor_inv: Optional[ExplicitConstructorInvocation] = None
        epilogue: List[ASTNode] = []

        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            if self._is_constructor_invocation_ahead():
                if ctor_inv is not None:
                    t = self.peek()
                    raise SyntacticError(
                        message="Múltiplas invocações explícitas de construtor não são permitidas no mesmo corpo de construtor",
                        line=t.line,
                        column=t.column,
                        expected="apenas uma invocação explícita de 'this(...)' ou 'super(...)'",
                        found=t.lexeme
                    )
                ctor_inv = self.parse_explicit_constructor_invocation()
                continue

            stmt = self.block_statement()
            if ctor_inv is None:
                prologue.append(stmt)
            else:
                epilogue.append(stmt)

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o corpo do construtor", expected="'}'")
        return ConstructorBody(prologue=prologue, constructor_invocation=ctor_inv, epilogue=epilogue, line=start_tok.line, column=start_tok.column)

    def _parse_method_or_field_after_prefix(
        self,
        annos: List[ASTNode],
        mods: List[str],
        type_params: List[TypeParameter],
        post_annos: Optional[List[ASTNode]] = None,
    ) -> ASTNode:
        """Processa MethodDeclaration ou FieldDeclaration após anotações, modificadores e TypeParameters."""
        if post_annos is None:
            leading_type_annos = [] if type_params else annos
        else:
            leading_type_annos = [] if type_params else post_annos
        type_ref = self.parse_type_reference(leading_annotations=leading_type_annos)
        name_tok = self.expect(
            TokenType.IDENTIFIER,
            "Era esperado o nome do membro (método ou campo)",
            expected="o nome do membro (método ou campo)",
        )

        # Método
        if self.check(TokenType.LPAREN):
            recv_param, params = self.parse_formal_parameters()
            dims, dims_annos = self._parse_trailing_dims_with_annotations()
            throws_types = self.parse_throws_clause()
            if self.check(TokenType.SEMICOLON):
                self.advance()
                body = None
            else:
                body = self.parse_block()
            return MethodDeclaration(
                name=name_tok.lexeme,
                return_type=type_ref,
                parameters=params,
                modifiers=mods,
                throws_types=throws_types,
                body=body,
                line=name_tok.line,
                column=name_tok.column,
                type_parameters=type_params,
                annotations=annos,
                receiver_parameter=recv_param,
                dims=dims,
                dims_annotations=dims_annos,
            )

        # Campo: VariableDeclaratorList
        declarators: List[VariableDeclarator] = []
        dims, dims_annos = self._parse_trailing_dims_with_annotations()
        first_id = VariableDeclaratorId(
            name=name_tok.lexeme,
            dims=dims,
            dims_annotations=dims_annos,
            line=name_tok.line,
            column=name_tok.column,
        )
        first_init = None
        if self.check(TokenType.ASSIGN):
            self.advance()
            first_init = self.variable_initializer()
        declarators.append(VariableDeclarator(id=first_id, initializer=first_init, line=name_tok.line, column=name_tok.column))

        while self.check(TokenType.COMMA):
            self.advance()
            decl_id = self.parse_variable_declarator_id()
            init = None
            if self.check(TokenType.ASSIGN):
                self.advance()
                init = self.variable_initializer()
            declarators.append(VariableDeclarator(id=decl_id, initializer=init, line=decl_id.line, column=decl_id.column))

        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da declaração do campo", expected="';'")
        return FieldDeclaration(type_ref=type_ref, declarators=declarators, modifiers=mods, line=name_tok.line, column=name_tok.column, annotations=annos)

    def class_member(self, class_name: str) -> ASTNode:
        """Processa um membro dentro de uma classe (JLS §8.1.7)."""
        if self.check(TokenType.SEMICOLON):
            sem_tok = self.advance()
            return EmptyStatement(line=sem_tok.line, column=sem_tok.column)

        annos, _pre_annos, post_annos, mods = self._parse_annotations_and_modifiers_detailed(allow_sealed=True)

        # 1. Inicializador de instância: { ... } (sem modificadores)
        if not mods and not annos and self.check(TokenType.LBRACE):
            block = self.parse_block()
            return InstanceInitializer(block=block, line=block.line, column=block.column)

        # 2. Inicializador estático: static { ... }
        if mods == ["static"] and not annos and self.check(TokenType.LBRACE):
            block = self.parse_block()
            return StaticInitializer(block=block, line=block.line, column=block.column)

        # 3. Tipos aninhados
        if self._is_annotation_interface_declaration_ahead():
            return self.annotation_interface_declaration(mods, annotations=annos)
        if self.check(TokenType.KEYWORD_CLASS):
            decl = self.class_declaration(mods)
            decl.annotations = annos
            return decl
        if self.check(TokenType.KEYWORD_INTERFACE):
            return self.interface_declaration(mods, annotations=annos)
        if self.check(TokenType.KEYWORD_ENUM):
            return self.enum_declaration(mods, annotations=annos)
        if self._is_record_declaration_ahead(allow_missing_name=True):
            return self.record_declaration(mods, annotations=annos)

        # 4. Parâmetros de tipo genérico (para métodos genéricos ou construtores genéricos)
        type_params = []
        if self.check(TokenType.LESS):
            type_params = self.parse_type_parameters()

        # 5. Construtor genérico: <U> ClassName(...)
        if type_params and self.check(TokenType.IDENTIFIER) and self.peek_offset(1).type == TokenType.LPAREN:
            ctor_tok = self.advance()
            recv_param, params = self.parse_formal_parameters()
            throws_types = self.parse_throws_clause()
            body = self.parse_constructor_body(ctor_tok.lexeme)
            return ConstructorDeclaration(
                name=ctor_tok.lexeme,
                parameters=params,
                modifiers=mods,
                throws_types=throws_types,
                body=body,
                line=ctor_tok.line,
                column=ctor_tok.column,
                receiver_parameter=recv_param,
                type_parameters=type_params,
                annotations=annos
            )

        # 6. Construtor normal: identificador seguido de '(' sem tipo de retorno
        if not type_params and self.check(TokenType.IDENTIFIER) and self.peek_offset(1).type == TokenType.LPAREN:
            if self.peek().lexeme == class_name or not any(m in ("static", "abstract", "native", "synchronized") for m in mods):
                ctor_tok = self.advance()
                recv_param, params = self.parse_formal_parameters()
                throws_types = self.parse_throws_clause()
                body = self.parse_constructor_body(ctor_tok.lexeme)
                return ConstructorDeclaration(
                    name=ctor_tok.lexeme,
                    parameters=params,
                    modifiers=mods,
                    throws_types=throws_types,
                    body=body,
                    line=ctor_tok.line,
                    column=ctor_tok.column,
                    receiver_parameter=recv_param,
                    type_parameters=[],
                    annotations=annos
                )

        # 7. Método ou Campo: inicia com o tipo
        return self._parse_method_or_field_after_prefix(annos, mods, type_params, post_annos=post_annos)

    def _parse_interface_constant_declaration(
        self,
        type_ref: TypeReference,
        name_tok: Token,
        mods: List[str],
        annos: List[ASTNode],
        container_label: str = "interface",
    ) -> InterfaceConstantDeclaration:
        """Helper compartilhado para declarações de constantes em interfaces e annotation interfaces (JLS §9.3, §9.6.1)."""
        declarators: List[VariableDeclarator] = []
        dims, dims_annos = self._parse_trailing_dims_with_annotations()
        first_id = VariableDeclaratorId(
            name=name_tok.lexeme,
            dims=dims,
            dims_annotations=dims_annos,
            line=name_tok.line,
            column=name_tok.column,
        )
        if not self.check(TokenType.ASSIGN):
            t = self.peek()
            raise SyntacticError(
                message=f"Constante de {container_label} '{first_id.name}' deve possuir inicializador obrigatório '=' (JLS §9.3)",
                line=t.line,
                column=t.column,
                expected=f"'=' para inicializar a constante de {container_label}",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        self.advance()  # consome '='
        first_init = self.variable_initializer()
        declarators.append(
            VariableDeclarator(
                id=first_id,
                initializer=first_init,
                line=name_tok.line,
                column=name_tok.column,
            )
        )

        while self.check(TokenType.COMMA):
            self.advance()
            decl_id = self.parse_variable_declarator_id()
            if not self.check(TokenType.ASSIGN):
                t = self.peek()
                raise SyntacticError(
                    message=f"Constante de {container_label} '{decl_id.name}' deve possuir inicializador obrigatório '=' (JLS §9.3)",
                    line=t.line,
                    column=t.column,
                    expected=f"'=' para inicializar a constante de {container_label}",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            self.advance()  # consome '='
            init = self.variable_initializer()
            declarators.append(
                VariableDeclarator(
                    id=decl_id,
                    initializer=init,
                    line=decl_id.line,
                    column=decl_id.column,
                )
            )

        self.expect(
            TokenType.SEMICOLON,
            f"Era esperado ';' ao final da declaração de constante da {container_label}",
            expected="';'",
        )
        return InterfaceConstantDeclaration(
            type_ref=type_ref,
            declarators=declarators,
            modifiers=mods,
            line=name_tok.line,
            column=name_tok.column,
            annotations=annos,
        )

    def annotation_interface_declaration(
        self, modifiers: List[str], annotations: List[ASTNode] = None
    ) -> AnnotationInterfaceDeclaration:
        """
        Processa declaração de annotation interface Java (JLS §9.6):
        {InterfaceModifier} @ interface TypeIdentifier AnnotationInterfaceBody
        """
        at_tok = self.expect(
            TokenType.AT,
            "Era esperado '@' na declaração de '@interface'",
            expected="'@'",
        )
        self.expect(
            TokenType.KEYWORD_INTERFACE,
            "Era esperado 'interface' após '@' na declaração de annotation interface",
            expected="'interface'",
        )
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado o nome da annotation interface após '@interface'",
                line=t.line,
                column=t.column,
                expected="identificador do tipo de anotação",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        name_tok = self.advance()

        if self.check(TokenType.LESS):
            t = self.peek()
            raise SyntacticError(
                message="Annotation interfaces (@interface) não podem declarar parâmetros de tipo '<...>' (JLS §9.6)",
                line=t.line,
                column=t.column,
                expected="'{' para abrir o corpo de '@interface'",
                found="<",
            )
        if self.check(TokenType.KEYWORD_EXTENDS):
            t = self.peek()
            raise SyntacticError(
                message="Annotation interfaces (@interface) não podem possuir cláusula 'extends' (JLS §9.6)",
                line=t.line,
                column=t.column,
                expected="'{' para abrir o corpo de '@interface'",
                found="extends",
            )
        if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "permits":
            t = self.peek()
            raise SyntacticError(
                message="Annotation interfaces (@interface) não podem possuir cláusula 'permits' (JLS §9.6)",
                line=t.line,
                column=t.column,
                expected="'{' para abrir o corpo de '@interface'",
                found="permits",
            )

        lbrace_tok = self.expect(
            TokenType.LBRACE,
            "Era esperado '{' para abrir o corpo da annotation interface",
            expected="'{'",
        )
        members: List[ASTNode] = []
        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            members.append(self.annotation_interface_member(name_tok.lexeme))

        self.expect(
            TokenType.RBRACE,
            "Era esperado '}' para fechar o corpo da annotation interface",
            expected="'}'",
        )
        body = AnnotationInterfaceBody(
            members=members, line=lbrace_tok.line, column=lbrace_tok.column
        )
        return AnnotationInterfaceDeclaration(
            name=name_tok.lexeme,
            modifiers=modifiers,
            members=members,
            annotations=annotations or [],
            body=body,
            line=at_tok.line,
            column=at_tok.column,
        )

    def annotation_interface_member(self, ann_name: str) -> ASTNode:
        """
        Processa membro de annotation interface (JLS §9.6.1):
        - AnnotationInterfaceElementDeclaration
        - ConstantDeclaration
        - ClassDeclaration / NormalInterfaceDeclaration / EnumDeclaration / RecordDeclaration / AnnotationInterfaceDeclaration
        - ';'
        """
        if self.check(TokenType.SEMICOLON):
            sem_tok = self.advance()
            return EmptyStatement(line=sem_tok.line, column=sem_tok.column)

        annos, pre_annos, post_annos, mods = self._parse_annotations_and_modifiers_detailed(
            allow_default=True, allow_sealed=True
        )

        if self.check(TokenType.LBRACE):
            t = self.peek()
            raise SyntacticError(
                message="Inicializadores de instância ou estáticos não são permitidos em '@interface' (JLS §9.6.1)",
                line=t.line,
                column=t.column,
                expected="elemento de anotação, constante ou declaração de tipo membro",
                found="{",
            )

        if self._is_annotation_interface_declaration_ahead():
            return self.annotation_interface_declaration(mods, annotations=annos)
        if self.check(TokenType.KEYWORD_CLASS):
            decl = self.class_declaration(mods)
            decl.annotations = annos
            return decl
        if self.check(TokenType.KEYWORD_INTERFACE):
            return self.interface_declaration(mods, annotations=annos)
        if self.check(TokenType.KEYWORD_ENUM):
            return self.enum_declaration(mods, annotations=annos)
        if self._is_record_declaration_ahead(allow_missing_name=True):
            return self.record_declaration(mods, annotations=annos)

        if self.check(TokenType.LESS):
            t = self.peek()
            raise SyntacticError(
                message="Elementos de '@interface' não podem declarar parâmetros de tipo genéricos '<...>' (JLS §9.6.1)",
                line=t.line,
                column=t.column,
                expected="tipo do elemento de anotação",
                found="<",
            )

        type_ref = self.parse_type_reference(leading_annotations=post_annos)
        name_tok = self.expect(
            TokenType.IDENTIFIER,
            "Era esperado o nome do elemento ou constante da annotation interface",
            expected="identificador do elemento ou constante",
        )

        if self.check(TokenType.LPAREN):
            self.advance()  # consome '('
            if not self.check(TokenType.RPAREN):
                t = self.peek()
                raise SyntacticError(
                    message=f"Elemento '{name_tok.lexeme}' de '@interface' não pode declarar parâmetros formais (JLS §9.6.1)",
                    line=t.line,
                    column=t.column,
                    expected="')'",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            self.advance()  # consome ')'

            dims, dims_annos = self._parse_trailing_dims_with_annotations()

            if self.check(TokenType.KEYWORD_THROWS):
                t = self.peek()
                raise SyntacticError(
                    message=f"Elemento '{name_tok.lexeme}' de '@interface' não pode declarar cláusula 'throws' (JLS §9.6.1)",
                    line=t.line,
                    column=t.column,
                    expected="'default' ou ';'",
                    found="throws",
                )

            default_val: Optional[AnnotationDefaultValue] = None
            if self.check(TokenType.KEYWORD_DEFAULT):
                def_tok = self.advance()
                ev = self.parse_element_value()
                default_val = AnnotationDefaultValue(
                    value=ev, line=def_tok.line, column=def_tok.column
                )

            if self.check(TokenType.LBRACE):
                t = self.peek()
                raise SyntacticError(
                    message=f"Elemento '{name_tok.lexeme}' de '@interface' não pode possuir corpo '{{ ... }}' (JLS §9.6.1)",
                    line=t.line,
                    column=t.column,
                    expected="';' ao final da declaração do elemento",
                    found="{",
                )

            self.expect(
                TokenType.SEMICOLON,
                f"Era esperado ';' ao final da declaração do elemento '{name_tok.lexeme}'",
                expected="';'",
            )
            return AnnotationInterfaceElementDeclaration(
                name=name_tok.lexeme,
                return_type=type_ref,
                modifiers=mods,
                default_value=default_val,
                annotations=annos,
                dims=dims,
                dims_annotations=dims_annos,
                line=name_tok.line,
                column=name_tok.column,
            )

        return self._parse_interface_constant_declaration(
            type_ref=type_ref,
            name_tok=name_tok,
            mods=mods,
            annos=annos,
            container_label="annotation interface",
        )

    def interface_member(self, interface_name: str) -> ASTNode:
        """Processa um membro dentro de uma interface (JLS §9.1.5 - §9.5)."""
        if self.check(TokenType.SEMICOLON):
            sem_tok = self.advance()
            return EmptyStatement(line=sem_tok.line, column=sem_tok.column)

        annos, pre_annos, post_annos, mods = self._parse_annotations_and_modifiers_detailed(
            allow_default=True, allow_sealed=True
        )

        # Interfaces não admitem inicializadores de instância ou estáticos
        if self.check(TokenType.LBRACE):
            t = self.peek()
            raise SyntacticError(
                message="Inicializadores de instância ou estáticos não são permitidos em interfaces (JLS §9.1.5)",
                line=t.line,
                column=t.column,
                expected="constante, método ou declaração de tipo membro (inicializadores são proibidos em interfaces)",
                found="{",
            )

        # Tipos aninhados (JLS §9.5)
        if self._is_annotation_interface_declaration_ahead():
            return self.annotation_interface_declaration(mods, annotations=annos)
        if self.check(TokenType.KEYWORD_CLASS):
            decl = self.class_declaration(mods)
            decl.annotations = annos
            return decl
        if self.check(TokenType.KEYWORD_INTERFACE):
            return self.interface_declaration(mods, annotations=annos)
        if self.check(TokenType.KEYWORD_ENUM):
            return self.enum_declaration(mods, annotations=annos)
        if self._is_record_declaration_ahead(allow_missing_name=True):
            return self.record_declaration(mods, annotations=annos)

        type_params = []
        if self.check(TokenType.LESS):
            type_params = self.parse_type_parameters()

        # Interfaces não podem declarar construtores (identificador seguido diretamente de '(' sem tipo de retorno)
        if self.check(TokenType.IDENTIFIER) and self.peek_offset(1).type == TokenType.LPAREN:
            t = self.peek()
            raise SyntacticError(
                message="Interfaces não podem declarar construtores (JLS §9.1.5)",
                line=t.line,
                column=t.column,
                expected="declaração de constante, método com tipo de retorno ou tipo aninhado (construtores são proibidos em interfaces)",
                found=t.lexeme,
            )

        leading_type_annos = [] if type_params else post_annos
        type_ref = self.parse_type_reference(leading_annotations=leading_type_annos)
        name_tok = self.expect(TokenType.IDENTIFIER, "Era esperado o nome do método ou constante da interface", expected="nome do método ou constante da interface")

        if self.check(TokenType.LPAREN):
            recv_param, params = self.parse_formal_parameters()
            dims, dims_annos = self._parse_trailing_dims_with_annotations()
            throws_types = self.parse_throws_clause()
            if self.check(TokenType.SEMICOLON):
                self.advance()
                body = None
            else:
                body = self.parse_block()
            return InterfaceMethodDeclaration(
                name=name_tok.lexeme,
                return_type=type_ref,
                parameters=params,
                modifiers=mods,
                throws_types=throws_types,
                body=body,
                line=name_tok.line,
                column=name_tok.column,
                type_parameters=type_params,
                annotations=annos,
                receiver_parameter=recv_param,
                dims=dims,
                dims_annotations=dims_annos,
            )

        return self._parse_interface_constant_declaration(
            type_ref=type_ref,
            name_tok=name_tok,
            mods=mods,
            annos=annos,
            container_label="interface",
        )

    # -------------------------------------------------------------------------
    # 2.6 REFERÊNCIA DE TIPO, GENERICS E PARÂMETROS (ETAPA S1)
    # -------------------------------------------------------------------------
    def _is_closing_generic_bracket(self) -> bool:
        """Verifica se o próximo token fecha um nível de generic: >, >> ou >>>."""
        return self.peek().type in (TokenType.GREATER, TokenType.RSHIFT, TokenType.URSHIFT)

    def _consume_closing_generic_bracket(self) -> Token:
        """
        Consome um delimitador '>' de fechamento genérico.
        Lida transparentemente com tokens compostos gerados por maximal munch no lexer:
        '>>' (RSHIFT) -> consome um '>' e substitui por '>' (GREATER)
        '>>>' (URSHIFT) -> consome um '>' e substitui por '>>' (RSHIFT)
        """
        tok = self.peek()
        if tok.type == TokenType.GREATER:
            return self.advance()
        elif tok.type == TokenType.RSHIFT:
            replacement = Token(TokenType.GREATER, ">", tok.line, tok.column + 1)
            self.tokens[self.current] = replacement
            return Token(TokenType.GREATER, ">", tok.line, tok.column)
        elif tok.type == TokenType.URSHIFT:
            replacement = Token(TokenType.RSHIFT, ">>", tok.line, tok.column + 1)
            self.tokens[self.current] = replacement
            return Token(TokenType.GREATER, ">", tok.line, tok.column)
        else:
            raise SyntacticError(
                message="Era esperado '>' para fechar argumentos ou parâmetros de tipo genérico",
                line=tok.line,
                column=tok.column,
                expected="'>'",
                found=tok.lexeme if tok.type != TokenType.EOF else "EOF"
            )

    def _parse_annotations_and_modifiers_detailed(
        self, allow_default: bool = False, allow_sealed: bool = True
    ) -> Tuple[List[ASTNode], List[ASTNode], List[ASTNode], List[str]]:
        """
        Processa annotations e modificadores em qualquer ordem preservando:
        (todas_annos, pre_modifier_annos, post_modifier_annos, mods).
        Annotations antes do último modificador-palavra-chave são estritamente
        de declaração; annotations adjacentes ao tipo podem atuar como type annotations.
        """
        pre_annos: List[ASTNode] = []
        post_annos: List[ASTNode] = []
        mods: List[str] = []
        while True:
            if self.check(TokenType.AT) and not self._is_annotation_interface_declaration_ahead():
                post_annos.extend(self._parse_optional_annotations())
            elif self.check(TokenType.KEYWORD_DEFAULT) and allow_default:
                pre_annos.extend(post_annos)
                post_annos.clear()
                mods.append(self.advance().lexeme)
            elif self.peek().type in MODIFIER_TOKENS:
                pre_annos.extend(post_annos)
                post_annos.clear()
                mods.append(self.advance().lexeme)
            elif allow_sealed and self._is_non_sealed_ahead():
                pre_annos.extend(post_annos)
                post_annos.clear()
                self.advance()  # non
                self.advance()  # -
                self.advance()  # sealed
                mods.append("non-sealed")
            elif allow_sealed and self._is_sealed_modifier_ahead():
                pre_annos.extend(post_annos)
                post_annos.clear()
                mods.append(self.advance().lexeme)
            else:
                break
        return pre_annos + post_annos, pre_annos, post_annos, mods

    def _is_annotation_interface_declaration_ahead(self, offset: int = 0) -> bool:
        """Verifica se há início de declaração '@interface' no offset especificado."""
        return (
            self.peek_offset(offset).type == TokenType.AT
            and self.peek_offset(offset + 1).type == TokenType.KEYWORD_INTERFACE
        )

    def _parse_trailing_dims_with_annotations(self) -> Tuple[int, List[List[ASTNode]]]:
        """Processa dimensões de array pós-nome/parênteses com annotations opcionais: { {Annotation} [] }."""
        dims = 0
        dims_annos: List[List[ASTNode]] = []
        while self._has_array_brackets_after_annotations():
            da = self._parse_optional_annotations() if self.check(TokenType.AT) else []
            self.advance()  # '['
            self.advance()  # ']'
            dims += 1
            dims_annos.append(da)
        return dims, dims_annos

    def _is_class_literal_ahead(self) -> bool:
        """
        Verifica lookahead para ClassLiteral (JLS §15.8.2):
        - void . class
        - PrimitiveType { [] } . class
        - TypeName { [] } . class
        """
        t0 = self.peek_offset(0)
        if t0.type == TokenType.KEYWORD_VOID:
            return (
                self.peek_offset(1).type == TokenType.DOT
                and self.peek_offset(2).type == TokenType.KEYWORD_CLASS
            )
        if t0.type in PRIMITIVE_TYPE_TOKENS:
            off = 1
            while (
                self.peek_offset(off).type == TokenType.LBRACKET
                and self.peek_offset(off + 1).type == TokenType.RBRACKET
            ):
                off += 2
            return (
                self.peek_offset(off).type == TokenType.DOT
                and self.peek_offset(off + 1).type == TokenType.KEYWORD_CLASS
            )
        if t0.type == TokenType.IDENTIFIER:
            off = 1
            while (
                self.peek_offset(off).type == TokenType.DOT
                and self.peek_offset(off + 1).type == TokenType.IDENTIFIER
            ):
                off += 2
            while (
                self.peek_offset(off).type == TokenType.LBRACKET
                and self.peek_offset(off + 1).type == TokenType.RBRACKET
            ):
                off += 2
            return (
                self.peek_offset(off).type == TokenType.DOT
                and self.peek_offset(off + 1).type == TokenType.KEYWORD_CLASS
            )
        return False

    def _parse_class_literal(self) -> ClassLiteral:
        """Processa ClassLiteral (JLS §15.8.2): Tipo.class | Tipo[].class | int.class | void.class."""
        start_tok = self.peek()
        if self.check(TokenType.KEYWORD_VOID):
            self.advance()
            type_ref = TypeReference(name="void", line=start_tok.line, column=start_tok.column)
        else:
            if self.peek().type in PRIMITIVE_TYPE_TOKENS:
                base_name = self.advance().lexeme
            else:
                parts = [
                    self.expect(
                        TokenType.IDENTIFIER,
                        "Era esperado um identificador de tipo antes de '.class'"
                    ).lexeme
                ]
                while self.check(TokenType.DOT) and self.peek_offset(1).type == TokenType.IDENTIFIER:
                    self.advance()
                    parts.append(self.advance().lexeme)
                base_name = ".".join(parts)
            dims = 0
            while self.check(TokenType.LBRACKET) and self.peek_offset(1).type == TokenType.RBRACKET:
                self.advance()
                self.advance()
                dims += 1
            type_ref = TypeReference(
                name=base_name,
                array_dimensions=dims,
                line=start_tok.line,
                column=start_tok.column,
            )
        self.expect(TokenType.DOT, "Era esperado '.' antes de 'class'", expected="'.'")
        self.expect(TokenType.KEYWORD_CLASS, "Era esperado 'class' no literal de classe", expected="'class'")
        return ClassLiteral(type_ref=type_ref, line=start_tok.line, column=start_tok.column)

    def _parse_single_annotation(self) -> Annotation:
        """
        Processa uma única annotation Java (JLS §9.7):
        MarkerAnnotation (@Nome), SingleElementAnnotation (@Nome(val)) ou NormalAnnotation (@Nome(k=v, ...)).
        """
        at_tok = self.advance()  # consome '@'
        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado um identificador após '@'",
                line=t.line,
                column=t.column,
                expected="o nome da anotação após '@'",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        name = self.qualified_identifier()
        if not self.check(TokenType.LPAREN):
            return MarkerAnnotation(name=name, line=at_tok.line, column=at_tok.column)

        self.advance()  # consome '('
        if self.check(TokenType.RPAREN):
            self.advance()  # consome ')'
            return NormalAnnotation(
                name=name,
                element_value_pair_list=ElementValuePairList(
                    pairs=[], line=at_tok.line, column=at_tok.column
                ),
                has_parentheses=True,
                line=at_tok.line,
                column=at_tok.column,
            )

        if self.check(TokenType.IDENTIFIER) and self.peek_offset(1).type == TokenType.ASSIGN:
            pairs: List[ElementValuePair] = []
            first_line = self.peek().line
            first_col = self.peek().column
            while True:
                if not self.check(TokenType.IDENTIFIER):
                    t = self.peek()
                    raise SyntacticError(
                        message="Era esperado o identificador do elemento no par 'nome = valor' da anotação",
                        line=t.line,
                        column=t.column,
                        expected="identificador do elemento antes de '='",
                        found=t.lexeme if t.type != TokenType.EOF else "EOF",
                    )
                key_tok = self.advance()
                self.expect(
                    TokenType.ASSIGN,
                    f"Era esperado '=' após o elemento '{key_tok.lexeme}' na anotação '@{name}'",
                    expected="'='",
                )
                val = self.parse_element_value()
                pairs.append(
                    ElementValuePair(
                        name=key_tok.lexeme,
                        value=val,
                        line=key_tok.line,
                        column=key_tok.column,
                    )
                )
                if self.check(TokenType.COMMA):
                    self.advance()
                    if self.check(TokenType.RPAREN):
                        t = self.peek()
                        raise SyntacticError(
                            message=f"Vírgula final não é permitida na lista de pares da anotação '@{name}' (JLS §9.7.1)",
                            line=t.line,
                            column=t.column,
                            expected="outro par 'nome = valor' após ','",
                            found=")",
                        )
                    continue
                break

            self.expect(
                TokenType.RPAREN,
                f"Era esperado ')' para fechar argumentos da anotação '@{name}'",
                expected="')'",
            )
            return NormalAnnotation(
                name=name,
                element_value_pair_list=ElementValuePairList(
                    pairs=pairs, line=first_line, column=first_col
                ),
                has_parentheses=True,
                line=at_tok.line,
                column=at_tok.column,
            )

        elem_val = self.parse_element_value()
        if self.check(TokenType.COMMA):
            t = self.peek()
            raise SyntacticError(
                message=f"Múltiplos valores posicionais em '@{name}' exigem chaves '{{...}}' ou pares 'nome = valor'",
                line=t.line,
                column=t.column,
                expected="')' após ElementValue",
                found=",",
            )
        self.expect(
            TokenType.RPAREN,
            f"Era esperado ')' para fechar argumentos da anotação '@{name}'",
            expected="')'",
        )
        return SingleElementAnnotation(
            name=name,
            element_value=elem_val,
            line=at_tok.line,
            column=at_tok.column,
        )

    def parse_element_value(self) -> ElementValue:
        """
        Processa ElementValue (JLS §9.7.1):
        ElementValue ::= ConditionalExpression | ElementValueArrayInitializer | Annotation
        """
        tok = self.peek()
        if self.check(TokenType.AT):
            if self._is_annotation_interface_declaration_ahead():
                raise SyntacticError(
                    message="Declaração '@interface' não é permitida como valor de elemento de anotação",
                    line=tok.line,
                    column=tok.column,
                    expected="expressão constante, '{...}' ou anotação aninhada",
                    found="@interface",
                )
            nested = self._parse_single_annotation()
            return ElementValue(value=nested, line=nested.line, column=nested.column)

        if self.check(TokenType.LBRACE):
            arr_init = self.parse_element_value_array_initializer()
            return ElementValue(value=arr_init, line=arr_init.line, column=arr_init.column)

        if tok.type in (
            TokenType.RPAREN,
            TokenType.COMMA,
            TokenType.RBRACE,
            TokenType.SEMICOLON,
            TokenType.EOF,
        ):
            found_repr = tok.lexeme if tok.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message="Era esperado um valor para o elemento da anotação (ElementValue)",
                line=tok.line,
                column=tok.column,
                expected="expressão constante, '{...}' ou anotação aninhada",
                found=found_repr,
            )

        expr = self.ternary_expression()
        return ElementValue(value=expr, line=tok.line, column=tok.column)

    def parse_element_value_array_initializer(self) -> ElementValueArrayInitializer:
        """
        Processa ElementValueArrayInitializer (JLS §9.7.1):
        { [ElementValueList] [,] }
        """
        lbrace_tok = self.expect(
            TokenType.LBRACE,
            "Era esperado '{' para iniciar inicializador de array da anotação",
            expected="'{'",
        )
        elements: List[ElementValue] = []
        has_trailing_comma = False

        if self.check(TokenType.COMMA):
            t = self.peek()
            raise SyntacticError(
                message="Vírgula inicial inesperada em inicializador de array da anotação",
                line=t.line,
                column=t.column,
                expected="valor do elemento ou '}'",
                found=",",
            )

        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            elements.append(self.parse_element_value())
            if self.check(TokenType.COMMA):
                self.advance()
                if self.check(TokenType.RBRACE):
                    has_trailing_comma = True
                    break
            else:
                break

        self.expect(
            TokenType.RBRACE,
            "Era esperado '}' para fechar o inicializador de array da anotação",
            expected="'}'",
        )
        return ElementValueArrayInitializer(
            elements=elements,
            has_trailing_comma=has_trailing_comma,
            line=lbrace_tok.line,
            column=lbrace_tok.column,
        )

    def _parse_optional_annotations(self) -> List[Annotation]:
        """Processa zero ou mais annotations no formato @Nome ou @Nome(...)."""
        annotations: List[Annotation] = []
        while self.check(TokenType.AT):
            # Não consome se for @interface
            if self._is_annotation_interface_declaration_ahead():
                break
            annotations.append(self._parse_single_annotation())
        return annotations

    def _parse_annotation_arguments(self) -> Any:
        """Processa argumentos de anotação dentro dos parênteses: (valor) ou (k=v, ...)."""
        if self.check(TokenType.RPAREN):
            return None
        if self.check(TokenType.LBRACE):
            return self.parse_array_initializer()
        if self.check(TokenType.IDENTIFIER) and self.peek_offset(1).type == TokenType.ASSIGN:
            pairs = {}
            while not self.check(TokenType.RPAREN) and not self.check(TokenType.EOF):
                k_tok = self.expect(TokenType.IDENTIFIER, "Era esperado nome de elemento na anotação")
                self.expect(TokenType.ASSIGN, "Era esperado '=' após o nome do elemento")
                if self.check(TokenType.LBRACE):
                    v = self.parse_array_initializer()
                elif self.check(TokenType.AT):
                    v = self._parse_optional_annotations()[0]
                else:
                    v = self.expression()
                pairs[k_tok.lexeme] = v
                if self.check(TokenType.COMMA):
                    self.advance()
                else:
                    break
            return pairs
        if self.check(TokenType.AT):
            return self._parse_optional_annotations()[0]
        return self.expression()

    def parse_type_parameters(self) -> List[TypeParameter]:
        """
        Processa parâmetros de tipo genérico na declaração de classes, interfaces, records ou métodos:
        < T [extends Bound1 & Bound2], U >
        """
        self.expect(TokenType.LESS, "Era esperado '<' para iniciar parâmetros de tipo", expected="'<'")
        if self._is_closing_generic_bracket():
            t = self.peek()
            raise SyntacticError(
                message="Era esperado nome de parâmetro genérico após '<'",
                line=t.line,
                column=t.column,
                expected="nome de parâmetro genérico",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        params = []
        while not self._is_closing_generic_bracket() and not self.check(TokenType.EOF):
            annos = self._parse_optional_annotations()
            p_tok = self.expect(TokenType.IDENTIFIER, "Era esperado nome de parâmetro genérico", expected="identificador de parâmetro genérico")
            bounds = []
            if self.check(TokenType.KEYWORD_EXTENDS):
                self.advance() # consome 'extends'
                bounds.append(self.parse_type_reference())
                while self.check(TokenType.BITWISE_AND):
                    self.advance() # consome '&'
                    bounds.append(self.parse_type_reference())
            params.append(TypeParameter(p_tok.lexeme, bounds, annos, p_tok.line, p_tok.column))
            if self.check(TokenType.COMMA):
                self.advance()
            else:
                break
        self._consume_closing_generic_bracket()
        return params

    def parse_type_arguments(self) -> List[ASTNode]:
        """
        Processa argumentos de tipo genérico no uso de tipos ou invocações genéricas:
        < String, ? extends Number, Map<K, List<V>> >
        """
        self.expect(TokenType.LESS, "Era esperado '<' para iniciar argumentos de tipo", expected="'<'")
        args = []
        while not self._is_closing_generic_bracket() and not self.check(TokenType.EOF):
            annos = self._parse_optional_annotations()
            if self.check(TokenType.QUESTION):
                q_tok = self.advance() # consome '?'
                bound_kind = None
                bound_type = None
                if self.check(TokenType.KEYWORD_EXTENDS):
                    self.advance()
                    bound_kind = "extends"
                    bound_type = self.parse_type_reference()
                elif self.check(TokenType.KEYWORD_SUPER):
                    self.advance()
                    bound_kind = "super"
                    bound_type = self.parse_type_reference()
                args.append(WildcardType(bound_kind, bound_type, annos, q_tok.line, q_tok.column))
            else:
                args.append(self.parse_type_reference(leading_annotations=annos))

            if self.check(TokenType.COMMA):
                self.advance()
            else:
                break
        self._consume_closing_generic_bracket()
        return args

    def _skip_annotations_offset(self, offset: int = 0) -> int:
        """Avança o offset de lookahead sobre zero ou mais annotations (@Nome ou @Nome(...))."""
        while self.peek_offset(offset).type == TokenType.AT:
            if self.peek_offset(offset + 1).type == TokenType.KEYWORD_INTERFACE:
                break
            offset += 1
            if self.peek_offset(offset).type == TokenType.IDENTIFIER:
                offset += 1
                while (
                    self.peek_offset(offset).type == TokenType.DOT
                    and self.peek_offset(offset + 1).type == TokenType.IDENTIFIER
                ):
                    offset += 2
                if self.peek_offset(offset).type == TokenType.LPAREN:
                    nesting = 1
                    offset += 1
                    while nesting > 0 and self.peek_offset(offset).type != TokenType.EOF:
                        if self.peek_offset(offset).type == TokenType.LPAREN:
                            nesting += 1
                        elif self.peek_offset(offset).type == TokenType.RPAREN:
                            nesting -= 1
                        offset += 1
        return offset

    def _has_array_brackets_after_annotations(self, start_offset: int = 0) -> bool:
        """Verifica se há um par '[]' imediatamente após possíveis type annotations."""
        off = self._skip_annotations_offset(start_offset)
        return (
            self.peek_offset(off).type == TokenType.LBRACKET
            and self.peek_offset(off + 1).type == TokenType.RBRACKET
        )

    def _is_local_type_declaration_ahead(self) -> bool:
        """Verifica se há uma declaração local de classe, interface, enum ou record."""
        off = 0
        while True:
            new_off = self._skip_annotations_offset(off)
            t = self.peek_offset(new_off)
            if t.type in MODIFIER_TOKENS:
                off = new_off + 1
            elif self._is_non_sealed_ahead(new_off):
                off = new_off + 3
            elif self._is_sealed_modifier_ahead(new_off):
                off = new_off + 1
            else:
                off = new_off
                break
        tok = self.peek_offset(off)
        return (
            tok.type in (TokenType.KEYWORD_CLASS, TokenType.KEYWORD_INTERFACE, TokenType.KEYWORD_ENUM)
            or self._is_annotation_interface_declaration_ahead(off)
            or self._is_record_declaration_ahead(off)
        )

    def parse_type_reference(self, leading_annotations: List[ASTNode] = None) -> TypeReference:
        """
        Processa tipos primitivos, nomes qualificados, generics (com wildcards e bounds),
        annotations e dimensões de arrays.
        """
        if leading_annotations is None:
            leading_annotations = self._parse_optional_annotations()
        elif self.check(TokenType.AT) and not self._is_annotation_interface_declaration_ahead():
            leading_annotations = list(leading_annotations) + self._parse_optional_annotations()

        tok = self.peek()
        segment_annotations: List[List[ASTNode]] = []
        segment_type_arguments: List[Optional[List[ASTNode]]] = []
        type_arguments = []

        if tok.type in PRIMITIVE_TYPE_TOKENS:
            self.advance()
            type_name = tok.lexeme
        elif tok.type == TokenType.IDENTIFIER:
            first_tok = self.advance()
            type_name = first_tok.lexeme
            segment_annotations = [list(leading_annotations)]
            segment_type_arguments = [None]
            while self.check(TokenType.DOT) and self.peek_offset(1).type == TokenType.IDENTIFIER:
                self.advance()
                type_name = f"{type_name}.{self.advance().lexeme}"
                segment_annotations.append([])
                segment_type_arguments.append(None)
            if self.check(TokenType.LESS):
                last_args = self.parse_type_arguments()
                segment_type_arguments[-1] = last_args
                type_arguments = last_args
            while self.check(TokenType.DOT) and (
                (self.peek_offset(1).type == TokenType.AT and not self._is_annotation_interface_declaration_ahead(1))
                or self.peek_offset(1).type == TokenType.IDENTIFIER
            ):
                self.advance()  # '.'
                seg_annos = self._parse_optional_annotations()
                seg_tok = self.expect(
                    TokenType.IDENTIFIER,
                    "Era esperado identificador de tipo após '.'",
                    expected="identificador de tipo",
                )
                type_name = f"{type_name}.{seg_tok.lexeme}"
                segment_annotations.append(seg_annos)
                if self.check(TokenType.LESS):
                    seg_args = self.parse_type_arguments()
                    segment_type_arguments.append(seg_args)
                    type_arguments = seg_args
                else:
                    segment_type_arguments.append(None)
                    type_arguments = []
        else:
            raise SyntacticError(
                message=f"Tipo inválido: '{tok.lexeme}'",
                line=tok.line,
                column=tok.column,
                expected="um tipo primitivo ou identificador de classe",
                found=tok.lexeme if tok.type != TokenType.EOF else "EOF",
            )

        # Dimensões de array (ex: int[], String[][], @Nullable [])
        array_dimensions = 0
        dims_annotations = []
        while True:
            if self._has_array_brackets_after_annotations():
                dim_annos = self._parse_optional_annotations()
                self.advance() # [
                self.advance() # ]
                array_dimensions += 1
                dims_annotations.append(dim_annos)
            else:
                break

        is_varargs = False
        if self.check(TokenType.ELLIPSIS):
            self.advance()
            is_varargs = True

        return TypeReference(
            name=type_name,
            array_dimensions=array_dimensions,
            type_arguments=type_arguments,
            is_varargs=is_varargs,
            line=tok.line,
            column=tok.column,
            annotations=leading_annotations,
            dims_annotations=dims_annotations,
            segment_annotations=segment_annotations,
            segment_type_arguments=segment_type_arguments,
        )

    def parse_formal_parameters(self) -> Tuple[Optional[ReceiverParameter], List[Parameter]]:
        """
        Processa parâmetros formais e parâmetro receptor opcional (JLS §8.4.1):
        ( [ReceiverParameter ,] [FormalParameterList] )
        """
        self.expect(TokenType.LPAREN, "Era esperado '(' para iniciar parâmetros", expected="'('")
        receiver_param = None
        params: List[Parameter] = []
        is_first = True

        while not self.check(TokenType.RPAREN) and not self.check(TokenType.EOF):
            p_pre: List[ASTNode] = []
            p_post: List[ASTNode] = []
            p_mods: List[str] = []
            while True:
                if self.check(TokenType.AT) and not self._is_annotation_interface_declaration_ahead():
                    p_post.extend(self._parse_optional_annotations())
                elif self.peek().type == TokenType.KEYWORD_FINAL:
                    p_pre.extend(p_post)
                    p_post.clear()
                    p_mods.append(self.advance().lexeme)
                else:
                    break
            p_annos = p_pre + p_post

            t_ref = self.parse_type_reference(leading_annotations=p_post)

            # Verifica se é ReceiverParameter no primeiro parâmetro:
            # {Annotation} UnannType [Identifier .] this
            if is_first and (self.check(TokenType.KEYWORD_THIS) or (self.check(TokenType.IDENTIFIER) and self.peek_offset(1).type == TokenType.DOT and self.peek_offset(2).type == TokenType.KEYWORD_THIS)):
                qualifier = None
                if self.check(TokenType.IDENTIFIER):
                    qual_tok = self.advance()
                    self.expect(TokenType.DOT, "Era esperado '.' em qualificador de this")
                    qualifier = qual_tok.lexeme
                this_tok = self.expect(TokenType.KEYWORD_THIS, "Era esperado 'this' no parâmetro receptor")
                receiver_param = ReceiverParameter(
                    type_ref=t_ref,
                    name="this",
                    qualifier=qualifier,
                    annotations=p_annos,
                    line=this_tok.line,
                    column=this_tok.column
                )
                is_first = False
                if self.check(TokenType.COMMA):
                    self.advance()
                    continue
                else:
                    break

            is_first = False

            if self.check(TokenType.KEYWORD_THIS):
                t = self.peek()
                raise SyntacticError(
                    message="O parâmetro receptor ('this') só pode aparecer como o primeiro parâmetro formal",
                    line=t.line,
                    column=t.column,
                    expected="um identificador de parâmetro válido",
                    found="this"
                )

            ellipsis_annos: List[ASTNode] = []
            if self.check(TokenType.AT):
                ellipsis_annos = self._parse_optional_annotations()

            is_var = t_ref.is_varargs
            if not is_var and self.check(TokenType.ELLIPSIS):
                self.advance()
                t_ref.is_varargs = True
                is_var = True
            elif ellipsis_annos and not is_var:
                t = self.peek()
                raise SyntacticError(
                    message="Type annotation após o tipo do parâmetro exige '...' (varargs) ou '[]'",
                    line=t.line,
                    column=t.column,
                    expected="'...' após type annotation do parâmetro varargs",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )

            decl_id = self.parse_variable_declarator_id()
            if is_var:
                param = VariableArityParameter(
                    type_ref=t_ref,
                    name=decl_id.name,
                    line=decl_id.line,
                    column=decl_id.column,
                    modifiers=p_mods,
                    annotations=p_annos,
                    ellipsis_annotations=ellipsis_annos,
                )
            else:
                param = FormalParameter(
                    type_ref=t_ref,
                    name=decl_id.name,
                    is_varargs=False,
                    line=decl_id.line,
                    column=decl_id.column,
                    modifiers=p_mods,
                    annotations=p_annos,
                    dims=decl_id.dims
                )
            params.append(param)

            if self.check(TokenType.COMMA):
                self.advance()
            else:
                break

        self.expect(TokenType.RPAREN, "Era esperado ')' para fechar os parâmetros", expected="')'")
        return receiver_param, params

    def parse_parameter_list(self) -> List[Parameter]:
        """Processa a lista de parâmetros entre parênteses: (Tipo a, Tipo... b)"""
        _, params = self.parse_formal_parameters()
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
    # 2.7 BLOCOS E INSTRUÇÕES (FASE C / ETAPA S6 - JLS §14)
    # -------------------------------------------------------------------------
    def parse_block(self) -> Block:
        """Processa Block (JLS §14.2): { [BlockStatements] } preservando a ordem exata."""
        start_tok = self.expect(TokenType.LBRACE, "Era esperado '{' para iniciar o bloco", expected="'{'")
        statements = []

        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            statements.append(self.block_statement())

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o bloco", expected="'}'")
        return Block(statements, start_tok.line, start_tok.column)

    def _parse_local_type_declaration(self) -> ASTNode:
        """Processa LocalClassOrInterfaceDeclaration (JLS §14.3) marcando is_local=True."""
        local_annos, _pre, _post, local_mods = self._parse_annotations_and_modifiers_detailed(allow_sealed=True)
        if self._is_annotation_interface_declaration_ahead():
            decl = self.annotation_interface_declaration(local_mods, annotations=local_annos)
            return decl
        if self.check(TokenType.KEYWORD_CLASS):
            decl = self.class_declaration(local_mods)
            decl.annotations = local_annos
            decl.is_local = True
            return decl
        if self.check(TokenType.KEYWORD_INTERFACE):
            decl = self.interface_declaration(local_mods, annotations=local_annos)
            decl.is_local = True
            return decl
        if self.check(TokenType.KEYWORD_ENUM):
            decl = self.enum_declaration(local_mods, annotations=local_annos)
            decl.is_local = True
            return decl
        decl = self.record_declaration(local_mods, annotations=local_annos)
        decl.is_local = True
        return decl

    def block_statement(self) -> ASTNode:
        """
        Processa BlockStatement (JLS §14.2):
        - LocalClassOrInterfaceDeclaration
        - LocalVariableDeclarationStatement
        - Statement
        """
        if self._is_constructor_invocation_ahead():
            t = self.peek()
            raise SyntacticError(
                message="Invocação explícita de construtor ('this' ou 'super') só é permitida no nível superior do corpo de um construtor",
                line=t.line,
                column=t.column,
                expected="instrução válida (invocação de construtor proibida nesta posição)",
                found=t.lexeme
            )

        if self._is_local_type_declaration_ahead():
            return self._parse_local_type_declaration()

        if self._is_local_declaration():
            return self.parse_local_variable_declaration()

        return self.parse_statement(no_short_if=False)

    def _is_labeled_statement_ahead(self) -> bool:
        """Verifica se há LabeledStatement (Identificador ':') na posição atual."""
        return self.check(TokenType.IDENTIFIER) and self.peek_offset(1).type == TokenType.COLON

    def _is_yield_statement_ahead(self) -> bool:
        """
        Desambiguação contextual de 'yield' (JLS §14.21):
        Reconhece 'yield Expressao;' como YieldStatement, mantendo 'yield' como
        identificador comum em atribuições, pós-incrementos e acessos com '.' ou '['.
        """
        tok = self.peek()
        if tok.type != TokenType.IDENTIFIER or tok.lexeme != "yield":
            return False
        nxt = self.peek_offset(1)
        if nxt.type in ASSIGNMENT_TOKENS or nxt.type in (
            TokenType.DOT, TokenType.LBRACKET, TokenType.INCREMENT, TokenType.DECREMENT,
            TokenType.DOUBLE_COLON, TokenType.ARROW, TokenType.COLON,
        ):
            return False
        if nxt.type == TokenType.LPAREN and self.peek_offset(2).type == TokenType.RPAREN:
            return False
        return True

    def _is_statement_expression(self, expr: ASTNode) -> bool:
        """
        Verifica se a expressão pertence à produção normativa StatementExpression (JLS §14.8):
        Assignment | PreIncrementExpression | PreDecrementExpression |
        PostIncrementExpression | PostDecrementExpression |
        MethodInvocation | ClassInstanceCreationExpression.
        """
        if isinstance(expr, (Assignment, ObjectCreationExpression, MethodCall)):
            return True
        if isinstance(expr, UnaryOp) and expr.op in ("++", "--"):
            return True
        return False

    def _parse_statement_expression_list(self) -> List[ASTNode]:
        """Processa StatementExpression {, StatementExpression} (ForInit / ForUpdate)."""
        exprs: List[ASTNode] = []
        while True:
            expr = self.expression()
            if not self._is_statement_expression(expr):
                raise SyntacticError(
                    message="Expressão inválida nesta posição: apenas StatementExpression (atribuição, ++/--, chamada de método ou 'new ...(...)') é permitida (JLS §14.8 / §14.14.1)",
                    line=getattr(expr, "line", self.peek().line),
                    column=getattr(expr, "column", self.peek().column),
                    expected="uma StatementExpression válida",
                    found=expr.__class__.__name__,
                )
            exprs.append(expr)
            if self.check(TokenType.COMMA):
                self.advance()
            else:
                break
        return exprs

    def parse_statement(self, no_short_if: bool = False) -> ASTNode:
        """
        Processa Statement ou StatementNoShortIf (JLS §14.5).
        Não aceita declarações locais diretamente fora de um Block.
        """
        if self._is_constructor_invocation_ahead():
            t = self.peek()
            raise SyntacticError(
                message="Invocação explícita de construtor ('this' ou 'super') só é permitida no nível superior do corpo de um construtor",
                line=t.line,
                column=t.column,
                expected="instrução válida (invocação de construtor proibida nesta posição)",
                found=t.lexeme
            )

        if self._is_local_type_declaration_ahead() or self._is_local_declaration():
            t = self.peek()
            raise SyntacticError(
                message="Declarações locais de variáveis ou tipos não são permitidas diretamente como subinstrução sem bloco '{ ... }' (JLS §14.2 / §14.5)",
                line=t.line,
                column=t.column,
                expected="uma instrução executável ou bloco '{ ... }'",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )

        if self._is_labeled_statement_ahead():
            return self.parse_labeled_statement(no_short_if=no_short_if)

        if self.check(TokenType.KEYWORD_IF):
            return self.parse_if_statement(no_short_if=no_short_if)

        if self.check(TokenType.KEYWORD_WHILE):
            return self.parse_while_statement(no_short_if=no_short_if)

        if self.check(TokenType.KEYWORD_FOR):
            return self.parse_for_statement(no_short_if=no_short_if)

        return self.parse_statement_without_trailing_substatement()

    def parse_statement_no_short_if(self) -> ASTNode:
        """Processa StatementNoShortIf (JLS §14.5) resolvendo dangling else sem ambiguidade."""
        return self.parse_statement(no_short_if=True)

    def parse_statement_without_trailing_substatement(self) -> ASTNode:
        """Processa StatementWithoutTrailingSubstatement (JLS §14.5)."""
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

        # 4. Laço do-while: 'do ... while (cond);'
        if self.check(TokenType.KEYWORD_DO):
            return self.parse_do_while_statement()

        # 5. Seleção múltipla: 'switch (expr) { ... }'
        if self.check(TokenType.KEYWORD_SWITCH):
            return self.parse_switch_statement()

        # 6. Comandos de desvio: 'break [rotulo];' e 'continue [rotulo];'
        if self.check(TokenType.KEYWORD_BREAK):
            return self.parse_break_statement()
        if self.check(TokenType.KEYWORD_CONTINUE):
            return self.parse_continue_statement()

        # 7. Lançamento de exceção: 'throw expr;'
        if self.check(TokenType.KEYWORD_THROW):
            return self.parse_throw_statement()

        # 8. Asserção: 'assert cond [: msg];'
        if self.check(TokenType.KEYWORD_ASSERT):
            return self.parse_assert_statement()

        # 9. Tratamento de exceções: 'try ... catch ... finally'
        if self.check(TokenType.KEYWORD_TRY):
            return self.parse_try_statement()

        # 10. Bloco sincronizado: 'synchronized (lock) { ... }'
        if self.check(TokenType.KEYWORD_SYNCHRONIZED):
            return self.parse_synchronized_statement()

        # 11. Instrução contextual yield: 'yield expr;' (JLS §14.21)
        if self._is_yield_statement_ahead():
            return self.parse_yield_statement()

        # 12. Atribuição simples ou qualificada rápida (compatibilidade AST Assignment)
        if (self.check(TokenType.IDENTIFIER) or self.check(TokenType.KEYWORD_THIS)) and self._is_assignment_ahead():
            return self.assignment()

        # 13. ExpressionStatement restrita a StatementExpression (JLS §14.8)
        expr = self.expression()
        if not self._is_statement_expression(expr):
            t_line = getattr(expr, "line", self.peek().line)
            t_col = getattr(expr, "column", self.peek().column)
            raise SyntacticError(
                message="Expressão isolada inválida como instrução: apenas atribuições, incrementos/decrementos (++ / --), chamadas de método e instanciações ('new ...(...)') são permitidos em ExpressionStatement (JLS §14.8)",
                line=t_line,
                column=t_col,
                expected="uma StatementExpression válida seguida de ';'",
                found=expr.__class__.__name__,
            )
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final do comando", expected="';'")
        if isinstance(expr, Assignment):
            return expr
        return ExpressionStatement(expr, line=expr.line, column=expr.column)

    # -------------------------------------------------------------------------
    # 2.8 COMANDOS ESPECÍFICOS DE CONTROLE DE FLUXO (FASE C / ETAPA S6)
    # -------------------------------------------------------------------------
    def parse_labeled_statement(self, no_short_if: bool = False) -> LabeledStatement:
        """Processa LabeledStatement / LabeledStatementNoShortIf (JLS §14.7): Identifier : Statement."""
        lbl_tok = self.expect(TokenType.IDENTIFIER, "Era esperado um identificador de rótulo", expected="identificador de rótulo")
        self.expect(TokenType.COLON, "Era esperado ':' após o rótulo", expected="':'")
        stmt = self.parse_statement(no_short_if=no_short_if)
        return LabeledStatement(label=lbl_tok.lexeme, statement=stmt, line=lbl_tok.line, column=lbl_tok.column)

    def parse_yield_statement(self) -> YieldStatement:
        """Processa YieldStatement (JLS §14.21): yield Expression ;."""
        y_tok = self.advance()  # consome 'yield'
        if self.check(TokenType.SEMICOLON) or self.check(TokenType.EOF):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado uma expressão após 'yield'",
                line=t.line,
                column=t.column,
                expected="uma expressão após 'yield'",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        expr = self.expression()
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final de 'yield'", expected="';'")
        return YieldStatement(expression=expr, contextual_keyword=y_tok.lexeme, line=y_tok.line, column=y_tok.column)

    def parse_if_statement(self, no_short_if: bool = False) -> IfStatement:
        """
        Processa IfThenStatement / IfThenElseStatement / NoShortIf (JLS §14.9).
        Garante resolução gramatical exata do dangling else associando cada 'else' ao 'if' interno mais próximo.
        """
        if_tok = self.advance()  # consome 'if'
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

        if no_short_if:
            then_branch = self.parse_statement_no_short_if()
            self.expect(
                TokenType.KEYWORD_ELSE,
                "Era esperado 'else' em instrução condicional completa (StatementNoShortIf)",
                expected="'else'",
            )
            else_branch = self.parse_statement_no_short_if()
            return IfStatement(condition, then_branch, else_branch, if_tok.line, if_tok.column)

        then_branch = self.parse_statement(no_short_if=False)
        else_branch = None
        if self.check(TokenType.KEYWORD_ELSE):
            self.advance()  # consome 'else'
            else_branch = self.parse_statement(no_short_if=False)
        return IfStatement(condition, then_branch, else_branch, if_tok.line, if_tok.column)

    def parse_while_statement(self, no_short_if: bool = False) -> WhileStatement:
        """Processa WhileStatement / WhileStatementNoShortIf (JLS §14.12): while (condicao) corpo."""
        while_tok = self.advance()  # consome 'while'
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
        body = self.parse_statement(no_short_if=no_short_if)
        return WhileStatement(condition, body, while_tok.line, while_tok.column)

    def parse_do_while_statement(self) -> DoWhileStatement:
        """Processa DoStatement (JLS §14.13): do Statement while ( Expression ) ;"""
        do_tok = self.advance()  # consome 'do'
        body = self.parse_statement(no_short_if=False)
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

    def parse_for_statement(self, no_short_if: bool = False) -> ASTNode:
        """Processa for tradicional ou for aprimorado (for-each)."""
        for_tok = self.advance()  # consome 'for'
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

        if self._is_enhanced_for_ahead():
            return self._parse_enhanced_for(for_tok, no_short_if=no_short_if)
        return self._parse_traditional_for(for_tok, no_short_if=no_short_if)

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

    def _parse_enhanced_for(self, for_tok: Token, no_short_if: bool = False) -> EnhancedForStatement:
        """Processa EnhancedForStatement (JLS §14.14.2): for ({VariableModifier} LocalVariableType VariableDeclaratorId : Expression) Statement."""
        annos, _pre, post_annos, mods = self._parse_annotations_and_modifiers_detailed()
        is_var = False
        if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "var":
            var_tok = self.advance()
            type_ref = TypeReference(
                name="var",
                array_dimensions=0,
                type_arguments=[],
                line=var_tok.line,
                column=var_tok.column,
                annotations=post_annos,
            )
            local_type = LocalVariableType(type_ref=type_ref, is_var=True, line=var_tok.line, column=var_tok.column)
            is_var = True
        else:
            type_ref = self.parse_type_reference(leading_annotations=post_annos)
            local_type = LocalVariableType(type_ref=type_ref, is_var=False, line=type_ref.line, column=type_ref.column)

        decl_id = self.parse_variable_declarator_id()
        if self.check(TokenType.COMMA):
            t = self.peek()
            raise SyntacticError(
                message="O cabeçalho do 'for' aprimorado aceita exatamente um declarador de variável",
                line=t.line,
                column=t.column,
                expected="':'",
                found=",",
            )
        if self.check(TokenType.ASSIGN):
            t = self.peek()
            raise SyntacticError(
                message="A variável do 'for' aprimorado não pode possuir inicializador '='",
                line=t.line,
                column=t.column,
                expected="':'",
                found="=",
            )

        effective_type = "var" if is_var else (type_ref.get_effective_type(decl_id.dims) if decl_id.dims > 0 else type_ref.name)
        var_decl = LocalVariableDeclaration(
            type_name=effective_type,
            name=decl_id.name,
            line=decl_id.line,
            column=decl_id.column,
            type_ref=type_ref,
            modifiers=mods,
            annotations=annos,
            declarators=[VariableDeclarator(id=decl_id, initializer=None, base_type=type_ref, line=decl_id.line, column=decl_id.column)],
            is_var=is_var,
            local_type=local_type,
            dims=decl_id.dims,
        )
        self.expect(TokenType.COLON, "Era esperado ':' após a variável no 'for' aprimorado", expected="':'")
        iterable = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' para fechar o cabeçalho do 'for' aprimorado", expected="')'")
        body = self.parse_statement(no_short_if=no_short_if)
        return EnhancedForStatement(var_decl, iterable, body, for_tok.line, for_tok.column)

    def _parse_traditional_for(self, for_tok: Token, no_short_if: bool = False) -> ForStatement:
        """Processa BasicForStatement / BasicForStatementNoShortIf (JLS §14.14.1): for ([ForInit]; [Expr]; [ForUpdate]) Statement."""
        init = None
        init_expressions: List[ASTNode] = []
        if self.check(TokenType.SEMICOLON):
            self.advance()  # ForInit vazio
        else:
            if self._is_local_declaration():
                init = self.parse_local_variable_declaration_in_for()
            else:
                init_expressions = self._parse_statement_expression_list()
                init = (
                    init_expressions[0]
                    if len(init_expressions) == 1
                    else StatementExpressionList(
                        expressions=init_expressions,
                        line=init_expressions[0].line,
                        column=init_expressions[0].column,
                    )
                )
            self.expect(TokenType.SEMICOLON, "Era esperado ';' após a inicialização do 'for'", expected="';'")

        condition = None
        if self.check(TokenType.SEMICOLON):
            self.advance()
        else:
            condition = self.expression()
            self.expect(TokenType.SEMICOLON, "Era esperado ';' após a condição do 'for'", expected="';'")

        update = None
        update_expressions: List[ASTNode] = []
        if not self.check(TokenType.RPAREN):
            update_expressions = self._parse_statement_expression_list()
            update = (
                update_expressions[0]
                if len(update_expressions) == 1
                else StatementExpressionList(
                    expressions=update_expressions,
                    line=update_expressions[0].line,
                    column=update_expressions[0].column,
                )
            )
        self.expect(TokenType.RPAREN, "Era esperado ')' para fechar o cabeçalho do 'for'", expected="')'")

        body = self.parse_statement(no_short_if=no_short_if)
        return ForStatement(
            init=init,
            condition=condition,
            update=update,
            body=body,
            line=for_tok.line,
            column=for_tok.column,
            init_expressions=init_expressions,
            update_expressions=update_expressions,
        )

    # -------------------------------------------------------------------------
    # 3.1B PATTERNS (ETAPA S7 — JLS §14.30 / §15.20.2 / §14.11.1)
    # -------------------------------------------------------------------------
    def _skip_generic_type_args_offset(self, scan_start: int, stop_tokens: Set[TokenType]) -> Optional[int]:
        """Avança offset sobre '<...>' balanceados incluindo '>>' e '>>>'; retorna None se não fechar."""
        depth = 1
        scan = scan_start
        while depth > 0:
            st = self.peek_offset(scan)
            if st.type in stop_tokens or st.type == TokenType.EOF:
                return None
            if st.type == TokenType.LESS:
                depth += 1
            elif st.type == TokenType.GREATER:
                depth -= 1
            elif st.type == TokenType.RSHIFT:
                depth -= 2
            elif st.type == TokenType.URSHIFT:
                depth -= 3
            scan += 1
        return scan

    def _looks_like_switch_pattern_ahead(self) -> bool:
        """
        Detecta sintaxe de pattern matching em labels de 'switch'
        (TypePattern, RecordPattern, e padrões inválidos como primitivo/var/_ para erro específico).
        """
        t0 = self.peek()
        if t0.type == TokenType.KEYWORD_FINAL:
            return True
        if t0.type == TokenType.AT and not self._is_annotation_interface_declaration_ahead():
            return True
        if t0.type in PRIMITIVE_TYPE_TOKENS:
            return True
        if t0.type == TokenType.IDENTIFIER and t0.lexeme == "_":
            return True
        if t0.type == TokenType.IDENTIFIER:
            if t0.lexeme == "var" and self.peek_offset(1).type in (TokenType.IDENTIFIER, TokenType.LPAREN):
                return True
            idx = 1
            stop = {TokenType.EOF, TokenType.COLON, TokenType.ARROW, TokenType.SEMICOLON}
            while True:
                while self.peek_offset(idx).type == TokenType.DOT:
                    step = idx + 1
                    if self.peek_offset(step).type == TokenType.AT and not self._is_annotation_interface_declaration_ahead(step):
                        step = self._skip_annotations_offset(step)
                    if self.peek_offset(step).type == TokenType.IDENTIFIER:
                        idx = step + 1
                    else:
                        break
                idx = self._skip_annotations_offset(idx)
                nxt = self.peek_offset(idx)
                if nxt.type == TokenType.LESS:
                    after_gen = self._skip_generic_type_args_offset(idx + 1, stop)
                    if after_gen is None:
                        return False
                    idx = after_gen
                    continue
                break
            while self._has_array_brackets_after_annotations(idx):
                idx = self._skip_annotations_offset(idx)
                idx += 2  # '[' ']'
            nxt = self.peek_offset(idx)
            if nxt.type in (TokenType.LPAREN, TokenType.IDENTIFIER):
                return True
        return False

    def _parse_type_pattern_after_type(
        self,
        type_ref: TypeReference,
        mods: List[str],
        annotations: List[ASTNode],
        in_record_component: bool = False,
        is_var: bool = False,
    ) -> TypePattern:
        """Constrói TypePattern após analisar modificadores, anotações e TypeReference/var."""
        if (
            not is_var
            and type_ref.name in (
                "int", "boolean", "char", "byte", "short", "long", "float", "double"
            )
            and type_ref.array_dimensions == 0
            and not self.enable_preview_primitive_patterns
        ):
            ctx = "componente de RecordPattern" if in_record_component else "TypePattern"
            expected_msg = (
                "um ReferenceType, 'var' ou '_'" if in_record_component else "um ReferenceType"
            )
            raise SyntacticError(
                message=f"Tipo primitivo '{type_ref.name}' não é permitido em {ctx} no modo padrão da JLS Java SE 26 (Preview JEP 530)",
                line=type_ref.line,
                column=type_ref.column,
                expected=expected_msg,
                found=type_ref.name,
            )
        if type_ref.name == "void":
            raise SyntacticError(
                message="Tipo 'void' não é permitido em TypePattern",
                line=type_ref.line,
                column=type_ref.column,
                expected="um tipo válido de pattern",
                found="void",
            )
        id_tok = self.expect(
            TokenType.IDENTIFIER,
            "Era esperado um identificador de variável no TypePattern",
            expected="identificador de variável",
        )
        if self._has_array_brackets_after_annotations():
            bt = self.peek()
            raise SyntacticError(
                message="Dimensões de array '[]' não são permitidas no identificador de um TypePattern (use-as junto ao tipo — JLS §14.30.1)",
                line=bt.line,
                column=bt.column,
                expected="fim do TypePattern sem '[]' pós-identificador",
                found="[",
            )
        if self.check(TokenType.ASSIGN):
            at = self.peek()
            raise SyntacticError(
                message="Inicializador '=' não é permitido em TypePattern (JLS §14.30.1)",
                line=at.line,
                column=at.column,
                expected="fim do TypePattern",
                found="=",
            )

        decl_id = VariableDeclaratorId(name=id_tok.lexeme, dims=0, line=id_tok.line, column=id_tok.column)
        v_decl = VariableDeclarator(id=decl_id, initializer=None, base_type=type_ref, line=id_tok.line, column=id_tok.column)
        eff_type = "var" if is_var else type_ref.full_name
        local_type = LocalVariableType(type_ref=type_ref, is_var=is_var, line=type_ref.line, column=type_ref.column)
        local_var = LocalVariableDeclaration(
            type_name=eff_type,
            name=id_tok.lexeme,
            line=id_tok.line,
            initializer=None,
            column=id_tok.column,
            type_ref=type_ref,
            modifiers=list(mods),
            annotations=list(annotations),
            declarators=[v_decl],
            is_var=is_var,
            local_type=local_type,
            dims=0,
        )
        pvar = PatternVariable(
            name=id_tok.lexeme,
            type_ref=type_ref,
            modifiers=list(mods),
            annotations=list(annotations),
            is_final=("final" in mods),
            is_unnamed=(id_tok.lexeme == "_"),
            is_var=is_var,
            line=id_tok.line,
            column=id_tok.column,
        )
        return TypePattern(
            type_ref=type_ref,
            name=id_tok.lexeme,
            variable=pvar,
            local_variable=local_var,
            modifiers=list(mods),
            annotations=list(annotations),
            is_final=("final" in mods),
            is_unnamed=(id_tok.lexeme == "_"),
            is_var=is_var,
            line=type_ref.line,
            column=type_ref.column,
        )

    def _parse_record_pattern_after_type(
        self,
        type_ref: TypeReference,
        start_line: int,
        start_column: int,
    ) -> RecordPattern:
        """Processa recursivamente RecordPattern: ReferenceType ( [ComponentPatternList] ) (JLS §14.30.1)."""
        if self._pattern_depth >= self.max_pattern_depth:
            raise SyntacticError(
                message="Profundidade máxima de aninhamento de RecordPattern excedida",
                line=start_line,
                column=start_column,
                expected="pattern com profundidade dentro do limite suportado",
                found="RecordPattern",
            )
        if type_ref.name in ("int", "boolean", "char", "byte", "short", "long", "float", "double", "void") or type_ref.array_dimensions > 0:
            raise SyntacticError(
                message=f"Tipo '{type_ref.full_name}' inválido para RecordPattern: apenas tipos de classe record são permitidos (JLS §14.30.1)",
                line=type_ref.line,
                column=type_ref.column,
                expected="nome de um record",
                found=type_ref.full_name,
            )

        lparen = self.expect(TokenType.LPAREN, "Era esperado '(' para iniciar componentes do RecordPattern", expected="'('")
        components: List[ComponentPattern] = []
        self._pattern_depth += 1
        try:
            if not self.check(TokenType.RPAREN):
                while True:
                    components.append(self.parse_component_pattern())
                    if self.check(TokenType.COMMA):
                        self.advance()
                        if self.check(TokenType.RPAREN):
                            t = self.peek()
                            raise SyntacticError(
                                message="Vírgula sobrando na lista de componentes de RecordPattern",
                                line=t.line,
                                column=t.column,
                                expected="um ComponentPattern após ','",
                                found=")",
                            )
                    else:
                        break
            self.expect(TokenType.RPAREN, "Era esperado ')' para fechar o RecordPattern", expected="')'")
        finally:
            self._pattern_depth -= 1

        comp_list = ComponentPatternList(components=list(components), line=lparen.line, column=lparen.column)
        return RecordPattern(
            type_ref=type_ref,
            components=components,
            component_list=comp_list,
            line=start_line,
            column=start_column,
        )

    def parse_component_pattern(self) -> ComponentPattern:
        """Processa ComponentPattern (JLS §14.30.1): Pattern | MatchAllPattern ('_')."""
        if (
            self.check(TokenType.IDENTIFIER)
            and self.peek().lexeme == "_"
            and self.peek_offset(1).type in (TokenType.COMMA, TokenType.RPAREN)
        ):
            u_tok = self.advance()
            return MatchAllPattern(lexeme="_", is_unnamed=True, line=u_tok.line, column=u_tok.column)
        return self.parse_pattern(in_record_component=True)

    def parse_pattern(self, in_record_component: bool = False) -> Pattern:
        """Processa Pattern (JLS §14.30.1): TypePattern | RecordPattern."""
        t0 = self.peek()
        if t0.type == TokenType.IDENTIFIER and t0.lexeme == "_":
            if in_record_component:
                raise SyntacticError(
                    message="'_' não pode ser usado como tipo em ComponentPattern; use '_' isolado (MatchAllPattern) ou '<Tipo> _'",
                    line=t0.line,
                    column=t0.column,
                    expected="Pattern ou '_'",
                    found="_",
                )
            raise SyntacticError(
                message="MatchAllPattern '_' só é permitido diretamente como componente de RecordPattern; para unnamed TypePattern use '<Tipo> _' (JLS §14.30.1)",
                line=t0.line,
                column=t0.column,
                expected="TypePattern ou RecordPattern",
                found="_",
            )

        annos, _pre, post_annos, mods = self._parse_annotations_and_modifiers_detailed()
        disallowed_mods = [m for m in mods if m != "final"]
        if disallowed_mods:
            t = self.peek()
            raise SyntacticError(
                message=f"Modificador(es) {', '.join(disallowed_mods)!r} inválido(s) em Pattern (apenas 'final' é permitido em TypePattern)",
                line=t.line,
                column=t.column,
                expected="'final' ou tipo do pattern",
                found=disallowed_mods[0],
            )

        if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "var":
            var_tok = self.advance()
            if self.check(TokenType.LPAREN):
                raise SyntacticError(
                    message="'var' não pode ser utilizado como tipo de um RecordPattern",
                    line=var_tok.line,
                    column=var_tok.column,
                    expected="nome de variável após 'var'",
                    found="(",
                )
            if not in_record_component:
                raise SyntacticError(
                    message="'var' não pode ser utilizado como tipo em TypePattern de nível superior (JLS §14.30.1)",
                    line=var_tok.line,
                    column=var_tok.column,
                    expected="um ReferenceType explícito",
                    found="var",
                )
            type_ref = TypeReference(
                name="var",
                array_dimensions=0,
                type_arguments=[],
                line=var_tok.line,
                column=var_tok.column,
                annotations=post_annos,
            )
            return self._parse_type_pattern_after_type(
                type_ref=type_ref,
                mods=mods,
                annotations=annos,
                in_record_component=True,
                is_var=True,
            )

        type_ref = self.parse_type_reference(leading_annotations=post_annos)
        if self.check(TokenType.LPAREN):
            if mods:
                raise SyntacticError(
                    message="Modificador 'final' não é permitido em RecordPattern (JLS §14.30.1)",
                    line=type_ref.line,
                    column=type_ref.column,
                    expected="identificador da variável após 'final <Tipo>'",
                    found="(",
                )
            return self._parse_record_pattern_after_type(type_ref, t0.line, t0.column)

        return self._parse_type_pattern_after_type(
            type_ref=type_ref,
            mods=mods,
            annotations=annos,
            in_record_component=in_record_component,
            is_var=False,
        )

    def _parse_switch_label(self, switch_position: Optional[int] = None) -> SwitchLabel:
        """Processa SwitchLabel completo (JLS §14.11.1): constantes, null[, default], patterns [when expr], default."""
        if self.check(TokenType.KEYWORD_DEFAULT):
            def_tok = self.advance()
            return DefaultLabel(line=def_tok.line, column=def_tok.column)

        case_tok = self.expect(TokenType.KEYWORD_CASE, "Era esperado 'case' ou 'default' no bloco 'switch'", expected="'case' ou 'default'")
        if self.check(TokenType.COLON) or self.check(TokenType.ARROW):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado um valor ou pattern após 'case'",
                line=t.line,
                column=t.column,
                expected="uma constante, 'null' ou pattern após 'case'",
                found=t.lexeme,
            )
        if self.check(TokenType.KEYWORD_DEFAULT):
            t = self.peek()
            raise SyntacticError(
                message="Sintaxe inválida em label 'case': use 'default' isolado ou 'case null, default'",
                line=t.line,
                column=t.column,
                expected="uma constante, 'null' ou pattern",
                found="default",
            )

        # 1. case null [, default]
        if self.check(TokenType.NULL_LITERAL):
            ntok = self.advance()
            has_default = False
            if self.check(TokenType.COMMA):
                if self.peek_offset(1).type == TokenType.KEYWORD_DEFAULT:
                    self.advance()  # ','
                    self.advance()  # 'default'
                    has_default = True
                else:
                    t = self.peek_offset(1)
                    raise SyntacticError(
                        message="Após 'case null,', apenas 'default' é permitido pela gramática Java SE 26 (JLS §14.11.1)",
                        line=t.line,
                        column=t.column,
                        expected="'default'",
                        found=t.lexeme if t.type != TokenType.EOF else "EOF",
                    )
            if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "when":
                t = self.peek()
                raise SyntacticError(
                    message="Cláusula de guarda 'when' não é permitida após 'case null' (JLS §14.11.1)",
                    line=t.line,
                    column=t.column,
                    expected="':' ou '->'",
                    found="when",
                )
            null_lit = Literal(ntok.lexeme, "NULL", line=ntok.line, column=ntok.column)
            const_list = CaseConstantList(constants=[null_lit], line=case_tok.line, column=case_tok.column)
            return CaseLabel(
                constants=[null_lit],
                constant_list=const_list,
                is_null=True,
                has_default=has_default,
                switch_position=switch_position,
                line=case_tok.line,
                column=case_tok.column,
            )

        # 2. case CasePattern { , CasePattern } [ Guard ]
        if self._looks_like_switch_pattern_ahead():
            patterns: List[ASTNode] = []
            while True:
                if self.check(TokenType.COLON) or self.check(TokenType.ARROW) or (
                    self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "when"
                ):
                    t = self.peek()
                    raise SyntacticError(
                        message="Vírgula sobrando em label 'case': era esperado outro pattern após ','",
                        line=t.line,
                        column=t.column,
                        expected="CasePattern após ','",
                        found=t.lexeme,
                    )
                if self.check(TokenType.NULL_LITERAL) or self.check(TokenType.KEYWORD_DEFAULT):
                    t = self.peek()
                    raise SyntacticError(
                        message=f"'{t.lexeme}' não pode ser combinado com patterns após ',' em um label 'case' (JLS §14.11.1)",
                        line=t.line,
                        column=t.column,
                        expected="CasePattern",
                        found=t.lexeme,
                    )
                pat = self.parse_pattern(in_record_component=False)
                patterns.append(pat)
                if self.check(TokenType.COMMA):
                    self.advance()
                    if (
                        self.check(TokenType.IDENTIFIER)
                        and self.peek_offset(1).type in (TokenType.COLON, TokenType.ARROW, TokenType.COMMA)
                        and self.peek().lexeme != "_"
                    ):
                        t = self.peek()
                        raise SyntacticError(
                            message=f"Múltiplos declaradores ('{t.lexeme}') sem tipo não são permitidos em case pattern; informe o tipo de cada alternativa (JLS §14.11.1 / §14.30.1)",
                            line=t.line,
                            column=t.column,
                            expected="CasePattern completo",
                            found=t.lexeme,
                        )
                else:
                    break

            guard = None
            if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "when":
                when_tok = self.advance()
                if self.check(TokenType.COLON) or self.check(TokenType.ARROW) or self.check(TokenType.EOF):
                    t = self.peek()
                    raise SyntacticError(
                        message="Era esperada uma expressão booleana após 'when' no guard do 'switch'",
                        line=t.line,
                        column=t.column,
                        expected="expressão booleana após 'when'",
                        found=t.lexeme if t.type != TokenType.EOF else "EOF",
                    )
                # Evita que `when flag -> ...` ou `when (flag) -> ...` confunda o '->' da SwitchRule com lambda
                guard_expr = self.assignment_expression()
                guard = Guard(expression=guard_expr, line=when_tok.line, column=when_tok.column)

            return PatternCaseLabel(
                patterns=patterns,
                guard=guard,
                switch_position=switch_position,
                line=case_tok.line,
                column=case_tok.column,
            )

        # 3. case CaseConstant { , CaseConstant }
        constants: List[ASTNode] = []
        while True:
            if self.check(TokenType.KEYWORD_DEFAULT):
                t = self.peek()
                raise SyntacticError(
                    message="'default' após vírgula só é permitido em 'case null, default'",
                    line=t.line,
                    column=t.column,
                    expected="constante de case",
                    found="default",
                )
            if self.check(TokenType.NULL_LITERAL) or self._looks_like_switch_pattern_ahead():
                t = self.peek()
                raise SyntacticError(
                    message="Não é permitido misturar constantes com patterns ou 'null' no mesmo label 'case' (JLS §14.11.1)",
                    line=t.line,
                    column=t.column,
                    expected="CaseConstant válida",
                    found=t.lexeme,
                )
            expr = self.ternary_expression()
            if isinstance(expr, (MethodCall, LambdaExpression, Assignment, ObjectCreationExpression)):
                raise SyntacticError(
                    message="Apenas expressões constantes são permitidas como labels constantes de 'case'",
                    line=getattr(expr, "line", case_tok.line),
                    column=getattr(expr, "column", case_tok.column),
                    expected="CaseConstant válida",
                    found=expr.__class__.__name__,
                )
            if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "when":
                t = self.peek()
                raise SyntacticError(
                    message="Cláusula de guarda 'when' só é permitida em labels 'case' com pattern (JLS §14.11.1)",
                    line=t.line,
                    column=t.column,
                    expected="':' ou '->'",
                    found="when",
                )
            if self.check(TokenType.IDENTIFIER):
                t = self.peek()
                raise SyntacticError(
                    message="Token inesperado após constante em label 'case'",
                    line=t.line,
                    column=t.column,
                    expected="':' ou '->' ou ','",
                    found=t.lexeme,
                )
            constants.append(expr)

            if self.check(TokenType.COMMA):
                self.advance()
                if self.check(TokenType.COLON) or self.check(TokenType.ARROW):
                    t = self.peek()
                    raise SyntacticError(
                        message="Vírgula sobrando em label 'case': era esperado outra constante após ','",
                        line=t.line,
                        column=t.column,
                        expected="constante após ','",
                        found=t.lexeme,
                    )
            else:
                break

        const_list = CaseConstantList(constants=list(constants), line=case_tok.line, column=case_tok.column)
        return CaseLabel(
            constants=constants,
            constant_list=const_list,
            is_null=False,
            has_default=False,
            switch_position=switch_position,
            line=case_tok.line,
            column=case_tok.column,
        )

    def _parse_switch_block(self, is_expression: bool = False) -> Tuple[SwitchBlock, List[SwitchCase], Optional[Block]]:
        """Processa SwitchBlock (JLS §14.11.1): statement groups (:) ou switch rules (->)."""
        lbrace_tok = self.expect(TokenType.LBRACE, "Era esperado '{' para iniciar o corpo do 'switch'", expected="'{'")

        statement_groups: List[SwitchBlockStatementGroup] = []
        switch_rules: List[SwitchRule] = []
        entries: List[ASTNode] = []
        compat_cases: List[SwitchCase] = []
        default_block: Optional[Block] = None
        block_mode: Optional[str] = None  # "groups" | "rules"
        label_pos = 0

        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            if not (self.check(TokenType.KEYWORD_CASE) or self.check(TokenType.KEYWORD_DEFAULT)):
                t = self.peek()
                found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                raise SyntacticError(
                    message="Era esperado 'case', 'default' ou '}' dentro do bloco 'switch'",
                    line=t.line,
                    column=t.column,
                    expected="'case', 'default' ou '}'",
                    found=found_repr,
                )

            first_label = self._parse_switch_label(switch_position=label_pos)
            label_pos += 1

            if self.check(TokenType.ARROW):
                if block_mode == "groups":
                    t = self.peek()
                    raise SyntacticError(
                        message="Não é permitido misturar grupos clássicos (':') e switch rules ('->') no mesmo bloco 'switch'",
                        line=t.line,
                        column=t.column,
                        expected="':'",
                        found="->",
                    )
                block_mode = "rules"
                self.advance()  # consome '->'

                is_block_body = False
                is_throw_body = False
                is_expr_body = False

                if self.check(TokenType.LBRACE):
                    body = self.parse_block()
                    is_block_body = True
                elif self.check(TokenType.KEYWORD_THROW):
                    body = self.parse_throw_statement()
                    is_throw_body = True
                else:
                    expr = self.expression()
                    if not is_expression and not self._is_statement_expression(expr):
                        raise SyntacticError(
                            message="Em switch statement, a expressão à direita de '->' deve ser uma StatementExpression válida seguida de ';' (atribuição, ++/--, chamada de método ou 'new ...(...)') — JLS §14.11.1",
                            line=getattr(expr, "line", first_label.line),
                            column=getattr(expr, "column", first_label.column),
                            expected="uma StatementExpression válida",
                            found=expr.__class__.__name__,
                        )
                    self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da switch rule", expected="';'")
                    if is_expression:
                        body = expr
                    elif isinstance(expr, Assignment):
                        body = expr
                    else:
                        body = ExpressionStatement(expr, line=expr.line, column=expr.column)
                    is_expr_body = True

                rule = SwitchRule(
                    labels=[first_label],
                    body=body,
                    is_throw=is_throw_body,
                    is_block=is_block_body,
                    is_expression=is_expr_body,
                    line=first_label.line,
                    column=first_label.column,
                )
                switch_rules.append(rule)
                entries.append(rule)
                continue

            if not self.check(TokenType.COLON):
                t = self.peek()
                found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                raise SyntacticError(
                    message="Era esperado ':' ou '->' após o label do 'switch'",
                    line=t.line,
                    column=t.column,
                    expected="':' ou '->'",
                    found=found_repr,
                )

            if block_mode == "rules":
                t = self.peek()
                raise SyntacticError(
                    message="Não é permitido misturar switch rules ('->') e grupos clássicos (':') no mesmo bloco 'switch'",
                    line=t.line,
                    column=t.column,
                    expected="'->'",
                    found=":",
                )
            block_mode = "groups"
            self.advance()  # consome ':'

            labels: List[SwitchLabel] = [first_label]
            while self.check(TokenType.KEYWORD_CASE) or self.check(TokenType.KEYWORD_DEFAULT):
                extra_lbl = self._parse_switch_label(switch_position=label_pos)
                label_pos += 1
                if self.check(TokenType.ARROW):
                    t = self.peek()
                    raise SyntacticError(
                        message="Não é permitido empilhar labels ':' diretamente com regra '->' ou misturar ':' e '->' no mesmo 'switch'",
                        line=t.line,
                        column=t.column,
                        expected="':'",
                        found="->",
                    )
                self.expect(TokenType.COLON, "Era esperado ':' após o label do 'case'/'default'", expected="':'")
                labels.append(extra_lbl)

            group_stmts: List[ASTNode] = []
            while (
                not self.check(TokenType.RBRACE)
                and not self.check(TokenType.EOF)
                and not self.check(TokenType.KEYWORD_CASE)
                and not self.check(TokenType.KEYWORD_DEFAULT)
            ):
                group_stmts.append(self.block_statement())

            group = SwitchBlockStatementGroup(
                labels=labels,
                statements=group_stmts,
                line=labels[0].line,
                column=labels[0].column,
            )
            statement_groups.append(group)
            entries.append(group)

            # Preenche campos retrocompatíveis cases / default_block para suítes legadas
            for idx, lbl in enumerate(labels):
                attached = group_stmts if idx == len(labels) - 1 else []
                if isinstance(lbl, DefaultLabel):
                    default_block = Block(statements=attached, line=lbl.line, column=lbl.column)
                elif isinstance(lbl, CaseLabel):
                    val_node = (
                        lbl.constants[0]
                        if lbl.constants
                        else (lbl.patterns[0] if lbl.patterns else Literal("null", "NULL", line=lbl.line, column=lbl.column))
                    )
                    compat_cases.append(SwitchCase(value=val_node, statements=attached, line=lbl.line, column=lbl.column))
                    if lbl.has_default and default_block is None:
                        default_block = Block(statements=attached, line=lbl.line, column=lbl.column)

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o 'switch'", expected="'}'")
        sw_block = SwitchBlock(
            statement_groups=statement_groups,
            switch_rules=switch_rules,
            entries=entries,
            is_rule_based=(block_mode == "rules"),
            line=lbrace_tok.line,
            column=lbrace_tok.column,
        )
        return sw_block, compat_cases, default_block

    def parse_switch_statement(self) -> SwitchStatement:
        """Processa SwitchStatement (JLS §14.11) com suporte a groups ':' e rules '->'."""
        sw_tok = self.advance()  # consome 'switch'
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'switch'", expected="'('")
        if self.check(TokenType.RPAREN):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado uma expressão de controle entre parênteses no 'switch'",
                line=t.line,
                column=t.column,
                expected="uma expressão de controle",
                found=")",
            )
        control_expr = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' após a expressão do 'switch'", expected="')'")
        sw_block, cases, default_block = self._parse_switch_block(is_expression=False)
        return SwitchStatement(
            expression=control_expr,
            cases=cases,
            default_block=default_block,
            line=sw_tok.line,
            column=sw_tok.column,
            switch_block=sw_block,
        )

    def _parse_switch_expression(self) -> SwitchExpression:
        """
        Processa expressão switch auxiliar para contextualização do YieldStatement na S6.
        Integração completa como poly-expression será auditada na Etapa S8.
        """
        sw_tok = self.advance()  # consome 'switch'
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'switch'", expected="'('")
        if self.check(TokenType.RPAREN):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado uma expressão de controle entre parênteses no 'switch'",
                line=t.line,
                column=t.column,
                expected="uma expressão de controle",
                found=")",
            )
        control_expr = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' após a expressão do 'switch'", expected="')'")
        sw_block, _cases, _def = self._parse_switch_block(is_expression=True)
        return SwitchExpression(expression=control_expr, switch_block=sw_block, line=sw_tok.line, column=sw_tok.column)

    def parse_local_variable_declaration_in_for(self) -> LocalVariableDeclaration:
        """Processa declaração de variável local no cabeçalho do 'for' (sem ponto e vírgula final)."""
        return self._parse_local_variable_declaration_core(require_semicolon=False, in_resource=False)

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
        """Processa TryStatement / TryWithResourcesStatement (JLS §14.20) com multi-catch e ResourceSpecification."""
        try_tok = self.advance()  # consome 'try'
        resources: List[ASTNode] = []
        wrapped_resources: List[Resource] = []
        resource_spec: Optional[ResourceSpecification] = None

        if self.check(TokenType.LPAREN):
            lp_tok = self.advance()  # consome '('
            if self.check(TokenType.RPAREN):
                t = self.peek()
                raise SyntacticError(
                    message="Especificação de recursos do 'try-with-resources' não pode estar vazia",
                    line=t.line,
                    column=t.column,
                    expected="declaração de recurso ou variável existente",
                    found=")",
                )
            trailing_semi = False
            while not self.check(TokenType.RPAREN) and not self.check(TokenType.EOF):
                trailing_semi = False
                if self._is_local_declaration():
                    decl = self.parse_local_variable_declaration_in_resource()
                    resources.append(decl)
                    wrapped_resources.append(Resource(declaration=decl, is_reference=False, line=decl.line, column=decl.column))
                else:
                    var_acc = self.expression()
                    if not isinstance(var_acc, (Identifier, MemberAccess)):
                        raise SyntacticError(
                            message="Recurso inválido em 'try-with-resources': informe declaração local com '=' ou acesso a variável final/efetivamente final",
                            line=getattr(var_acc, "line", lp_tok.line),
                            column=getattr(var_acc, "column", lp_tok.column),
                            expected="declaração de recurso ou referência a variável",
                            found=var_acc.__class__.__name__,
                        )
                    res_node = Resource(variable_access=var_acc, is_reference=True, line=var_acc.line, column=var_acc.column)
                    resources.append(res_node)
                    wrapped_resources.append(res_node)

                if self.check(TokenType.SEMICOLON):
                    self.advance()
                    trailing_semi = True
                    if self.check(TokenType.RPAREN):
                        break
                else:
                    break
            self.expect(TokenType.RPAREN, "Era esperado ')' para fechar os recursos do 'try'", expected="')'")
            resource_spec = ResourceSpecification(
                resources=wrapped_resources,
                has_trailing_semicolon=trailing_semi,
                line=lp_tok.line,
                column=lp_tok.column,
            )

        body = self.parse_block()

        catches: List[CatchClause] = []
        while self.check(TokenType.KEYWORD_CATCH):
            catch_tok = self.advance()  # consome 'catch'
            self.expect(TokenType.LPAREN, "Era esperado '(' após 'catch'", expected="'('")
            c_annos, _c_pre, c_post, c_mods = self._parse_annotations_and_modifiers_detailed()
            if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "var":
                t = self.peek()
                raise SyntacticError(
                    message="'var' não é permitido como tipo de exceção em cláusula 'catch'",
                    line=t.line,
                    column=t.column,
                    expected="um tipo de exceção",
                    found="var",
                )
            p_type = self.parse_type_reference(leading_annotations=c_post)
            catch_types: List[TypeReference] = [p_type]
            while self.check(TokenType.BITWISE_OR):
                self.advance()  # consome '|'
                if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "var":
                    t = self.peek()
                    raise SyntacticError(
                        message="'var' não é permitido em tipo de captura multicatch",
                        line=t.line,
                        column=t.column,
                        expected="um tipo de exceção após '|'",
                        found="var",
                    )
                catch_types.append(self.parse_type_reference())

            catch_type_node = CatchType(types=catch_types, line=p_type.line, column=p_type.column)
            decl_id = self.parse_variable_declarator_id()
            if decl_id.dims > 0:
                raise SyntacticError(
                    message="Parâmetro da cláusula 'catch' não pode declarar dimensões de array '[]'",
                    line=decl_id.line,
                    column=decl_id.column,
                    expected="')'",
                    found="[",
                )
            param = Parameter(
                p_type,
                decl_id.name,
                line=decl_id.line,
                column=decl_id.column,
                modifiers=c_mods,
                annotations=c_annos,
            )
            self.expect(TokenType.RPAREN, "Era esperado ')' após o parâmetro do 'catch'", expected="')'")
            c_body = self.parse_block()
            catches.append(CatchClause(param, c_body, catch_tok.line, catch_tok.column, catch_type=catch_type_node))

        finally_block = None
        if self.check(TokenType.KEYWORD_FINALLY):
            self.advance()  # consome 'finally'
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

        return TryStatement(
            resources,
            body,
            catches,
            finally_block,
            try_tok.line,
            try_tok.column,
            resource_specification=resource_spec,
        )

    def parse_local_variable_declaration_in_resource(self) -> LocalVariableDeclaration:
        """Processa declaração de variável dentro dos recursos do try: {VariableModifier} LocalVariableType id = expr."""
        return self._parse_local_variable_declaration_core(require_semicolon=False, in_resource=True)

    def parse_synchronized_statement(self) -> SynchronizedStatement:
        """Processa synchronized (lock) { corpo }."""
        sync_tok = self.advance()  # consome 'synchronized'
        self.expect(TokenType.LPAREN, "Era esperado '(' após 'synchronized'", expected="'('")
        lock = self.expression()
        self.expect(TokenType.RPAREN, "Era esperado ')' após a expressão de lock do 'synchronized'", expected="')'")
        body = self.parse_block()
        return SynchronizedStatement(lock, body, sync_tok.line, sync_tok.column)

    def _parse_local_variable_declaration_core(
        self,
        require_semicolon: bool = True,
        in_resource: bool = False,
    ) -> LocalVariableDeclaration:
        """Implementa LocalVariableDeclaration (JLS §14.4) com suporte completo a múltiplos declaradores e 'var'."""
        annos, _pre, post_annos, mods = self._parse_annotations_and_modifiers_detailed()
        disallowed_mods = [m for m in mods if m != "final"]
        if disallowed_mods:
            t = self.peek()
            raise SyntacticError(
                message=f"Modificador(es) {', '.join(disallowed_mods)!r} inválido(s) em declaração de variável local (apenas 'final' é permitido)",
                line=t.line,
                column=t.column,
                expected="'final' ou tipo da variável",
                found=disallowed_mods[0],
            )

        is_var = False
        if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "var":
            var_tok = self.advance()
            type_ref = TypeReference(
                name="var",
                array_dimensions=0,
                type_arguments=[],
                line=var_tok.line,
                column=var_tok.column,
                annotations=post_annos,
            )
            local_type = LocalVariableType(type_ref=type_ref, is_var=True, line=var_tok.line, column=var_tok.column)
            is_var = True
        else:
            type_ref = self.parse_type_reference(leading_annotations=post_annos)
            local_type = LocalVariableType(type_ref=type_ref, is_var=False, line=type_ref.line, column=type_ref.column)

        declarators: List[VariableDeclarator] = []
        while True:
            decl_id = self.parse_variable_declarator_id()
            if not is_var and decl_id.name == type_ref.name and type_ref.name in (
                "int", "boolean", "char", "byte", "short", "long", "float", "double", "void"
            ):
                raise SyntacticError(
                    message=f"Nome de variável inválido: '{decl_id.name}' é uma palavra reservada",
                    line=decl_id.line,
                    column=decl_id.column,
                    expected="um identificador de variável",
                    found=decl_id.name,
                )
            init = None
            if self.check(TokenType.ASSIGN):
                self.advance()
                if (
                    self.check(TokenType.SEMICOLON)
                    or self.check(TokenType.COMMA)
                    or (in_resource and self.check(TokenType.RPAREN))
                    or self.check(TokenType.EOF)
                ):
                    t = self.peek()
                    found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
                    raise SyntacticError(
                        message="Era esperado uma expressão após '='",
                        line=t.line,
                        column=t.column,
                        expected="uma expressão após '='",
                        found=found_repr,
                    )
                init = self.variable_initializer()
            elif in_resource:
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado '=' na inicialização do recurso do 'try'",
                    line=t.line,
                    column=t.column,
                    expected="'='",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )

            declarators.append(
                VariableDeclarator(
                    id=decl_id,
                    initializer=init,
                    base_type=type_ref,
                    line=decl_id.line,
                    column=decl_id.column,
                )
            )
            if not in_resource and self.check(TokenType.COMMA):
                self.advance()
            else:
                break

        if require_semicolon:
            self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da declaração", expected="';'")

        first_decl = declarators[0]
        first_id = first_decl.id
        first_eff_type = (
            "var"
            if is_var
            else (type_ref.get_effective_type(first_id.dims) if first_id.dims > 0 else type_ref.name)
        )
        return LocalVariableDeclaration(
            type_name=first_eff_type,
            name=first_id.name,
            line=first_id.line,
            initializer=first_decl.initializer,
            column=first_id.column,
            type_ref=type_ref,
            modifiers=mods,
            annotations=annos,
            declarators=declarators,
            is_var=is_var,
            local_type=local_type,
            dims=first_id.dims,
        )

    def parse_local_variable_declaration(self) -> LocalVariableDeclaration:
        """Processa declaração local: {VariableModifier} LocalVariableType VariableDeclaratorList ;"""
        return self._parse_local_variable_declaration_core(require_semicolon=True, in_resource=False)

    # -------------------------------------------------------------------------
    # 2.9 COMANDOS E MODO FRAGMENTO DIDÁTICO
    # -------------------------------------------------------------------------
    def statement(self) -> ASTNode:
        """Processa declarações, atribuições e estruturas de controle de nível superior."""
        if self.check(TokenType.KEYWORD_SWITCH):
            return self.parse_switch_statement()

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
            t = self.peek()
            found_repr = t.lexeme if t.type != TokenType.EOF else "EOF"
            raise SyntacticError(
                message=f"Era esperado '=' após o identificador '{name}'",
                line=t.line,
                column=t.column,
                expected=f"'=' após o identificador '{name}'",
                found=found_repr,
            )

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
        self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da atribuição", expected="';'")
        return Assignment(name, start_tok.line, expr, operator=op, column=start_tok.column, target=target_node)

    # -------------------------------------------------------------------------
    # 2.10 EXPRESSÕES E OPERADORES (FASE D)
    # -------------------------------------------------------------------------
    def expression(self) -> ASTNode:
        """Ponto de entrada de expressões: inicia pela avaliação de expressões lambda."""
        return self.lambda_expression()

    def _is_lambda_ahead(self) -> bool:
        """Verifica se os próximos tokens iniciam uma LambdaExpression ('id ->' ou '(params) ->')."""
        if (
            self.check(TokenType.IDENTIFIER)
            and self.peek().lexeme != "var"
            and self.peek_offset(1).type == TokenType.ARROW
        ):
            return True
        if self.check(TokenType.LPAREN) and self._is_lambda_parameters_ahead():
            return True
        return False

    def _is_explicit_lambda_param_ahead(self) -> bool:
        """Determina se o próximo parâmetro dentro de '(...)' possui tipo explícito antes do nome."""
        off = self._skip_annotations_offset(0)
        t = self.peek_offset(off)
        if t.type in PRIMITIVE_TYPE_TOKENS:
            return True
        if t.type == TokenType.IDENTIFIER:
            if t.lexeme == "var":
                return False
            idx = off + 1
            while (
                self.peek_offset(idx).type == TokenType.DOT
                and (
                    self.peek_offset(idx + 1).type == TokenType.IDENTIFIER
                    or (
                        self.peek_offset(idx + 1).type == TokenType.AT
                        and not self._is_annotation_interface_declaration_ahead(idx + 1)
                    )
                )
            ):
                step = self._skip_annotations_offset(idx + 1)
                if self.peek_offset(step).type == TokenType.IDENTIFIER:
                    idx = step + 1
                else:
                    break
            if self.peek_offset(idx).type == TokenType.LESS:
                depth = 1
                idx += 1
                while depth > 0:
                    st = self.peek_offset(idx)
                    if st.type in (TokenType.EOF, TokenType.SEMICOLON):
                        return False
                    if st.type == TokenType.LESS:
                        depth += 1
                    elif st.type == TokenType.GREATER:
                        depth -= 1
                    elif st.type == TokenType.RSHIFT:
                        depth -= 2
                    elif st.type == TokenType.URSHIFT:
                        depth -= 3
                    idx += 1
            while True:
                step = self._skip_annotations_offset(idx)
                if self.peek_offset(step).type == TokenType.LBRACKET and self.peek_offset(step + 1).type == TokenType.RBRACKET:
                    idx = step + 2
                else:
                    idx = step
                    break
            if self.peek_offset(idx).type == TokenType.ELLIPSIS:
                idx += 1
            return self.peek_offset(idx).type == TokenType.IDENTIFIER
        return False

    def lambda_expression(self) -> ASTNode:
        """
        Nível 1: Expressões lambda '->' (JLS §15.27).
        Suporta:
        - Parâmetro único sem parênteses: x -> x * 2
        - Parâmetros entre parênteses: () -> ..., (a, b) -> ..., (int a, int b) -> ..., (var a, var b) -> ...
        - Validação de consistência (sem misturar tipos explícitos, 'var' e inferidos)
        - Corpo como expressão ou bloco: x -> { return x + 1; }
        """
        # Caso 1: identificador único seguido de '->' (ex: x -> ...)
        if self.check(TokenType.IDENTIFIER) and self.peek_offset(1).type == TokenType.ARROW:
            if self.peek().lexeme == "var":
                vt = self.peek()
                raise SyntacticError(
                    message="'var' não pode ser utilizado como nome de parâmetro lambda sem parênteses (use '(var x) -> ...')",
                    line=vt.line,
                    column=vt.column,
                    expected="identificador de parâmetro ou '(var x) ->'",
                    found="var",
                )
            param_tok = self.advance()
            self.advance()  # consome '->'
            if self.check(TokenType.LBRACE):
                body = self.parse_block()
                is_block = True
            else:
                body = self.expression()
                is_block = False
            return LambdaExpression(
                parameters=[param_tok.lexeme],
                typed_parameters=[LambdaParameter(name=param_tok.lexeme, line=param_tok.line, column=param_tok.column)],
                parameter_mode="inferred",
                body=body,
                is_block_body=is_block,
                line=param_tok.line,
                column=param_tok.column,
            )

        # Caso 2: parâmetros entre parênteses seguidos de '->'
        if self.check(TokenType.LPAREN) and self._is_lambda_parameters_ahead():
            start_tok = self.advance()  # consome '('
            params: List[str] = []
            typed_params: List[LambdaParameter] = []
            kinds_seen: Set[str] = set()

            while not self.check(TokenType.RPAREN) and not self.check(TokenType.EOF):
                annos, _pre, post_annos, mods = self._parse_annotations_and_modifiers_detailed(
                    allow_default=False,
                    allow_sealed=False,
                )
                disallowed_mods = [m for m in mods if m != "final"]
                if disallowed_mods:
                    t = self.peek()
                    raise SyntacticError(
                        message=f"Modificador(es) {', '.join(disallowed_mods)!r} inválido(s) em parâmetro de expressão lambda (JLS §15.27.1)",
                        line=t.line,
                        column=t.column,
                        expected="'final' ou tipo/nome de parâmetro",
                        found=disallowed_mods[0],
                    )

                if self.check(TokenType.KEYWORD_VOID):
                    t = self.peek()
                    raise SyntacticError(
                        message="Tipo 'void' não é permitido como tipo de parâmetro de expressão lambda",
                        line=t.line,
                        column=t.column,
                        expected="tipo válido de parâmetro",
                        found="void",
                    )

                if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "var" and self.peek_offset(1).type != TokenType.COMMA and self.peek_offset(1).type != TokenType.RPAREN:
                    var_tok = self.advance()
                    if self.check(TokenType.LBRACKET) or self.check(TokenType.LESS):
                        t = self.peek()
                        raise SyntacticError(
                            message="'var' não pode ser combinado com '[]' ou argumentos genéricos em parâmetro lambda (JLS §15.27.1)",
                            line=t.line,
                            column=t.column,
                            expected="nome do parâmetro",
                            found=t.lexeme,
                        )
                    name_tok = self.expect(
                        TokenType.IDENTIFIER,
                        "Era esperado nome do parâmetro após 'var' na expressão lambda",
                        expected="nome de parâmetro",
                    )
                    if self.check(TokenType.ELLIPSIS):
                        et = self.peek()
                        raise SyntacticError(
                            message="'var' não pode ser combinado com varargs '...' em parâmetro lambda",
                            line=et.line,
                            column=et.column,
                            expected="',' ou ')'",
                            found="...",
                        )
                    kinds_seen.add("var")
                    params.append(name_tok.lexeme)
                    typed_params.append(
                        LambdaParameter(
                            name=name_tok.lexeme,
                            is_var=True,
                            modifiers=mods,
                            annotations=annos,
                            line=var_tok.line,
                            column=var_tok.column,
                        )
                    )
                elif self._is_explicit_lambda_param_ahead():
                    type_ref = self.parse_type_reference(leading_annotations=post_annos)
                    if type_ref.name == "void":
                        raise SyntacticError(
                            message="Tipo 'void' não é permitido em parâmetro lambda",
                            line=type_ref.line,
                            column=type_ref.column,
                            expected="tipo válido",
                            found="void",
                        )
                    name_tok = self.expect(
                        TokenType.IDENTIFIER,
                        "Era esperado nome do parâmetro após o tipo na expressão lambda",
                        expected="nome de parâmetro",
                    )
                    extra_dims, _ = self._parse_trailing_dims_with_annotations()
                    if extra_dims:
                        type_ref.array_dimensions += extra_dims
                    if type_ref.is_varargs and self.check(TokenType.COMMA):
                        t = self.peek()
                        raise SyntacticError(
                            message="Parâmetro varargs '...' deve ser o último parâmetro da expressão lambda",
                            line=t.line,
                            column=t.column,
                            expected="')'",
                            found=",",
                        )
                    kinds_seen.add("explicit")
                    params.append(name_tok.lexeme)
                    typed_params.append(
                        LambdaParameter(
                            name=name_tok.lexeme,
                            type_ref=type_ref,
                            modifiers=mods,
                            annotations=annos,
                            is_varargs=type_ref.is_varargs,
                            line=type_ref.line,
                            column=type_ref.column,
                        )
                    )
                else:
                    if mods or annos:
                        t = self.peek()
                        raise SyntacticError(
                            message="Modificadores e anotações não são permitidos em parâmetro lambda com tipo inferido (use tipo explícito ou 'var')",
                            line=t.line,
                            column=t.column,
                            expected="nome de parâmetro sem 'final'/anotações",
                            found=t.lexeme if t.type != TokenType.EOF else "EOF",
                        )
                    first_tok = self.expect(
                        TokenType.IDENTIFIER,
                        "Era esperado nome de parâmetro na expressão lambda",
                        expected="nome de parâmetro",
                    )
                    if first_tok.lexeme == "var":
                        raise SyntacticError(
                            message="'var' exige nome de parâmetro em expressão lambda (ex: '(var x) -> ...')",
                            line=first_tok.line,
                            column=first_tok.column,
                            expected="identificador após 'var'",
                            found="var",
                        )
                    kinds_seen.add("inferred")
                    params.append(first_tok.lexeme)
                    typed_params.append(
                        LambdaParameter(
                            name=first_tok.lexeme,
                            line=first_tok.line,
                            column=first_tok.column,
                        )
                    )

                if self.check(TokenType.COMMA):
                    self.advance()
                    if self.check(TokenType.RPAREN):
                        t = self.peek()
                        raise SyntacticError(
                            message="Vírgula sobrando na lista de parâmetros da expressão lambda",
                            line=t.line,
                            column=t.column,
                            expected="próximo parâmetro",
                            found=")",
                        )
                else:
                    break

            if len(kinds_seen) > 1:
                raise SyntacticError(
                    message="Não é permitido misturar parâmetros com tipo explícito, 'var' e tipo inferido na mesma expressão lambda (JLS §15.27.1)",
                    line=start_tok.line,
                    column=start_tok.column,
                    expected="parâmetros uniformes (todos explícitos, todos 'var' ou todos inferidos)",
                    found=", ".join(sorted(kinds_seen)),
                )

            self.expect(TokenType.RPAREN, "Era esperado ')' para fechar os parâmetros da lambda", expected="')'")
            self.expect(TokenType.ARROW, "Era esperado '->' na expressão lambda", expected="'->'")
            if self.check(TokenType.LBRACE):
                body = self.parse_block()
                is_block = True
            else:
                body = self.expression()
                is_block = False

            param_mode = next(iter(kinds_seen), "empty")
            return LambdaExpression(
                parameters=params,
                typed_parameters=typed_params,
                parameter_mode=param_mode,
                body=body,
                is_block_body=is_block,
                line=start_tok.line,
                column=start_tok.column,
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
            right = self.expression()

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
            if self._is_lambda_ahead():
                else_expr = self.lambda_expression()
            else:
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
                node = self._parse_instanceof_rhs(node, op_tok)
            else:
                op_tok = self.advance()
                op = op_tok.lexeme
                self._check_missing_operand(op)
                right = self.shift()
                node = BinaryOp(op, node, right, line=op_tok.line, column=op_tok.column)
        return node

    def _parse_instanceof_rhs(self, expr: ASTNode, op_tok: Token) -> ASTNode:
        """
        Processa o operando direito de 'instanceof' (JLS §15.20.2):
        - ReferenceType (verificação tradicional de tipo)
        - TypePattern | RecordPattern (pattern matching -> PatternInstanceOfExpression)
        """
        t0 = self.peek()
        if t0.type == TokenType.IDENTIFIER and t0.lexeme == "_":
            raise SyntacticError(
                message="MatchAllPattern '_' não é permitido após 'instanceof'; use '<Tipo> _' para unnamed TypePattern ou 'Record(..., _)' (JLS §14.30.1)",
                line=t0.line,
                column=t0.column,
                expected="ReferenceType ou Pattern",
                found="_",
            )
        if t0.type == TokenType.IDENTIFIER and t0.lexeme == "var":
            raise SyntacticError(
                message="'var' não pode ser utilizado como tipo após 'instanceof' ou em TypePattern de nível superior (JLS §14.30.1)",
                line=t0.line,
                column=t0.column,
                expected="um ReferenceType explícito",
                found="var",
            )

        annos, _pre, post_annos, mods = self._parse_annotations_and_modifiers_detailed()
        disallowed_mods = [m for m in mods if m != "final"]
        if disallowed_mods:
            t = self.peek()
            raise SyntacticError(
                message=f"Modificador(es) {', '.join(disallowed_mods)!r} inválido(s) após 'instanceof' (apenas 'final' é permitido em TypePattern)",
                line=t.line,
                column=t.column,
                expected="'final' ou ReferenceType",
                found=disallowed_mods[0],
            )

        if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "var":
            vt = self.peek()
            raise SyntacticError(
                message="'var' não pode ser utilizado como tipo em TypePattern de nível superior (JLS §14.30.1)",
                line=vt.line,
                column=vt.column,
                expected="um ReferenceType explícito",
                found="var",
            )

        target_type = self.parse_type_reference(leading_annotations=post_annos)
        if target_type.name == "void":
            raise SyntacticError(
                message="Tipo 'void' não é permitido após 'instanceof'",
                line=target_type.line,
                column=target_type.column,
                expected="ReferenceType ou Pattern",
                found="void",
            )

        is_primitive = (
            target_type.name in ("int", "boolean", "char", "byte", "short", "long", "float", "double")
            and target_type.array_dimensions == 0
        )
        if is_primitive and not self.enable_preview_primitive_patterns:
            raise SyntacticError(
                message=f"Tipo primitivo '{target_type.name}' não é permitido em 'instanceof' no modo padrão da JLS Java SE 26 (Preview JEP 530)",
                line=target_type.line,
                column=target_type.column,
                expected="um ReferenceType",
                found=target_type.name,
            )

        if self.check(TokenType.LPAREN):
            if mods:
                raise SyntacticError(
                    message="Modificador 'final' não é permitido em RecordPattern (JLS §14.30.1)",
                    line=target_type.line,
                    column=target_type.column,
                    expected="identificador da variável após 'final <Tipo>'",
                    found="(",
                )
            rec_pat = self._parse_record_pattern_after_type(target_type, t0.line, t0.column)
            return PatternInstanceOfExpression(
                expression=expr,
                target_type=rec_pat.type_ref,
                pattern=rec_pat,
                line=op_tok.line,
                column=op_tok.column,
            )

        if self.check(TokenType.IDENTIFIER):
            type_pat = self._parse_type_pattern_after_type(
                type_ref=target_type,
                mods=mods,
                annotations=annos,
                in_record_component=False,
                is_var=False,
            )
            return PatternInstanceOfExpression(
                expression=expr,
                target_type=type_pat.type_ref,
                pattern=type_pat,
                line=op_tok.line,
                column=op_tok.column,
            )

        if mods:
            t = self.peek()
            raise SyntacticError(
                message="Era esperado o identificador da pattern variable após 'final <Tipo>' em 'instanceof'",
                line=t.line,
                column=t.column,
                expected="identificador de pattern variable",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )

        if self.check(TokenType.ASSIGN):
            at = self.peek()
            raise SyntacticError(
                message="Inicializador '=' não é permitido em expressão 'instanceof'",
                line=at.line,
                column=at.column,
                expected="operador ou delimitador de expressão",
                found="=",
            )

        return InstanceOfExpression(expr, target_type, op_tok.line, op_tok.column)

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
        node = next_fn()
        while self.peek().type in token_types:
            op_token = self.advance()
            op = op_token.lexeme
            self._check_missing_operand(op)
            right = next_fn()
            node = BinaryOp(op, node, right, line=op_token.line, column=op_token.column)
        return node

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

    def _skip_generic_angle_tokens(self, idx: int) -> int:
        """Avança o índice após '<...>' balanceado (>, >>, >>>) ou retorna -1 se inválido."""
        if idx >= len(self.tokens) or self.tokens[idx].type != TokenType.LESS:
            return idx
        idx += 1
        g_depth = 1
        while idx < len(self.tokens) and g_depth > 0:
            tt = self.tokens[idx].type
            if tt in (TokenType.EOF, TokenType.SEMICOLON, TokenType.LBRACE, TokenType.RBRACE):
                return -1
            if tt == TokenType.LESS:
                g_depth += 1
            elif tt == TokenType.GREATER:
                g_depth -= 1
            elif tt == TokenType.RSHIFT:
                g_depth -= 2
            elif tt == TokenType.URSHIFT:
                g_depth -= 3
            idx += 1
        return idx if g_depth <= 0 else -1

    def _skip_cast_ref_type_tokens(self, idx: int) -> int:
        """Avança sobre um ReferenceType (com qualificadores, generics, anotações e []) a partir de idx."""
        idx = self.current + self._skip_annotations_offset(idx - self.current)
        if idx >= len(self.tokens) or self.tokens[idx].type != TokenType.IDENTIFIER:
            return -1
        idx += 1
        while idx + 1 < len(self.tokens) and self.tokens[idx].type == TokenType.DOT:
            step = self.current + self._skip_annotations_offset((idx + 1) - self.current)
            if step < len(self.tokens) and self.tokens[step].type == TokenType.IDENTIFIER:
                idx = step + 1
                if idx < len(self.tokens) and self.tokens[idx].type == TokenType.LESS:
                    idx = self._skip_generic_angle_tokens(idx)
                    if idx < 0:
                        return -1
            else:
                break
        if idx < len(self.tokens) and self.tokens[idx].type == TokenType.LESS:
            idx = self._skip_generic_angle_tokens(idx)
            if idx < 0:
                return -1
        while idx + 1 < len(self.tokens) and self.tokens[idx].type == TokenType.DOT:
            step = self.current + self._skip_annotations_offset((idx + 1) - self.current)
            if step < len(self.tokens) and self.tokens[step].type == TokenType.IDENTIFIER:
                idx = step + 1
                if idx < len(self.tokens) and self.tokens[idx].type == TokenType.LESS:
                    idx = self._skip_generic_angle_tokens(idx)
                    if idx < 0:
                        return -1
            else:
                break
        while True:
            idx = self.current + self._skip_annotations_offset(idx - self.current)
            if idx + 1 < len(self.tokens) and self.tokens[idx].type == TokenType.LBRACKET and self.tokens[idx + 1].type == TokenType.RBRACKET:
                idx += 2
            else:
                break
        return idx

    def _is_cast_ahead(self) -> bool:
        """
        Determina se a abertura de parênteses à frente representa um cast: (Tipo) expressao
        ou cast de interseção: (Tipo & Bound1 & ...) expressao.
        """
        idx = self.current + self._skip_annotations_offset(1)
        if idx >= len(self.tokens):
            return False

        first = self.tokens[idx]

        # 1. Tipos primitivos: (int) x, (double[]) arr, (@A int @B []) arr
        if first.type in PRIMITIVE_TYPE_TOKENS and first.type != TokenType.KEYWORD_VOID:
            idx += 1
            while True:
                idx = self.current + self._skip_annotations_offset(idx - self.current)
                if idx + 1 < len(self.tokens) and self.tokens[idx].type == TokenType.LBRACKET and self.tokens[idx + 1].type == TokenType.RBRACKET:
                    idx += 2
                else:
                    break
            return idx < len(self.tokens) and self.tokens[idx].type == TokenType.RPAREN

        # 2. Tipos de referência (incluindo generics aninhados e bounds '&')
        if first.type == TokenType.IDENTIFIER:
            idx = self._skip_cast_ref_type_tokens(idx)
            if idx < 0:
                return False
            while idx < len(self.tokens) and self.tokens[idx].type == TokenType.BITWISE_AND:
                idx = self._skip_cast_ref_type_tokens(idx + 1)
                if idx < 0:
                    return False

            if idx < len(self.tokens) and self.tokens[idx].type == TokenType.RPAREN:
                if idx + 1 < len(self.tokens):
                    after = self.tokens[idx + 1]
                    valid_cast_starters = {
                        TokenType.IDENTIFIER, TokenType.INT, TokenType.NUMBER, TokenType.LONG, TokenType.DOUBLE, TokenType.FLOAT,
                        TokenType.STRING_LITERAL, TokenType.CHAR_LITERAL, TokenType.BOOLEAN_LITERAL, TokenType.NULL_LITERAL,
                        TokenType.KEYWORD_THIS, TokenType.KEYWORD_SUPER, TokenType.KEYWORD_NEW, TokenType.KEYWORD_SWITCH,
                        TokenType.LPAREN, TokenType.LOGICAL_NOT, TokenType.BITWISE_NOT,
                    }
                    return after.type in valid_cast_starters
        return False

    def parse_cast_expression(self) -> CastExpression:
        """Processa conversão de tipo: (Tipo) expressao ou (Tipo & Bound1 & ...) expressao (JLS §15.16)."""
        start_tok = self.advance()  # consome '('
        target_type = self.parse_type_reference()
        if target_type.name in ("void", "var"):
            raise SyntacticError(
                message=f"Tipo '{target_type.name}' não é permitido em expressão de cast (JLS §15.16)",
                line=target_type.line,
                column=target_type.column,
                expected="tipo primitivo ou tipo de referência válido",
                found=target_type.name,
            )
        primitive_types = {"boolean", "byte", "short", "char", "int", "long", "float", "double"}
        additional_bounds: List[TypeReference] = []
        while self.check(TokenType.BITWISE_AND):
            if target_type.name in primitive_types or target_type.array_dimensions > 0:
                t = self.peek()
                raise SyntacticError(
                    message="Bounds adicionais '&' em cast só são permitidos após ReferenceType não-array (JLS §15.16)",
                    line=t.line,
                    column=t.column,
                    expected="')'",
                    found="&",
                )
            self.advance()  # '&'
            bound_ref = self.parse_type_reference()
            if bound_ref.name in primitive_types or bound_ref.name == "void" or bound_ref.array_dimensions > 0:
                raise SyntacticError(
                    message=f"Bound adicional '{bound_ref.pretty()}' em cast de interseção deve ser interface/ReferenceType (JLS §15.16)",
                    line=bound_ref.line,
                    column=bound_ref.column,
                    expected="interface de referência",
                    found=bound_ref.pretty(),
                )
            additional_bounds.append(bound_ref)
        self.expect(TokenType.RPAREN, "Era esperado ')' para fechar o tipo no cast", expected="')'")
        self._check_missing_operand(f"({target_type.name})")
        if self._is_lambda_ahead():
            expr = self.lambda_expression()
        else:
            expr = self.unary()
        return CastExpression(
            target_type=target_type,
            expression=expr,
            line=start_tok.line,
            column=start_tok.column,
            additional_bounds=additional_bounds,
        )

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
            # 1. Ponto '.' para membro, chamada, chamada genérica explícita ou 'outer.new Inner()'
            if self.check(TokenType.DOT):
                self.advance()  # consome '.'
                if self.check(TokenType.KEYWORD_NEW):
                    new_expr = self.parse_new_expression()
                    new_expr.target = node
                    node = new_expr
                    continue
                if self.check(TokenType.LESS):
                    call_type_args = self.parse_type_arguments()
                    member_tok = self.expect(
                        TokenType.IDENTIFIER,
                        "Era esperado um identificador de método após os argumentos genéricos",
                        expected="nome do método",
                    )
                    self.expect(TokenType.LPAREN, "Era esperado '(' após invocação de método genérico", expected="'('")
                    args = self.parse_arguments()
                    self.expect(TokenType.RPAREN, "Era esperado ')' para fechar argumentos", expected="')'")
                    node = MethodCall(
                        method_name=member_tok.lexeme,
                        target=node,
                        arguments=args,
                        type_arguments=call_type_args,
                        line=member_tok.line,
                        column=member_tok.column,
                    )
                    continue
                if self.check(TokenType.KEYWORD_CLASS) or self.check(TokenType.KEYWORD_THIS) or self.check(TokenType.KEYWORD_SUPER):
                    member_tok = self.advance()
                else:
                    member_tok = self.expect(TokenType.IDENTIFIER, "Era esperado um identificador após '.'", expected="identificador após '.'")

                if self.check(TokenType.LPAREN):
                    self.advance()  # consome '('
                    args = self.parse_arguments()
                    self.expect(TokenType.RPAREN, "Era esperado ')' para fechar argumentos", expected="')'")
                    node = MethodCall(method_name=member_tok.lexeme, target=node, arguments=args, line=member_tok.line, column=member_tok.column)
                else:
                    node = MemberAccess(target=node, member_name=member_tok.lexeme, line=member_tok.line, column=member_tok.column)

            # 2. Chamada direta de método após identificador: id(args)
            elif self.check(TokenType.LPAREN) and isinstance(node, Identifier):
                self.advance()  # consome '('
                args = self.parse_arguments()
                self.expect(TokenType.RPAREN, "Era esperado ')' para fechar argumentos", expected="')'")
                node = MethodCall(method_name=node.name, target=None, arguments=args, line=node.line, column=node.column)

            # 3. Indexação de array: expr[indice]
            elif self.check(TokenType.LBRACKET):
                bracket_tok = self.advance()  # consome '['
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

            # 4. Referência de método: alvo::[<TypeArgs>]metodo ou Tipo::new
            elif self.check(TokenType.DOUBLE_COLON):
                col_tok = self.advance()  # consome '::'
                ref_type_args: List[TypeReference] = []
                if self.check(TokenType.LESS):
                    ref_type_args = self.parse_type_arguments()
                if self.check(TokenType.KEYWORD_NEW) and not ref_type_args:
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
                node = MethodReference(
                    target=node,
                    method_name=method_name,
                    type_arguments=ref_type_args,
                    line=col_tok.line,
                    column=col_tok.column,
                )

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

    def _is_array_creation_ref_ahead(self) -> bool:
        """Verifica lookahead para referência a construtor de array: int[]::new ou String[]::new."""
        t0 = self.peek_offset(0)
        if t0.type in PRIMITIVE_TYPE_TOKENS and t0.type != TokenType.KEYWORD_VOID:
            idx = self.current + 1
        elif t0.type == TokenType.IDENTIFIER:
            idx = self.current + 1
            while idx + 1 < len(self.tokens) and self.tokens[idx].type == TokenType.DOT and self.tokens[idx + 1].type == TokenType.IDENTIFIER:
                idx += 2
            if idx < len(self.tokens) and self.tokens[idx].type == TokenType.LESS:
                idx = self._skip_generic_angle_tokens(idx)
                if idx < 0:
                    return False
        else:
            return False

        dims = 0
        while True:
            step = self.current + self._skip_annotations_offset(idx - self.current)
            if step + 1 < len(self.tokens) and self.tokens[step].type == TokenType.LBRACKET and self.tokens[step + 1].type == TokenType.RBRACKET:
                idx = step + 2
                dims += 1
            else:
                idx = step
                break
        if dims == 0 or idx + 1 >= len(self.tokens):
            return False
        return self.tokens[idx].type == TokenType.DOUBLE_COLON and self.tokens[idx + 1].type == TokenType.KEYWORD_NEW

    def _is_generic_type_method_ref_ahead(self) -> bool:
        """Verifica lookahead para Tipo<Args>::new ou Tipo<Args>::metodo."""
        if self.peek().type != TokenType.IDENTIFIER:
            return False
        idx = self.current + 1
        while idx + 1 < len(self.tokens) and self.tokens[idx].type == TokenType.DOT and self.tokens[idx + 1].type == TokenType.IDENTIFIER:
            idx += 2
        if idx >= len(self.tokens) or self.tokens[idx].type != TokenType.LESS:
            return False
        idx = self._skip_generic_angle_tokens(idx)
        if idx < 0 or idx >= len(self.tokens):
            return False
        return self.tokens[idx].type == TokenType.DOUBLE_COLON

    def _parse_type_method_reference(self) -> MethodReference:
        """Processa referências iniciadas por tipo genérico ou array: int[]::new, ArrayList<String>::new."""
        tref = self.parse_type_reference()
        col_tok = self.expect(TokenType.DOUBLE_COLON, "Era esperado '::' após o tipo na referência de método", expected="'::'")
        ref_type_args: List[TypeReference] = []
        if self.check(TokenType.LESS):
            ref_type_args = self.parse_type_arguments()
        if self.check(TokenType.KEYWORD_NEW) and not ref_type_args:
            m_tok = self.advance()
            method_name = m_tok.lexeme
        elif self.check(TokenType.IDENTIFIER) and tref.array_dimensions == 0:
            m_tok = self.advance()
            method_name = m_tok.lexeme
        else:
            t = self.peek()
            raise SyntacticError(
                message="Era esperado 'new' (ou nome de método para tipo não-array) após '::'",
                line=t.line,
                column=t.column,
                expected="'new' ou identificador de método",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )
        return MethodReference(
            target=tref,
            method_name=method_name,
            type_arguments=ref_type_args,
            is_array_creation=(tref.array_dimensions > 0 and method_name == "new"),
            array_type=tref if tref.array_dimensions > 0 else None,
            line=col_tok.line,
            column=col_tok.column,
        )

    def primary(self) -> ASTNode:
        """Processa operandos primários, literais, class literals, referências de array/genéricos, instanciações e parênteses."""
        # 0. Literal de classe (JLS §15.8.2): Tipo.class, int.class, void.class, Tipo[].class
        if self._is_class_literal_ahead():
            return self._parse_class_literal()

        # 0.1 Referência a construtor de array ou método com tipo parametrizado: int[]::new, List<String>::size
        if self._is_array_creation_ref_ahead() or self._is_generic_type_method_ref_ahead():
            return self._parse_type_method_reference()

        # 1. Instanciação com 'new': objetos ou arrays
        if self.check(TokenType.KEYWORD_NEW):
            return self.parse_new_expression()

        # 1.1 Expressão switch auxiliar para suporte contextual ao YieldStatement na S6
        if self.check(TokenType.KEYWORD_SWITCH):
            return self._parse_switch_expression()

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

        if self.check(TokenType.LONG):
            tok = self.advance()
            return Literal(tok.lexeme, "LONG", line=tok.line, column=tok.column)

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

        if self.check(TokenType.NULL_LITERAL):
            tok = self.advance()
            return Literal(tok.lexeme, "NULL", line=tok.line, column=tok.column)

        # 5. Expressões entre parênteses com controle de profundidade
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
                if isinstance(expr, ASTNode):
                    expr.parenthesized = True
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

    def parse_new_expression(self) -> ASTNode:
        """Processa instanciação de objeto 'new [@Ann] Tipo(args)' ou criação de array 'new [@Ann] Tipo @A [dim]'."""
        new_tok = self.advance()  # consome 'new'
        leading_annos = self._parse_optional_annotations()
        tok = self.peek()
        segment_annotations: List[List[ASTNode]] = []
        if tok.type in PRIMITIVE_TYPE_TOKENS:
            self.advance()
            type_name = tok.lexeme
        elif tok.type == TokenType.IDENTIFIER:
            first_tok = self.advance()
            parts = [first_tok.lexeme]
            seg_annos_list: List[List[ASTNode]] = [list(leading_annos)]
            while self.check(TokenType.DOT):
                self.advance()
                seg_annos = self._parse_optional_annotations()
                part_tok = self.expect(
                    TokenType.IDENTIFIER,
                    "Era esperado um identificador de tipo após '.'",
                    expected="identificador de tipo",
                )
                parts.append(part_tok.lexeme)
                seg_annos_list.append(seg_annos)
            type_name = ".".join(parts)
            if len(parts) > 1:
                segment_annotations = seg_annos_list
        else:
            raise SyntacticError(
                message=f"Tipo inválido após 'new': '{tok.lexeme}'",
                line=tok.line,
                column=tok.column,
                expected="um tipo primitivo ou identificador de classe",
                found=tok.lexeme if tok.type != TokenType.EOF else "EOF",
            )

        type_args = []
        is_diamond = False
        if self.check(TokenType.LESS):
            if tok.type in PRIMITIVE_TYPE_TOKENS:
                t = self.peek()
                raise SyntacticError(
                    message=f"Tipo primitivo '{tok.lexeme}' não pode receber argumentos de tipo genérico ou operador diamond '<>'",
                    line=t.line,
                    column=t.column,
                    expected="'['",
                    found="<",
                )
            if self.peek_offset(1).type == TokenType.GREATER:
                self.advance()  # '<'
                self.advance()  # '>'
                is_diamond = True
            else:
                type_args = self.parse_type_arguments()

        base_type = TypeReference(
            type_name,
            array_dimensions=0,
            type_arguments=type_args,
            line=tok.line,
            column=tok.column,
            annotations=leading_annos,
            segment_annotations=segment_annotations,
        )

        # Caso A: Criação de array: new [@Ann] Tipo @A [10] @B [] { ... }
        has_array_dim = self.check(TokenType.LBRACKET) or (
            self.check(TokenType.AT)
            and self.peek_offset(self._skip_annotations_offset(0)).type == TokenType.LBRACKET
        )
        if has_array_dim:
            if is_diamond:
                raise SyntacticError(
                    message="Operador diamond '<>' não é permitido na criação de arrays",
                    line=new_tok.line,
                    column=new_tok.column,
                    expected="'('",
                    found="[",
                )
            dimensions = []
            dims_annotations: List[List[ASTNode]] = []
            while self.check(TokenType.LBRACKET) or (
                self.check(TokenType.AT)
                and self.peek_offset(self._skip_annotations_offset(0)).type == TokenType.LBRACKET
            ):
                dim_annos = self._parse_optional_annotations()
                dims_annotations.append(dim_annos)
                self.advance()  # consome '['
                if self.check(TokenType.RBRACKET):
                    self.advance()  # consome ']'
                    dimensions.append(None)
                else:
                    dim_expr = self.expression()
                    self.expect(TokenType.RBRACKET, "Era esperado ']' para fechar dimensão do array", expected="']'")
                    dimensions.append(dim_expr)
            initializer = None
            if self.check(TokenType.LBRACE):
                initializer = self.parse_array_initializer()
            seen_empty_dim = False
            for dim in dimensions:
                if dim is None:
                    seen_empty_dim = True
                elif seen_empty_dim:
                    raise SyntacticError(
                        message="Dimensão de array especificada após dimensão vazia '[]' inválida (JLS §15.10.1)",
                        line=getattr(dim, "line", new_tok.line),
                        column=getattr(dim, "column", new_tok.column),
                        expected="']'",
                        found=dim.__class__.__name__,
                    )
            if initializer is not None and any(dim is not None for dim in dimensions):
                raise SyntacticError(
                    message="Não é permitido especificar tamanho de dimensão e inicializador '{...}' na mesma criação de array (JLS §15.10.1)",
                    line=initializer.line,
                    column=initializer.column,
                    expected="apenas dimensões vazias '[]' antes do inicializador '{...}'",
                    found="{",
                )
            if initializer is None and all(dim is None for dim in dimensions):
                raise SyntacticError(
                    message="Criação de array exige ao menos uma expressão de dimensão ou um inicializador '{...}' (JLS §15.10.1)",
                    line=new_tok.line,
                    column=new_tok.column,
                    expected="dimensão numérica ou inicializador '{...}'",
                    found="[]",
                )
            base_type.array_dimensions = len(dimensions)
            base_type.dims_annotations = dims_annotations
            return ArrayCreationExpression(base_type, dimensions, initializer, new_tok.line, new_tok.column)

        # Caso B: Instanciação de classe: new [@Ann] Classe(args) [{ corpo anonimo }]
        if tok.type in PRIMITIVE_TYPE_TOKENS:
            raise SyntacticError(
                message=f"Tipo primitivo '{tok.lexeme}' não pode ser instanciado com 'new {tok.lexeme}()'",
                line=tok.line,
                column=tok.column,
                expected="dimensões de array '[...]'",
                found="(",
            )
        self.expect(TokenType.LPAREN, "Era esperado '(' após tipo na instanciação com 'new'", expected="'('")
        args = self.parse_arguments()
        self.expect(TokenType.RPAREN, "Era esperado ')' após argumentos da instanciação", expected="')'")
        anonymous_body = None
        if self.check(TokenType.LBRACE):
            self.advance()  # consome '{'
            anonymous_body = []
            while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
                member = self.class_member("<anonymous>")
                if isinstance(member, ConstructorDeclaration):
                    raise SyntacticError(
                        message="Classe anônima não pode declarar construtores explícitos (JLS §15.9.5)",
                        line=member.line,
                        column=member.column,
                        expected="campo, método ou inicializador",
                        found=member.name,
                    )
                anonymous_body.append(member)
            self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o corpo da classe anônima", expected="'}'")
        return ObjectCreationExpression(
            base_type,
            args,
            line=new_tok.line,
            column=new_tok.column,
            is_diamond=is_diamond,
            anonymous_body=anonymous_body,
        )

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
        """Determina se os próximos tokens representam uma declaração local de variável (incluindo 'var')."""
        offset = 0
        while True:
            new_off = self._skip_annotations_offset(offset)
            if self.peek_offset(new_off).type == TokenType.KEYWORD_FINAL:
                offset = new_off + 1
            else:
                offset = new_off
                break

        t = self.peek_offset(offset)
        if t.type in PRIMITIVE_TYPE_TOKENS and t.type != TokenType.KEYWORD_VOID:
            return True

        if t.type == TokenType.IDENTIFIER:
            if offset == 0 and t.lexeme == "yield" and self._is_yield_statement_ahead():
                return False
            if t.lexeme == "var":
                return self.peek_offset(offset + 1).type == TokenType.IDENTIFIER
            idx = offset + 1
            # Suporta nomes qualificados e anotados: pkg.Outer.@Ann Inner
            while self.peek_offset(idx).type == TokenType.DOT:
                step = idx + 1
                if self.peek_offset(step).type == TokenType.AT and not self._is_annotation_interface_declaration_ahead(step):
                    step = self._skip_annotations_offset(step)
                if self.peek_offset(step).type == TokenType.IDENTIFIER:
                    idx = step + 1
                else:
                    break
            idx = self._skip_annotations_offset(idx)
            next_t = self.peek_offset(idx)
            # Evita confundir comparação 'a < b;' com generic 'List<String> x'
            if next_t.type == TokenType.LESS:
                depth = 1
                scan = idx + 1
                while depth > 0:
                    st = self.peek_offset(scan)
                    if st.type in (TokenType.EOF, TokenType.SEMICOLON):
                        return False
                    if st.type == TokenType.LESS:
                        depth += 1
                    elif st.type == TokenType.GREATER:
                        depth -= 1
                    elif st.type == TokenType.RSHIFT:
                        depth -= 2
                    elif st.type == TokenType.URSHIFT:
                        depth -= 3
                    scan += 1
                idx = scan
                while self.peek_offset(idx).type == TokenType.DOT:
                    step = idx + 1
                    if self.peek_offset(step).type == TokenType.AT and not self._is_annotation_interface_declaration_ahead(step):
                        step = self._skip_annotations_offset(step)
                    if self.peek_offset(step).type == TokenType.IDENTIFIER:
                        idx = step + 1
                        if self.peek_offset(idx).type == TokenType.LESS:
                            d2 = 1
                            s2 = idx + 1
                            while d2 > 0:
                                st2 = self.peek_offset(s2)
                                if st2.type in (TokenType.EOF, TokenType.SEMICOLON):
                                    return False
                                if st2.type == TokenType.LESS:
                                    d2 += 1
                                elif st2.type == TokenType.GREATER:
                                    d2 -= 1
                                elif st2.type == TokenType.RSHIFT:
                                    d2 -= 2
                                elif st2.type == TokenType.URSHIFT:
                                    d2 -= 3
                                s2 += 1
                            idx = s2
                    else:
                        break
                idx = self._skip_annotations_offset(idx)
                next_t = self.peek_offset(idx)
            # Ex: String nome
            if next_t.type == TokenType.IDENTIFIER:
                return True
            # Ex: String[] nomes ou String @A [] nomes
            if next_t.type == TokenType.LBRACKET and self.peek_offset(idx + 1).type == TokenType.RBRACKET:
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

    # -------------------------------------------------------------------------
    # 2.12 PROCESSAMENTO DE MÓDULOS E UNIDADES COMPACTAS (ETAPA S2)
    # -------------------------------------------------------------------------
    def _is_package_declaration_ahead(self) -> bool:
        """Verifica se há uma declaração de pacote, mesmo precedida por annotations."""
        offset = self._skip_annotations_offset(0)
        return self.peek_offset(offset).type == TokenType.KEYWORD_PACKAGE

    def _is_module_declaration_ahead(self) -> bool:
        """Verifica se os próximos tokens (após eventuais annotations) iniciam uma declaração de módulo."""
        offset = self._skip_annotations_offset(0)

        t = self.peek_offset(offset)
        if t.type == TokenType.IDENTIFIER and t.lexeme == "open":
            offset += 1
            t = self.peek_offset(offset)

        if t.type == TokenType.IDENTIFIER and t.lexeme == "module":
            next_t = self.peek_offset(offset + 1)
            if next_t.type == TokenType.IDENTIFIER:
                return True
        return False

    def _is_compact_compilation_unit(self) -> bool:
        """
        Determina se a unidade de compilação é compacta (JLS §7.3):
        sem package e sem classe explícita que englobe o arquivo,
        mas com declarações de métodos no nível superior (sem modificadores de acesso proibidos).
        """
        offset = 0
        has_method = False
        has_explicit_top_class = False
        brace_depth = 0

        while self.peek_offset(offset).type != TokenType.EOF:
            t = self.peek_offset(offset)

            if t.type == TokenType.LBRACE:
                brace_depth += 1
                offset += 1
                continue
            elif t.type == TokenType.RBRACE:
                brace_depth = max(0, brace_depth - 1)
                offset += 1
                continue

            # Se estiver dentro de algum bloco ou classe interna, não analisa assinaturas de nível superior
            if brace_depth > 0:
                offset += 1
                continue

            # Pula annotations no nível raiz
            offset = self._skip_annotations_offset(offset)

            mods = []
            while True:
                if self.peek_offset(offset).type in MODIFIER_TOKENS:
                    mods.append(self.peek_offset(offset).lexeme)
                    offset += 1
                elif self._is_non_sealed_ahead(offset):
                    mods.append("non-sealed")
                    offset += 3
                elif self._is_sealed_modifier_ahead(offset):
                    mods.append("sealed")
                    offset += 1
                else:
                    break

            t = self.peek_offset(offset)
            is_record = self._is_record_declaration_ahead(offset, allow_missing_name=True)
            is_ann_iface = self._is_annotation_interface_declaration_ahead(offset)

            # Se encontrar tipo explícito no nível raiz com public/protected/private, não é compact unit
            if t.type in (TokenType.KEYWORD_CLASS, TokenType.KEYWORD_INTERFACE, TokenType.KEYWORD_ENUM) or is_record or is_ann_iface:
                if any(m in ("public", "protected", "private") for m in mods):
                    has_explicit_top_class = True
                    break
                offset += 2 if is_ann_iface else 1
                continue

            # Se encontrar método no nível superior (sem modificadores de acesso proibidos)
            if t.type in PRIMITIVE_TYPE_TOKENS or t.type == TokenType.IDENTIFIER:
                off_look = offset + 1
                while self.peek_offset(off_look).type == TokenType.LBRACKET and self.peek_offset(off_look + 1).type == TokenType.RBRACKET:
                    off_look += 2
                if self.peek_offset(off_look).type == TokenType.IDENTIFIER and self.peek_offset(off_look + 1).type == TokenType.LPAREN:
                    if not any(m in ("public", "protected", "private", "abstract") for m in mods):
                        has_method = True
                        break

            offset += 1

        if has_explicit_top_class:
            return False

        return has_method

    def parse_module_declaration(self, leading_annotations: List[ASTNode] = None) -> ModuleDeclaration:
        """
        Processa declaração de módulo (JLS §7.7):
        {Annotation} [open] module Identifier {. Identifier} { {ModuleDirective} }
        """
        if leading_annotations is None:
            leading_annotations = self._parse_optional_annotations()

        is_open = False
        tok = self.peek()
        if tok.type == TokenType.IDENTIFIER and tok.lexeme == "open":
            is_open = True
            self.advance()

        mod_tok = self.peek()
        if not (mod_tok.type == TokenType.IDENTIFIER and mod_tok.lexeme == "module"):
            raise SyntacticError(
                message="Era esperado 'module' para iniciar a declaração de módulo",
                line=mod_tok.line,
                column=mod_tok.column,
                expected="'module'",
                found=mod_tok.lexeme if mod_tok.type != TokenType.EOF else "EOF",
            )
        self.advance() # consome 'module'

        if not self.check(TokenType.IDENTIFIER):
            t = self.peek()
            raise SyntacticError(
                message="Era esperado o nome do módulo após 'module'",
                line=t.line,
                column=t.column,
                expected="o nome do módulo",
                found=t.lexeme if t.type != TokenType.EOF else "EOF",
            )

        module_name = self.qualified_identifier()

        self.expect(TokenType.LBRACE, "Era esperado '{' para abrir o corpo do módulo", expected="'{'")

        directives: List[ModuleDirective] = []
        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            directives.append(self.parse_module_directive())

        self.expect(TokenType.RBRACE, "Era esperado '}' para fechar o corpo do módulo", expected="'}'")

        return ModuleDeclaration(
            name=module_name,
            is_open=is_open,
            directives=directives,
            annotations=leading_annotations,
            line=mod_tok.line,
            column=mod_tok.column,
        )

    def parse_module_directive(self) -> ModuleDirective:
        """
        Processa uma diretiva de módulo (JLS §7.7):
        - requires {RequiresModifier} ModuleName ;
        - exports PackageName [to ModuleName {, ModuleName}] ;
        - opens PackageName [to ModuleName {, ModuleName}] ;
        - uses TypeName ;
        - provides TypeName with TypeName {, TypeName} ;
        """
        tok = self.peek()

        if tok.type == TokenType.IDENTIFIER and tok.lexeme == "requires":
            req_tok = self.advance() # consome 'requires'
            is_transitive = False
            is_static = False
            while True:
                if self.check(TokenType.KEYWORD_STATIC):
                    self.advance()
                    is_static = True
                elif self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "transitive":
                    self.advance()
                    is_transitive = True
                else:
                    break

            if not self.check(TokenType.IDENTIFIER):
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado o nome do módulo após 'requires'",
                    line=t.line,
                    column=t.column,
                    expected="nome do módulo após 'requires'",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            mod_name = self.qualified_identifier()
            self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da diretiva 'requires'", expected="';'")
            return RequiresDirective(
                module_name=mod_name,
                is_transitive=is_transitive,
                is_static=is_static,
                line=req_tok.line,
                column=req_tok.column,
            )

        elif tok.type == TokenType.IDENTIFIER and tok.lexeme == "exports":
            exp_tok = self.advance() # consome 'exports'
            if not self.check(TokenType.IDENTIFIER):
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado o nome do pacote após 'exports'",
                    line=t.line,
                    column=t.column,
                    expected="nome do pacote após 'exports'",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            pkg_name = self.qualified_identifier()
            to_modules = []
            if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "to":
                self.advance() # consome 'to'
                if not self.check(TokenType.IDENTIFIER):
                    t = self.peek()
                    raise SyntacticError(
                        message="Era esperado o nome do módulo de destino após 'to'",
                        line=t.line,
                        column=t.column,
                        expected="nome do módulo de destino",
                        found=t.lexeme if t.type != TokenType.EOF else "EOF",
                    )
                to_modules.append(self.qualified_identifier())
                while self.check(TokenType.COMMA):
                    self.advance()
                    to_modules.append(self.qualified_identifier())
            self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da diretiva 'exports'", expected="';'")
            return ExportsDirective(
                package_name=pkg_name,
                to_modules=to_modules,
                line=exp_tok.line,
                column=exp_tok.column,
            )

        elif tok.type == TokenType.IDENTIFIER and tok.lexeme == "opens":
            opn_tok = self.advance() # consome 'opens'
            if not self.check(TokenType.IDENTIFIER):
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado o nome do pacote após 'opens'",
                    line=t.line,
                    column=t.column,
                    expected="nome do pacote após 'opens'",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            pkg_name = self.qualified_identifier()
            to_modules = []
            if self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "to":
                self.advance() # consome 'to'
                if not self.check(TokenType.IDENTIFIER):
                    t = self.peek()
                    raise SyntacticError(
                        message="Era esperado o nome do módulo de destino após 'to'",
                        line=t.line,
                        column=t.column,
                        expected="nome do módulo de destino",
                        found=t.lexeme if t.type != TokenType.EOF else "EOF",
                    )
                to_modules.append(self.qualified_identifier())
                while self.check(TokenType.COMMA):
                    self.advance()
                    to_modules.append(self.qualified_identifier())
            self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da diretiva 'opens'", expected="';'")
            return OpensDirective(
                package_name=pkg_name,
                to_modules=to_modules,
                line=opn_tok.line,
                column=opn_tok.column,
            )

        elif tok.type == TokenType.IDENTIFIER and tok.lexeme == "uses":
            uses_tok = self.advance() # consome 'uses'
            if not self.check(TokenType.IDENTIFIER):
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado o nome do tipo de serviço após 'uses'",
                    line=t.line,
                    column=t.column,
                    expected="nome do tipo de serviço após 'uses'",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            service_type = self.parse_type_reference()
            self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da diretiva 'uses'", expected="';'")
            return UsesDirective(
                service_type=service_type,
                line=uses_tok.line,
                column=uses_tok.column,
            )

        elif tok.type == TokenType.IDENTIFIER and tok.lexeme == "provides":
            prov_tok = self.advance() # consome 'provides'
            if not self.check(TokenType.IDENTIFIER):
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado o nome do tipo de serviço após 'provides'",
                    line=t.line,
                    column=t.column,
                    expected="o nome do tipo de serviço",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            service_type = self.parse_type_reference()
            if not (self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "with"):
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado 'with' na diretiva 'provides'",
                    line=t.line,
                    column=t.column,
                    expected="'with'",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            self.advance() # consome 'with'
            if not self.check(TokenType.IDENTIFIER):
                t = self.peek()
                raise SyntacticError(
                    message="Era esperado o nome da classe implementadora após 'with'",
                    line=t.line,
                    column=t.column,
                    expected="nome da classe implementadora",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )
            with_types = [self.parse_type_reference()]
            while self.check(TokenType.COMMA):
                self.advance()
                with_types.append(self.parse_type_reference())
            self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da diretiva 'provides'", expected="';'")
            return ProvidesDirective(
                service_type=service_type,
                with_types=with_types,
                line=prov_tok.line,
                column=prov_tok.column,
            )

        else:
            raise SyntacticError(
                message=f"Diretiva de módulo desconhecida ou inválida: '{tok.lexeme}'",
                line=tok.line,
                column=tok.column,
                expected="uma diretiva ('requires', 'exports', 'opens', 'uses', 'provides')",
                found=tok.lexeme if tok.type != TokenType.EOF else "EOF",
            )

    def parse_compact_compilation_unit(self, imports: List[ImportDeclaration]) -> CompactCompilationUnit:
        """
        Processa uma unidade de compilação compacta (JLS §7.3):
        {ImportDeclaration} {ClassMemberDeclarationNoMethod} MethodDeclaration {ClassMemberDeclaration}
        Declara implicitamente uma classe (top-level) contendo os membros.
        Membros não podem possuir modificadores de acesso ('public', 'protected', 'private', 'abstract').
        Deve possuir obrigatoriamente pelo menos uma declaração de método.
        Antes do primeiro método, somente são permitidos ClassMemberDeclarationNoMethod (campos, classes, interfaces, ;).
        """
        start_line = self.peek().line
        start_col = self.peek().column
        members: List[ASTNode] = []
        found_first_method = False

        while not self.check(TokenType.EOF):
            old_current = self.current

            # Ponto e vírgula avulso ';'
            if self.check(TokenType.SEMICOLON):
                self.advance()
                members.append(EmptyStatement(line=self.peek().line, column=self.peek().column))
                continue

            annos, _pre_annos, post_annos, mods = self._parse_annotations_and_modifiers_detailed()

            for m in mods:
                if m in ("public", "protected", "private", "abstract"):
                    t = self.peek()
                    raise SyntacticError(
                        message=f"Modificadores de acesso ou abstratos ('{m}') não são permitidos em membros de unidades compactas no nível superior",
                        line=t.line,
                        column=t.column,
                        expected="membro sem modificadores de acesso ('static', 'final', ou sem modificadores)",
                        found=m,
                    )

            # Verificação de inicializadores de instância ou estáticos
            if (not mods and not annos and self.check(TokenType.LBRACE)) or (mods == ["static"] and not annos and self.check(TokenType.LBRACE)):
                if not found_first_method:
                    t = self.peek()
                    raise SyntacticError(
                        message="Inicializadores de classe não são permitidos antes da primeira declaração de método em uma unidade de compilação compacta (JLS §7.3)",
                        line=t.line,
                        column=t.column,
                        expected="declaração de campo, classe, interface ou método",
                        found=t.lexeme
                    )
                block = self.parse_block()
                if mods == ["static"]:
                    members.append(StaticInitializer(block=block, line=block.line, column=block.column))
                else:
                    members.append(InstanceInitializer(block=block, line=block.line, column=block.column))
                continue

            if self._is_annotation_interface_declaration_ahead():
                members.append(self.annotation_interface_declaration(mods, annotations=annos))
            elif self.check(TokenType.KEYWORD_CLASS):
                cls = self.class_declaration(mods)
                cls.annotations = annos
                members.append(cls)
            elif self.check(TokenType.KEYWORD_INTERFACE):
                members.append(self.interface_declaration(mods, annotations=annos))
            elif self.check(TokenType.KEYWORD_ENUM):
                members.append(self.enum_declaration(mods, annotations=annos))
            elif self._is_record_declaration_ahead(allow_missing_name=True):
                members.append(self.record_declaration(mods, annotations=annos))
            else:
                type_params = []
                if self.check(TokenType.LESS):
                    type_params = self.parse_type_parameters()

                leading_type_annos = [] if type_params else post_annos
                type_ref = self.parse_type_reference(leading_annotations=leading_type_annos)
                name_tok = self.expect(TokenType.IDENTIFIER, "Era esperado o nome do membro (método ou campo)")

                if self.check(TokenType.LPAREN):
                    found_first_method = True
                    recv_param, params = self.parse_formal_parameters()
                    dims, dims_annos = self._parse_trailing_dims_with_annotations()
                    throws_types = self.parse_throws_clause()
                    if self.check(TokenType.SEMICOLON):
                        t = self.peek()
                        raise SyntacticError(
                            message="Métodos sem corpo não são permitidos em unidades de compilação compactas",
                            line=t.line,
                            column=t.column,
                            expected="corpo do método '{ ... }'",
                            found=";",
                        )
                    body = self.parse_block()
                    members.append(
                        MethodDeclaration(
                            name=name_tok.lexeme,
                            return_type=type_ref,
                            parameters=params,
                            modifiers=mods,
                            throws_types=throws_types,
                            body=body,
                            line=name_tok.line,
                            column=name_tok.column,
                            type_parameters=type_params,
                            annotations=annos,
                            dims_annotations=dims_annos,
                            receiver_parameter=recv_param,
                            dims=dims
                        )
                    )
                else:
                    declarators: List[VariableDeclarator] = []
                    dims = 0
                    while self.check(TokenType.LBRACKET) and self.peek_offset(1).type == TokenType.RBRACKET:
                        self.advance()
                        self.advance()
                        dims += 1
                    first_id = VariableDeclaratorId(name=name_tok.lexeme, dims=dims, line=name_tok.line, column=name_tok.column)
                    first_init = None
                    if self.check(TokenType.ASSIGN):
                        self.advance()
                        first_init = self.variable_initializer()
                    declarators.append(VariableDeclarator(id=first_id, initializer=first_init, line=name_tok.line, column=name_tok.column))

                    while self.check(TokenType.COMMA):
                        self.advance()
                        decl_id = self.parse_variable_declarator_id()
                        init = None
                        if self.check(TokenType.ASSIGN):
                            self.advance()
                            init = self.variable_initializer()
                        declarators.append(VariableDeclarator(id=decl_id, initializer=init, line=decl_id.line, column=decl_id.column))

                    self.expect(TokenType.SEMICOLON, "Era esperado ';' ao final da declaração do campo", expected="';'")
                    members.append(
                        FieldDeclaration(
                            type_ref=type_ref,
                            declarators=declarators,
                            modifiers=mods,
                            line=name_tok.line,
                            column=name_tok.column,
                            annotations=annos,
                        )
                    )

            if self.current <= old_current:
                t = self.peek()
                raise SyntacticError(
                    message="Loop detectado em unidade compacta: parser não avançou tokens",
                    line=t.line,
                    column=t.column,
                    expected="declaração de membro de classe válida",
                    found=t.lexeme if t.type != TokenType.EOF else "EOF",
                )

        if not found_first_method:
            raise SyntacticError(
                message="Unidade de compilação compacta exige pelo menos uma declaração de método (JLS §7.3)",
                line=start_line,
                column=start_col,
                expected="ao menos uma declaração de método",
                found="nenhum método declarado"
            )

        return CompactCompilationUnit(imports=imports, class_members=members, line=start_line, column=start_col)
