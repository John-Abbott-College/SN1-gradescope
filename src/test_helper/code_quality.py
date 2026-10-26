import ast
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
                    f"Nested function '{node.name}' is not allowed.",
                    _get_line(tree, node)
                )
            self.func_depth += 1
            self.generic_visit(node)
            self.func_depth -= 1

    NestedVisitor().visit(tree)

# ---------------------------------------------------------
# Warning/Error on "== True" or "== False"
# ---------------------------------------------------------
def check_no_literal_comparisons(tree: ast.AST, filename: str) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(comparator, ast.Constant):
                    if comparator.value in (True, False):
                        raise CodeQualityError(
                            filename, node.lineno,
                            "Comparison to True/False literal is restricted.",
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
# Parameter value is overwritten inside a function
# ---------------------------------------------------------
def check_no_parameter_overwrites(tree: ast.AST, filename: str) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            param_names = {arg.arg for arg in node.args.args}
            # Check statements in the function body for immediate/unconditional overwrites
            for stmt in node.body:
                for subnode in ast.walk(stmt):
                    if isinstance(subnode, ast.Assign):
                        for target in subnode.targets:
                            if isinstance(target, ast.Name) and target.id in param_names:
                                raise CodeQualityError(
                                    filename, subnode.lineno,
                                    f"Parameter '{target.id}' is overwritten inside function '{node.name}'.",
                                    _get_line(tree, subnode)
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
            
# ---------------------------------------------------------
# Runner list for unit tests
# ---------------------------------------------------------
DEFAULT_QUALITY_CHECKS = [
    check_naming_conventions,
    check_variable_length,
    check_no_nested_functions,
    check_no_literal_comparisons,
    check_no_tuples,
    check_no_dictionaries,
    check_no_lists,
    check_no_list_comprehensions,
    check_no_parameter_overwrites,
    check_no_function_assignments,
    check_no_classes,
]
