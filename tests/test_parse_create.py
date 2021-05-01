import unittest

from sqliteparser import ast, parse


class ParseCreateTests(unittest.TestCase):
    def test_parse_simple_create_statement(self):
        sql = """
        CREATE TABLE people(
          name TEXT,
          age INTEGER
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateStatement(
                    name="people",
                    columns=[
                        ast.Column(name="name", type="TEXT"),
                        ast.Column(name="age", type="INTEGER"),
                    ],
                    constraints=[],
                    as_select=None,
                    temporary=False,
                    without_rowid=False,
                    if_not_exists=False,
                ),
            ],
        )
