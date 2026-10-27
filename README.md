# test_helper

Helpers for writing Gradescope autograder tests for student Python code.

The main entry point is `JACTestCase` (in `test_helper/jactestcase.py`), a subclass of `unittest.TestCase` that adds assertions for checking *how* student code is written, not just what it outputs.

## Installation

Add this line to `requirements.txt`, replacing `<tag>` with a released tag:

```
test_helper @ git+https://github.com/John-Abbott-College/SN1-gradescope.git@<tag>
```

For local development against a clone, use an editable install:

```
pip install -e /path/to/SN1-gradescope
```

## Quick start

```python
import unittest

from test_helper.jactestcase import JACTestCase
import student_submission


class TestAssignment(JACTestCase):
    def test_uses_helper(self):
        self.assertFunctionCalls(student_submission.main, "compute_total")

    def test_style(self):
        self.assertCodeStyle(student_submission)

    def test_quality(self):
        self.assertCodeQuality(student_submission, "student_submission.py")


if __name__ == "__main__":
    unittest.main()
```

Because `JACTestCase` extends `unittest.TestCase`, all the standard `assertEqual`, `assertTrue`, etc. methods are available alongside the ones below.

## API reference

| Method | Checks that... |
|---|---|
| [`assertFunctionCalls`](#assertfunctioncallsfunction-other_function) | a function calls another function |
| [`assertFunctionDoesNotCall`](#assertfunctiondoesnotcallfunction-other_function) | a function does *not* call another function |
| [`assertNamingConventions`](#assertnamingconventionsfunction-min_chars--none) | names inside a function follow naming conventions |
| [`assertCodeStyle`](#assertcodestylestudent_code) | pylint reports no issues for the student's file |
| [`assertCodeQuality`](#assertcodequalitystudent_code-filename-rules) | the student's code passes a set of AST-based quality rules |
| [`assertFunctionReturns`](#assertfunctionreturnsstudent_function-filename) | a function that returns a value does so on every code path |

---

### `assertFunctionCalls(function, other_function)`

Asserts that `function` calls the function named `other_function`.

| Parameter | Type | Description |
|---|---|---|
| `function` | `FunctionType` | The student's function to inspect. |
| `other_function` | `str` | The *name* of the function that must be called. |

Delegates to `usage.assert_function_dependency` and always runs in verbose mode.

```python
self.assertFunctionCalls(student_submission.main, "compute_total")
```

---

### `assertFunctionDoesNotCall(function, other_function)`

The opposite of `assertFunctionCalls`: asserts that `function` does **not** call the function named `other_function`. Useful for forbidding a shortcut, for example requiring students to implement something themselves instead of calling a built-in.

| Parameter | Type | Description |
|---|---|---|
| `function` | `FunctionType` | The student's function to inspect. |
| `other_function` | `str` | The *name* of the function that must not be called. |

```python
self.assertFunctionDoesNotCall(student_submission.my_max, "max")
```

---

### `assertNamingConventions(function, min_chars=None)`

Checks the naming conventions used inside `function` by delegating to `naming.check_naming_in`, in verbose mode.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `function` | `FunctionType` | | The student's function to inspect. |
| `min_chars` | `int` | `None` | Minimum number of characters required in names. When `None`, no minimum length is passed to the checker. |

```python
self.assertNamingConventions(student_submission.main, min_chars=3)
```

---

### `assertCodeStyle(student_code)`

Runs **pylint** on the source file that contains `student_code` and fails the test if pylint exits with a non-zero return code. The failure message includes pylint's full output.

| Parameter | Type | Description |
|---|---|---|
| `student_code` | module, class, or function | Anything `inspect.getfile` accepts. The entire file containing it is linted, not just the object itself. |

```python
self.assertCodeStyle(student_submission)
```

---

### `assertCodeQuality(student_code, filename, rules)`

Parses the student's source into an AST and runs each rule against it. Every rule that fails is reported, and the test then fails once with all the messages listed together, so students see all the problems at the same time.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `student_code` | module or function | | The object whose source is analysed (via `inspect.getsource`). |
| `filename` | `str` | | The file name, used when parsing and in error messages. |
| `rules` | `list[Callable[[ast.AST, str], None]]` | `code_quality.DEFAULT_QUALITY_CHECKS` | The checks to run. |

Each rule is a function that takes `(tree, filename)` and raises `code_quality.CodeQualityError` when it finds a problem. Only `CodeQualityError` is collected; any other exception propagates normally. Each rule stops at the first violation it finds, so a single rule reports at most one problem per run. See [Quality checks](#quality-checks) for the built-in rules and which ones run by default.

```python
# Run the default checks
self.assertCodeQuality(student_submission, "student_submission.py")

# Run only specific checks
self.assertCodeQuality(
    student_submission,
    "student_submission.py",
    rules=[code_quality.check_no_literal_bool_comparisons],
)

# Run the defaults plus an extra check
self.assertCodeQuality(
    student_submission,
    "student_submission.py",
    rules=[*code_quality.DEFAULT_QUALITY_CHECKS, my_custom_check],
)
```

---

### `assertFunctionReturns(student_function, filename)`

Asserts that if the student's function returns a value on some paths, it returns on all of them, using `code_quality.check_return_paths`. Void functions pass. Fails the test with the checker's message if it finds a problem.

| Parameter | Type | Description |
|---|---|---|
| `student_function` | function | The function whose source is analysed. |
| `filename` | `str` | The file name, used when parsing and in error messages. |

```python
self.assertFunctionReturns(student_submission.get_grade, "student_submission.py")
```

---

## Quality checks

All checks live in `test_helper/code_quality.py`. Each one takes `(tree, filename)` and raises `CodeQualityError` on the first violation it finds. The list `code_quality.DEFAULT_QUALITY_CHECKS` holds the checks that `assertCodeQuality` runs when you don't pass `rules`. `check_return_paths` is also what `assertFunctionReturns` runs on its own.

### Run by default

| Check | Description |
|---|---|
| `check_naming_conventions` | Requires function names and variable names to be `snake_case` or `ALL_CAPS`. It looks at every name that appears in the code, including names being read, not only names being assigned. |
| `check_variable_length` | Requires assigned variable names to be at least 3 characters long. The names `i`, `j`, `k`, `ex` and `_` are exempt, as is any name used as a `for` loop variable anywhere in the file. |
| `check_no_nested_functions` | Disallows defining a function inside another function. |
| `check_no_literal_bool_comparisons` | Disallows comparing to `True` or `False` with `==`, `!=`, `is` or `is not`, on either side and inside chained comparisons. Students should write `if flag:` or `if not flag:` instead. Comparisons such as `== 0` are not flagged. |
| `check_no_tuples` | Disallows any tuple, including unpacking (`a, b = ...`) and returning several values (`return a, b`). |
| `check_no_dictionaries` | Disallows dictionary literals (`{...}`) and dictionary comprehensions. Calls to `dict()` are not detected. |
| `check_no_list_comprehensions` | Disallows list comprehensions. Plain list literals are still allowed by this check. |
| `check_no_function_assignments` | Flags any assignment whose right-hand side is a single bare name, such as `fn = my_function`, which is how a function gets assigned instead of called. It can't tell functions from variables, so `b = a` is flagged too. |
| `check_no_classes` | Disallows class definitions. |
| `check_no_function_name_shadowing` | Disallows reusing a function's own name for a variable, parameter, or other name bound inside that function. |
| `check_no_builtin_shadowing` | Disallows binding a name that matches a Python built-in (such as `list`, `sum`, `max`, `input` or `id`) through assignment, a loop variable, a parameter, a `def` or `class`, an import alias, or `except ... as`. Dunder names like `__name__` are ignored. |
| `check_no_overwritten_parameters` | Flags a parameter that is assigned a new value before its original value is used, as in `def f(x): x = 5`. Only the top-level statements of the function body are examined, so assignments inside an `if` or a loop are not flagged. |
| `check_return_paths` | For any function that returns a value on at least one path, requires that every path ends in a `return` or `raise`. It understands `if`/`else`, loops, `try`, `with` and `match`; a loop that may run zero times doesn't count as returning unless its `else` clause does. Functions with no `return <value>` (bare `return` and `return None` don't count) are treated as void and never flagged. |

### Available but not run by default

To use these, pass them in `rules` (see the [`assertCodeQuality`](#assertcodequalitystudent_code-filename-rules) examples).

| Check | Description |
|---|---|
| `check_no_lists` | Disallows list literals (`[...]`). It does not flag `list()` calls or list comprehensions. |

## Writing custom quality rules

A rule for `assertCodeQuality` is any function with this shape:

```python
import ast
from test_helper import code_quality


def check_no_print(tree: ast.AST, filename: str) -> None:
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            raise code_quality.CodeQualityError(
                filename, node.lineno,
                "print() is not allowed here.",
                "",
            )
```
