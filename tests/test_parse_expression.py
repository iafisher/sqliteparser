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

    def test_parse_string_literal(self):
        self.assertEqual(
            parse(r"SELECT 'abc'"),
            [ast.SelectStatement(columns=[ast.String("abc")])],
        )

    def test_parse_string_literal_with_backslashes_and_single_quotes(self):
        self.assertEqual(
            parse(r"SELECT '\ \n '' '"),
            [ast.SelectStatement(columns=[ast.String("\\ \\n ' ")])],
        )

    def test_parse_blob_literal(self):
        self.assertEqual(
            parse("SELECT X'41'"),
            [ast.SelectStatement(columns=[ast.Blob(b"A")])],
        )

    def test_parse_comparisons(self):
        self.assertEqual(
            parse("SELECT 0 < x OR 20 >= x"),
            [
                ast.SelectStatement(
                    columns=[
                        ast.Infix(
                            "OR",
                            ast.Infix("<", ast.Integer(0), ast.Identifier("x")),
                            ast.Infix(">=", ast.Integer(20), ast.Identifier("x")),
                        )
                    ]
                )
            ],
        )

    def test_parse_AND(self):
        self.assertEqual(
            parse('SELECT ("size" >= 1) AND ("size" <= 4)'),
            [
                ast.SelectStatement(
                    columns=[
                        ast.Infix(
                            "AND",
                            ast.Infix(">=", ast.Identifier("size"), ast.Integer(1)),
                            ast.Infix("<=", ast.Identifier("size"), ast.Integer(4)),
                        )
                    ]
                )
            ],
        )

    def test_parse_expression_list(self):
        self.assertEqual(
            parse("SELECT 1 IN (1, 2, 3)"),
            [
                ast.SelectStatement(
                    columns=[
                        ast.Infix(
                            "IN",
                            ast.Integer(1),
                            ast.ExpressionList(
                                [ast.Integer(1), ast.Integer(2), ast.Integer(3)]
                            ),
                        )
                    ]
                )
            ],
        )

    def test_parse_function(self):
        self.assertEqual(
            parse("SELECT foo(1, 2) + bar(3, baz(4))"),
            [
                ast.SelectStatement(
                    columns=[
                        ast.Infix(
                            "+",
                            ast.Call(
                                ast.Identifier("foo"), [ast.Integer(1), ast.Integer(2)]
                            ),
                            ast.Call(
                                ast.Identifier("bar"),
                                [
                                    ast.Integer(3),
                                    ast.Call(ast.Identifier("baz"), [ast.Integer(4)]),
                                ],
                            ),
                        )
                    ]
                )
            ],
        )

    def test_parse_special_functions(self):
        self.assertEqual(
            parse("SELECT count(*)"),
            [
                ast.SelectStatement(
                    columns=[ast.Call(ast.Identifier("count"), [], star=True)]
                )
            ],
        )

        self.assertEqual(
            parse("SELECT count(DISTINCT x)"),
            [
                ast.SelectStatement(
                    columns=[
                        ast.Call(
                            ast.Identifier("count"),
                            [ast.Identifier("x")],
                            star=False,
                            distinct=True,
                        )
                    ]
                )
            ],
        )

    def test_parse_string_concatenation(self):
        self.assertEqual(
            parse("SELECT 'a' || 'b'"),
            [
                ast.SelectStatement(
                    columns=[ast.Infix("||", ast.String("a"), ast.String("b"))]
                )
            ],
        )
