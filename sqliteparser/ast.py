import enum
import re
from abc import ABC
from token import OP
from typing import List, Optional, Union

from attr import Factory, attrs

from .utils import quote


class StringEnum(enum.Enum):
    def __str__(self):
        return self.name


class OnConflict(StringEnum):
    ROLLBACK = enum.auto()
    ABORT = enum.auto()
    FAIL = enum.auto()
    IGNORE = enum.auto()
    REPLACE = enum.auto()

    def __str__(self):
        return self.name


class OnDelete(StringEnum):
    SET_NULL = enum.auto()
    SET_DEFAULT = enum.auto()
    CASCADE = enum.auto()
    RESTRICT = enum.auto()
    NO_ACTION = enum.auto()

    def __str__(self):
        if self == OnDelete.SET_NULL:
            return "SET NULL"
        elif self == OnDelete.SET_DEFAULT:
            return "SET DEFAULT"
        elif self == OnDelete.NO_ACTION:
            return "NO ACTION"
        else:
            return super().__str__()


OnUpdate = OnDelete


class ForeignKeyMatch(StringEnum):
    SIMPLE = enum.auto()
    FULL = enum.auto()
    PARTIAL = enum.auto()


class CollatingSequence(StringEnum):
    BINARY = enum.auto()
    NOCASE = enum.auto()
    RTRIM = enum.auto()


class GeneratedColumnStorage(StringEnum):
    VIRTUAL = enum.auto()
    STORED = enum.auto()


class DefaultValue(StringEnum):
    CURRENT_TIME = enum.auto()
    CURRENT_TIMESTAMP = enum.auto()
    CURRENT_DATE = enum.auto()

class Trigger(StringEnum):
    BEFORE = enum.auto()
    AFTER= enum.auto()
    INSTEAD_OF = enum.auto()

    def __str__(self):
        if self == Trigger.BEFORE:
            return "BEFORE"
        elif self == Trigger.AFTER:
            return "AFTER"
        elif self == Trigger.INSTEAD_OF:
            return "INSTEAD OF"
        else:
            return super().__str__()

class Operation(StringEnum):
    DELETE = enum.auto()
    INSERT= enum.auto()
    UPDATE = enum.auto()

    def __str__(self):
        if self == Operation.DELETE:
            return "DELETE"
        elif self == Operation.INSERT:
            return "INSERT"
        elif self == Operation.UPDATE:
            return "UPDATE"
        else:
            return super().__str__()

class Node(ABC):
    def accept(self, visitor):
        """
        Accept a visitor implementing the visitor pattern.

        For example::

            class RenameVisitor:
                def __init__(self, old_name, new_name):
                    self.old_name = old_name
                    self.new_name = new_name

                def rename(self, node):
                    return node.accept(self)

                def visit_column(self, node):
                    if node.name == self.old_name:
                        return Column(self.new_name, node.definition)
                    else:
                        return node

                def visit_default(self, node):
                    return node

        The implementation uses introspection to avoid having to define ``accept``
        methods on every ``Node`` subclass and every ``visit_XYZ`` method on the visitor
        class.
        """
        name = snake_case(self.__class__.__name__)
        visit_method = getattr(visitor, "visit_" + name, None)
        if visit_method is not None:
            return visit_method(self)
        else:
            default_visit_method = getattr(visitor, "visit_default", None)
            if default_visit_method is not None:
                return default_visit_method(self)
            else:
                return None

    def as_string(self, *, p: bool) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.as_string(p=True)


class BaseConstraint(Node):
    pass


class Expression(Node):
    pass


@attrs(auto_attribs=True)
class CreateTableStatement(Node):
    """
    A SQL ``CREATE TABLE`` statement.
    """

    name: Union[str, "TableName"]
    columns: List["Column"]
    constraints: List[BaseConstraint] = Factory(list)
    as_select: Optional[Node] = None
    temporary: bool = False
    without_rowid: bool = False
    if_not_exists: bool = False

    def as_string(self, *, p: bool) -> str:
        builder = ["CREATE "]
        if self.temporary:
            builder.append("TEMPORARY ")
        builder.append("TABLE ")
        if self.if_not_exists:
            builder.append("IF NOT EXISTS ")

        if isinstance(self.name, TableName):
            builder.append(str(self.name))
        else:
            builder.append(quote(self.name))

        if self.as_select:
            builder.append(" AS ")
            builder.append(str(self.as_select))
            return "".join(builder)

        builder.append("(\n")
        for i, column in enumerate(self.columns):
            builder.append(str(column))
            if i < len(self.columns) - 1 or self.constraints:
                builder.append(",")
            builder.append("\n")

        for i, constraint in enumerate(self.constraints):
            builder.append(str(constraint))
            if i < len(self.constraints) - 1:
                builder.append(",")
            builder.append("\n")

        builder.append(")")
        if self.without_rowid:
            builder.append(" WITHOUT ROWID")

        return "".join(builder)

@attrs(auto_attribs=True)
class CreateIndexStatement(Node):
    """
    A SQL ``CREATE INDEX`` statement.
    """
    name: Union[str, "TableName"]
    table:Union[str, "TableName"]
    columns: List["Column"]
    if_not_exists: bool = False
    unique: bool = False
    where:Expression = None

@attrs(auto_attribs=True)
class CreateVirtualTableStatement(Node):
    """
    A SQL ``CREATE VIRTUAL TABLE`` statement.
    """
    name: Union[str, "TableName"]
    module:str
    arguments:Optional[List[str]]
    if_not_exists: bool = False

@attrs(auto_attribs=True)
class CreateTriggerStatement(Node):
    """
    A SQL ``CREATE TRIGGER`` statement.
    """
    name: Union[str, "TableName"]
    table:Union[str, "TableName"]
    operation:Operation
    trigger:Trigger
    when:str
    statements:List[str]
    if_not_exists: bool = False
  

@attrs(auto_attribs=True)
class CreateViewStatement(Node):
    """
    A SQL ``CREATE VIEW`` statement.
    """
    name: Union[str, "TableName"]
    tables: List[Union[str, "TableName"]]
    if_not_exists: bool = False
    






@attrs(auto_attribs=True)
class SelectStatement(Node):
    """
    A SQL ``SELECT`` statement.
    """

    columns: List[Expression]

    def as_string(self, *, p: bool) -> str:
        raise NotImplementedError


@attrs(auto_attribs=True)
class Column(Node):
    name: str
    definition: Optional["ColumnDefinition"]

    def as_string(self, *, p: bool) -> str:
        if self.definition is None:
            return quote(self.name)
        else:
            definition = self.definition.as_string(p=False)
            return f"{quote(self.name)} {definition}"


@attrs(auto_attribs=True)
class ColumnType(Node):
    name: str
    args: List[int]

    def as_string(self, *, p: bool) -> str:
        joined_args = ", ".join(map(str, self.args))
        return f"{quote(self.name)}({joined_args})"


@attrs(auto_attribs=True)
class ColumnDefinition(Node):
    type: Optional[Union[ColumnType, str]] = None
    default: Optional[Expression] = None
    constraints: List[BaseConstraint] = Factory(list)

    def as_string(self, *, p: bool) -> str:
        builder = []
        if self.type is not None:
            builder.append(" ")
            builder.append(str(self.type))

        for constraint in self.constraints:
            builder.append(" ")
            builder.append(str(constraint))

        if self.default is not None:
            builder.append(" DEFAULT ")
            builder.append(str(self.default))

        return "".join(builder)


@attrs(auto_attribs=True)
class CheckConstraint(BaseConstraint):
    expr: Expression

    def as_string(self, *, p: bool) -> str:
        e = self.expr.as_string(p=False)
        return f"CHECK({e})"


@attrs(auto_attribs=True)
class NamedConstraint(BaseConstraint):
    name: str
    constraint: BaseConstraint

    def as_string(self, *, p: bool) -> str:
        return f"CONSTRAINT {quote(self.name)} {self.constraint}"


@attrs(auto_attribs=True)
class NotNullConstraint(BaseConstraint):
    on_conflict: Optional[OnConflict] = None

    def as_string(self, *, p: bool) -> str:
        if self.on_conflict is not None:
            return f"NOT NULL {self.on_conflict}"
        else:
            return "NOT NULL"


@attrs(auto_attribs=True)
class PrimaryKeyConstraint(BaseConstraint):
    # NOTE: This is for a PRIMARY KEY constraint on a single column. For a multi-
    # column table-level constraint, see PrimaryKeyTableConstraint.
    ascending: Optional[bool] = None
    on_conflict: Optional[OnConflict] = None
    autoincrement: bool = False

    def as_string(self, *, p: bool) -> str:
        builder = ["PRIMARY KEY"]
        if self.ascending is not None:
            if self.ascending:
                builder.append(" ASC")
            else:
                builder.append(" DESC")

        if self.on_conflict is not None:
            builder.append(" ")
            builder.append(str(self.on_conflict))

        if self.autoincrement:
            builder.append(" AUTOINCREMENT")

        return "".join(builder)


@attrs(auto_attribs=True)
class PrimaryKeyTableConstraint(BaseConstraint):
    # NOTE: This is for a table-level PRIMARY KEY constraint. For a constraint on an
    # individual column, see PrimaryKeyConstraint.
    columns: List[str]
    on_conflict: Optional[OnConflict] = None

    def as_string(self, *, p: bool) -> str:
        builder = ["PRIMARY KEY ("]
        for i, column in enumerate(self.columns):
            builder.append(column)
            if i != len(self.columns) - 1:
                builder.append(", ")
        builder.append(")")

        if self.on_conflict is not None:
            builder.append(" ")
            builder.append(str(self.on_conflict))

        return "".join(builder)


@attrs(auto_attribs=True)
class CollateConstraint(BaseConstraint):
    sequence: CollatingSequence

    def as_string(self, *, p: bool) -> str:
        return f"COLLATE {self.sequence}"


@attrs(auto_attribs=True)
class ForeignKeyConstraint(BaseConstraint):
    columns: List[str]
    foreign_table: str
    foreign_columns: List[str]
    on_delete: Optional[OnDelete] = None
    on_update: Optional[OnUpdate] = None
    match: Optional[ForeignKeyMatch] = None
    deferrable: Optional[bool] = None
    initially_deferred: Optional[bool] = None

    def as_string(self, *, p: bool) -> str:
        builder = []
        if self.columns:
            builder.append("FOREIGN KEY (")
            builder.append(", ".join(map(str, self.columns)))
            builder.append(" ")

        builder.append("REFERENCES ")
        builder.append(self.foreign_table)
        if self.foreign_columns:
            builder.append("(")
            builder.append(", ".join(map(str, self.foreign_columns)))
            builder.append(")")

        if self.on_delete:
            builder.append(f" ON DELETE {self.on_delete}")

        if self.on_update:
            builder.append(f" ON UPDATE {self.on_update}")

        if self.match:
            builder.append(f" MATCH {self.match}")

        if self.deferrable is not None:
            builder.append(" ")
            if not self.deferrable:
                builder.append("NOT")
            builder.append(" DEFERRABLE")

            if self.initially_deferred is not None:
                builder.append(" INITIALLY ")
                builder.append("DEFERRED" if self.initially_deferred else "IMMEDIATE")

        return "".join(builder)


@attrs(auto_attribs=True)
class UniqueConstraint(BaseConstraint):
    on_conflict: Optional[OnConflict] = None

    def as_string(self, *, p: bool) -> str:
        if self.on_conflict is not None:
            return f"UNIQUE {self.on_conflict}"
        else:
            return "UNIQUE"


@attrs(auto_attribs=True)
class GeneratedColumnConstraint(BaseConstraint):
    expression: Expression
    storage: Optional[GeneratedColumnStorage] = None

    def as_string(self, *, p: bool) -> str:
        e = self.expression.as_string(p=False)
        storage_string = "" if self.storage is None else " " + str(self.storage)
        return f"GENERATED ALWAYS AS ({e}){storage_string}"


@attrs(auto_attribs=True)
class Infix(Expression):
    operator: str
    left: Expression
    right: Expression

    def as_string(self, *, p: bool) -> str:
        left = self.left.as_string(p=True)
        right = self.right.as_string(p=True)
        core = f"{left} {self.operator} {right}"
        return f"({core})" if p else core


@attrs(auto_attribs=True)
class Call(Expression):
    function: "Identifier"
    arguments: List[Expression]
    star: bool = False
    distinct: bool = False

    def as_string(self, *, p: bool) -> str:
        function_string = self.function.as_string(p=False)
        if self.star:
            arguments_string = "*"
        else:
            arguments_string = ", ".join(
                arg.as_string(p=False) for arg in self.arguments
            )
            if self.distinct:
                arguments_string = "DISTINCT " + arguments_string
        return f"{function_string}({arguments_string})"


@attrs(auto_attribs=True)
class ExpressionList(Expression):
    values: List[Expression]

    def as_string(self, *, p: bool) -> str:
        return "(" + ", ".join(v.as_string(p=False) for v in self.values) + ")"


@attrs(auto_attribs=True)
class Identifier(Expression):
    value: str

    def as_string(self, *, p: bool) -> str:
        return quote(self.value)


@attrs(auto_attribs=True)
class String(Expression):
    value: str

    def as_string(self, *, p: bool) -> str:
        escaped = self.value.replace("'", "''")
        return f"'{escaped}'"


@attrs(auto_attribs=True)
class Blob(Expression):
    value: bytes

    def as_string(self, *, p: bool) -> str:
        return "X'" + "".join(f"{hex(b)[2:]:0>2}" for b in self.value) + "'"


@attrs(auto_attribs=True)
class Integer(Expression):
    value: int

    def as_string(self, *, p: bool) -> str:
        return str(self.value)


@attrs(auto_attribs=True)
class Null(Expression):
    def as_string(self, *, p: bool) -> str:
        return "NULL"


@attrs(auto_attribs=True)
class Boolean(Expression):
    value: bool

    def as_string(self, *, p: bool) -> str:
        return "TRUE" if self.value else "FALSE"


@attrs(auto_attribs=True)
class TableName(Node):
    schema_name: str
    table_name: str

    def as_string(self, *, p: bool) -> str:
        return f"{quote(self.schema_name)}.{quote(self.table_name)}"


def snake_case(s: str) -> str:
    def snake_case_replacer(match: re.Match) -> str:
        text = match.group(0)
        return text[0] + "_" + text[1]

    name = re.sub(r"[a-z][A-Z]", snake_case_replacer, s)
    return name.lower()
