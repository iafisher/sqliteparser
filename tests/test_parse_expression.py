import unittest

from sqliteparser import ast, parse


class ParseExpressionTests(unittest.TestCase):
    def test_parse_integer_literal(self):
        self.assertEqual(
            parse("SELECT 1"), [ast.SelectStatement(columns=[ast.Integer(1)])]
        )
