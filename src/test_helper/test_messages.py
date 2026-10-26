"""
Author: Youmna
Description: File used to output useful messages to students
"""

generic_messages = {
    'files_submitted': "✅ All required files submitted!",
    'file_not_found': "❌ File not found, make sure it wasn't renamed!",
    'files_missing':"🔍 Make sure the files were not renamed, and re-submit all the required files again!",
    'success_no_crash': "✅ Correct: Program runs without crashing!",
    'success_calculation': "✅ Correct calculations",
    'success_format': "✅ Correct: Program runs and produces the required output using the provided variables.",
    'params_error':"❌ The function isn't defined with the correct parameter names or their order was inverted",
    'return_error': "❌ The function isn't returning the correct data type",
    'function_no_return':"❌ The function isn't returning when it should be",
    'calculation_error': "❌ Calculation Error: there's a mistake in the calculation of a value",
    'logic_error':"❌ Logic mistake, one or more conditions aren't correct",
    'missing_statement':"❌ This function is missing a critical statement (loop or condition)",
    'format_error': "❌ Error: Function doesn't produce the expected output.",
    'runtime_error': "❌ Error: Program crashes before producing an output",
    'general_error': "❌ An unknown error occurred. Ask the teacher for assistance"
}

def inner_func_message(function_name:str, inner_list:list[str])->str:
    msg = ', '.join(i + "()" for i in inner_list)

    return f"""Oops! It looks like you've defined the function(s) {msg} inside the function {function_name}().\n
    Remember to define your functions at the same level of indentation to ensure they can be accessible to other \n
    python scripts"""

def not_found_message(func_name, file):
    return f"{func_name} is not defined in {file}"

def actual_not_expected(func_name, params,actual, expected):
    return f"Tried {func_name}{params}. \nExpected {expected}. \nGot: {actual}"
