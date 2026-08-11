import numpy as np
import pytest

from qaequilibrae.modules.processing_provider.matrix_procedures.matrix_expression import (
    MatrixExpressionError,
    evaluate,
)


@pytest.fixture
def matrices():
    return {"cars": np.arange(9, dtype=float).reshape(3, 3), "trucks": np.full((3, 3), 4.0)}


def test_arithmetic_and_transposition(matrices):
    # The expression the matrix calculator is documented with
    result = evaluate("(cars - (trucks * 0.25)).T", matrices)

    assert np.array_equal(result, (matrices["cars"] - matrices["trucks"] * 0.25).T)


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("cars + trucks", lambda c, t: c + t),
        ("cars - trucks", lambda c, t: c - t),
        ("cars * 2", lambda c, t: c * 2),
        ("cars / 2", lambda c, t: c / 2),
        ("-cars", lambda c, t: -c),
        ("min(cars)", lambda c, t: np.min(c)),
        ("max(cars)", lambda c, t: np.max(c)),
        ("abs(cars - trucks)", lambda c, t: np.absolute(c - t)),
        ("ln(cars + 1)", lambda c, t: np.log(c + 1)),
        ("exp(cars / 10)", lambda c, t: np.exp(c / 10)),
        ("power(cars, 2)", lambda c, t: np.power(c, 2)),
    ],
)
def test_documented_operations(matrices, expression, expected):
    result = evaluate(expression, matrices)

    assert np.allclose(result, expected(matrices["cars"], matrices["trucks"]))


def test_null_diag_zeroes_the_diagonal_without_touching_the_input(matrices):
    result = evaluate("null_diag(cars)", matrices)

    assert np.array_equal(np.diag(result), np.zeros(3))
    assert np.array_equal(matrices["cars"], np.arange(9, dtype=float).reshape(3, 3))


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo pwned')",
        "open('/tmp/pwned', 'w')",
        "cars.__class__.__bases__",
        "().__class__.__base__.__subclasses__()",
        "[c for c in cars]",
        "np.min(cars)",
        "lambda: 1",
        "not_a_matrix + 1",
        "cars; import os",
    ],
)
def test_rejects_anything_outside_matrix_algebra(matrices, expression):
    with pytest.raises(MatrixExpressionError):
        evaluate(expression, matrices)
