import unittest

from sqliteparser import ast, parse


class ParseCreateTests(unittest.TestCase):
    def test_parse_simple_create_index_statement(self):
        sql = """
        CREATE INDEX idx_people ON people(
          name,age
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateIndexStatement(
                    name="idx_people",
                    table="people",
                    columns=["name","age"]
                ),
            ],
        )


    def test_parse_simple_create_unique_index_statement(self):
        sql = """
        CREATE UNIQUE INDEX idx_people on people(
          name,age
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateIndexStatement(
                    name="idx_people",
                    table="people",
                    unique=True,
                    columns=["name","age"],
                ),
            ],
        )  


    def test_parse_simple_create_unique_index_exists_statement(self):
        sql = """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_people on people(
          name,age
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateIndexStatement(
                    name="idx_people",
                    table="people",
                    unique=True,
                    if_not_exists=True,
                    columns=["name","age"],
                ),
            ],
        )  


    def test_parse_create_partial_index_statement_verbatim_expression(self):
        sql = """
        CREATE INDEX idx_people on people(
          name
        ) WHERE name is not null  ;
        """

        self.assertEqual(
            parse(sql, verbatim=True),
            [
                ast.CreateIndexStatement(
                    name="idx_people",
                    table="people",
                    columns=["name"],
                    where= ast.String(value= "name is not null")
                ),
            ],
        )     