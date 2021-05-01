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
    NOT_EQ = enum.auto()
    STRING = enum.auto()
    INTEGER = enum.auto()
    UNKNOWN = enum.auto()


class Lexer:
    def __init__(self, program):
        self.program = program
        self.index = 0
        self.line = 1
        self.column = 1

        self.pushed_token = None
        self.current_token = None
        self.advance()

    def current(self):
        return (
            self.pushed_token if self.pushed_token is not None else self.current_token
        )

    def expect(self, type=None, value=None):
        if self.done():
            raise SQLiteParserError("premature end of input")

        token = self.advance()
        if token.type == TokenType.UNKNOWN:
            raise SQLiteParserError("unknown token")

        if type is not None and token.type != type:
            raise SQLiteParserError(f"expected {type!r}, got {token.type!r}")

        if value is not None and token.value != value:
            raise SQLiteParserError(f"expected {value!r}, got {token.value!r}")

        return token

    def advance(self):
        if self.pushed_token is not None:
            ret = self.pushed_token
            self.pushed_token = None
            return ret

        self.read_whitespace()

        if self.index == len(self.program):
            return None

        self.current_token = self._advance()
        self.read_whitespace()
        return self.current_token

    def _advance(self):
        c = self.c()
        if c.isalpha():
            return self.read_symbol()
        elif c.isdigit():
            return self.read_integer()
        elif c == "'":
            return self.read_string()
        elif c == "(":
            return self.character_token(TokenType.LEFT_PARENTHESIS)
        elif c == ")":
            return self.character_token(TokenType.RIGHT_PARENTHESIS)
        elif c == ",":
            return self.character_token(TokenType.COMMA)
        elif c == ";":
            return self.character_token(TokenType.SEMICOLON)
        elif self.prefix(2) == "!=":
            return self.multi_character_token(TokenType.NOT_EQ, 2)
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
            self.next_character()

    def read_symbol(self):
        start = self.index
        start_column = self.column
        while not self.done() and is_symbol_character(self.c()):
            self.next_character()

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

    def read_integer(self):
        start = self.index
        start_column = self.column
        while not self.done() and self.c().isdigit():
            self.next_character()

        value = self.program[start : self.index]
        return Token(
            type=TokenType.INTEGER, value=value, line=self.line, column=start_column
        )

    def read_string(self):
        start = self.index
        start_column = self.column

        self.next_character()
        while not self.done() and self.c() != "'":
            self.next_character()

        if self.done():
            raise SQLiteParserError("unterminated string literal")
        else:
            self.next_character()

        return Token(
            type=TokenType.STRING,
            value=self.program[start : self.index],
            line=self.line,
            column=start_column,
        )

    def next_character(self):
        if self.c() == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        self.index += 1

    def c(self):
        return self.prefix(1)

    def prefix(self, length):
        return self.program[self.index : self.index + length]

    def character_token(self, type):
        return self.multi_character_token(type, 1)

    def multi_character_token(self, type, length):
        value = self.program[self.index : self.index + length]
        line = self.line
        column = self.column
        for _ in range(length):
            self.next_character()
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
