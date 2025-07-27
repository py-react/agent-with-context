from langchain_core.tools import tool

@tool
def calculate(expression: str, precision: int = 2) -> str:
    """Perform mathematical calculations and evaluate expressions. Use this when users ask for calculations, math problems, arithmetic, or need to compute values. Examples: 'Calculate 2+2', 'What is 15 * 7?', 'Solve 100 / 4', 'Add 25 and 75', 'Calculate the sum of 10 and 20'."""
    try:
        # Simple and safe evaluation (only basic math operations)
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in expression):
            return "Error: Only basic mathematical operations (+, -, *, /, parentheses) and numbers are allowed"
        
        # Evaluate the expression
        result = eval(expression)
        
        # Format the result
        if isinstance(result, (int, float)):
            if isinstance(result, int):
                formatted_result = f"Result: {result}"
            else:
                formatted_result = f"Result: {result:.{precision}f}"
        else:
            formatted_result = f"Result: {result}"
        
        return formatted_result
            
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error: {str(e)}" 