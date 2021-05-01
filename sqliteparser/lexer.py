import enum

from attr import attrib, attrs

from .exceptions import SQLiteParserError


@attrs
class Token:
    type = attrib()
    value = attrib()
    line = attrib()
    column = attrib()


class TokenType(enum.Enum):
    KEYWORD = enum.auto()
    IDENTIFIER = enum.auto()
    LEFT_PARENTHESIS = enum.auto()
    RIGHT_PARENTHESIS = enum.auto()
    COMMA = enum.auto()
    SEMICOLON = enum.auto()
    UNKNOWN = enum.auto()


class Lexer:
    def __init__(self, program):
        self.program = program
        self.index = 0
        self.line = 1
        self.column = 1
        self.pushed_token = None

    def expect(self, type=None, value=None):
        if self.done():
            raise SQLiteParserError("premature end of input")

        token = self.next()
        if token.type == TokenType.UNKNOWN:
            raise SQLiteParserError("unknown token")

        if type is not None and token.type != type:
            raise SQLiteParserError(f"expected {type!r}, got {token.type!r}")

        if value is not None and token.value != value:
            raise SQLiteParserError(f"expected {value!r}, got {token.value!r}")

        return token

    def next(self):
        if self.pushed_token is not None:
            ret = self.pushed_token
            self.pushed_token = None
            return ret

        self.read_whitespace()

        if self.index == len(self.program):
            return None

        ret = self._next()
        self.read_whitespace()
        return ret

    def _next(self):
        c = self.c()
        if c.isalpha():
            return self.read_symbol()
        elif c == "(":
            return self.character_token(TokenType.LEFT_PARENTHESIS)
        elif c == ")":
            return self.character_token(TokenType.RIGHT_PARENTHESIS)
        elif c == ",":
            return self.character_token(TokenType.COMMA)
        elif c == ";":
            return self.character_token(TokenType.SEMICOLON)
        else:
            return self.character_token(TokenType.UNKNOWN)

    def push(self, token):
        if self.pushed_token is not None:
            raise SQLiteParserError("token already pushed")

        self.pushed_token = token

    def done(self):
        return self.index == len(self.program)

    def read_whitespace(self):
        while not self.done() and self.c().isspace():
            self.advance()

    def read_symbol(self):
        start = self.index
        start_column = self.column
        while not self.done() and is_symbol_character(self.program[self.index]):
            self.advance()

        value = self.program[start : self.index]
        if value in SQL_KEYWORDS:
            return Token(
                type=TokenType.KEYWORD,
                value=value.upper(),
                line=self.line,
                column=start_column,
            )
        else:
            return Token(
                type=TokenType.IDENTIFIER,
                value=value,
                line=self.line,
                column=start_column,
            )

    def advance(self):
        if self.c() == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        self.index += 1

    def c(self):
        return self.program[self.index]

    def character_token(self, type):
        value = self.c()
        line = self.line
        column = self.column
        self.advance()
        return Token(type=type, value=value, line=line, column=column)


def is_symbol_character(c):
    return c.isalpha() or c.isdigit() or c == "_"


# According to https://sqlite.org/lang_keywords.html
SQL_KEYWORDS = {
    "ABORT",
    "ACTION",
    "ADD",
    "AFTER",
    "ALL",
    "ALTER",
    "ALWAYS",
    "ANALYZE",
    "AND",
    "AS",
    "ASC",
    "ATTACH",
    "AUTOINCREMENT",
    "BEFORE",
    "BEGIN",
    "BETWEEN",
    "BY",
    "CASCADE",
    "CASE",
    "CAST",
    "CHECK",
    "COLLATE",
    "COLUMN",
    "COMMIT",
    "CONFLICT",
    "CONSTRAINT",
    "CREATE",
    "CROSS",
    "CURRENT",
    "CURRENT_DATE",
    "CURRENT_TIME",
    "CURRENT_TIMESTAMP",
    "DATABASE",
    "DEFAULT",
    "DEFERRABLE",
    "DEFERRED",
    "DELETE",
    "DESC",
    "DETACH",
    "DISTINCT",
    "DO",
    "DROP",
    "EACH",
    "ELSE",
    "END",
    "ESCAPE",
    "EXCEPT",
    "EXCLUDE",
    "EXCLUSIVE",
    "EXISTS",
    "EXPLAIN",
    "FAIL",
    "FILTER",
    "FIRST",
    "FOLLOWING",
    "FOR",
    "FOREIGN",
    "FROM",
    "FULL",
    "GENERATED",
    "GLOB",
    "GROUP",
    "GROUPS",
    "HAVING",
    "IF",
    "IGNORE",
    "IMMEDIATE",
    "IN",
    "INDEX",
    "INDEXED",
    "INITIALLY",
    "INNER",
    "INSERT",
    "INSTEAD",
    "INTERSECT",
    "INTO",
    "IS",
    "ISNULL",
    "JOIN",
    "KEY",
    "LAST",
    "LEFT",
    "LIKE",
    "LIMIT",
    "MATCH",
    "MATERIALIZED",
    "NATURAL",
    "NO",
    "NOT",
    "NOTHING",
    "NOTNULL",
    "NULL",
    "NULLS",
    "OF",
    "OFFSET",
    "ON",
    "OR",
    "ORDER",
    "OTHERS",
    "OUTER",
    "OVER",
    "PARTITION",
    "PLAN",
    "PRAGMA",
    "PRECEDING",
    "PRIMARY",
    "QUERY",
    "RAISE",
    "RANGE",
    "RECURSIVE",
    "REFERENCES",
    "REGEXP",
    "REINDEX",
    "RELEASE",
    "RENAME",
    "REPLACE",
    "RESTRICT",
    "RETURNING",
    "RIGHT",
    "ROLLBACK",
    "ROW",
    "ROWS",
    "SAVEPOINT",
    "SELECT",
    "SET",
    "TABLE",
    "TEMP",
    "TEMPORARY",
    "THEN",
    "TIES",
    "TO",
    "TRANSACTION",
    "TRIGGER",
    "UNBOUNDED",
    "UNION",
    "UNIQUE",
    "UPDATE",
    "USING",
    "VACUUM",
    "VALUES",
    "VIEW",
    "VIRTUAL",
    "WHEN",
    "WHERE",
    "WINDOW",
    "WITH",
    "WITHOUT",
}
