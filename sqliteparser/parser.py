from ast import Not
from functools import partialmethod
from typing import List, Optional, Union

from . import ast
from .exceptions import SQLiteParserError, SQLiteParserImpossibleError
from .lexer import Lexer, TokenType


def parse(program: str, *, debug: bool = False, verbatim: bool = False) -> List[ast.Node]:
    """
    Parse the SQL program into a list of AST objects.
    """
    lexer = Lexer(program)
    parser = Parser(lexer, debug=debug, verbatim = verbatim)
    return parser.parse()


def parse_column(column_string: str, *, debug: bool = False) -> ast.Column:
    """
    Parse a single column from a ``CREATE TABLE`` statement.
    """
    lexer = Lexer(column_string)
    parser = Parser(lexer, debug=debug)
    return parser.parse_column()


def debuggable(f):
    def wrapped(self: "Parser", *args, **kwargs):
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

    lexer: Lexer
    debug: bool
    debug_indent: int

    def __init__(self, lexer: Lexer, *, debug: bool = False, verbatim: bool = False) -> None:
        self.lexer = lexer
        self.debug = debug
        self.debug_indent = 0
        self.verbatim = verbatim

    def parse(self) -> List[ast.Node]:
        statements = []
        while True:
            if self.lexer.done():
                break

            statement = self.match_statement()
            statements.append(statement)

            if not self.lexer.done():
                self.lexer.advance(expecting=[TokenType.SEMICOLON])

        return statements

    def parse_column(self) -> ast.Column:
        column = self.match_column()
        if not self.lexer.done():
            raise SQLiteParserError("trailing input")
        return column

    @debuggable
    def match_statement(self) -> ast.Node:
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
    def match_create_statement(self) -> Union[
                                            ast.CreateTableStatement,
                                            ast.CreateIndexStatement,
                                            ast.CreateTriggerStatement,
                                            ast.CreateViewStatement,
                                            ast.CreateVirtualTableStatement]:
        token = self.lexer.advance(expecting=["TABLE", "TEMPORARY", "TEMP","UNIQUE","INDEX","TRIGGER","VIEW","VIRTUAL"])
        temporary = False
        unique = False
        virtual = False
        if token.value in ("TEMPORARY", "TEMP"):
            temporary = True
            self.lexer.advance(expecting=["TABLE","TRIGGER","VIEW"])
        elif token.value == "UNIQUE":
            unique = True
            self.lexer.advance(expecting=["INDEX"])
        elif token.value == "VIRTUAL":
            virtual = True
            self.lexer.advance(expecting=["TABLE"])     
        type = self.lexer.current_token.value 
        token = self.lexer.advance(expecting=["IF", TokenType.IDENTIFIER, "TEMP"])
        if token.value == "IF":
            self.lexer.advance(expecting=["NOT"])
            self.lexer.advance(expecting=["EXISTS"])
            if_not_exists = True
            name_token = self.lexer.advance(expecting=[TokenType.IDENTIFIER])
        else:
            if_not_exists = False
            name_token = token

        token = self.lexer.advance(
            expecting=[TokenType.DOT, TokenType.LEFT_PARENTHESIS,TokenType.KEYWORD])
        if token.type == TokenType.DOT:
            table_name_token = self.lexer.advance(expecting=[TokenType.IDENTIFIER])
            name = ast.TableName(name_token.value, table_name_token.value)
            self.lexer.advance(expecting=[TokenType.LEFT_PARENTHESIS,TokenType.KEYWORD])
        else:
            name = name_token.value

        if type == "TABLE":
            if virtual:
                return self.match_create_virtual_table_statement(if_not_exists=if_not_exists,name=name)
            else:    
                return self.match_create_table_statement(if_not_exists=if_not_exists,temporary=temporary,name=name)
        elif type == "INDEX":
            return self.match_create_index_statement(if_not_exists=if_not_exists,unique=unique,name=name)
        elif type == "TRIGGER":
            return self.match_create_trigger_statement(if_not_exists=if_not_exists, name=name)
        elif type == "VIEW":
            return self.match_create_view_statement(if_not_exists=if_not_exists, name=name)
        else:
            raise SQLiteParserError(f"unknown type :{type}")    

    @debuggable
    def match_create_table_statement(self, if_not_exists, temporary, name) -> ast.CreateTableStatement:
        columns = []
        constraints: List[ast.BaseConstraint] = []
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
            if_not_exists=if_not_exists)    

    @debuggable
    def match_create_index_statement(self, if_not_exists, unique, name) -> ast.CreateIndexStatement:
        self.lexer.check(["ON"])
        token = self.lexer.advance()
        table=token.value
        self.lexer.advance(expecting=[TokenType.LEFT_PARENTHESIS])
        self.lexer.advance()
        columns = self.match_identifier_list()
        self.lexer.check([TokenType.RIGHT_PARENTHESIS])  
        token = self.lexer.advance(expecting=[TokenType.SEMICOLON,TokenType.KEYWORD])
        if token.type == TokenType.SEMICOLON:
            where= None
        else:    
            self.lexer.check(['WHERE'])
            start_index = self.lexer.index
            self.lexer.advance()
            where = self.match_expression(verbatim=self.verbatim, start_index=start_index)
   
        return ast.CreateIndexStatement(
            name=name,
            if_not_exists=if_not_exists,
            table=table,
            columns=columns,
            unique=unique,
            where=where)       

    @debuggable
    def match_create_virtual_table_statement(self, if_not_exists, name) -> ast.CreateVirtualTableStatement:
        raise NotImplementedError('Create virtual table is not yet implemented')

    @debuggable
    def match_create_trigger_statement(self, if_not_exists, name) -> ast.CreateTriggerStatement:
        raise NotImplementedError('Create trigger is not yet implemented')

    @debuggable
    def match_create_view_statement(self, if_not_exists, name) -> ast.CreateViewStatement:
        raise NotImplementedError('create view is not yet implemented')





    @debuggable
    def match_select_statement(self) -> ast.SelectStatement:
        self.lexer.advance()
        e = self.match_expression()
        return ast.SelectStatement(columns=[e])

    @debuggable
    def match_column_or_constraint(self) -> Union[ast.BaseConstraint, ast.Column]:
        token = self.lexer.current()
        if token.type == TokenType.KEYWORD and token.value == "FOREIGN":
            return self.match_foreign_key_constraint()
        elif token.type == TokenType.KEYWORD and token.value == "PRIMARY":
            return self.match_primary_key_table_constraint()
        elif token.type == TokenType.IDENTIFIER or token.type == TokenType.KEYWORD:
            return self.match_column()
        else:
            raise SQLiteParserError("expected start of column or constraint")

    @debuggable
    def match_column(self) -> ast.Column:
        # SQLite allows some but not all SQL keywords to serve as column names. We are
        # more permissive here. See #5 for details.
        name_token = self.lexer.check([TokenType.IDENTIFIER, TokenType.KEYWORD])
        if name_token.type == TokenType.KEYWORD:
            # Use ``original_value`` because it preserves the original case of the
            # identifier instead of putting it in all caps.
            name = name_token.original_value
        else:
            name = name_token.value

        assert name is not None

        column_type = self.match_column_type()
        token = self.lexer.current()
        constraints = []
        default = None
        while True:
            if token is not None and token.type == TokenType.KEYWORD:
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
                elif token.value == "NULL":
                    # Django's ORM will produce columns with a NULL constraint, and
                    # SQLite accepts it although it is not documented and appears to
                    # have no effect.
                    self.lexer.advance()
                else:
                    raise SQLiteParserError(f"unexpected keyword: {token.value}")
            else:
                break

            token = self.lexer.current()

        if column_type is None and default is None and not constraints:
            definition = None
        else:
            definition = ast.ColumnDefinition(
                type=column_type,
                default=default,
                constraints=constraints,
            )

        return ast.Column(name=name, definition=definition)

    @debuggable
    def match_column_type(self) -> Optional[Union[str, ast.ColumnType]]:
        type_token = self.lexer.advance()
        if type_token.type != TokenType.IDENTIFIER:
            return None

        token = self.lexer.advance()
        if token.type == TokenType.LEFT_PARENTHESIS:
            args = []
            while True:
                token = self.lexer.advance()
                if token.type == TokenType.RIGHT_PARENTHESIS:
                    break
                elif token.type == TokenType.INTEGER:
                    args.append(int(token.value))
                    token = self.lexer.advance()
                    if token.type == TokenType.COMMA:
                        continue
                    elif token.type == TokenType.RIGHT_PARENTHESIS:
                        break
                    else:
                        raise SQLiteParserError("expected comma or right parenthesis")

            token = self.lexer.advance()
            return ast.ColumnType(name=type_token.value, args=args)
        else:
            # SQL allows for multi-word column types, e.g. `smallint unsigned`.
            name_parts = [type_token.value]
            while token.type == TokenType.IDENTIFIER:
                name_parts.append(token.value)
                token = self.lexer.advance()
            return " ".join(name_parts)

    @debuggable
    def match_foreign_key_constraint(self) -> ast.ForeignKeyConstraint:
        self.lexer.check(["FOREIGN"])
        self.lexer.advance(expecting=["KEY"])

        self.lexer.advance(expecting=[TokenType.LEFT_PARENTHESIS])
        self.lexer.advance()
        columns = self.match_identifier_list()
        self.lexer.check([TokenType.RIGHT_PARENTHESIS])
        self.lexer.advance()
        return self.match_foreign_key_clause(columns=columns)

    @debuggable
    def match_foreign_key_clause(
        self, *, columns: List[str]
    ) -> ast.ForeignKeyConstraint:
        self.lexer.check(["REFERENCES"])

        foreign_table = self.lexer.advance(expecting=[TokenType.IDENTIFIER]).value

        token = self.lexer.advance()
        if token is not None and token.type == TokenType.LEFT_PARENTHESIS:
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
            if token is None:
                break

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
    def match_not_null_constraint(self) -> ast.NotNullConstraint:
        self.lexer.check(["NOT"])
        self.lexer.advance(expecting=["NULL"])
        token = self.lexer.advance()
        if (
            token is not None
            and token.type == TokenType.KEYWORD
            and token.value == "ON"
        ):
            on_conflict = self.match_on_conflict_clause()
        else:
            on_conflict = None
        return ast.NotNullConstraint(on_conflict=on_conflict)

    @debuggable
    def match_primary_key_constraint(self) -> ast.PrimaryKeyConstraint:
        # NOTE: Not to be confused with match_primary_key_table_constraint, which is for
        # table-level constraints.
        self.lexer.check(["PRIMARY"])
        self.lexer.advance(expecting=["KEY"])
        token = self.lexer.advance()

        if token is None or token.type != TokenType.KEYWORD:
            return ast.PrimaryKeyConstraint()

        ascending: Optional[bool]
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
    def match_primary_key_table_constraint(self) -> ast.PrimaryKeyTableConstraint:
        # NOTE: Not to be confused with match_primary_key_constraint, which is for
        # column-level constraints.
        self.lexer.check(["PRIMARY"])
        self.lexer.advance(expecting=["KEY"])

        self.lexer.advance(expecting=[TokenType.LEFT_PARENTHESIS])
        self.lexer.advance()
        columns = self.match_identifier_list()
        self.lexer.check([TokenType.RIGHT_PARENTHESIS])

        token = self.lexer.advance()
        if token.value == "ON":
            on_conflict = self.match_on_conflict_clause()
        else:
            on_conflict = None

        return ast.PrimaryKeyTableConstraint(columns=columns, on_conflict=on_conflict)

    @debuggable
    def match_check_constraint(self) -> ast.CheckConstraint:
        self.lexer.check(["CHECK"])
        self.lexer.advance(expecting=[TokenType.LEFT_PARENTHESIS])
        start_index=self.lexer.index
        self.lexer.advance()
        expr = self.match_expression(verbatim=self.verbatim, start_index=start_index)
        self.lexer.check([TokenType.RIGHT_PARENTHESIS])
        self.lexer.advance()
        return ast.CheckConstraint(expr)

    @debuggable
    def match_collate_constraint(self) -> ast.CollateConstraint:
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
    def match_unique_constraint(self) -> ast.UniqueConstraint:
        self.lexer.check(["UNIQUE"])
        token = self.lexer.advance()
        if (
            token is not None
            and token.type == TokenType.KEYWORD
            and token.value == "ON"
        ):
            on_conflict = self.match_on_conflict_clause()
        else:
            on_conflict = None
        return ast.UniqueConstraint(on_conflict=on_conflict)

    @debuggable
    def match_generated_column_constraint(self) -> ast.GeneratedColumnConstraint:
        token = self.lexer.check(["GENERATED", "AS"])
        if token.value == "GENERATED":
            self.lexer.advance(expecting=["ALWAYS"])
            self.lexer.advance(expecting=["AS"])

        self.lexer.advance(expecting=[TokenType.LEFT_PARENTHESIS])
        start_index=self.lexer.index
        self.lexer.advance()
        e = self.match_expression(verbatim=self.verbatim,start_index=start_index)
        self.lexer.check([TokenType.RIGHT_PARENTHESIS])

        token = self.lexer.advance()
        storage: Optional[ast.GeneratedColumnStorage]
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
    def match_default_clause(self) -> Union[ast.DefaultValue, ast.Node]:
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
            start_index=self.lexer.index
            self.lexer.advance()
            e = self.match_expression(verbatim=self.verbatim, start_index=start_index)
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
    def match_on_conflict_clause(self) -> ast.OnConflict:
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
    def match_expression(self, precedence: int = -1, verbatim = False,start_index=0) -> Union[ast.Expression,ast.String]:
        
        if verbatim:
            level = 0
            prev_index=self.lexer.index
            while True:
                      
                if self.lexer.current_token.type == TokenType.RIGHT_PARENTHESIS:
                    if level == 0:      
                        break
                    else:
                        level -= 1
                        if level < 0:
                            raise SQLiteParserError('unbalanced parenthesis')

                elif self.lexer.current_token.type == TokenType.LEFT_PARENTHESIS:
                    level += 1            
                prev_index=self.lexer.index
                self.lexer.advance()
                if self.lexer.current_token.type == TokenType.SEMICOLON:     
                    break  
                if self.lexer.done() :
                    if level == 0:
                        break
                    else:                
                        raise SQLiteParserError('unbalanced parenthesis')
            return ast.String(self.lexer.program[start_index:prev_index].rstrip())    

        
        left = self.match_prefix()

        while True:
            token = self.lexer.current()
            if token is None:
                break

            p = PRECEDENCE.get(token.value)
            if p is None or precedence >= p:
                break

            if token.value == "(":
                if not isinstance(left, ast.Identifier):
                    raise SQLiteParserError("function must be an identifier")

                next_token = self.lexer.advance()
                if next_token.value == "*":
                    self.lexer.advance(expecting=[TokenType.RIGHT_PARENTHESIS])
                    self.lexer.advance()
                    left = ast.Call(left, [], star=True, distinct=False)
                elif next_token.value == "DISTINCT":
                    self.lexer.advance()
                    arguments = self.match_expression_list()
                    left = ast.Call(left, arguments, star=False, distinct=True)
                else:
                    arguments = self.match_expression_list()
                    left = ast.Call(left, arguments, star=False, distinct=False)
            else:
                left = self.match_infix(left, p)
        return left

    @debuggable
    def match_infix(self, left: ast.Expression, precedence: int) -> ast.Infix:
        operator_token = self.lexer.current()
        self.lexer.advance()
        right = self.match_expression(precedence)
        return ast.Infix(operator_token.value, left, right)

    @debuggable
    def match_prefix(self) -> ast.Expression:
        token = self.lexer.current()
        if token.type == TokenType.IDENTIFIER:
            self.lexer.advance()
            return ast.Identifier(token.value)
        elif token.type == TokenType.LEFT_PARENTHESIS:
            self.lexer.advance()
            values = self.match_expression_list()
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

    def match_identifier_list(self) -> List[str]:
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

    def match_expression_list(self) -> List[ast.Expression]:
        expressions = []
        while True:
            e = self.match_expression()
            expressions.append(e)
            token = self.lexer.check([TokenType.COMMA, TokenType.RIGHT_PARENTHESIS])
            self.lexer.advance()
            if token.type == TokenType.RIGHT_PARENTHESIS:
                break
        return expressions


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
    "(": 8,
}
