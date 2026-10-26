"""
Author: Youmna
Description: Helper functions used for unit testing student assignments.
"""
import ast
import inspect
import typing
from inspect import Signature
from modulefinder import Module
from os import PathLike
from types import ModuleType
from typing import Callable

import re


def normalize(text: str, handle_whitespaces=True, handle_case_sensitive=True) -> str:
    """Inner function to address whitespaces and empty lines. Original idea: Claude AI"""
    normalized_text = text

    if handle_whitespaces:
        normalized_text = re.sub(r'\s+', '', normalized_text).strip()
    normalized_text = normalized_text.replace(':', '')
    if handle_case_sensitive:
        normalized_text = normalized_text.lower()
    return normalized_text

def get_inner_func(student_code: ModuleType) -> dict[str,list[str]]:
    """Return a dictionary mapping each top-level function to a list of its inner function names."""
    source = inspect.getsource(student_code)
    nodes = ast.walk(ast.parse(source))

    func_nodes = [node for node in nodes if isinstance(node, ast.FunctionDef)]

    inner_func_dict = {}
    for outer_func in func_nodes:
        inner_func_dict[outer_func.name] = \
            [inner_func.name for inner_func in ast.walk(outer_func)
             if isinstance(inner_func, ast.FunctionDef) and inner_func.name != outer_func.name]


    return inner_func_dict

def returns_bool_expression(function:Callable):
    """This function checks for returns of comparison, or boolean expressions. It
    excludes bool constants.
    ex: This function would return True
    def is_positive(num):
        return num > 0

    ex: This function would return False
    def is_positive(num):
        if num > 0:
            return True
        else:
            return False
    """
    return_nodes = [node for node in ast.walk(ast.parse(inspect.getsource(function))) if isinstance(node, ast.Return)]
    is_bool_expression =[]
    for return_node in return_nodes:
        is_bool_expression += [isinstance(node, (ast.BoolOp, ast.Compare, ast.Or, ast.And))
                               for node in ast.walk(return_node)]

    return any(is_bool_expression)

def uses_try_except(func:Callable)->bool:
    """Detects if a function uses try...except blocks.
    source: Google AI overview"""
    source = inspect.getsource(func)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            return True
    return False

def find_exceptions(func:Callable)->list:
    """This function was created by Google AI Overview"""
    # Get the source code of the function
    source = inspect.getsource(func)
    tree = ast.parse(source)

    exceptions = []
    # Walk through every node in the AST
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            # Check the exception type being raised
            if isinstance(node.exc, ast.Call):
                exceptions.append(node.exc.func.id)
            elif isinstance(node.exc, ast.Name):
                exceptions.append(node.exc.id)

    return exceptions

def raises_exceptions(function:Callable)->bool:
    """Checks if a function raises exceptions. Useful to detect AI-generated code"""
    return len(find_exceptions(function)) !=0

def uses_loop(function:Callable)->bool:
    """Check if the given function contains a loop (for or while)."""
    nodes = ast.walk(ast.parse(inspect.getsource(function)))
    return any(isinstance(node, (ast.For, ast.While)) for node in nodes)

def uses_condition(function:Callable)->bool:
    """Check if the given function contains an if statement."""
    nodes = ast.walk(ast.parse(inspect.getsource(function)))
    return any(isinstance(node,ast.If) for node in nodes)

def get_signature(function:Callable)->Signature:
    """Return the signature (parameters) of the given function."""
    return inspect.signature(function)

def contains_func(student_code :ModuleType, func_name:str )->bool:
    """Check if the module contains a function with the specified name."""
    return hasattr(student_code, func_name)

def get_func_calls(caller:Callable)->list[str]:
    """Return a list of function names called within the given function."""
    nodes = ast.walk(ast.parse(inspect.getsource(caller)))
    func_calls = (call for call in nodes if isinstance(call,ast.Call))
    call_names = [call.func.id for call in func_calls if isinstance(call.func,ast.Name)]
    return call_names

def call_func_with_redirect(function:Callable, params:tuple=())->str:
    """
    Calls a function while redirecting the stdout stream.
    """
    from contextlib import redirect_stdout
    import io

    # output buffer
    f = io.StringIO()

    with redirect_stdout(f):
        function(*params)
    out = f.getvalue()

    return out

def do_nothing_func():
    """Return a lambda that ignores all arguments and does nothing. Useful for replacing
     functions that will require user prompt. Useful for unattended run of the tests"""
    return lambda *args : None

def modify_globals(student_code: PathLike, globals_dict: dict)->list[str]:
    """
    Modifies the global variables in a python file and saves it with the new values. If it can't find
    the variable, it ignores it (fails silently).
    The injected values should be provided in a dictionary along with the variable name:
    ex: {variable_name : injected_value}
    """

    def is_definition(line: str, var_name: str) -> bool:
        """
        Check if `line` is a definition assignment to `var_name`, using AST parsing.
        Handles simple, chained, tuple-unpacking.
        """
        try:
            tree = ast.parse(line.strip())
        except SyntaxError:
            return False

        if len(tree.body) != 1:
            return False

        node = tree.body[0]

        if isinstance(node, ast.Assign):
            targets = node.targets
        else:
            return False

        for target in targets:
            for name_node in ast.walk(target):
                if isinstance(name_node, ast.Name) and name_node.id == var_name:
                    return True
        return False

    modified_code = []
    with open(student_code, 'r') as file:
        code = file.readlines()

        for line in code:

            if line.strip() is None:
                continue
            for var_name, value in globals_dict.items():
                if is_definition(line,var_name):
                    line = line.strip()
                    broken_down = line.replace(' ', '').split('=')
                    # replace the last part of the assignment with the value:
                    broken_down[-1] = f'"{value}"' if isinstance(value, str) else str(value)
                    line = " = ".join(broken_down)
                    line += "\n" #Put the end line char back
                    # stop looking for other vars
                    break


            modified_code.append(line)

    with open(student_code, 'w') as file:
        file.write("".join(modified_code))

    return modified_code

def run_with(student_code: PathLike, globals_dict: dict):
    """Less than perfect way to modify global variables in a student script before importing.
    This is useful for assignments that aren't using functions.
    The injected values should be provided in a dictionary along with the variable name:
    ex: {variable_name : injected_value}
    """
    import subprocess
    import platform

    # Modify code
    if globals_dict:
        modify_globals(student_code, globals_dict)


    python_command = "python" if platform.system() == "Windows" else "python3"

    output_stream = subprocess.run(
        [python_command, student_code],
        capture_output=True,
        text=True,
        check=True)

    return output_stream


def stdout_match(
        student_code:PathLike,
        globals_dict:dict,
        expected_output: str ="",
        handle_whitespaces:bool =True,
        handle_case_sensitive:bool = True )->bool:
    """Less than perfect way to validate the output stream of a file after running it with updated
    global vars.
    Useful for assignment without functions.

    """
    output_stream = run_with(student_code, globals_dict)

    is_matching = normalize(output_stream.stdout) == normalize(expected_output)
    return is_matching

def extract_numbers(stream:str)->list[str]:
    """
    Extract all the numbers from the output stream and returns a list of the strings storing those numbers.
    Useful for when validating format precision, or calculations accuracy without casting into an int or float.
    Ex: If the output stream contains:
    Age : 26
    Height: 5.5

    Returns: ["26","5.5"]
    """
    import re
    pattern = r"-?\d+(?:\.\d+)?"  # -> Digit(s), followed optionally by a decimal point and more digits.

    return re.findall(pattern, stream)

def global_dict_tostring(global_dict:dict)->str:
    message = "Tested with: \n"
    for name,value in global_dict.items():
        message += f"{name} = {value}\n"

    return message


if __name__ =="__main__":
    from pathlib import Path
    run_with(Path('test.py'),{'x':3})