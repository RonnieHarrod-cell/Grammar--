"""
G-- (Grammar--) Lexer
Tokenises G-- source code into a stream of tokens.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


class TT(Enum):
    """Token Types"""
    NUMBER      = auto()
    STRING      = auto()
    BOOLEAN     = auto()
    NOTHING     = auto()
    IDENT       = auto()
    LET         = auto()
    BE          = auto()
    SET         = auto()
    TO          = auto()
    A           = auto()
    AN          = auto()
    SAY         = auto()
    ASK         = auto()
    IF          = auto()
    THEN        = auto()
    OTHERWISE   = auto()
    END         = auto()
    WHILST      = auto()
    DO          = auto()
    REPEAT      = auto()
    TIMES       = auto()
    FOR         = auto()
    EACH        = auto()
    IN          = auto()
    DEFINE      = auto()
    ROUTINE     = auto()
    CALLED      = auto()
    TAKING      = auto()
    PERFORM     = auto()
    WITH        = auto()
    LIST        = auto()
    OF          = auto()
    ADD         = auto()
    REMOVE      = auto()
    FROM        = auto()
    THE         = auto()
    FIRST       = auto()
    LAST        = auto()
    ITEM        = auto()
    LENGTH      = auto()
    CONTAINS    = auto()
    PLUS        = auto()
    MINUS       = auto()
    DIVIDED_BY  = auto()
    IS          = auto()
    NOT         = auto()
    GREATER_THAN = auto()
    LESS_THAN   = auto()
    AT_LEAST    = auto()
    AND         = auto()
    OR          = auto()
    DOT         = auto()
    COMMA       = auto()
    EOF         = auto()


KEYWORDS: dict[str, TT] = {
    "let":       TT.LET,
    "be":        TT.BE,
    "set":       TT.SET,
    "to":        TT.TO,
    "a":         TT.A,
    "an":        TT.AN,
    "say":       TT.SAY,
    "ask":       TT.ASK,
    "if":        TT.IF,
    "then":      TT.THEN,
    "otherwise": TT.OTHERWISE,
    "end":       TT.END,
    "whilst":    TT.WHILST,
    "do":        TT.DO,
    "repeat":    TT.REPEAT,
    "times":     TT.TIMES,
    "for":       TT.FOR,
    "each":      TT.EACH,
    "in":        TT.IN,
    "define":    TT.DEFINE,
    "routine":   TT.ROUTINE,
    "called":    TT.CALLED,
    "taking":    TT.TAKING,
    "perform":   TT.PERFORM,
    "with":      TT.WITH,
    "list":      TT.LIST,
    "of":        TT.OF,
    "add":       TT.ADD,
    "remove":    TT.REMOVE,
    "from":      TT.FROM,
    "the":       TT.THE,
    "first":     TT.FIRST,
    "last":      TT.LAST,
    "item":      TT.ITEM,
    "length":    TT.LENGTH,
    "contains":  TT.CONTAINS,
    "plus":      TT.PLUS,
    "minus":     TT.MINUS,
    "divided":   TT.DIVIDED_BY,
    "is":        TT.IS,
    "not":       TT.NOT,
    "and":       TT.AND,
    "or":        TT.OR,
    "greater":   TT.GREATER_THAN,
    "less":      TT.LESS_THAN,
    "at":        TT.AT_LEAST,
}


@dataclass
class Token:
    type: TT
    value: object
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"


class LexError(Exception):
    def __init__(self, msg: str, line: int = 0, col: int = 0):
        super().__init__(msg)
        self.line = line
        self.col = col


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []

    def error(self, msg: str) -> LexError:
        return LexError(msg, self.line, self.col)

    def peek(self, offset: int = 0) -> Optional[str]:
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return None

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def skip_whitespace(self):
        while self.pos < len(self.source) and self.source[self.pos] in ' \t\r\n':
            self.advance()

    def skip_comment(self):
        """Comments are (like this — nested comments are (also fine))"""
        self.advance()  # consume '('
        depth = 1
        while self.pos < len(self.source):
            ch = self.advance()
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    return
        raise self.error("I'm afraid a comment was opened but never closed.")

    def read_string(self) -> Token:
        line, col = self.line, self.col
        self.advance()  # consume opening "
        buf = []
        while self.pos < len(self.source):
            ch = self.peek()
            if ch == '"':
                self.advance()
                return Token(TT.STRING, ''.join(buf), line, col)
            elif ch == '\\':
                self.advance()
                esc = self.advance()
                buf.append({'n': '\n', 't': '\t', '"': '"', '\\': '\\'}.get(esc, esc))
            else:
                buf.append(self.advance())
        raise self.error("I'm afraid a string was opened but never closed.")

    def read_number(self) -> Token:
        line, col = self.line, self.col
        buf = []
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            buf.append(self.advance())
        # Only consume decimal point if followed by digit
        if (self.pos < len(self.source) and self.source[self.pos] == '.'
                and self.pos + 1 < len(self.source) and self.source[self.pos + 1].isdigit()):
            buf.append(self.advance())  # '.'
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                buf.append(self.advance())
        text = ''.join(buf)
        if '.' in text:
            return Token(TT.NUMBER, float(text), line, col)
        return Token(TT.NUMBER, int(text), line, col)

    def read_word(self) -> Token:
        line, col = self.line, self.col
        buf = []
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            buf.append(self.advance())
        word = ''.join(buf)
        lower = word.lower()
        if lower == 'true':
            return Token(TT.BOOLEAN, True, line, col)
        if lower == 'false':
            return Token(TT.BOOLEAN, False, line, col)
        if lower == 'nothing':
            return Token(TT.NOTHING, None, line, col)
        tt = KEYWORDS.get(lower, TT.IDENT)
        return Token(tt, word, line, col)

    def tokenise(self) -> list[Token]:
        while self.pos < len(self.source):
            self.skip_whitespace()
            if self.pos >= len(self.source):
                break

            ch = self.peek()

            if ch == '(':
                self.skip_comment()
            elif ch == '"':
                self.tokens.append(self.read_string())
            elif ch == '.':
                line, col = self.line, self.col
                self.advance()
                self.tokens.append(Token(TT.DOT, '.', line, col))
            elif ch == ',':
                line, col = self.line, self.col
                self.advance()
                self.tokens.append(Token(TT.COMMA, ',', line, col))
            elif ch.isdigit():
                self.tokens.append(self.read_number())
            elif ch.isalpha() or ch == '_':
                self.tokens.append(self.read_word())
            else:
                raise self.error(f"I'm afraid I don't recognise the character '{ch}'.")

        self.tokens.append(Token(TT.EOF, None, self.line, self.col))
        return self.tokens