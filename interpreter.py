"""
G-- (Grammar--) Interpreter
A tree-walking evaluator for G-- programmes.
"""

from __future__ import annotations
from typing import Any, Optional
from ast_nodes import *


# ── Runtime Exceptions ────────────────────────────────────────────────────────

class RuntimeError_(Exception):
    """A friendly runtime error."""
    def __init__(self, msg: str):
        super().__init__(msg)


class ReturnException(Exception):
    """Used to unwind the call stack on 'return'."""
    def __init__(self, value: Any):
        self.value = value


# ── Environment (variable store) ─────────────────────────────────────────────

class Environment:
    def __init__(self, parent: Optional[Environment] = None):
        self.store: dict[str, Any] = {}
        self.parent = parent

    def get(self, name: str) -> Any:
        key = name.lower()
        if key in self.store:
            return self.store[key]
        if self.parent:
            return self.parent.get(name)
        raise RuntimeError_(f"I'm afraid '{name}' has not been defined.")

    def set(self, name: str, value: Any):
        self.store[name.lower()] = value

    def assign(self, name: str, value: Any):
        """Assign to existing variable, searching up the scope chain."""
        key = name.lower()
        if key in self.store:
            self.store[key] = value
            return
        if self.parent:
            self.parent.assign(name, value)
            return
        raise RuntimeError_(f"I'm afraid '{name}' has not been defined, so I cannot set it.")

    def define(self, name: str, value: Any):
        self.store[name.lower()] = value


# ── Routine (user-defined function) ───────────────────────────────────────────

class Routine:
    def __init__(self, name: str, params: list[str], body: list[Node], closure: Environment):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure

    def __repr__(self):
        return f"<routine '{self.name}'>"


# ── Interpreter ───────────────────────────────────────────────────────────────

class Interpreter:
    def __init__(self, output_fn=None, input_fn=None):
        """
        output_fn: callable(str) for output (defaults to print)
        input_fn:  callable(str) -> str for input (defaults to input())
        """
        self.output = output_fn or print
        self.input_fn = input_fn or (lambda prompt="": input(prompt))
        self.global_env = Environment()
        self._register_builtins()

    def _register_builtins(self):
        """Register built-in routines."""
        pass  # Builtins are handled in call_routine

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self, programme: Programme):
        self.execute_stmts(programme.statements, self.global_env)

    def run_stmt(self, stmt: Node, env: Optional[Environment] = None):
        self.execute(stmt, env or self.global_env)

    # ── Statement execution ───────────────────────────────────────────────────

    def execute_stmts(self, stmts: list[Node], env: Environment):
        for stmt in stmts:
            self.execute(stmt, env)

    def execute(self, node: Node, env: Environment):
        method = f"exec_{type(node).__name__}"
        handler = getattr(self, method, None)
        if handler is None:
            # Might be an expression used as a statement
            self.evaluate(node, env)
            return
        handler(node, env)

    def exec_Programme(self, node: Programme, env: Environment):
        self.execute_stmts(node.statements, env)

    def exec_LetStmt(self, node: LetStmt, env: Environment):
        value = self.evaluate(node.value, env)
        env.define(node.name, value)

    def exec_SetStmt(self, node: SetStmt, env: Environment):
        value = self.evaluate(node.value, env)
        try:
            env.assign(node.name, value)
        except RuntimeError_:
            raise RuntimeError_(
                f"I'm afraid '{node.name}' has not been defined. "
                f"Perhaps you meant to use 'let {node.name} be ...' first?"
            )

    def exec_SayStmt(self, node: SayStmt, env: Environment):
        value = self.evaluate(node.value, env)
        self.output(self.stringify(value))

    def exec_AskStmt(self, node: AskStmt, env: Environment):
        user_input = self.input_fn()
        # Try to coerce to number if possible
        try:
            if '.' in user_input:
                coerced: Any = float(user_input)
            else:
                coerced = int(user_input)
        except (ValueError, AttributeError):
            coerced = user_input
        env.define(node.name, coerced)

    def exec_IfStmt(self, node: IfStmt, env: Environment):
        condition = self.evaluate(node.condition, env)
        if self.is_truthy(condition):
            child_env = Environment(env)
            self.execute_stmts(node.then_body, child_env)
        elif node.else_body:
            child_env = Environment(env)
            self.execute_stmts(node.else_body, child_env)

    def exec_WhilstStmt(self, node: WhilstStmt, env: Environment):
        iterations = 0
        max_iter = 1_000_000
        while True:
            condition = self.evaluate(node.condition, env)
            if not self.is_truthy(condition):
                break
            iterations += 1
            if iterations > max_iter:
                raise RuntimeError_("I'm afraid the programme appears to be stuck in an endless loop.")
            child_env = Environment(env)
            self.execute_stmts(node.body, child_env)

    def exec_RepeatStmt(self, node: RepeatStmt, env: Environment):
        count = self.evaluate(node.count, env)
        if not isinstance(count, (int, float)):
            raise RuntimeError_(f"I'm afraid 'repeat' requires a number, but got '{count}'.")
        for _ in range(int(count)):
            child_env = Environment(env)
            self.execute_stmts(node.body, child_env)

    def exec_ForEachStmt(self, node: ForEachStmt, env: Environment):
        lst = self.evaluate(node.list_expr, env)
        if not isinstance(lst, list):
            raise RuntimeError_(f"I'm afraid I can only iterate over a list, but got '{self.stringify(lst)}'.")
        for item in list(lst):  # copy to allow mutation
            child_env = Environment(env)
            child_env.define(node.var_name, item)
            self.execute_stmts(node.body, child_env)

    def exec_DefineRoutine(self, node: DefineRoutine, env: Environment):
        routine = Routine(node.name, node.params, node.body, env)
        env.define(node.name, routine)

    def exec_PerformStmt(self, node: PerformStmt, env: Environment):
        self.call_routine(node.name, node.args, env)

    def exec_AddToList(self, node: AddToList, env: Environment):
        lst = env.get(node.list_name)
        if not isinstance(lst, list):
            raise RuntimeError_(f"I'm afraid '{node.list_name}' is not a list.")
        item = self.evaluate(node.item, env)
        lst.append(item)

    def exec_RemoveFromList(self, node: RemoveFromList, env: Environment):
        lst = env.get(node.list_name)
        if not isinstance(lst, list):
            raise RuntimeError_(f"I'm afraid '{node.list_name}' is not a list.")
        item = self.evaluate(node.item, env)
        try:
            lst.remove(item)
        except ValueError:
            raise RuntimeError_(
                f"I'm afraid '{self.stringify(item)}' is not in the list '{node.list_name}'."
            )

    def exec_ReturnStmt(self, node: ReturnStmt, env: Environment):
        value = self.evaluate(node.value, env)
        raise ReturnException(value)

    # ── Expression evaluation ─────────────────────────────────────────────────

    def evaluate(self, node: Node, env: Environment) -> Any:
        method = f"eval_{type(node).__name__}"
        handler = getattr(self, method, None)
        if handler is None:
            raise RuntimeError_(f"I'm afraid I don't know how to evaluate a {type(node).__name__}.")
        return handler(node, env)

    def eval_NumberLit(self, node: NumberLit, env: Environment) -> Any:
        return node.value

    def eval_StringLit(self, node: StringLit, env: Environment) -> Any:
        return node.value

    def eval_BoolLit(self, node: BoolLit, env: Environment) -> Any:
        return node.value

    def eval_NothingLit(self, node: NothingLit, env: Environment) -> Any:
        return None

    def eval_VarRef(self, node: VarRef, env: Environment) -> Any:
        return env.get(node.name)

    def eval_ListLit(self, node: ListLit, env: Environment) -> Any:
        return [self.evaluate(item, env) for item in node.items]

    def eval_UnaryOp(self, node: UnaryOp, env: Environment) -> Any:
        val = self.evaluate(node.operand, env)
        if node.op == 'not':
            return not self.is_truthy(val)
        if node.op == 'negate':
            if isinstance(val, (int, float)):
                return -val
            raise RuntimeError_(f"I'm afraid I cannot negate '{self.stringify(val)}'.")

    def eval_BinOp(self, node: BinOp, env: Environment) -> Any:
        op = node.op

        # Short-circuit boolean
        if op == 'and':
            left = self.evaluate(node.left, env)
            if not self.is_truthy(left):
                return False
            return self.is_truthy(self.evaluate(node.right, env))

        if op == 'or':
            left = self.evaluate(node.left, env)
            if self.is_truthy(left):
                return True
            return self.is_truthy(self.evaluate(node.right, env))

        left = self.evaluate(node.left, env)
        right = self.evaluate(node.right, env)

        if op == 'plus':
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left + right
            # String concatenation
            return self.stringify(left) + self.stringify(right)

        if op == 'minus':
            return self._require_numbers(op, left, right, lambda a, b: a - b)

        if op == 'times':
            return self._require_numbers(op, left, right, lambda a, b: a * b)

        if op == 'divided by':
            if right == 0:
                raise RuntimeError_("I'm afraid division by zero is not permitted.")
            return self._require_numbers(op, left, right, lambda a, b: a / b)

        if op == 'is':
            return self._equals(left, right)

        if op == 'is not':
            return not self._equals(left, right)

        if op == 'is greater than':
            return self._compare(op, left, right) > 0

        if op == 'is less than':
            return self._compare(op, left, right) < 0

        if op == 'is at least':
            return self._compare(op, left, right) >= 0

        if op == 'is at most':
            return self._compare(op, left, right) <= 0

        raise RuntimeError_(f"I'm afraid I don't know the operator '{op}'.")

    def eval_ContainsCheck(self, node: ContainsCheck, env: Environment) -> Any:
        lst = self.evaluate(node.list_expr, env)
        item = self.evaluate(node.item_expr, env)
        if isinstance(lst, list):
            return item in lst
        if isinstance(lst, str):
            return self.stringify(item) in lst
        raise RuntimeError_(f"I'm afraid I cannot check membership in '{self.stringify(lst)}'.")

    def eval_FirstItem(self, node: FirstItem, env: Environment) -> Any:
        lst = self.evaluate(node.list_expr, env)
        if not isinstance(lst, list):
            raise RuntimeError_("I'm afraid I can only take the first item of a list.")
        if not lst:
            raise RuntimeError_("I'm afraid the list is empty, so there is no first item.")
        return lst[0]

    def eval_LastItem(self, node: LastItem, env: Environment) -> Any:
        lst = self.evaluate(node.list_expr, env)
        if not isinstance(lst, list):
            raise RuntimeError_("I'm afraid I can only take the last item of a list.")
        if not lst:
            raise RuntimeError_("I'm afraid the list is empty, so there is no last item.")
        return lst[-1]

    def eval_LengthOf(self, node: LengthOf, env: Environment) -> Any:
        val = self.evaluate(node.list_expr, env)
        if isinstance(val, (list, str)):
            return len(val)
        raise RuntimeError_(f"I'm afraid I cannot find the length of '{self.stringify(val)}'.")

    def eval_ItemAt(self, node: ItemAt, env: Environment) -> Any:
        lst = self.evaluate(node.list_expr, env)
        idx = self.evaluate(node.index_expr, env)
        if not isinstance(lst, list):
            raise RuntimeError_("I'm afraid I can only index into a list.")
        if not isinstance(idx, (int, float)):
            raise RuntimeError_("I'm afraid a list index must be a number.")
        i = int(idx)
        if i < 0 or i >= len(lst):
            raise RuntimeError_(
                f"I'm afraid index {i + 1} is out of range for a list of {len(lst)} items."
            )
        return lst[i]

    def eval_RoutineCall(self, node: RoutineCall, env: Environment) -> Any:
        return self.call_routine(node.name, node.args, env)

    # ── Routine calls ─────────────────────────────────────────────────────────

    def call_routine(self, name: str, arg_nodes: list[Node], env: Environment) -> Any:
        args = [self.evaluate(a, env) for a in arg_nodes]

        # Built-ins
        builtins = {
            'shout': self._builtin_shout,
            'whisper': self._builtin_whisper,
            'absolute': self._builtin_absolute,
            'round': self._builtin_round,
            'floor': self._builtin_floor,
            'ceiling': self._builtin_ceiling,
        }
        if name.lower() in builtins:
            return builtins[name.lower()](args, name)

        # User-defined
        try:
            routine = env.get(name)
        except RuntimeError_:
            raise RuntimeError_(f"I'm afraid there is no routine called '{name}'.")

        if not isinstance(routine, Routine):
            raise RuntimeError_(f"I'm afraid '{name}' is not a routine.")

        if len(args) != len(routine.params):
            raise RuntimeError_(
                f"I'm afraid '{name}' expects {len(routine.params)} argument(s) "
                f"but received {len(args)}."
            )

        call_env = Environment(routine.closure)
        for param, arg in zip(routine.params, args):
            call_env.define(param, arg)

        try:
            self.execute_stmts(routine.body, call_env)
        except ReturnException as ret:
            return ret.value

        return None

    # ── Built-in routines ─────────────────────────────────────────────────────

    def _builtin_shout(self, args: list, name: str) -> Any:
        if len(args) != 1:
            raise RuntimeError_("I'm afraid 'shout' takes exactly one argument.")
        self.output(self.stringify(args[0]).upper())
        return None

    def _builtin_whisper(self, args: list, name: str) -> Any:
        if len(args) != 1:
            raise RuntimeError_("I'm afraid 'whisper' takes exactly one argument.")
        self.output(self.stringify(args[0]).lower())
        return None

    def _builtin_absolute(self, args: list, name: str) -> Any:
        if len(args) != 1:
            raise RuntimeError_("I'm afraid 'absolute' takes exactly one argument.")
        v = args[0]
        if not isinstance(v, (int, float)):
            raise RuntimeError_("I'm afraid 'absolute' requires a number.")
        return abs(v)

    def _builtin_round(self, args: list, name: str) -> Any:
        if len(args) not in (1, 2):
            raise RuntimeError_("I'm afraid 'round' takes one or two arguments.")
        v = args[0]
        if not isinstance(v, (int, float)):
            raise RuntimeError_("I'm afraid 'round' requires a number.")
        dp = int(args[1]) if len(args) == 2 else 0
        return round(v, dp) if dp else round(v)

    def _builtin_floor(self, args: list, name: str) -> Any:
        import math
        if len(args) != 1:
            raise RuntimeError_("I'm afraid 'floor' takes exactly one argument.")
        return math.floor(args[0])

    def _builtin_ceiling(self, args: list, name: str) -> Any:
        import math
        if len(args) != 1:
            raise RuntimeError_("I'm afraid 'ceiling' takes exactly one argument.")
        return math.ceil(args[0])

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value != ''
        if isinstance(value, list):
            return len(value) > 0
        return True

    def _equals(self, a: Any, b: Any) -> bool:
        if type(a) == type(b):
            return a == b
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a == b
        return str(a) == str(b)

    def _compare(self, op: str, a: Any, b: Any) -> int:
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return (a > b) - (a < b)
        if isinstance(a, str) and isinstance(b, str):
            return (a > b) - (a < b)
        raise RuntimeError_(
            f"I'm afraid I cannot compare '{self.stringify(a)}' with '{self.stringify(b)}'."
        )

    def _require_numbers(self, op: str, a: Any, b: Any, fn) -> Any:
        if not isinstance(a, (int, float)):
            raise RuntimeError_(f"I'm afraid '{self.stringify(a)}' is not a number, so I cannot use '{op}' on it.")
        if not isinstance(b, (int, float)):
            raise RuntimeError_(f"I'm afraid '{self.stringify(b)}' is not a number, so I cannot use '{op}' on it.")
        result = fn(a, b)
        # Return int if whole number
        if isinstance(result, float) and result == int(result):
            return int(result)
        return result

    def stringify(self, value: Any) -> str:
        if value is None:
            return "nothing"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float) and value == int(value):
            return str(int(value))
        if isinstance(value, list):
            return "[" + ", ".join(self.stringify(v) for v in value) + "]"
        return str(value)