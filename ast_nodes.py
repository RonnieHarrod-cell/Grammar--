"""
G-- (Grammar--) Abstract Syntax Tree Nodes
"""

from dataclasses import dataclass, field
from typing import Any, Optional


# ── Base ──────────────────────────────────────────────────────────────────────

class Node:
    pass


# ── Expressions ───────────────────────────────────────────────────────────────

@dataclass
class NumberLit(Node):
    value: float | int

@dataclass
class StringLit(Node):
    value: str

@dataclass
class BoolLit(Node):
    value: bool

@dataclass
class NothingLit(Node):
    pass

@dataclass
class VarRef(Node):
    name: str

@dataclass
class BinOp(Node):
    op: str        # 'plus', 'minus', 'times', 'divided by',
                   # 'is', 'is not', 'is greater than', 'is less than',
                   # 'is at least', 'is at most', 'and', 'or'
    left: Node
    right: Node

@dataclass
class UnaryOp(Node):
    op: str        # 'not', 'negate'
    operand: Node

@dataclass
class ListLit(Node):
    items: list[Node]

@dataclass
class FirstItem(Node):
    list_expr: Node

@dataclass
class LastItem(Node):
    list_expr: Node

@dataclass
class LengthOf(Node):
    list_expr: Node

@dataclass
class ContainsCheck(Node):
    list_expr: Node
    item_expr: Node

@dataclass
class ItemAt(Node):
    list_expr: Node
    index_expr: Node

@dataclass
class RoutineCall(Node):
    name: str
    args: list[Node]


# ── Statements ────────────────────────────────────────────────────────────────

@dataclass
class LetStmt(Node):
    name: str
    value: Node

@dataclass
class SetStmt(Node):
    name: str
    value: Node

@dataclass
class SayStmt(Node):
    value: Node

@dataclass
class AskStmt(Node):
    name: str

@dataclass
class IfStmt(Node):
    condition: Node
    then_body: list[Node]
    else_body: list[Node]

@dataclass
class WhilstStmt(Node):
    condition: Node
    body: list[Node]

@dataclass
class RepeatStmt(Node):
    count: Node
    body: list[Node]

@dataclass
class ForEachStmt(Node):
    var_name: str
    list_expr: Node
    body: list[Node]

@dataclass
class DefineRoutine(Node):
    name: str
    params: list[str]
    body: list[Node]

@dataclass
class PerformStmt(Node):
    name: str
    args: list[Node]

@dataclass
class AddToList(Node):
    item: Node
    list_name: str

@dataclass
class RemoveFromList(Node):
    item: Node
    list_name: str

@dataclass
class ReturnStmt(Node):
    value: Node

@dataclass
class Programme(Node):
    statements: list[Node]