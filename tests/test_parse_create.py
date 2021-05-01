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
                ),
            ],
        )

    def test_parse_create_statement_with_column_constraints(self):
        sql = """
        CREATE TABLE people(
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          age INTEGER
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="id",
                            type="INTEGER",
                            constraints=[ast.PrimaryKeyConstraint()],
                        ),
                        ast.Column(
                            name="name",
                            type="TEXT",
                            constraints=[ast.NotNullConstraint()],
                        ),
                        ast.Column(name="age", type="INTEGER"),
                    ],
                ),
            ],
        )

    def test_parse_create_statement_with_simple_check_constraint(self):
        sql = """
        CREATE TABLE people(
          name TEXT CHECK(name != '')
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="name",
                            type="TEXT",
                            constraints=[
                                ast.CheckConstraint(
                                    ast.Infix(
                                        "!=",
                                        ast.Identifier("name"),
                                        ast.StringLiteral(""),
                                    )
                                )
                            ],
                        ),
                    ],
                ),
            ],
        )
