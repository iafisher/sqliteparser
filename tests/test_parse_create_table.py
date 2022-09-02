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
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="name", definition=ast.ColumnDefinition(type="TEXT")
                        ),
                        ast.Column(
                            name="age", definition=ast.ColumnDefinition(type="INTEGER")
                        ),
                    ],
                ),
            ],
        )

    def test_parse_simple_create_table_statement_with_no_semicolon(self):
        sql = """
        CREATE TABLE people(
          name TEXT,
          age INTEGER
        )
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="name", definition=ast.ColumnDefinition(type="TEXT")
                        ),
                        ast.Column(
                            name="age", definition=ast.ColumnDefinition(type="INTEGER")
                        ),
                    ],
                ),
            ],
        )

    def test_parse_create_table_statement_with_no_type_names(self):
        sql = """
        CREATE TABLE people(name, age);
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(name="name", definition=None),
                        ast.Column(name="age", definition=None),
                    ],
                ),
            ],
        )

    def test_parse_create_table_statement_with_column_constraints(self):
        sql = """
        CREATE TABLE people(
          id INTEGER PRIMARY KEY NOT NULL,
          name TEXT NOT NULL,
          age INTEGER NOT NULL ON CONFLICT ROLLBACK
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="id",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.PrimaryKeyConstraint(),
                                    ast.NotNullConstraint(),
                                ],
                            ),
                        ),
                        ast.Column(
                            name="name",
                            definition=ast.ColumnDefinition(
                                type="TEXT",
                                constraints=[ast.NotNullConstraint()],
                            ),
                        ),
                        ast.Column(
                            name="age",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.NotNullConstraint(
                                        on_conflict=ast.OnConflict.ROLLBACK
                                    )
                                ],
                            ),
                        ),
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
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="name",
                            definition=ast.ColumnDefinition(
                                type="TEXT",
                                constraints=[
                                    ast.CheckConstraint(
                                        ast.Infix(
                                            "!=",
                                            ast.Identifier("name"),
                                            ast.String(""),
                                        )
                                    )
                                ],
                            ),
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
                ast.CreateTableStatement(
                    name=ast.TableName("main", "people"),
                    columns=[
                        ast.Column(
                            name="name", definition=ast.ColumnDefinition(type="TEXT")
                        ),
                        ast.Column(
                            name="age", definition=ast.ColumnDefinition(type="INTEGER")
                        ),
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
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="name", definition=ast.ColumnDefinition(type="TEXT")
                        ),
                        ast.Column(
                            name="age", definition=ast.ColumnDefinition(type="INTEGER")
                        ),
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
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="name", definition=ast.ColumnDefinition(type="TEXT")
                        ),
                        ast.Column(
                            name="age", definition=ast.ColumnDefinition(type="INTEGER")
                        ),
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
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="name", definition=ast.ColumnDefinition(type="TEXT")
                        ),
                        ast.Column(
                            name="age", definition=ast.ColumnDefinition(type="INTEGER")
                        ),
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
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="job_id",
                            definition=ast.ColumnDefinition(type="INTEGER"),
                        )
                    ],
                    constraints=[
                        ast.ForeignKeyConstraint(
                            columns=["job_id"],
                            foreign_table="jobs",
                            foreign_columns=[],
                            on_delete=ast.OnDelete.NO_ACTION,
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
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="id1", definition=ast.ColumnDefinition(type="INTEGER")
                        ),
                        ast.Column(
                            name="id2", definition=ast.ColumnDefinition(type="INTEGER")
                        ),
                        ast.Column(
                            name="id3", definition=ast.ColumnDefinition(type="INTEGER")
                        ),
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
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="team_id",
                            definition=ast.ColumnDefinition(type="INTEGER"),
                        ),
                        ast.Column(
                            name="job_id",
                            definition=ast.ColumnDefinition(type="INTEGER"),
                        ),
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
                            on_delete=ast.OnDelete.SET_NULL,
                            on_update=ast.OnUpdate.CASCADE,
                            match=ast.ForeignKeyMatch.FULL,
                            deferrable=True,
                            initially_deferred=True,
                        ),
                    ],
                )
            ],
        )

    def test_parse_create_table_with_inline_foreign_key(self):
        sql = """
        CREATE TABLE people(
            job_id INTEGER REFERENCES jobs(id)
              ON DELETE SET NULL
              MATCH FULL
              ON UPDATE CASCADE
              DEFERRABLE INITIALLY DEFERRED
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="job_id",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.ForeignKeyConstraint(
                                        columns=[],
                                        foreign_table="jobs",
                                        foreign_columns=["id"],
                                        on_delete=ast.OnDelete.SET_NULL,
                                        on_update=ast.OnUpdate.CASCADE,
                                        match=ast.ForeignKeyMatch.FULL,
                                        deferrable=True,
                                        initially_deferred=True,
                                    ),
                                ],
                            ),
                        ),
                    ],
                )
            ],
        )

    def test_parse_create_table_statement_with_collating_sequence(self):
        sql = """
        CREATE TABLE people(
          name TEXT COLLATE NOCASE,
          age INTEGER COLLATE BINARY
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="name",
                            definition=ast.ColumnDefinition(
                                type="TEXT",
                                constraints=[
                                    ast.CollateConstraint(ast.CollatingSequence.NOCASE)
                                ],
                            ),
                        ),
                        ast.Column(
                            name="age",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.CollateConstraint(ast.CollatingSequence.BINARY)
                                ],
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_parse_create_table_statement_with_unique_constraint(self):
        sql = """
        CREATE TABLE people(
          name TEXT UNIQUE,
          age INTEGER UNIQUE ON CONFLICT FAIL
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="name",
                            definition=ast.ColumnDefinition(
                                type="TEXT",
                                constraints=[ast.UniqueConstraint(on_conflict=None)],
                            ),
                        ),
                        ast.Column(
                            name="age",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.UniqueConstraint(
                                        on_conflict=ast.OnConflict.FAIL
                                    )
                                ],
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_parse_create_table_statement_with_default_clause(self):
        sql = """
        CREATE TABLE people(
          name TEXT DEFAULT '',
          age INTEGER DEFAULT ( 2 + 2 ),
          employed BOOLEAN DEFAULT TRUE,
          last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="name",
                            definition=ast.ColumnDefinition(
                                type="TEXT", default=ast.String("")
                            ),
                        ),
                        ast.Column(
                            name="age",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                default=ast.Infix("+", ast.Integer(2), ast.Integer(2)),
                            ),
                        ),
                        ast.Column(
                            name="employed",
                            definition=ast.ColumnDefinition(
                                type="BOOLEAN", default=ast.Boolean(True)
                            ),
                        ),
                        ast.Column(
                            name="last_updated",
                            definition=ast.ColumnDefinition(
                                type="TIMESTAMP",
                                default=ast.DefaultValue.CURRENT_TIMESTAMP,
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_parse_create_table_statement_with_primary_key_constraint(self):
        sql = """
        CREATE TABLE people(
          id1 INTEGER PRIMARY KEY,
          id2 INTEGER PRIMARY KEY ASC,
          id3 INTEGER PRIMARY KEY DESC ON CONFLICT IGNORE,
          id4 INTEGER PRIMARY KEY DESC ON CONFLICT IGNORE AUTOINCREMENT,
          id5 INTEGER PRIMARY KEY ON CONFLICT IGNORE AUTOINCREMENT,
          id6 INTEGER PRIMARY KEY AUTOINCREMENT
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="id1",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.PrimaryKeyConstraint(
                                        ascending=None,
                                        on_conflict=None,
                                        autoincrement=False,
                                    )
                                ],
                            ),
                        ),
                        ast.Column(
                            name="id2",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.PrimaryKeyConstraint(
                                        ascending=True,
                                        on_conflict=None,
                                        autoincrement=False,
                                    )
                                ],
                            ),
                        ),
                        ast.Column(
                            name="id3",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.PrimaryKeyConstraint(
                                        ascending=False,
                                        on_conflict=ast.OnConflict.IGNORE,
                                        autoincrement=False,
                                    )
                                ],
                            ),
                        ),
                        ast.Column(
                            name="id4",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.PrimaryKeyConstraint(
                                        ascending=False,
                                        on_conflict=ast.OnConflict.IGNORE,
                                        autoincrement=True,
                                    )
                                ],
                            ),
                        ),
                        ast.Column(
                            name="id5",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.PrimaryKeyConstraint(
                                        ascending=None,
                                        on_conflict=ast.OnConflict.IGNORE,
                                        autoincrement=True,
                                    )
                                ],
                            ),
                        ),
                        ast.Column(
                            name="id6",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.PrimaryKeyConstraint(
                                        ascending=None,
                                        on_conflict=None,
                                        autoincrement=True,
                                    )
                                ],
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_parse_create_table_statement_with_generated_column_constraint(self):
        sql = """
        CREATE TABLE people(
          age INTEGER GENERATED ALWAYS AS ( 2 + 2 ) STORED,
        );
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(
                            name="age",
                            definition=ast.ColumnDefinition(
                                type="INTEGER",
                                constraints=[
                                    ast.GeneratedColumnConstraint(
                                        ast.Infix("+", ast.Integer(2), ast.Integer(2)),
                                        storage=ast.GeneratedColumnStorage.STORED,
                                    )
                                ],
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_parse_create_table_statement_with_quoted_names(self):
        sql = """
        CREATE TABLE "people"([name], `age`);
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="people",
                    columns=[
                        ast.Column(name="name", definition=None),
                        ast.Column(name="age", definition=None),
                    ],
                ),
            ],
        )

    def test_parse_create_table_statement_with_schema_name(self):
        sql = """
        CREATE TABLE temp.people(name);
        """

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name=ast.TableName("TEMP", "people"),
                    columns=[
                        ast.Column(name="name", definition=None),
                    ],
                ),
            ],
        )

    def test_parse_create_table_statement_with_table_primary_key_constraint(self):
        # Regression test for https://github.com/iafisher/sqliteparser/issues/8
        sql = "create table t1 (c1 text,c2 text,primary key(c1,c2))"

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="t1",
                    columns=[
                        ast.Column(
                            name="c1", definition=ast.ColumnDefinition(type="text")
                        ),
                        ast.Column(
                            name="c2", definition=ast.ColumnDefinition(type="text")
                        ),
                    ],
                    constraints=[
                        ast.PrimaryKeyTableConstraint(
                            columns=["c1", "c2"], on_conflict=None
                        ),
                    ],
                )
            ],
        )

    def test_parse_create_table_statement_with_generated_clause(self):
        # Regression test for https://github.com/iafisher/sqliteparser/issues/9
        sql = "create table t2 (c1 text, c2 text generated always as (upper(c1)));"

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="t2",
                    columns=[
                        ast.Column(
                            name="c1",
                            definition=ast.ColumnDefinition(type="text"),
                        ),
                        ast.Column(
                            name="c2",
                            definition=ast.ColumnDefinition(
                                type="text",
                                constraints=[
                                    ast.GeneratedColumnConstraint(
                                        ast.Call(
                                            ast.Identifier("upper"),
                                            [ast.Identifier("c1")],
                                        )
                                    )
                                ],
                            ),
                        ),
                    ],
                )
            ],
        )

        sql = "create table t1 (c1 text,c2 generated always as (2+2));"

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="t1",
                    columns=[
                        ast.Column(
                            name="c1",
                            definition=ast.ColumnDefinition(type="text"),
                        ),
                        ast.Column(
                            name="c2",
                            definition=ast.ColumnDefinition(
                                type=None,
                                constraints=[
                                    ast.GeneratedColumnConstraint(
                                        ast.Infix("+", ast.Integer(2), ast.Integer(2))
                                    )
                                ],
                            ),
                        ),
                    ],
                )
            ],
        )

    def test_parse_create_table_statement_with_table_unique_constraint(self):
        # Regression test for https://github.com/iafisher/sqliteparser/issues/8
        sql = "create table t1 (c1 text,c2 text,unique (c1,c2))"

        self.assertEqual(
            parse(sql),
            [
                ast.CreateTableStatement(
                    name="t1",
                    columns=[
                        ast.Column(
                            name="c1", definition=ast.ColumnDefinition(type="text")
                        ),
                        ast.Column(
                            name="c2", definition=ast.ColumnDefinition(type="text")
                        ),
                    ],
                    constraints=[
                        ast.UniqueTableConstraint(
                            columns=["c1", "c2"], on_conflict=None
                        ),
                    ],
                )
            ],
        )