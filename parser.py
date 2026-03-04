"""
G-- (Grammar--) Parser
Builds an AST from the token stream produced by the Lexer.
"""

from typing import Optional
from lexer import Token, TT
from ast_nodes import *


class ParseError(Exception):
    def __init__(self, msg: str, line: int = 0, col: int = 0):
        super().__init__(msg)
        self.line = line
        self.col = col


# Tokens that can start a new statement (used to detect end-of-expression)
STMT_STARTERS = {
    TT.LET, TT.SET, TT.SAY, TT.ASK, TT.IF, TT.WHILST, TT.REPEAT,
    TT.FOR, TT.DEFINE, TT.PERFORM, TT.ADD, TT.REMOVE, TT.END,
    TT.OTHERWISE, TT.EOF
}

# Tokens that can legally be used as variable/parameter names
NAME_TYPES = {TT.IDENT, TT.ITEM, TT.ADD, TT.REMOVE, TT.FROM, TT.WITH,
              TT.LIST, TT.OF, TT.THE, TT.LENGTH, TT.FIRST, TT.LAST,
              TT.CONTAINS, TT.IN, TT.DO, TT.EACH}


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # ── Helpers ───────────────────────────────────────────────────────────────

    def peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF

    def current(self) -> Token:
        return self.peek(0)

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def check(self, *types: TT) -> bool:
        return self.current().type in types

    def match(self, *types: TT) -> Optional[Token]:
        if self.check(*types):
            return self.advance()
        return None

    def expect(self, tt: TT, friendly: str = "") -> Token:
        if self.current().type == tt:
            return self.advance()
        tok = self.current()
        hint = friendly or tt.name
        raise ParseError(
            f"I'm afraid I expected {hint} but found '{tok.value}' instead.",
            tok.line, tok.col
        )

    def expect_dot(self):
        self.expect(TT.DOT, "a full stop '.'")

    def error(self, msg: str) -> ParseError:
        tok = self.current()
        return ParseError(msg, tok.line, tok.col)

    def expect_name(self, context: str = "a name") -> Token:
        """Expect any token that can serve as an identifier."""
        tok = self.current()
        if tok.type == TT.IDENT or tok.type in NAME_TYPES:
            return self.advance()
        raise ParseError(
            f"I'm afraid I expected {context} but found '{tok.value}'.",
            tok.line, tok.col
        )

    # ── Programme ─────────────────────────────────────────────────────────────

    def parse(self) -> Programme:
        stmts = []
        while not self.check(TT.EOF):
            stmt = self.parse_statement()
            if stmt is not None:
                stmts.append(stmt)
        return Programme(stmts)

    # ── Statements ────────────────────────────────────────────────────────────

    def parse_statement(self) -> Optional[Node]:
        tok = self.current()

        if tok.type == TT.EOF:
            return None
        if tok.type == TT.LET:
            return self.parse_let()
        if tok.type == TT.SET:
            return self.parse_set()
        if tok.type == TT.SAY:
            return self.parse_say()
        if tok.type == TT.ASK:
            return self.parse_ask()
        if tok.type == TT.IF:
            return self.parse_if()
        if tok.type == TT.WHILST:
            return self.parse_whilst()
        if tok.type == TT.REPEAT:
            return self.parse_repeat()
        if tok.type == TT.FOR:
            return self.parse_for_each()
        if tok.type == TT.DEFINE:
            return self.parse_define()
        if tok.type == TT.PERFORM:
            return self.parse_perform()
        if tok.type == TT.ADD:
            return self.parse_add()
        if tok.type == TT.REMOVE:
            return self.parse_remove()
        # 'return' is an IDENT since it's not a keyword
        if tok.type == TT.IDENT and tok.value.lower() == 'return':
            return self.parse_return()

        raise ParseError(
            f"I'm afraid I don't know how to begin a statement with '{tok.value}'.",
            tok.line, tok.col
        )

    def parse_let(self) -> Node:
        self.advance()  # consume 'let'
        name_tok = self.expect_name("a variable name")
        name = str(name_tok.value)
        self.expect(TT.BE, "'be'")

        # let colours be a list of ...
        if self.check(TT.A, TT.AN):
            saved = self.pos
            self.advance()  # consume 'a' / 'an'
            if self.check(TT.LIST):
                self.advance()  # consume 'list'
                self.expect(TT.OF, "'of'")
                # Handle empty list
                if self.check(TT.DOT):
                    self.expect_dot()
                    return LetStmt(name, ListLit([]))
                items = self.parse_comma_separated_expressions()
                self.expect_dot()
                return LetStmt(name, ListLit(items))
            else:
                self.pos = saved

        value = self.parse_expression()
        self.expect_dot()
        return LetStmt(name, value)

    def parse_set(self) -> Node:
        self.advance()  # consume 'set'
        name_tok = self.expect_name("a variable name")
        name = str(name_tok.value)
        self.expect(TT.TO, "'to'")
        value = self.parse_expression()
        self.expect_dot()
        return SetStmt(name, value)

    def parse_say(self) -> Node:
        self.advance()  # consume 'say'
        value = self.parse_expression()
        self.expect_dot()
        return SayStmt(value)

    def parse_ask(self) -> Node:
        self.advance()  # consume 'ask'
        name_tok = self.expect_name("a variable name")
        self.expect_dot()
        return AskStmt(str(name_tok.value))

    def parse_if(self) -> Node:
        self.advance()  # consume 'if'
        condition = self.parse_expression()
        self.expect(TT.THEN, "'then'")
        then_body = self.parse_body()
        else_body = []
        if self.check(TT.OTHERWISE):
            self.advance()
            else_body = self.parse_body()
        self.expect(TT.END, "'end'")
        self.expect_dot()
        return IfStmt(condition, then_body, else_body)

    def parse_whilst(self) -> Node:
        self.advance()  # consume 'whilst'
        condition = self.parse_expression()
        self.expect(TT.DO, "'do'")
        body = self.parse_body()
        self.expect(TT.END, "'end'")
        self.expect_dot()
        return WhilstStmt(condition, body)

    def parse_repeat(self) -> Node:
        self.advance()  # consume 'repeat'
        count = self.parse_repeat_count()
        self.expect(TT.TIMES, "'times'")
        body = self.parse_body()
        self.expect(TT.END, "'end'")
        self.expect_dot()
        return RepeatStmt(count, body)

    def parse_repeat_count(self) -> Node:
        """Parse the count for 'repeat N times' — stops before 'times'"""
        # For repeat, count is a simple primary expression (number or variable)
        # We don't want to accidentally consume 'times' as a multiply operator
        return self.parse_primary()

    def parse_for_each(self) -> Node:
        self.advance()  # consume 'for'
        self.expect(TT.EACH, "'each'")
        var_tok = self.expect_name("a loop variable name")
        self.expect(TT.IN, "'in'")
        list_expr = self.parse_primary()  # just a variable reference usually
        self.expect(TT.DO, "'do'")
        body = self.parse_body()
        self.expect(TT.END, "'end'")
        self.expect_dot()
        return ForEachStmt(str(var_tok.value), list_expr, body)

    def parse_define(self) -> Node:
        self.advance()  # consume 'define'
        self.expect(TT.A, "'a'")
        self.expect(TT.ROUTINE, "'routine'")
        self.expect(TT.CALLED, "'called'")
        name_tok = self.expect_name("a routine name")
        name = str(name_tok.value)
        params = []
        if self.check(TT.TAKING):
            self.advance()
            params = self.parse_param_list()
        body = self.parse_body()
        self.expect(TT.END, "'end'")
        self.expect_dot()
        return DefineRoutine(name, params, body)

    def parse_param_list(self) -> list[str]:
        params = []
        tok = self.expect_name("a parameter name")
        params.append(str(tok.value))
        while self.check(TT.AND) or self.check(TT.COMMA):
            self.advance()  # consume 'and' or ','
            # optionally skip 'also' after 'and'
            if self.current().type == TT.IDENT and self.current().value.lower() == 'also':
                self.advance()
            tok = self.expect_name("a parameter name")
            params.append(str(tok.value))
        return params

    def parse_perform(self) -> Node:
        self.advance()  # consume 'perform'
        name_tok = self.expect_name("a routine name")
        name = str(name_tok.value)
        args = []
        if self.check(TT.WITH):
            self.advance()
            args = self.parse_comma_separated_expressions()
        self.expect_dot()
        return PerformStmt(name, args)

    def parse_add(self) -> Node:
        self.advance()  # consume 'add'
        item = self.parse_expression()
        self.expect(TT.TO, "'to'")
        name_tok = self.expect_name("a list name")
        self.expect_dot()
        return AddToList(item, str(name_tok.value))

    def parse_remove(self) -> Node:
        self.advance()  # consume 'remove'
        item = self.parse_expression()
        self.expect(TT.FROM, "'from'")
        name_tok = self.expect_name("a list name")
        self.expect_dot()
        return RemoveFromList(item, str(name_tok.value))

    def parse_return(self) -> Node:
        self.advance()  # consume 'return'
        value = self.parse_expression()
        self.expect_dot()
        return ReturnStmt(value)

    def parse_body(self) -> list[Node]:
        """Parse statements until 'end' or 'otherwise'"""
        stmts = []
        while not self.check(TT.END, TT.OTHERWISE, TT.EOF):
            stmt = self.parse_statement()
            if stmt is not None:
                stmts.append(stmt)
        return stmts

    def parse_comma_separated_expressions(self) -> list[Node]:
        exprs = [self.parse_expression()]
        while self.check(TT.COMMA):
            self.advance()
            exprs.append(self.parse_expression())
        return exprs

    # ── Expressions ───────────────────────────────────────────────────────────
    # Precedence (lowest → highest):
    #   or
    #   and
    #   not
    #   comparison (is, is not, is greater than, ...)
    #   addition (plus, minus)
    #   multiplication (times, divided by)
    #   unary minus
    #   primary

    def parse_expression(self) -> Node:
        return self.parse_or()

    def parse_or(self) -> Node:
        left = self.parse_and()
        while self.check(TT.OR):
            self.advance()
            right = self.parse_and()
            left = BinOp('or', left, right)
        return left

    def parse_and(self) -> Node:
        left = self.parse_not()
        # 'and' is ambiguous: could be boolean AND or part of "a and b" in param list
        # In expression context, we treat it as boolean AND
        while self.check(TT.AND):
            # Don't consume 'and' if the next token looks like a param separator
            # (i.e., if we're in a context where AND acts as list separator)
            # We handle this conservatively: consume AND as boolean operator in expressions
            self.advance()
            right = self.parse_not()
            left = BinOp('and', left, right)
        return left

    def parse_not(self) -> Node:
        if self.check(TT.NOT):
            self.advance()
            operand = self.parse_not()
            return UnaryOp('not', operand)
        return self.parse_comparison()

    def parse_comparison(self) -> Node:
        left = self.parse_addition()

        # is not
        if self.check(TT.IS) and self.peek(1).type == TT.NOT:
            self.advance()  # 'is'
            self.advance()  # 'not'
            right = self.parse_addition()
            return BinOp('is not', left, right)

        # is greater than
        if self.check(TT.IS) and self.peek(1).type == TT.GREATER_THAN:
            self.advance()  # 'is'
            self.advance()  # 'greater'
            if self.current().value and str(self.current().value).lower() == 'than':
                self.advance()  # 'than'
            right = self.parse_addition()
            return BinOp('is greater than', left, right)

        # is less than
        if self.check(TT.IS) and self.peek(1).type == TT.LESS_THAN:
            self.advance()  # 'is'
            self.advance()  # 'less'
            if self.current().value and str(self.current().value).lower() == 'than':
                self.advance()  # 'than'
            right = self.parse_addition()
            return BinOp('is less than', left, right)

        # is at least / is at most
        if self.check(TT.IS) and self.peek(1).type == TT.AT_LEAST:
            self.advance()  # 'is'
            self.advance()  # 'at'
            qualifier = str(self.current().value).lower()
            self.advance()  # 'least' or 'most'
            right = self.parse_addition()
            op = 'is at least' if qualifier == 'least' else 'is at most'
            return BinOp(op, left, right)

        # contains
        if self.check(TT.CONTAINS):
            self.advance()
            right = self.parse_addition()
            return ContainsCheck(left, right)

        # plain is (equality)
        if self.check(TT.IS):
            self.advance()
            right = self.parse_addition()
            return BinOp('is', left, right)

        return left

    def parse_addition(self) -> Node:
        left = self.parse_multiplication()
        while self.check(TT.PLUS, TT.MINUS):
            op = 'plus' if self.current().type == TT.PLUS else 'minus'
            self.advance()
            right = self.parse_multiplication()
            left = BinOp(op, left, right)
        return left

    def parse_multiplication(self) -> Node:
        left = self.parse_unary()
        while self.check(TT.TIMES, TT.DIVIDED_BY):
            if self.current().type == TT.TIMES:
                op = 'times'
                self.advance()
            else:
                op = 'divided by'
                self.advance()
                # consume 'by' if present
                if self.current().value and str(self.current().value).lower() == 'by':
                    self.advance()
            right = self.parse_unary()
            left = BinOp(op, left, right)
        return left

    def parse_unary(self) -> Node:
        if self.check(TT.MINUS):
            self.advance()
            operand = self.parse_unary()
            return UnaryOp('negate', operand)
        return self.parse_primary()

    def parse_primary(self) -> Node:
        tok = self.current()

        if tok.type == TT.NUMBER:
            self.advance()
            return NumberLit(tok.value)

        if tok.type == TT.STRING:
            self.advance()
            return StringLit(tok.value)

        if tok.type == TT.BOOLEAN:
            self.advance()
            return BoolLit(tok.value)

        if tok.type == TT.NOTHING:
            self.advance()
            return NothingLit()

        if tok.type == TT.THE:
            return self.parse_the_expression()

        # Inline list in expression context
        if tok.type in (TT.A, TT.AN):
            saved = self.pos
            self.advance()
            if self.check(TT.LIST):
                self.advance()
                self.expect(TT.OF, "'of'")
                items = self.parse_comma_separated_expressions()
                return ListLit(items)
            self.pos = saved

        # Variable reference — allow keywords that can double as identifiers
        if tok.type == TT.IDENT or tok.type in NAME_TYPES:
            self.advance()
            return VarRef(str(tok.value))

        raise ParseError(
            f"I'm afraid I don't understand '{tok.value}' in this context.",
            tok.line, tok.col
        )

    def parse_the_expression(self) -> Node:
        """Parse 'the first/last item of X', 'the length of X', 'the Nth item of X'"""
        self.advance()  # consume 'the'
        tok = self.current()

        if tok.type == TT.FIRST:
            self.advance()
            if self.current().type == TT.ITEM:
                self.advance()
            self.expect(TT.OF, "'of'")
            list_expr = self.parse_primary()
            return FirstItem(list_expr)

        if tok.type == TT.LAST:
            self.advance()
            if self.current().type == TT.ITEM:
                self.advance()
            self.expect(TT.OF, "'of'")
            list_expr = self.parse_primary()
            return LastItem(list_expr)

        if tok.type == TT.LENGTH:
            self.advance()
            self.expect(TT.OF, "'of'")
            list_expr = self.parse_primary()
            return LengthOf(list_expr)

        # the Nth item of <list>  (1-based ordinals)
        if tok.type == TT.NUMBER:
            idx_val = tok.value
            self.advance()
            # consume optional ordinal suffix: st, nd, rd, th
            if self.current().type == TT.IDENT and str(self.current().value).lower() in ('st', 'nd', 'rd', 'th'):
                self.advance()
            if self.current().type == TT.ITEM:
                self.advance()
            self.expect(TT.OF, "'of'")
            list_expr = self.parse_primary()
            return ItemAt(list_expr, NumberLit(int(idx_val) - 1))  # 1-based → 0-based

        raise ParseError(
            f"I'm afraid I don't understand 'the {tok.value}' here.",
            tok.line, tok.col
        )