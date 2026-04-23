from __future__ import annotations

import ast
import operator as op

_ALLOWED = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg}


def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return _ALLOWED[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _ALLOWED[type(node.op)](_eval(node.operand))
    raise ValueError('Unsupported expression')


def calculate(expression: str):
    tree = ast.parse(expression, mode='eval')
    for node in ast.walk(tree):
        if isinstance(node, (ast.Call, ast.Attribute, ast.Name)):
            raise ValueError('Calculator only supports arithmetic expressions')
    return _eval(tree.body)
