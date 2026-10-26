import ast
import inspect


def get_method_name(node):
    """
    Helper to reconstruct strings like 'visualizer.plot_point' or 'plot_point'.
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{get_method_name(node.value)}.{node.attr}"
    
    return None


def assert_function_dependency(test_case, method, should_call, other_fn_name, verbose=False):
    """
    Checks whether a given function calls another function. Assertion fails
    depending on whether the function should or should not call said function.
    """
    source_code = inspect.getsource(method)
    tree = ast.parse(source_code)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_str = get_method_name(node.func)
            
            # Matches either full 'visualizer.plot_point' or just 'plot_point'
            if call_str == other_fn_name or (call_str and call_str.endswith(f".{other_fn_name}")):
                if should_call:
                    if verbose:
                        print(f"✅ {method.__name__}() calls {other_fn_name}()")    
                    return
                else:
                    test_case.fail(f"❌ {method.__name__}() should not be calling {other_fn_name}()")     

    if should_call:
        # if we got here then it means we missed calling something
        test_case.fail(f"❌ {method.__name__} is missing a call to {other_fn_name}()")
    elif verbose:
        # if we got here then all is good: we were not supposed to call and we didn't
        print(f"✅ {method.__name__}() does not call {other_fn_name}()")