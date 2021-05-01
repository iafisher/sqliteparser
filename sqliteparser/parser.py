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
        token = self.lexer.next()
        if token.type == TokenType.KEYWORD:
            if token.value == "CREATE":
                return self.match_create_statement()
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
            token = self.lexer.next()
            if token.type == TokenType.RIGHT_PARENTHESIS:
                break
            self.lexer.push(token)
            columns.append(self.match_column_definition())

            token = self.lexer.next()
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

    def match_column_definition(self):
        name_token = self.lexer.expect(TokenType.IDENTIFIER)
        type_token = self.lexer.expect(TokenType.IDENTIFIER)
        return ast.Column(name=name_token.value, type=type_token.value)


def parse(program):
    lexer = Lexer(program)
    parser = Parser(lexer)
    return parser.parse()
