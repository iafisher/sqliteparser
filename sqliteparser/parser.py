from . import ast
from .exceptions import SQLiteParserError, SQLiteParserImpossibleError
from .lexer import Lexer, TokenType


def parse(program, *, debug=False):
    """
    Parse the SQL program into a list of AST objects.
    """
    lexer = Lexer(program)
    parser = Parser(lexer, debug=debug)
    return parser.parse()


def debuggable(f):
    def wrapped(self, *args, **kwargs):
        name = f.__name__
        if self.debug:
            indent = "  " * (self.debug_indent * 2)
            self.debug_indent += 1
            print(indent + f"{name} (token = {self.lexer.current().value!r})")

        r = f(self, *args, **kwargs)

        if self.debug:
            print(
                indent
                + f"{name} returned (token = {self.lexer.current().value!r}, "
                + f"value = {r!r})"
            )
            self.debug_indent -= 1

        return r

    return wrapped


class Parser:
    """
    The SQL parser.

    It is implemented as a recursive-descent parser. Each match_XYZ method obeys the
    following protocol:

      - It assumes that the lexer is positioned at the first token of the fragment to be
        matched, e.g. match_create_statement assumes that self.lexer.current() will
        return the CREATE token.

      - It leaves the lexer positioned at one past the last token of the fragment.
    """

    def __init__(self, lexer, *, debug=False):
        self.lexer = lexer
        self.debug = debug
        self.debug_indent = 0

    def parse(self):
        statements = []
        while True:
            if self.lexer.done():
                break

            statement = self.match_statement()
            statements.append(statement)

            if not self.lexer.done():
                self.lexer.advance(expecting=[TokenType.SEMICOLON])

        return statements

    @debuggable
    def match_statement(self):
        token = self.lexer.current()
        if token.type == TokenType.KEYWORD:
            if token.value == "CREATE":
                return self.match_create_statement()
            elif token.value == "SELECT":
                return self.match_select_statement()
            else:
                raise SQLiteParserError(f"unexpected keyword: {token.value}")
        else:
            raise SQLiteParserError(f"unexpected token type: {token.type}")

    @debuggable
    def match_create_statement(self):
        token = self.lexer.advance(expecting=["TABLE", "TEMPORARY", "TEMP"])
        if token.value in ("TEMPORARY", "TEMP"):
            temporary = True
            self.lexer.advance(expecting=["TABLE"])
        else:
            temporary = False

        token = self.lexer.advance(expecting=["IF", TokenType.IDENTIFIER])
        if token.value == "IF":
            self.lexer.advance(expecting=["NOT"])
            self.lexer.advance(expecting=["EXISTS"])
            if_not_exists = True
            name_token = self.lexer.advance(expecting=[TokenType.IDENTIFIER])
        else:
            if_not_exists = False
            name_token = token

        token = self.lexer.advance(
            expecting=[TokenType.DOT, TokenType.LEFT_PARENTHESIS]
        )
        if token.type == TokenType.DOT:
            table_name_token = self.lexer.advance(expecting=[TokenType.IDENTIFIER])
            name = ast.TableName(name_token.value, table_name_token.value)
            self.lexer.advance(expecting=[TokenType.LEFT_PARENTHESIS])
        else:
            name = name_token.value

        columns = []
        constraints = []
        while True:
            token = self.lexer.advance()
            if token.type == TokenType.RIGHT_PARENTHESIS:
                break

            column_or_constraint = self.match_column_or_constraint()
            if isinstance(column_or_constraint, ast.Column):
                if constraints:
                    raise SQLiteParserError

                columns.append(column_or_constraint)
            else:
                constraints.append(column_or_constraint)

            token = self.lexer.check([TokenType.COMMA, TokenType.RIGHT_PARENTHESIS])
            if token.type == TokenType.RIGHT_PARENTHESIS:
                break

        token = self.lexer.advance()
        if token is not None:
            if token.type == TokenType.KEYWORD and token.value == "WITHOUT":
                self.lexer.advance(expecting=[(TokenType.IDENTIFIER, "ROWID")])
                without_rowid = True
            else:
                self.lexer.push(token)
                without_rowid = False
        else:
            without_rowid = False

        return ast.CreateTableStatement(
            name=name,
            columns=columns,
            constraints=constraints,
            as_select=None,
            temporary=temporary,
            without_rowid=without_rowid,
            if_not_exists=if_not_exists,
        )

    @debuggable
    def match_select_statement(self):
        self.lexer.advance()
        e = self.match_expression()
        return ast.SelectStatement(columns=[e])

    @debuggable
    def match_column_or_constraint(self):
        token = self.lexer.current()
        if token.type == TokenType.KEYWORD and token.value == "FOREIGN":
            return self.match_foreign_key_constraint()
        elif token.type == TokenType.IDENTIFIER:
            return self.match_column()

    @debuggable
    def match_column(self):
        name_token = self.lexer.check([TokenType.IDENTIFIER])
        type_token = self.lexer.advance()
        if type_token.type != TokenType.IDENTIFIER:
            return ast.Column(name=name_token.value, definition=None)

        constraints = []
        default = None

        token = self.lexer.advance()
        while True:
            if token.type == TokenType.KEYWORD:
                if token.value == "PRIMARY":
                    constraints.append(self.match_primary_key_constraint())
                elif token.value == "NOT":
                    constraints.append(self.match_not_null_constraint())
                elif token.value == "CHECK":
                    constraints.append(self.match_check_constraint())
                elif token.value == "COLLATE":
                    constraints.append(self.match_collate_constraint())
                elif token.value == "REFERENCES":
                    constraints.append(self.match_foreign_key_clause(columns=[]))
                elif token.value == "UNIQUE":
                    constraints.append(self.match_unique_constraint())
                elif token.value == "GENERATED" or token.value == "AS":
                    constraints.append(self.match_generated_column_constraint())
                elif token.value == "DEFAULT":
                    default = self.match_default_clause()
            else:
                break

            token = self.lexer.current()

        return ast.Column(
            name=name_token.value,
            definition=ast.ColumnDefinition(
                type=type_token.value,
                default=default,
                constraints=constraints,
            ),
        )

    @debuggable
    def match_foreign_key_constraint(self):
        self.lexer.check(["FOREIGN"])
        self.lexer.advance(expecting=["KEY"])

        self.lexer.advance(expecting=[TokenType.LEFT_PARENTHESIS])
        self.lexer.advance()
        columns = self.match_identifier_list()
        self.lexer.check([TokenType.RIGHT_PARENTHESIS])
        self.lexer.advance()
        return self.match_foreign_key_clause(columns=columns)

    @debuggable
    def match_foreign_key_clause(self, *, columns):
        self.lexer.check(["REFERENCES"])

        foreign_table = self.lexer.advance(expecting=[TokenType.IDENTIFIER]).value

        token = self.lexer.advance()
        if token.type == TokenType.LEFT_PARENTHESIS:
            self.lexer.advance()
            foreign_columns = self.match_identifier_list()
            self.lexer.check([TokenType.RIGHT_PARENTHESIS])
            token = self.lexer.advance()
        else:
            foreign_columns = []

        on_delete = None
        on_update = None
        match = None
        deferrable = None
        initially_deferred = None

        while True:
            if token.value == "ON":
                delete_or_update = self.lexer.advance(expecting=["DELETE", "UPDATE"])
                token = self.lexer.advance(
                    expecting=["SET", "CASCADE", "RESTRICT", "NO"]
                )
                if token.value == "SET":
                    token = self.lexer.advance(expecting=["NULL", "DEFAULT"])
                    value = (
                        ast.OnDelete.SET_NULL
                        if token.value == "NULL"
                        else ast.OnDelete.SET_DEFAULT
                    )
                elif token.value == "NO":
                    self.lexer.advance(expecting=["ACTION"])
                    value = ast.OnDelete.NO_ACTION
                elif token.value == "CASCADE":
                    value = ast.OnDelete.CASCADE
                elif token.value == "RESTRICT":
                    value = ast.OnDelete.RESTRICT
                else:
                    raise SQLiteParserImpossibleError(token.value)

                if delete_or_update.value == "DELETE":
                    on_delete = value
                else:
                    on_update = value
            elif token.value == "MATCH":
                match_token = self.lexer.advance(
                    expecting=["SIMPLE", "FULL", "PARTIAL"]
                )
                if match_token.value == "FULL":
                    match = ast.ForeignKeyMatch.FULL
                elif match_token.value == "PARTIAL":
                    match = ast.ForeignKeyMatch.PARTIAL
                else:
                    match = ast.ForeignKeyMatch.SIMPLE
            elif token.value == "NOT" or token.value == "DEFERRABLE":
                if token.value == "NOT":
                    self.lexer.advance(expecting=["DEFERRABLE"])
                    deferrable = False
                else:
                    deferrable = True

                token = self.lexer.advance()
                if not (token.type == TokenType.KEYWORD and token.value == "INITIALLY"):
                    break

                token = self.lexer.advance(expecting=["DEFERRED", "IMMEDIATE"])
                initially_deferred = bool(token.value == "DEFERRED")
                self.lexer.advance()
                break
            else:
                break

            token = self.lexer.advance()

        return ast.ForeignKeyConstraint(
            columns=columns,
            foreign_table=foreign_table,
            foreign_columns=foreign_columns,
            on_delete=on_delete,
            on_update=on_update,
            match=match,
            deferrable=deferrable,
            initially_deferred=initially_deferred,
        )

    @debuggable
    def match_not_null_constraint(self):
        self.lexer.check(["NOT"])
        self.lexer.advance(expecting=["NULL"])
        token = self.lexer.advance()
        if token.type == TokenType.KEYWORD and token.value == "ON":
            on_conflict = self.match_on_conflict_clause()
        else:
            on_conflict = None
        return ast.NotNullConstraint(on_conflict=on_conflict)

    @debuggable
    def match_primary_key_constraint(self):
        self.lexer.check(["PRIMARY"])
        self.lexer.advance(expecting=["KEY"])
        token = self.lexer.advance()

        if token.type != TokenType.KEYWORD:
            return ast.PrimaryKeyConstraint()

        if token.value == "ASC":
            ascending = True
            token = self.lexer.advance()
        elif token.value == "DESC":
            ascending = False
            token = self.lexer.advance()
        else:
            ascending = None

        if token.type != TokenType.KEYWORD:
            return ast.PrimaryKeyConstraint(ascending=ascending)

        if token.value == "ON":
            on_conflict = self.match_on_conflict_clause()
            token = self.lexer.current()
        else:
            on_conflict = None

        if token.type != TokenType.KEYWORD:
            return ast.PrimaryKeyConstraint(
                ascending=ascending, on_conflict=on_conflict
            )

        if token.value == "AUTOINCREMENT":
            autoincrement = True
            self.lexer.advance()
        else:
            autoincrement = False

        return ast.PrimaryKeyConstraint(
            ascending=ascending, on_conflict=on_conflict, autoincrement=autoincrement
        )

    @debuggable
    def match_check_constraint(self):
        self.lexer.check(["CHECK"])
        self.lexer.advance(expecting=[TokenType.LEFT_PARENTHESIS])
        self.lexer.advance()
        expr = self.match_expression()
        self.lexer.check([TokenType.RIGHT_PARENTHESIS])
        self.lexer.advance()
        return ast.CheckConstraint(expr)

    @debuggable
    def match_collate_constraint(self):
        self.lexer.check(["COLLATE"])
        sequence = self.lexer.advance(
            expecting=[
                (TokenType.IDENTIFIER, "BINARY"),
                (TokenType.IDENTIFIER, "NOCASE"),
                (TokenType.IDENTIFIER, "RTRIM"),
            ]
        ).value
        self.lexer.advance()
        if sequence == "NOCASE":
            return ast.CollateConstraint(ast.CollatingSequence.NOCASE)
        elif sequence == "RTRIM":
            return ast.CollateConstraint(ast.CollatingSequence.RTRIM)
        elif sequence == "BINARY":
            return ast.CollateConstraint(ast.CollatingSequence.BINARY)
        else:
            raise SQLiteParserImpossibleError(sequence)

    @debuggable
    def match_unique_constraint(self):
        self.lexer.check(["UNIQUE"])
        token = self.lexer.advance()
        if token.type == TokenType.KEYWORD and token.value == "ON":
            on_conflict = self.match_on_conflict_clause()
        else:
            on_conflict = None
        return ast.UniqueConstraint(on_conflict=on_conflict)

    @debuggable
    def match_generated_column_constraint(self):
        token = self.lexer.check(["GENERATED", "AS"])
        if token.value == "GENERATED":
            self.lexer.advance(expecting=["ALWAYS"])
            self.lexer.advance(expecting=["AS"])

        self.lexer.advance(expecting=[TokenType.LEFT_PARENTHESIS])
        self.lexer.advance()
        e = self.match_expression()
        self.lexer.check([TokenType.RIGHT_PARENTHESIS])

        token = self.lexer.advance()
        if token.value == "STORED":
            storage = ast.GeneratedColumnStorage.STORED
            self.lexer.advance()
        elif token.value == "VIRTUAL":
            storage = ast.GeneratedColumnStorage.VIRTUAL
            self.lexer.advance()
        else:
            storage = None

        return ast.GeneratedColumnConstraint(e, storage=storage)

    @debuggable
    def match_default_clause(self):
        self.lexer.check(["DEFAULT"])
        token = self.lexer.advance(
            expecting=[
                TokenType.LEFT_PARENTHESIS,
                TokenType.STRING,
                TokenType.INTEGER,
                TokenType.IDENTIFIER,
                "NULL",
                "CURRENT_TIME",
                "CURRENT_DATE",
                "CURRENT_TIMESTAMP",
            ]
        )

        # TODO(2021-05-05): Merge this with match_prefix?
        if token.type == TokenType.LEFT_PARENTHESIS:
            self.lexer.advance()
            e = self.match_expression()
            self.lexer.check([TokenType.RIGHT_PARENTHESIS])
            self.lexer.advance()
            return e
        elif token.type == TokenType.STRING:
            self.lexer.advance()
            return ast.String(token.value)
        elif token.type == TokenType.BLOB:
            self.lexer.advance()
            return ast.Blob(token.value)
        elif token.type == TokenType.INTEGER:
            self.lexer.advance()
            return ast.Integer(int(token.value))
        elif token.type == TokenType.IDENTIFIER:
            if token.value.upper() in ("TRUE", "FALSE"):
                self.lexer.advance()
                return ast.Boolean(token.value.upper() == "TRUE")
            else:
                raise SQLiteParserError
        elif token.type == TokenType.KEYWORD:
            self.lexer.advance()
            if token.value == "NULL":
                return ast.Null()
            elif token.value == "CURRENT_TIME":
                return ast.DefaultValue.CURRENT_TIME
            elif token.value == "CURRENT_TIMESTAMP":
                return ast.DefaultValue.CURRENT_TIMESTAMP
            elif token.value == "CURRENT_DATE":
                return ast.DefaultValue.CURRENT_DATE
            else:
                raise SQLiteParserImpossibleError(token.value)
        else:
            raise SQLiteParserImpossibleError(token.type)

    @debuggable
    def match_on_conflict_clause(self):
        self.lexer.check(["ON"])
        self.lexer.advance(expecting=["CONFLICT"])
        strategy = self.lexer.advance(
            expecting=["ROLLBACK", "ABORT", "FAIL", "IGNORE", "REPLACE"]
        ).value
        self.lexer.advance()
        if strategy == "ROLLBACK":
            return ast.OnConflict.ROLLBACK
        elif strategy == "ABORT":
            return ast.OnConflict.ABORT
        elif strategy == "FAIL":
            return ast.OnConflict.FAIL
        elif strategy == "IGNORE":
            return ast.OnConflict.IGNORE
        elif strategy == "REPLACE":
            return ast.OnConflict.REPLACE
        else:
            raise SQLiteParserImpossibleError(strategy)

    @debuggable
    def match_expression(self, precedence=-1):
        left = self.match_prefix()

        while True:
            token = self.lexer.current()
            if token is None:
                break

            p = PRECEDENCE.get(token.value)
            if p is None or precedence >= p:
                break

            left = self.match_infix(left, p)
        return left

    @debuggable
    def match_infix(self, left, precedence):
        operator_token = self.lexer.current()
        self.lexer.advance()
        right = self.match_expression(precedence)
        return ast.Infix(operator_token.value, left, right)

    @debuggable
    def match_prefix(self):
        token = self.lexer.current()
        if token.type == TokenType.IDENTIFIER:
            self.lexer.advance()
            return ast.Identifier(token.value)
        elif token.type == TokenType.LEFT_PARENTHESIS:
            self.lexer.advance()
            values = []
            while True:
                e = self.match_expression()
                values.append(e)
                token = self.lexer.check([TokenType.COMMA, TokenType.RIGHT_PARENTHESIS])
                self.lexer.advance()
                if token.type == TokenType.RIGHT_PARENTHESIS:
                    break

            if len(values) == 1:
                return values[0]
            else:
                return ast.ExpressionList(values)
        elif token.type == TokenType.STRING:
            self.lexer.advance()
            return ast.String(token.value)
        elif token.type == TokenType.BLOB:
            self.lexer.advance()
            return ast.Blob(token.value)
        elif token.type == TokenType.INTEGER:
            self.lexer.advance()
            return ast.Integer(int(token.value))
        else:
            raise SQLiteParserError(token.type, token.value)

    def match_identifier_list(self):
        identifiers = []
        while True:
            token = self.lexer.current()
            if token.type == TokenType.IDENTIFIER:
                identifiers.append(token.value)
                self.lexer.advance()
            elif token.type == TokenType.COMMA:
                self.lexer.advance()
            else:
                break
        return identifiers


# From https://sqlite.org/lang_expr.html
PRECEDENCE = {
    "OR": 0,
    "AND": 1,
    "=": 2,
    "==": 2,
    "!=": 2,
    "<>": 2,
    "IS": 2,
    "IN": 2,
    "LIKE": 2,
    "GLOB": 2,
    "MATCH": 2,
    "REGEXP": 2,
    "<": 3,
    "<=": 3,
    ">": 3,
    ">=": 3,
    "<<": 4,
    ">>": 4,
    "&": 4,
    "|": 4,
    "+": 5,
    "-": 5,
    "*": 6,
    "/": 6,
    "%": 6,
    "||": 7,
}
