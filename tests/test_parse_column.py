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
            parse_column("id INTEGER not NULL"),
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

        self.assertEqual(
            parse_column("name TEXT NOT NULL check(name != '')"),
            ast.Column(
                name="name",
                definition=ast.ColumnDefinition(
                    type="TEXT",
                    constraints=[
                        ast.NotNullConstraint(),
                        ast.CheckConstraint(
                            ast.Infix("!=", ast.Identifier("name"), ast.String(""))
                        ),
                    ],
                ),
            ),
        )

    def test_parse_column_with_trailing_input(self):
        with self.assertRaises(SQLiteParserError):
            parse_column("name TEXT, age INTEGER")

    def test_parse_compound_column_types(self):
        self.assertEqual(
            parse_column("name VARCHAR(500) NOT NULL"),
            ast.Column(
                name="name",
                definition=ast.ColumnDefinition(
                    type=ast.ColumnType(name="VARCHAR", args=[500]),
                    constraints=[ast.NotNullConstraint()],
                ),
            ),
        )

        self.assertEqual(
            parse_column("name FOO(1, 2) NOT NULL"),
            ast.Column(
                name="name",
                definition=ast.ColumnDefinition(
                    type=ast.ColumnType(name="FOO", args=[1, 2]),
                    constraints=[ast.NotNullConstraint()],
                ),
            ),
        )

    def test_parse_column_with_multi_word_type(self):
        self.assertEqual(
            parse_column("x smallint unsigned"),
            ast.Column(
                name="x", definition=ast.ColumnDefinition(type="smallint unsigned")
            ),
        )

    def test_parse_column_with_null_constraint(self):
        # According to the SQLite syntax diagrams this isn't legal syntax, but Django
        # produced it and SQLite accepts it.
        self.assertEqual(
            parse_column('"object_id" text NULL'),
            ast.Column(name="object_id", definition=ast.ColumnDefinition(type="text")),
        )

    def test_parse_column_with_keyword_name(self):
        self.assertEqual(
            parse_column("end DATE"),
            ast.Column(name="end", definition=ast.ColumnDefinition(type="DATE")),
        )
