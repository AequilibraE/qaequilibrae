"""Evaluate matrix expressions using a restricted syntax tree, without ``eval``."""

import ast
import operator

import numpy as np


class MatrixExpressionError(Exception):
    """Unsupported matrix expression."""


def null_diag(matrix):
    """Return a copy of *matrix* with a zero diagonal."""
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
    """Evaluate an expression using the named matrices."""
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
    if not isinstance(node.func, ast.Name):
        attribute = getattr(node.func, "attr", "")
        hint = f" Write '{attribute}(...)' instead." if attribute in FUNCTIONS else ""
        raise MatrixExpressionError(f"Only unqualified function calls are supported.{hint}")

    if node.func.id not in FUNCTIONS:
        raise MatrixExpressionError(f"Unknown function '{node.func.id}'. Available: {', '.join(sorted(FUNCTIONS))}")

    if node.keywords:
        raise MatrixExpressionError(f"'{node.func.id}' does not take keyword arguments")

    arguments = [_evaluate(argument, matrices) for argument in node.args]
    try:
        return FUNCTIONS[node.func.id](*arguments)
    except (TypeError, ValueError) as error:
        raise MatrixExpressionError(f"Could not apply '{node.func.id}': {error}") from error
