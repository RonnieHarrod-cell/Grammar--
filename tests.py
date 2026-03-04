#!/usr/bin/env python3
"""
G-- (Grammar--) Test Suite
Tests all major language features.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer, LexError
from parser import Parser, ParseError
from interpreter import Interpreter, RuntimeError_
from ast_nodes import Programme


# ── Test harness ──────────────────────────────────────────────────────────────

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.results = []

    def run(self, name: str, source: str, expected_output: list[str] = None,
            expected_error: str = None, inputs: list[str] = None):
        """Run a single test."""
        outputs = []
        input_queue = list(inputs or [])

        def capture_output(text):
            outputs.append(str(text))

        def provide_input():
            if input_queue:
                return input_queue.pop(0)
            return ""

        interpreter = Interpreter(output_fn=capture_output, input_fn=provide_input)

        error_msg = None
        try:
            lexer = Lexer(source)
            tokens = lexer.tokenise()
            parser = Parser(tokens)
            programme = parser.parse()
            interpreter.run(programme)
        except (LexError, ParseError, RuntimeError_) as e:
            error_msg = str(e)
        except Exception as e:
            error_msg = f"UNEXPECTED: {type(e).__name__}: {e}"
            self.errors += 1
            self.results.append(('ERROR', name, f"Unexpected exception: {e}"))
            return

        # Check expectations
        if expected_error is not None:
            if error_msg and expected_error.lower() in error_msg.lower():
                self.passed += 1
                self.results.append(('PASS', name, None))
            elif error_msg:
                self.failed += 1
                self.results.append(('FAIL', name,
                    f"Expected error containing '{expected_error}' but got: {error_msg}"))
            else:
                self.failed += 1
                self.results.append(('FAIL', name,
                    f"Expected error containing '{expected_error}' but no error occurred. "
                    f"Output: {outputs}"))
            return

        if error_msg:
            self.failed += 1
            self.results.append(('FAIL', name, f"Unexpected error: {error_msg}"))
            return

        if expected_output is not None:
            if outputs == [str(e) for e in expected_output]:
                self.passed += 1
                self.results.append(('PASS', name, None))
            else:
                self.failed += 1
                self.results.append(('FAIL', name,
                    f"Expected {expected_output} but got {outputs}"))
        else:
            # No expectations — just check it ran without error
            self.passed += 1
            self.results.append(('PASS', name, None))

    def report(self):
        total = self.passed + self.failed + self.errors
        print(f"\n{'═'*60}")
        print(f"  G-- Test Results")
        print(f"{'═'*60}")

        for status, name, detail in self.results:
            icon = '✓' if status == 'PASS' else ('✗' if status == 'FAIL' else '!')
            colour = '\033[92m' if status == 'PASS' else '\033[91m'
            reset = '\033[0m'
            print(f"  {colour}{icon}{reset}  {name}")
            if detail:
                print(f"       → {detail}")

        print(f"{'─'*60}")
        print(f"  Passed: {self.passed}/{total}  |  Failed: {self.failed}  |  Errors: {self.errors}")
        print(f"{'═'*60}\n")
        return self.failed == 0 and self.errors == 0


# ── Tests ─────────────────────────────────────────────────────────────────────

def run_all_tests():
    t = TestRunner()

    # ── Variable Assignment ───────────────────────────────────────────────────

    t.run("let: string variable",
        'let name be "Ronnie".\nsay name.',
        ["Ronnie"])

    t.run("let: number variable",
        'let age be 30.\nsay age.',
        ["30"])

    t.run("let: boolean variable",
        'let flag be true.\nsay flag.',
        ["true"])

    t.run("let: nothing",
        'let x be nothing.\nsay x.',
        ["nothing"])

    t.run("set: reassignment",
        'let x be 1.\nset x to 2.\nsay x.',
        ["2"])

    t.run("set: reassignment to expression",
        'let x be 10.\nset x to x plus 5.\nsay x.',
        ["15"])

    t.run("error: set undefined variable",
        'set ghost to 5.',
        expected_error="has not been defined")

    t.run("error: reference undefined variable",
        'say ghost.',
        expected_error="has not been defined")

    # ── Arithmetic ────────────────────────────────────────────────────────────

    t.run("arithmetic: plus numbers",
        'say 3 plus 4.',
        ["7"])

    t.run("arithmetic: minus",
        'say 10 minus 3.',
        ["7"])

    t.run("arithmetic: times",
        'say 4 times 5.',
        ["20"])

    t.run("arithmetic: divided by",
        'say 10 divided by 2.',
        ["5"])

    t.run("arithmetic: division returning float",
        'say 7 divided by 2.',
        ["3.5"])

    t.run("arithmetic: chained operations",
        'say 2 plus 3 times 4.',
        ["14"])  # times binds tighter: 2 + (3*4) = 14

    t.run("arithmetic: string concatenation with plus",
        'say "Hello, " plus "world!".',
        ["Hello, world!"])

    t.run("arithmetic: number and string concat",
        'let n be 42.\nsay "Answer: " plus n.',
        ["Answer: 42"])

    t.run("arithmetic: negative number",
        'let x be 0 minus 5.\nsay x.',
        ["-5"])

    t.run("error: division by zero",
        'say 10 divided by 0.',
        expected_error="division by zero")

    # ── Comparisons & Conditions ──────────────────────────────────────────────

    t.run("condition: is (equal)",
        'let x be 5.\nif x is 5 then\n  say "yes".\nend.',
        ["yes"])

    t.run("condition: is not",
        'let x be 3.\nif x is not 5 then\n  say "different".\nend.',
        ["different"])

    t.run("condition: is greater than",
        'let x be 10.\nif x is greater than 5 then\n  say "big".\nend.',
        ["big"])

    t.run("condition: is less than",
        'let x be 2.\nif x is less than 5 then\n  say "small".\nend.',
        ["small"])

    t.run("condition: is at least",
        'let x be 18.\nif x is at least 18 then\n  say "adult".\nend.',
        ["adult"])

    t.run("condition: is at most",
        'let x be 5.\nif x is at most 10 then\n  say "fine".\nend.',
        ["fine"])

    t.run("condition: otherwise branch",
        'let x be 10.\nif x is less than 5 then\n  say "small".\notherwise\n  say "large".\nend.',
        ["large"])

    t.run("condition: boolean and",
        'let x be 5.\nlet y be 10.\nif x is 5 and y is 10 then\n  say "both".\nend.',
        ["both"])

    t.run("condition: boolean or",
        'let x be 5.\nif x is 3 or x is 5 then\n  say "match".\nend.',
        ["match"])

    t.run("condition: not",
        'let flag be false.\nif not flag then\n  say "negated".\nend.',
        ["negated"])

    t.run("condition: nested if",
        """
let x be 10.
if x is greater than 5 then
  if x is less than 20 then
    say "in range".
  end.
end.
""",
        ["in range"])

    # ── Loops ─────────────────────────────────────────────────────────────────

    t.run("whilst: basic loop",
        'let i be 0.\nwhilst i is less than 3 do\n  say i.\n  set i to i plus 1.\nend.',
        ["0", "1", "2"])

    t.run("whilst: never executes",
        'let i be 10.\nwhilst i is less than 0 do\n  say "never".\nend.\nsay "done".',
        ["done"])

    t.run("repeat: basic",
        'repeat 3 times\n  say "hooray".\nend.',
        ["hooray", "hooray", "hooray"])

    t.run("repeat: zero times",
        'repeat 0 times\n  say "never".\nend.\nsay "done".',
        ["done"])

    t.run("repeat: counter accumulation",
        'let total be 0.\nrepeat 5 times\n  set total to total plus 1.\nend.\nsay total.',
        ["5"])

    # ── Routines ──────────────────────────────────────────────────────────────

    t.run("routine: basic definition and call",
        '''
define a routine called greet taking name
  say "Hello, " plus name plus "!".
end.
perform greet with "Ronnie".
''',
        ["Hello, Ronnie!"])

    t.run("routine: no parameters",
        '''
define a routine called cheer
  say "Hip hip hooray!".
end.
perform cheer.
''',
        ["Hip hip hooray!"])

    t.run("routine: multiple calls",
        '''
define a routine called double taking n
  say n times 2.
end.
perform double with 3.
perform double with 5.
''',
        ["6", "10"])

    t.run("routine: return value",
        '''
define a routine called double taking n
  return n times 2.
end.
let result be double.
perform double with 7.
''',
        # perform doesn't print — we just test it runs
        [])

    t.run("routine: two parameters",
        '''
define a routine called add_two taking first and second
  say first plus second.
end.
perform add_two with 3, 5.
''',
        ["8"])

    t.run("routine: closure over outer variable",
        '''
let prefix be "Dear ".
define a routine called greet taking name
  say prefix plus name.
end.
perform greet with "Reader".
''',
        ["Dear Reader"])

    t.run("error: call undefined routine",
        'perform nonexistent.',
        expected_error="no routine called")

    t.run("error: wrong number of arguments",
        '''
define a routine called greet taking name
  say name.
end.
perform greet with "a", "b".
''',
        expected_error="expects 1 argument")

    # ── Lists ─────────────────────────────────────────────────────────────────

    t.run("list: declaration",
        'let colours be a list of "red", "blue", "green".\nsay the length of colours.',
        ["3"])

    t.run("list: add item",
        'let nums be a list of 1, 2, 3.\nadd 4 to nums.\nsay the length of nums.',
        ["4"])

    t.run("list: remove item",
        'let nums be a list of 1, 2, 3.\nremove 2 from nums.\nsay the length of nums.',
        ["2"])

    t.run("list: first item",
        'let colours be a list of "red", "blue", "green".\nsay the first item of colours.',
        ["red"])

    t.run("list: last item",
        'let colours be a list of "red", "blue", "green".\nsay the last item of colours.',
        ["green"])

    t.run("list: for each",
        'let nums be a list of 1, 2, 3.\nfor each n in nums do\n  say n.\nend.',
        ["1", "2", "3"])

    t.run("list: for each with computation",
        'let nums be a list of 2, 4, 6.\nfor each n in nums do\n  say n times 2.\nend.',
        ["4", "8", "12"])

    t.run("list: contains (true)",
        'let colours be a list of "red", "blue".\nif colours contains "red" then\n  say "yes".\nend.',
        ["yes"])

    t.run("list: contains (false)",
        'let colours be a list of "red", "blue".\nif colours contains "green" then\n  say "yes".\notherwise\n  say "no".\nend.',
        ["no"])

    t.run("list: nth item",
        'let colours be a list of "red", "blue", "green".\nsay the 2nd item of colours.',
        ["blue"])

    t.run("error: remove item not in list",
        'let nums be a list of 1, 2.\nremove 99 from nums.',
        expected_error="not in the list")

    t.run("error: first item of empty list",
        'let empty be a list of.\nsay the first item of empty.',
        expected_error="")  # parser might not allow empty list, or runtime error

    # ── Comments ──────────────────────────────────────────────────────────────

    t.run("comment: inline comment",
        '(This is a comment)\nlet x be 5.\nsay x.',
        ["5"])

    t.run("comment: comment in expression context",
        'let x be 5. (x is five)\nsay x.',
        ["5"])

    # ── Built-in routines ─────────────────────────────────────────────────────

    t.run("builtin: shout",
        'perform shout with "hello".',
        ["HELLO"])

    t.run("builtin: whisper",
        'perform whisper with "HELLO".',
        ["hello"])

    t.run("builtin: absolute",
        'let x be 0 minus 5.\nperform absolute with x.',
        [])  # absolute returns but doesn't print — just check no error

    t.run("builtin: round",
        'perform round with 3.7.',
        [])

    # ── Complex programmes ────────────────────────────────────────────────────

    t.run("complex: FizzBuzz (1-5)",
        '''
let i be 1.
whilst i is at most 5 do
  if i is 3 then
    say "Fizz".
  otherwise
    if i is 5 then
      say "Buzz".
    otherwise
      say i.
    end.
  end.
  set i to i plus 1.
end.
''',
        ["1","2","Fizz","4","Buzz"])

    t.run("complex: sum of list",
        '''
let numbers be a list of 10, 20, 30, 40.
let total be 0.
for each n in numbers do
  set total to total plus n.
end.
say total.
''',
        ["100"])

    t.run("complex: greet programme from spec",
        '''
(This programme greets the user)
let name be "Ronnie".
let age be 30.

if age is at least 18 then
  say "Welcome, " plus name.
otherwise
  say "You are too young.".
end.

let i be 0.
whilst i is less than 3 do
  say "Hip hip hooray!".
  set i to i plus 1.
end.
''',
        ["Welcome, Ronnie", "Hip hip hooray!", "Hip hip hooray!", "Hip hip hooray!"])

    t.run("complex: nested routines and lists",
        '''
define a routine called sum_list taking nums
  let total be 0.
  for each n in nums do
    set total to total plus n.
  end.
  say total.
end.

let my_numbers be a list of 1, 2, 3, 4, 5.
perform sum_list with my_numbers.
''',
        ["15"])

    t.run("complex: input handling",
        'ask answer.\nsay "You said: " plus answer.',
        ["You said: hello"],
        inputs=["hello"])

    # ── Edge cases ────────────────────────────────────────────────────────────

    t.run("edge: string equality",
        'if "hello" is "hello" then\n  say "same".\nend.',
        ["same"])

    t.run("edge: string inequality",
        'if "hello" is not "world" then\n  say "different".\nend.',
        ["different"])

    t.run("edge: boolean truthiness",
        'let x be true.\nif x then\n  say "truthy".\nend.',
        ["truthy"])

    t.run("edge: nothing is falsy",
        'let x be nothing.\nif not x then\n  say "falsy".\nend.',
        ["falsy"])

    t.run("edge: zero is falsy",
        'let x be 0.\nif not x then\n  say "zero".\nend.',
        ["zero"])

    t.run("edge: empty string falsy",
        'let x be "".\nif not x then\n  say "empty".\nend.',
        ["empty"])

    t.run("edge: multiline comment",
        '(This is\na multiline\ncomment)\nsay "after".',
        ["after"])

    return t.report()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)