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

    def test_parse_create_table_with_foreign_keys_multiple_on_delete_clauses(self):
        sql = """
        CREATE TABLE people(
            job_id INTEGER,
            FOREIGN KEY (job_id) REFERENCES jobs
              ON DELETE SET NULL
              ON DELETE NO ACTION
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateStatement(
                    name="people",
                    columns=[ast.Column(name="job_id", type="INTEGER")],
                    constraints=[
                        ast.ForeignKeyConstraint(
                            columns=["job_id"],
                            foreign_table="jobs",
                            foreign_columns=[],
                            on_delete=ast.OnDeleteOrUpdate.NO_ACTION,
                            on_update=None,
                            match=None,
                            deferrable=None,
                            initially_deferred=None,
                        ),
                    ],
                )
            ],
        )

    def test_parse_create_table_with_foreign_keys_deferrable_constraints(self):
        sql = """
        CREATE TABLE people(
            id1 INTEGER,
            id2 INTEGER,
            id3 INTEGER,
            FOREIGN KEY (id1) REFERENCES table1 NOT DEFERRABLE,
            FOREIGN KEY (id2) REFERENCES table2 DEFERRABLE,
            FOREIGN KEY (id3) REFERENCES table3 DEFERRABLE INITIALLY IMMEDIATE
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateStatement(
                    name="people",
                    columns=[
                        ast.Column(name="id1", type="INTEGER"),
                        ast.Column(name="id2", type="INTEGER"),
                        ast.Column(name="id3", type="INTEGER"),
                    ],
                    constraints=[
                        ast.ForeignKeyConstraint(
                            columns=["id1"],
                            foreign_table="table1",
                            foreign_columns=[],
                            on_delete=None,
                            on_update=None,
                            match=None,
                            deferrable=False,
                            initially_deferred=None,
                        ),
                        ast.ForeignKeyConstraint(
                            columns=["id2"],
                            foreign_table="table2",
                            foreign_columns=[],
                            on_delete=None,
                            on_update=None,
                            match=None,
                            deferrable=True,
                            initially_deferred=None,
                        ),
                        ast.ForeignKeyConstraint(
                            columns=["id3"],
                            foreign_table="table3",
                            foreign_columns=[],
                            on_delete=None,
                            on_update=None,
                            match=None,
                            deferrable=True,
                            initially_deferred=False,
                        ),
                    ],
                )
            ],
        )

    def test_parse_create_table_with_foreign_keys(self):
        sql = """
        CREATE TABLE people(
            team_id INTEGER,
            job_id INTEGER,
            FOREIGN KEY (team_id) REFERENCES teams,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
              ON DELETE SET NULL
              MATCH FULL
              ON UPDATE CASCADE
              DEFERRABLE INITIALLY DEFERRED
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateStatement(
                    name="people",
                    columns=[
                        ast.Column(name="team_id", type="INTEGER"),
                        ast.Column(name="job_id", type="INTEGER"),
                    ],
                    constraints=[
                        ast.ForeignKeyConstraint(
                            columns=["team_id"],
                            foreign_table="teams",
                            foreign_columns=[],
                            on_delete=None,
                            on_update=None,
                            match=None,
                            deferrable=None,
                            initially_deferred=None,
                        ),
                        ast.ForeignKeyConstraint(
                            columns=["job_id"],
                            foreign_table="jobs",
                            foreign_columns=["id"],
                            on_delete=ast.OnDeleteOrUpdate.SET_NULL,
                            on_update=ast.OnDeleteOrUpdate.CASCADE,
                            match=ast.ForeignKeyMatch.FULL,
                            deferrable=True,
                            initially_deferred=True,
                        ),
                    ],
                )
            ],
        )