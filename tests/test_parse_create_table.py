import unittest

from sqliteparser import ast, parse


class ParseCreateTests(unittest.TestCase):
    def test_parse_simple_create_table_statement(self):
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

    def test_parse_create_table_statement_with_column_constraints(self):
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

    def test_parse_create_table_statement_with_simple_check_constraint(self):
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
                                        "!=", ast.Identifier("name"), ast.String(""),
                                    )
                                )
                            ],
                        ),
                    ],
                ),
            ],
        )

    def test_parse_create_table_statement_with_explicit_schema_name(self):
        sql = """
        CREATE TABLE main.people(
          name TEXT,
          age INTEGER
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateStatement(
                    name=ast.TableName("main", "people"),
                    columns=[
                        ast.Column(name="name", type="TEXT"),
                        ast.Column(name="age", type="INTEGER"),
                    ],
                ),
            ],
        )

    def test_parse_create_temporary_table_statement(self):
        sql = """
        CREATE TEMPORARY TABLE people(
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
                    temporary=True,
                ),
            ],
        )

    def test_parse_create_table_without_rowid(self):
        sql = """
        CREATE TABLE people(
          name TEXT,
          age INTEGER
        ) WITHOUT ROWID;
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
                    without_rowid=True,
                ),
            ],
        )

    def test_parse_create_table_if_not_exists(self):
        sql = """
        CREATE TABLE IF NOT EXISTS people(
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
                    if_not_exists=True,
                ),
            ],
        )
