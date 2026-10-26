import ast
import inspect
import re
from types import FunctionType

def check_naming_in(test_case, method: FunctionType, min_chars: int = None, verbose: bool = True):
    """Helper to inspect parameter and variable names of a given function using AST."""
    source = inspect.getsource(method)
    tree = ast.parse(source)

    # Regex allowing either snake_case OR ALL_CAPS constants
    naming_regex = re.compile(r"^([a-z_][a-z0-9_]*|[A-Z_][A-Z0-9_]*)$")

    names_to_check = set()
    loop_variable_names = set()

    for node in ast.walk(tree):
        # 1. Collect loop variable names from 'for' and 'async for' loops
        if isinstance(node, (ast.For, ast.AsyncFor)):
            for loop_var in ast.walk(node.target):
                if isinstance(loop_var, ast.Name):
                    loop_variable_names.add(loop_var.id)

        # 2. Collect parameter names
        if isinstance(node, ast.arg):
            names_to_check.add(node.arg)

        # 3. Collect local variable names (assignments, loop variables, etc.)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names_to_check.add(node.id)

    # Ignore private double-underscore built-ins like '__class__' if generated
    names_to_check = {n for n in names_to_check if not n.startswith("__")}

    # Validate each collected name
    for name in names_to_check:
        is_loop_var = name in loop_variable_names

        # Allow single/double character names or '_' specifically for loop variables
        if is_loop_var and (name == "_" or len(name) <= 2):
            continue

        # Check standard length constraint (>= 3 chars)
        if min_chars is not None and (len(name) < min_chars):
            test_case.fail(
                f"❌ Function '{method.__name__}' uses name '{name}' which is shorter than 3 characters."
            )

        # Check naming convention constraint (snake_case or ALL_CAPS)
        if not naming_regex.match(name):
            test_case.fail(
                f"❌ Function '{method.__name__}' uses name '{name}' which is not in snake_case or ALL_CAPS."
            )

    if verbose:
        print(f"✅ No naming problems in {method.__name__}()")