#!/usr/bin/env python3
import sys
import os
import traceback

from lexer import Lexer, LexError
from parser import Parser, ParseError
from interpreter import Interpreter, RuntimeError_

BANNER = r"""
  ██████╗     ███╗   ███╗    ███╗   ███╗
 ██╔════╝     ████╗ ████║    ████╗ ████║
 ██║  ███╗    ██╔████╔██║    ██╔████╔██║
 ██║   ██║    ██║╚██╔╝██║    ██║╚██╔╝██║
 ╚██████╔╝    ██║ ╚═╝ ██║    ██║ ╚═╝ ██║
  ╚═════╝     ╚═╝     ╚═╝    ╚═╝     ╚═╝

  G-- (Grammar--) Interpreter  v1.0
  A programming language that reads like English prose.
  Type 'help.' for guidance, or 'quit.' to leave.
"""

HELP_TEXT = """
G-- Quick Reference
═══════════════════

  Variables:    let name be "Ronnie".
                set name to "Ron".

  Output:       say "Hello, world!".
  Input:        ask name.

  Arithmetic:   3 plus 4  |  10 minus 2  |  3 times 4  |  10 divided by 2

  Comparison:   x is 5  |  x is not 5  |  x is greater than 3
                x is less than 10  |  x is at least 0  |  x is at most 100

  Boolean:      x is 1 and y is 2  |  x is 1 or y is 2  |  not x is 1

  Conditions:   if age is at least 18 then
                  say "Welcome!".
                otherwise
                  say "Too young.".
                end.

  Whilst loop:  whilst x is less than 10 do
                  set x to x plus 1.
                end.

  Repeat:       repeat 5 times
                  say "Again!".
                end.

  For each:     for each colour in colours do
                  say colour.
                end.

  Lists:        let colours be a list of "red", "blue", "green".
                add "yellow" to colours.
                remove "red" from colours.
                say the first item of colours.
                say the last item of colours.
                say the length of colours.

  Routines:     define a routine called greet taking name
                  say "Hello, " plus name.
                end.
                perform greet with "Ronnie".

  Comments:     (This is a comment — like an aside)

  Built-ins:    perform shout with "hello".    → HELLO
                perform whisper with "HELLO".  → hello
                perform absolute with -5.      → 5
                perform round with 3.7.        → 4
"""

def run_source(source: str, interpreter: Interpreter = None) -> Interpreter:
    if interpreter is None:
        interpreter = Interpreter()

    try:
        lexer = Lexer(source)
        tokens = lexer.tokenise()
    except LexError as e:
        print(f"Lexical error (line {e.line}, col {e.col}): {e}")
        return interpreter
    
    try:
        parser = Parser(tokens)
        programme = parser.parse()
    except ParseError as e:
        if e.line:
            print(f"Syntax error (line {e.line}, col {e.col}): {e}")
        else:
            print(f"Syntax error: {e}")
        return interpreter
    
    try:
        interpreter.run(programme)
    except RuntimeError_ as e:
        print(f"Runtime error: {e}")
    except KeyboardInterrupt:
        print("\nInterrupted.")

    return interpreter

def run_file(path: str):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"I'm afraid I cannot find the file '{path}'.")
        return
    except OSError as e:
        print(f"I'm afraid I could not read '{path}': {e}")
        return
    
    run_source(source)

def repl():
    print(BANNER)
    interpreter = Interpreter()

    # Buffer for multi-line input
    buffer = []
    continuation_keywords = {'if', 'whilst', 'repeat', 'for', 'define'}
    open_blocks = 0

    while True:
        try:
            if open_blocks > 0:
                prompt = " " * open_blocks + "... "
            else:
                prompt = "G-- >"

            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nFarewell!")
            break

        stripped = line.strip()

        # REPL commands
        if stripped.lower() in ('quit.', 'quit', 'exit.', 'exit', 'bye.', 'bye'):
            print("Farewell! It was a pleasure.")
            break

        if stripped.lower() in ('help.', 'help'):
            print(HELP_TEXT)
            continue

        if stripped.lower() in ('clear.', 'clear'):
            os.system('clear' if os.name == 'posix' else 'cls')
            continue

        if not stripped:
            if open_blocks == 0:
                continue
            buffer.append(line)
            continue

        buffer.append(line)

        #Track block depth
        first_word = stripped.split()[0].lower() if stripped.split() else ''
        if first_word in continuation_keywords:
            open_blocks += 1
        if stripped.lower().startswith('end.'):
            open_blocks = max(0, open_blocks - 1)

        # Execute when have a complete statement (block depth returns to 0)
        if open_blocks == 0:
            source = ' '.join(buffer)
            buffer = []

            try:
                lexer = Lexer(source)
                tokens = lexer.tokenise()
                parser = Parser(tokens)
                programme = parser.parse()
                interpreter.run(programme)
            except LexError as e:
                print(f"  Lexical error: {e}")
                buffer = []
            except ParseError as e:
                print(f"  Syntax error: {e}")
                buffer = []
            except RuntimeError_ as e:
                print(f"  {e}")
                buffer = []
            except KeyboardInterrupt:
                print("\n  Interrupted.")
                buffer = []
                open_blocks = 0

def main():
    if len(sys.argv) == 1:
        repl()
    elif len(sys.argv) == 2:
        if sys.argv[1] in ('-h', '--help'):
            print(HELP_TEXT)
        else:
            run_file(sys.argv[1])
    else:
        print("Usage: python gmm.py [file.gmm]")
        sys.exit(1)

if __name__ == '__main__':
    main()