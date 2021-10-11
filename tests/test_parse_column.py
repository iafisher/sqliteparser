import unittest

from sqliteparser import SQLiteParserError, ast, parse_column


class ParseColumnTests(unittest.TestCase):
    def test_parse_simple_column(self):
        self.assertEqual(
            parse_column("name TEXT"),
            ast.Column(name="name", definition=ast.ColumnDefinition(type="TEXT")),
        )

    def test_parse_column_with_constraints(self):
        self.assertEqual(
            parse_column("id INTEGER PRIMARY KEY"),
            ast.Column(
                name="id",
                definition=ast.ColumnDefinition(
                    type="INTEGER", constraints=[ast.PrimaryKeyConstraint()]
                ),
            ),
        )

        self.assertEqual(
            parse_column("id INTEGER UNIQUE"),
            ast.Column(
                name="id",
                definition=ast.ColumnDefinition(
                    type="INTEGER", constraints=[ast.UniqueConstraint()]
                ),
            ),
        )

        self.assertEqual(
            parse_column("id INTEGER NOT NULL"),
            ast.Column(
                name="id",
                definition=ast.ColumnDefinition(
                    type="INTEGER", constraints=[ast.NotNullConstraint()]
                ),
            ),
        )

        self.assertEqual(
            parse_column("model INTEGER REFERENCES models"),
            ast.Column(
                name="model",
                definition=ast.ColumnDefinition(
                    type="INTEGER",
                    constraints=[
                        ast.ForeignKeyConstraint(
                            columns=[], foreign_table="models", foreign_columns=[]
                        )
                    ],
                ),
            ),
        )

    def test_parse_column_with_trailing_input(self):
        with self.assertRaises(SQLiteParserError):
            parse_column("name TEXT, age INTEGER")
