"""
Módulo de Definição de Tokens do Compilador Java (AV3).
Contém os tipos de token (TokenType) e a estrutura de dados Token,
preservando compatibilidade total com as etapas didáticas anteriores
e expandindo o reconhecimento para o conjunto lexical do Java.
"""

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """Tipos de tokens reconhecidos pelo analisador léxico."""

    # =========================================================================
    # SEÇÃO 1: PALAVRAS-CHAVE (KEYWORDS) ORIGINAIS E DIDÁTICAS
    # =========================================================================
    KEYWORD_INT = auto()         # Palavra-chave 'int'
    KEYWORD_STRING = auto()      # Palavra-chave 'String'

    # =========================================================================
    # SEÇÃO 2: PALAVRAS-CHAVE (KEYWORDS) JAVA EXPANDIDAS
    # =========================================================================
    KEYWORD_ABSTRACT = auto()     # 'abstract'
    KEYWORD_ASSERT = auto()       # 'assert'
    KEYWORD_BOOLEAN = auto()      # 'boolean'
    KEYWORD_BREAK = auto()        # 'break'
    KEYWORD_BYTE = auto()         # 'byte'
    KEYWORD_CASE = auto()         # 'case'
    KEYWORD_CATCH = auto()        # 'catch'
    KEYWORD_CHAR = auto()         # 'char'
    KEYWORD_CLASS = auto()        # 'class'
    KEYWORD_CONST = auto()        # 'const' (reservada)
    KEYWORD_CONTINUE = auto()     # 'continue'
    KEYWORD_DEFAULT = auto()      # 'default'
    KEYWORD_DO = auto()           # 'do'
    KEYWORD_DOUBLE = auto()       # 'double'
    KEYWORD_ELSE = auto()         # 'else'
    KEYWORD_ENUM = auto()         # 'enum'
    KEYWORD_EXTENDS = auto()      # 'extends'
    KEYWORD_FINAL = auto()        # 'final'
    KEYWORD_FINALLY = auto()      # 'finally'
    KEYWORD_FLOAT = auto()        # 'float'
    KEYWORD_FOR = auto()          # 'for'
    KEYWORD_IF = auto()           # 'if'
    KEYWORD_IMPLEMENTS = auto()   # 'implements'
    KEYWORD_IMPORT = auto()       # 'import'
    KEYWORD_INSTANCEOF = auto()   # 'instanceof'
    KEYWORD_INTERFACE = auto()    # 'interface'
    KEYWORD_LONG = auto()         # 'long'
    KEYWORD_NATIVE = auto()       # 'native'
    KEYWORD_NEW = auto()          # 'new'
    KEYWORD_PACKAGE = auto()      # 'package'
    KEYWORD_PRIVATE = auto()      # 'private'
    KEYWORD_PROTECTED = auto()    # 'protected'
    KEYWORD_PUBLIC = auto()       # 'public'
    KEYWORD_RETURN = auto()       # 'return'
    KEYWORD_SHORT = auto()        # 'short'
    KEYWORD_STATIC = auto()       # 'static'
    KEYWORD_STRICTFP = auto()     # 'strictfp'
    KEYWORD_SUPER = auto()        # 'super'
    KEYWORD_SWITCH = auto()       # 'switch'
    KEYWORD_SYNCHRONIZED = auto() # 'synchronized'
    KEYWORD_THIS = auto()         # 'this'
    KEYWORD_THROW = auto()        # 'throw'
    KEYWORD_THROWS = auto()       # 'throws'
    KEYWORD_TRANSIENT = auto()    # 'transient'
    KEYWORD_TRY = auto()          # 'try'
    KEYWORD_VOID = auto()         # 'void'
    KEYWORD_VOLATILE = auto()     # 'volatile'
    KEYWORD_WHILE = auto()        # 'while'

    # =========================================================================
    # SEÇÃO 3: IDENTIFICADORES E LITERAIS
    # =========================================================================
    IDENTIFIER = auto()           # Nomes de variáveis, métodos, classes
    INT = auto()                  # Literal inteiro (decimal, hex, bin, oct)
    NUMBER = INT                  # Alias para retrocompatibilidade com subconjunto didático
    LONG = auto()                 # Literal inteiro long (sufixo L/l)
    DOUBLE = auto()               # Literais de ponto flutuante double (ex: 3.1415, 2.0)
    FLOAT = auto()                # Literais de ponto flutuante float (ex: 1.23f)
    STRING_LITERAL = auto()       # Texto delimitado por aspas duplas: "..."
    CHAR_LITERAL = auto()         # Caractere delimitado por aspas simples: '...'
    BOOLEAN_LITERAL = auto()      # Literais booleanos: 'true', 'false'
    NULL_LITERAL = auto()         # Literal nulo: 'null'

    # =========================================================================
    # SEÇÃO 4: DELIMITADORES E PONTUAÇÃO
    # =========================================================================
    LPAREN = auto()               # '('
    RPAREN = auto()               # ')'
    LBRACE = auto()               # '{'
    RBRACE = auto()               # '}'
    LBRACKET = auto()             # '['
    RBRACKET = auto()             # ']'
    SEMICOLON = auto()            # ';'
    COMMA = auto()                # ','
    DOT = auto()                  # '.'
    AT = auto()                   # '@'
    QUESTION = auto()             # '?'
    COLON = auto()                # ':'

    # =========================================================================
    # SEÇÃO 5: OPERADORES DE ATRIBUIÇÃO
    # =========================================================================
    ASSIGN = auto()               # '='
    PLUS_ASSIGN = auto()          # '+='
    MINUS_ASSIGN = auto()         # '-='
    STAR_ASSIGN = auto()          # '*='
    SLASH_ASSIGN = auto()         # '/='
    PERCENT_ASSIGN = auto()       # '%='
    AND_ASSIGN = auto()           # '&='
    OR_ASSIGN = auto()            # '|='
    XOR_ASSIGN = auto()           # '^='
    LSHIFT_ASSIGN = auto()        # '<<='
    RSHIFT_ASSIGN = auto()        # '>>='
    URSHIFT_ASSIGN = auto()       # '>>>='

    # =========================================================================
    # SEÇÃO 6: OPERADORES ARITMÉTICOS E UNÁRIOS
    # =========================================================================
    PLUS = auto()                 # '+'
    MINUS = auto()                # '-'
    STAR = auto()                 # '*'
    SLASH = auto()                # '/'
    PERCENT = auto()              # '%'
    INCREMENT = auto()            # '++'
    DECREMENT = auto()            # '--'

    # =========================================================================
    # SEÇÃO 7: OPERADORES RELACIONAIS E DE IGUALDADE
    # =========================================================================
    EQUAL = auto()                # '=='
    NOT_EQUAL = auto()            # '!='
    LESS = auto()                 # '<'
    LESS_EQUAL = auto()           # '<='
    GREATER = auto()              # '>'
    GREATER_EQUAL = auto()        # '>='

    # =========================================================================
    # SEÇÃO 8: OPERADORES LÓGICOS E BITWISE
    # =========================================================================
    LOGICAL_AND = auto()          # '&&'
    LOGICAL_OR = auto()           # '||'
    LOGICAL_NOT = auto()         # '!'
    BITWISE_AND = auto()          # '&'
    BITWISE_OR = auto()           # '|'
    BITWISE_XOR = auto()          # '^'
    BITWISE_NOT = auto()          # '~'

    # =========================================================================
    # SEÇÃO 9: OPERADORES DE SHIFT E ESPECIAIS DE JAVA
    # =========================================================================
    LSHIFT = auto()               # '<<'
    RSHIFT = auto()               # '>>'
    URSHIFT = auto()              # '>>>'
    ARROW = auto()                # '->'
    DOUBLE_COLON = auto()         # '::'
    ELLIPSIS = auto()             # '...'

    # =========================================================================
    # SEÇÃO 10: FIM DE ARQUIVO (EOF)
    # =========================================================================
    EOF = auto()

    # Aliases mantidos para compatibilidade retroativa total
    INT_KEYWORD = KEYWORD_INT
    STRING = KEYWORD_STRING
    ID = IDENTIFIER
    INT_LITERAL = INT
    LONG_LITERAL = LONG
    DOUBLE_LITERAL = DOUBLE
    FLOAT_LITERAL = FLOAT


@dataclass
class Token:
    """
    Estrutura de dados que representa uma unidade léxica (Token).
    Preserva o tipo, o lexema original, o número de linha e a coluna.
    """
    type: TokenType
    lexeme: str
    line: int
    column: int = 1

    def __str__(self):
        """Formatação textual padronizada para exibição no terminal e testes."""
        return f"{self.type.name:<24} -> {self.lexeme!r:<16} (linha {self.line}, coluna {self.column})"
