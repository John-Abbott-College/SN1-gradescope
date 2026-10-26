import ast
import inspect
import unittest

from collections.abc import Callable
from types import FunctionType

from . import usage
from . import naming
from . import linting
from . import code_quality


class JACTestCase(unittest.TestCase):
    def assertFunctionCalls(self, function: FunctionType, other_function: str):
        usage.assert_function_dependency(self, function, True, other_function, verbose=True)

    def assertFunctionDoesNotCall(self, function: FunctionType, other_function: str):
        usage.assert_function_dependency(self, function, False, other_function, verbose=True)

    def assertNamingConventions(self, function: FunctionType, min_chars: int = None):
        naming.check_naming_in(self, function, min_chars, verbose=True)

    def assertCodeStyle(self, student_code):
        """
        Use this if you want to run pylint on the student code
        """
        source_file = inspect.getfile(student_code)
        returncode, output = linting.pylint(source_file)

        self.assertEqual(
            returncode,
            0,
            msg=f"❌ code style issues in {source_file}:\n{output}",
        )

    def assertCodeQuality(self, student_code, filename, rules: list[Callable[[ast.AST, str], None]] = code_quality.DEFAULT_QUALITY_CHECKS):
        source_code = inspect.getsource(student_code)
        tree = ast.parse(source_code, filename=filename)

        errors = []

        for check in rules:
            try:
                check(tree, filename)
            except code_quality.CodeQualityError as e:
                errors.append(f"❌ {e.args[0]}")

        if len(errors) > 0:
            self.fail(f"Code style errors:\n{"\n".join(errors)}")

    def assertFunctionReturns(self, student_function, filename):
        source_code = inspect.getsource(student_function)
        tree = ast.parse(source_code, filename=filename)

        try:
            code_quality.check_return_paths(tree, filename)
        except code_quality.CodeQualityError as e:
            self.fail(f"❌ {e.args[0]}")