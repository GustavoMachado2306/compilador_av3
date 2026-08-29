from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    INT = auto()
    STRING = auto()
    ID = auto()
    NUMBER = auto()
    STRING_LITERAL = auto()
    ASSIGN = auto()
    PLUS = auto()
    MINUS = auto()
    SEMICOLON = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()

@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int

    def __str__(self):
        return f"{self.type.name:<15} -> {self.lexeme!r:<12} (linha {self.line})"
