from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # Palavras reservadas e tipos principais
    KEYWORD = auto()
    KEYWORD_INT = auto()
    KEYWORD_STRING = auto()
    BOOLEAN_LITERAL = auto()
    NULL_LITERAL = auto()

    # Identificadores
    IDENTIFIER = auto()

    # Literais
    STRING_LITERAL = auto()
    CHAR_LITERAL = auto()
    HEX_LITERAL = auto()
    BINARY_LITERAL = auto()
    OCTAL_LITERAL = auto()
    FLOAT_LITERAL = auto()
    NUMBER = auto()

    # Operadores de 3 caracteres
    URSHIFT_ASSIGN = auto()   # >>>=
    RSHIFT_ASSIGN = auto()    # >>=
    LSHIFT_ASSIGN = auto()    # <<=
    URSHIFT = auto()          # >>>
    ELLIPSIS = auto()         # ...

    # Operadores de 2 caracteres
    EQ = auto()               # ==
    NEQ = auto()              # !=
    LTE = auto()              # <=
    GTE = auto()              # >=
    AND = auto()              # &&
    OR = auto()               # ||
    INCREMENT = auto()        # ++
    DECREMENT = auto()        # --
    PLUS_ASSIGN = auto()      # +=
    MINUS_ASSIGN = auto()     # -=
    MUL_ASSIGN = auto()       # *=
    DIV_ASSIGN = auto()       # /=
    MOD_ASSIGN = auto()       # %=
    AND_ASSIGN = auto()       # &=
    OR_ASSIGN = auto()        # |=
    XOR_ASSIGN = auto()       # ^=
    LSHIFT = auto()           # <<
    RSHIFT = auto()           # >>
    METHOD_REF = auto()       # ::
    ARROW = auto()            # ->

    # Operadores de 1 caractere
    ASSIGN = auto()           # =
    GT = auto()               # >
    LT = auto()               # <
    NOT = auto()              # !
    BIT_NOT = auto()          # ~
    QUESTION = auto()         # ?
    COLON = auto()            # :
    PLUS = auto()             # +
    MINUS = auto()            # -
    MULTIPLY = auto()         # *
    DIVIDE = auto()           # /
    MODULO = auto()           # %
    BIT_AND = auto()          # &
    BIT_OR = auto()           # |
    BIT_XOR = auto()          # ^

    # Pontuação e delimitadores
    LBRACE = auto()           # {
    RBRACE = auto()           # }
    LPAREN = auto()           # (
    RPAREN = auto()           # )
    LBRACKET = auto()         # [
    RBRACKET = auto()         # ]
    SEMICOLON = auto()        # ;
    COMMA = auto()            # ,
    DOT = auto()              # .
    AT = auto()               # @

    # Controle
    EOF = auto()

    # Aliases para compatibilidade total
    INT = KEYWORD_INT
    STRING = KEYWORD_STRING
    ID = IDENTIFIER
    INTEGER = NUMBER
    FLOAT = FLOAT_LITERAL
    HEX = HEX_LITERAL
    BINARY = BINARY_LITERAL
    OCTAL = OCTAL_LITERAL
    MUL = MULTIPLY
    STAR = MULTIPLY
    DIV = DIVIDE
    SLASH = DIVIDE
    MOD = MODULO


@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int = 1

    def __str__(self):
        return f"{self.type.name:<16} -> {self.lexeme!r:<14} (linha {self.line}, coluna {self.column})"
