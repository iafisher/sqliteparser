import unittest

from sqliteparser import ast, parse


class ParseExpressionTests(unittest.TestCase):
    def test_parse_integer_literal(self):
        self.assertEqual(
            parse("SELECT 1"), [ast.SelectStatement(columns=[ast.Integer(1)])]
        )

    def test_parse_simple_arithmetic_with_precedence(self):
        self.assertEqual(
            parse("SELECT 1+2*3"),
            [
                ast.SelectStatement(
                    columns=[
                        ast.Infix(
                            "+",
                            ast.Integer(1),
                            ast.Infix("*", ast.Integer(2), ast.Integer(3)),
                        )
                    ]
                )
            ],
        )
