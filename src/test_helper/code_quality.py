import ast
import builtins
import re

class CodeQualityError(Exception):
    """Custom exception for code quality infractions."""
    def __init__(self, filename: str, line_number: int, message: str, offending_text: str = ""):
        self.filename = filename
        self.line_number = line_number
        self.offending_text = offending_text
        super().__init__(
            f"CodeQualityError in {filename} at line {line_number}: {message}"
            f"{f' (Offending: {offending_text})' if offending_text else ''}"
        )

# Helper regex for Rule 1
NAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$|^[A-Z_][A-Z0-9_]*$")
ALLOWED_SHORT_NAMES = {'i', 'j', 'k', 'ex', '_'}

def _get_line(tree, node) -> str:
    """Safely extract the source line if available."""
    try:
        return ast.get_source_segment(tree, node) or ""
    except Exception:
        return ""

# ---------------------------------------------------------
# snake_case or ALL_CAPS for variables & functions
# ---------------------------------------------------------
def check_naming_conventions(tree: ast.AST, filename: str) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Name)):
            name = getattr(node, 'id', getattr(node, 'name', None))
            if name and not NAME_PATTERN.match(name):
                raise CodeQualityError(
                    filename, node.lineno,
                    f"Name '{name}' must use snake_case or ALL_CAPS.",
                    _get_line(tree, node)
                )

# ---------------------------------------------------------
# Variable names must be >= 3 chars (unless loop var)
# ---------------------------------------------------------
def check_variable_length(tree: ast.AST, filename: str) -> None:
    # Track loop variables to exempt them
    loop_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)):
            for target in ast.walk(node.target):
                if isinstance(target, ast.Name):
                    loop_vars.add(target.id)

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            name = node.id
            if len(name) < 3 and name not in ALLOWED_SHORT_NAMES and name not in loop_vars:
                raise CodeQualityError(
                    filename, node.lineno,
                    f"Variable name '{name}' is too short (must be at least 3 characters).",
                    _get_line(tree, node)
                )

# ---------------------------------------------------------
# No defining functions inside other functions
# ---------------------------------------------------------
def check_no_nested_functions(tree: ast.AST, filename: str) -> None:
    class NestedVisitor(ast.NodeVisitor):
        def __init__(self):
            self.func_depth = 0

        def visit_FunctionDef(self, node):
            self._check_nested(node)
        def visit_AsyncFunctionDef(self, node):
            self._check_nested(node)

        def _check_nested(self, node):
            if self.func_depth > 0:
                raise CodeQualityError(
                    filename, node.lineno,
                    f"Nested functions are not allowed. Move {node.name}() so that it is not inside another function.",
                    _get_line(tree, node)
                )
            self.func_depth += 1
            self.generic_visit(node)
            self.func_depth -= 1

    NestedVisitor().visit(tree)


def _is_bool_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, bool)


def check_no_literal_bool_comparisons(tree: ast.AST, filename: str) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue

        # Pair each operator with the operands on either side of it,
        # which also handles chained comparisons like a == b == True
        operands = [node.left, *node.comparators]
        for op, left, right in zip(node.ops, operands, operands[1:]):
            if isinstance(op, (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)) and (
                _is_bool_literal(left) or _is_bool_literal(right)
            ):
                raise CodeQualityError(
                    filename, node.lineno,
                    "Don't explicitly compare with True or False",
                    _get_line(tree, node)
                )

# ---------------------------------------------------------
# Do not allow tuples
# ---------------------------------------------------------
def check_no_tuples(tree: ast.AST, filename: str) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple):
            raise CodeQualityError(
                filename, node.lineno,
                "Use of tuples is not allowed.",
                _get_line(tree, node)
            )

# ---------------------------------------------------------
# Do not allow dictionaries
# ---------------------------------------------------------
def check_no_dictionaries(tree: ast.AST, filename: str) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Dict, ast.DictComp)):
            raise CodeQualityError(
                filename, node.lineno,
                "Use of dictionaries is not allowed.",
                _get_line(tree, node)
            )

# ---------------------------------------------------------
# Do not allow lists
# ---------------------------------------------------------
def check_no_lists(tree: ast.AST, filename: str) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.List):
            raise CodeQualityError(
                filename, node.lineno,
                "Use of lists is not allowed.",
                _get_line(tree, node)
            )

# ---------------------------------------------------------
# Do not allow list comprehensions
# ---------------------------------------------------------
def check_no_list_comprehensions(tree: ast.AST, filename: str) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ListComp):
            raise CodeQualityError(
                filename, node.lineno,
                "Use of list comprehensions is not allowed.",
                _get_line(tree, node)
            )

# ---------------------------------------------------------
# Function assigned to a variable (instead of calling)
# ---------------------------------------------------------
def check_no_function_assignments(tree: ast.AST, filename: str) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            # If RHS is a bare name (and not a Call), it might be a function reference assignment
            if isinstance(node.value, ast.Name):
                raise CodeQualityError(
                    filename, node.lineno,
                    "Assigning a function reference to a variable instead of calling it is not allowed.",
                    _get_line(tree, node)
                )

# ---------------------------------------------------------
# Do not allow definition of classes
# ---------------------------------------------------------
def check_no_classes(tree: ast.AST, filename: str) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            raise CodeQualityError(
                filename, node.lineno,
                f"Class definition '{node.name}' is not allowed.",
                _get_line(tree, node)
            )


# ---------------------------------------------------------
# All paths in a function must return
# ---------------------------------------------------------

def _has_guaranteed_return(node: ast.AST) -> bool:
    """Helper to recursively check if a statement or block guarantees a return or raise."""
    if isinstance(node, ast.Return):
        return True
    elif isinstance(node, ast.Raise):
        return True
    elif isinstance(node, ast.If):
        has_else = len(node.orelse) > 0
        if not has_else:
            return False
        
        if_returns = any(_has_guaranteed_return(stmt) for stmt in node.body)
        else_returns = any(_has_guaranteed_return(stmt) for stmt in node.orelse)
        return if_returns and else_returns
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
        if not node.body:
            return False
        return _has_guaranteed_return(node.body[-1])
    
    return False


def check_return_paths(tree: ast.AST, filename: str) -> None:
    """Check function matching the uniform (tree, filename) signature."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # You can optionally skip empty functions (like 'pass') or initializers if needed
            if not _has_guaranteed_return(node):
                raise CodeQualityError(
                    filename=filename,
                    line_number=node.lineno,
                    offending_text=node.name,
                    message=f"Function '{node.name}' contains a code path that does not return a value."
                )


def _bound_name(node: ast.AST) -> str | None:
    """Return the name this node binds, or None if it doesn't bind one."""
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        return node.id
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.arg):
        return node.arg
    if isinstance(node, ast.alias):
        return node.asname or node.name.split(".")[0]
    if isinstance(node, ast.ExceptHandler):
        return node.name
    return None


# ---------------------------------------------------------
# Don't declare variables/params with the same name as the
# current function
# ---------------------------------------------------------

def check_no_function_name_shadowing(tree: ast.AST, filename: str) -> None:
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for node in ast.walk(func):
            if node is func:
                continue    # the def itself obviously binds its own name

            if _bound_name(node) == func.name:
                raise CodeQualityError(
                    filename, node.lineno,
                    f"'{func.name}' is the name of the enclosing function "
                    f"and shouldn't be reused for a variable or parameter.",
                    _get_line(tree, node)
                )


# ---------------------------------------------------------
# Don't declare variables/params with the same name as a
# built-in function
# ---------------------------------------------------------            

def check_no_builtin_shadowing(tree: ast.AST, filename: str) -> None:
    # Skip dunders like __name__ and __doc__, which students rarely touch
    _BUILTIN_NAMES = {name for name in dir(builtins) if not name.startswith("_")}

    for node in ast.walk(tree):
        name = _bound_name(node)

        if name in _BUILTIN_NAMES:
            raise CodeQualityError(
                filename, node.lineno,
                f"'{name}' shadows a built-in Python name.",
                _get_line(tree, node)
            )


def _reads_name(node: ast.AST, name: str) -> bool:
    return any(
        isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load)
        for n in ast.walk(node)
    )


def _stores_name(node: ast.AST, name: str) -> bool:
    return any(
        isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Store)
        for n in ast.walk(node)
    )

# ---------------------------------------------------------
# Don't modify a param's value before using it
# --------------------------------------------------------- 
def check_no_overwritten_parameters(tree: ast.AST, filename: str) -> None:
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        a = func.args
        params = {p.arg for p in a.posonlyargs + a.args + a.kwonlyargs}
        params -= {"self", "cls", "_"}

        for param in params:
            for stmt in func.body:
                # A plain assignment that doesn't use the parameter's own value
                if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and stmt.value is not None:
                    targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                    if (any(_stores_name(t, param) for t in targets)
                            and not _reads_name(stmt.value, param)):
                        raise CodeQualityError(
                            filename, stmt.lineno,
                            f"Parameter '{param}' is overwritten before its "
                            f"value is used. Use the value that was passed in.",
                            _get_line(tree, stmt)
                        )

                # Any other touch of the parameter means we can't say it was ignored
                if _reads_name(stmt, param) or _stores_name(stmt, param):
                    break


# ---------------------------------------------------------
# Runner list for unit tests
# ---------------------------------------------------------
DEFAULT_QUALITY_CHECKS = [
    check_naming_conventions,
    check_variable_length,
    check_no_nested_functions,
    check_no_literal_bool_comparisons,
    check_no_tuples,
    check_no_dictionaries,
    check_no_list_comprehensions,
    check_no_function_assignments,
    check_no_classes,
    check_no_function_name_shadowing,
    check_no_builtin_shadowing,
    check_no_overwritten_parameters
]
