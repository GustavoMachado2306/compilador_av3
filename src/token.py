from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    KEYWORD_INT = auto()
    KEYWORD_STRING = auto()
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING_LITERAL = auto()
    ASSIGN = auto()
    PLUS = auto()
    MINUS = auto()
    SEMICOLON = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()

    # Aliases para compatibilidade total
    INT = KEYWORD_INT
    STRING = KEYWORD_STRING
    ID = IDENTIFIER


@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int = 1

    def __str__(self):
        return f"{self.type.name:<16} -> {self.lexeme!r:<14} (linha {self.line}, coluna {self.column})"
