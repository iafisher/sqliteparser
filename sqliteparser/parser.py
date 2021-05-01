from . import ast
from .exceptions import SQLiteParserError
from .lexer import Lexer, TokenType


class Parser:
    def __init__(self, lexer):
        self.lexer = lexer

    def parse(self):
        statements = []
        while True:
            if self.lexer.done():
                break

            statement = self.match_statement()
            statements.append(statement)

            if not self.lexer.done():
                self.lexer.expect(TokenType.SEMICOLON)

        return statements

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

    def match_create_statement(self):
        self.lexer.expect(TokenType.KEYWORD, "TABLE")
        name_token = self.lexer.expect(TokenType.IDENTIFIER)
        self.lexer.expect(TokenType.LEFT_PARENTHESIS)

        columns = []
        while True:
            token = self.lexer.advance()
            if token.type == TokenType.RIGHT_PARENTHESIS:
                break
            self.lexer.push(token)
            columns.append(self.match_column_definition())

            token = self.lexer.advance()
            if token.type == TokenType.COMMA:
                continue
            elif token.type == TokenType.RIGHT_PARENTHESIS:
                break
            else:
                raise SQLiteParserError

        return ast.CreateStatement(
            name=name_token.value,
            columns=columns,
            constraints=[],
            as_select=None,
            temporary=False,
            without_rowid=False,
            if_not_exists=False,
        )

    def match_select_statement(self):
        e = self.match_expression()
        return ast.SelectStatement(columns=[e])

    def match_column_definition(self):
        name_token = self.lexer.expect(TokenType.IDENTIFIER)
        type_token = self.lexer.expect(TokenType.IDENTIFIER)
        constraints = []

        token = self.lexer.advance()
        if token.type == TokenType.KEYWORD and token.value == "PRIMARY":
            constraints.append(self.match_primary_key_constraint())
        elif token.type == TokenType.KEYWORD and token.value == "NOT":
            constraints.append(self.match_not_null_constraint())
        elif token.type == TokenType.KEYWORD and token.value == "CHECK":
            constraints.append(self.match_check_constraint())
        else:
            self.lexer.push(token)

        return ast.Column(
            name=name_token.value, type=type_token.value, constraints=constraints
        )

    def match_not_null_constraint(self):
        self.lexer.expect(TokenType.KEYWORD, "NULL")
        return ast.NotNullConstraint()

    def match_primary_key_constraint(self):
        self.lexer.expect(TokenType.KEYWORD, "KEY")
        return ast.PrimaryKeyConstraint()

    def match_check_constraint(self):
        self.lexer.expect(TokenType.LEFT_PARENTHESIS)
        expr = self.match_expression()
        self.lexer.expect(TokenType.RIGHT_PARENTHESIS)
        return ast.CheckConstraint(expr)

    def match_expression(self, precedence=-1):
        left = self.match_prefix()

        while True:
            token = self.lexer.advance()
            if token is None:
                break

            p = PRECEDENCE.get(token.value)
            if p is None or precedence >= p:
                self.lexer.push(token)
                break

            left = self.match_infix(left, p)
        return left

    def match_infix(self, left, precedence):
        operator_token = self.lexer.current()
        right = self.match_expression(precedence)
        return ast.Infix(operator_token.value, left, right)

    def match_prefix(self):
        token = self.lexer.advance()
        if token.type == TokenType.IDENTIFIER:
            return ast.Identifier(token.value)
        elif token.type == TokenType.LEFT_PARENTHESIS:
            e = self.match_expression()
            self.lexer.expect(TokenType.RIGHT_PARENTHESIS)
            return e
        elif token.type == TokenType.STRING:
            return ast.String(token.value[1:-1])
        elif token.type == TokenType.INTEGER:
            return ast.Integer(int(token.value))
        else:
            raise SQLiteParserError(token.type)


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


def parse(program):
    lexer = Lexer(program)
    parser = Parser(lexer)
    return parser.parse()
