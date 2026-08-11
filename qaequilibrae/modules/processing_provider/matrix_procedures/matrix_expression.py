"""Safe evaluation of the expressions typed into the matrix calculator.

The expression is user input, so it is parsed into an abstract syntax tree and walked node
by node rather than handed to ``eval``. Only the arithmetic, functions and attributes
documented for the tool are accepted; anything else raises MatrixExpressionError.
"""

import ast
import operator

import numpy as np


class MatrixExpressionError(Exception):
    """Raised when an expression uses something the matrix calculator does not support."""


def null_diag(matrix):
    """Returns a copy of *matrix* with its main diagonal zeroed out."""
    result = np.array(matrix, copy=True)
    np.fill_diagonal(result, 0)
    return result


FUNCTIONS = {
    "min": np.min,
    "max": np.max,
    "abs": np.absolute,
    "ln": np.log,
    "exp": np.exp,
    "power": np.power,
    "null_diag": null_diag,
}

ATTRIBUTES = ("T",)

BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def evaluate(expression, matrices):
    """Evaluates *expression* over *matrices*, a mapping of matrix name to NumPy array."""
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except (SyntaxError, ValueError) as error:
        raise MatrixExpressionError(f"Could not parse the expression: {error}") from error

    return _evaluate(tree.body, matrices)


def _evaluate(node, matrices):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise MatrixExpressionError(f"Only numbers can be used as constants, got {node.value!r}")
        return node.value

    if isinstance(node, ast.Name):
        if node.id not in matrices:
            raise MatrixExpressionError(f"Unknown matrix '{node.id}'")
        return matrices[node.id]

    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPS:
        return BINARY_OPS[type(node.op)](_evaluate(node.left, matrices), _evaluate(node.right, matrices))

    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return UNARY_OPS[type(node.op)](_evaluate(node.operand, matrices))

    if isinstance(node, ast.Attribute):
        if node.attr not in ATTRIBUTES:
            raise MatrixExpressionError(f"Unsupported attribute '.{node.attr}'")
        return getattr(_evaluate(node.value, matrices), node.attr)

    if isinstance(node, ast.Call):
        return _evaluate_call(node, matrices)

    raise MatrixExpressionError(f"Unsupported operation in the expression: {type(node).__name__}")


def _evaluate_call(node, matrices):
    if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
        name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "?")
        raise MatrixExpressionError(f"Unknown function '{name}'. Available: {', '.join(sorted(FUNCTIONS))}")

    if node.keywords:
        raise MatrixExpressionError(f"'{node.func.id}' does not take keyword arguments")

    arguments = [_evaluate(argument, matrices) for argument in node.args]
    try:
        return FUNCTIONS[node.func.id](*arguments)
    except (TypeError, ValueError) as error:
        raise MatrixExpressionError(f"Could not apply '{node.func.id}': {error}") from error
