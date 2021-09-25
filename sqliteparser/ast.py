import enum
from abc import ABC

from attr import attrib, attrs

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


class Node(ABC):
    def as_string(self, *, p):
        raise NotImplementedError

    def __str__(self):
        return self.as_string(p=True)


@attrs
class CreateTableStatement(Node):
    name = attrib()
    columns = attrib()
    constraints = attrib(factory=list)
    as_select = attrib(default=None)
    temporary = attrib(default=False)
    without_rowid = attrib(default=False)
    if_not_exists = attrib(default=False)

    def as_string(self, *, p):
        builder = ["CREATE "]
        if self.temporary:
            builder.append("TEMPORARY ")
        builder.append("TABLE ")
        if self.if_not_exists:
            builder.append("IF NOT EXISTS ")
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


@attrs
class SelectStatement(Node):
    columns = attrib()

    def as_string(self, *, p):
        raise NotImplementedError


@attrs
class Column(Node):
    name = attrib()
    definition = attrib()

    def as_string(self, *, p):
        if self.definition is None:
            return quote(self.name)
        else:
            definition = self.definition.as_string(p=False)
            return f"{quote(self.name)} {definition}"


@attrs
class ColumnDefinition(Node):
    type = attrib(default=None)
    default = attrib(default=None)
    constraints = attrib(factory=list)

    def as_string(self, *, p):
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


@attrs
class CheckConstraint(Node):
    expr = attrib()

    def as_string(self, *, p):
        e = self.expr.as_string(p=False)
        return f"CHECK({e})"


@attrs
class NamedConstraint(Node):
    name = attrib()
    constraint = attrib()

    def as_string(self, *, p):
        return f"CONSTRAINT {quote(self.name)} {self.constraint}"


@attrs
class NotNullConstraint(Node):
    on_conflict = attrib(default=None)

    def as_string(self, *, p):
        if self.on_conflict is not None:
            return f"NOT NULL {self.on_conflict}"
        else:
            return "NOT NULL"


@attrs
class PrimaryKeyConstraint(Node):
    ascending = attrib(default=None)
    on_conflict = attrib(default=None)
    autoincrement = attrib(default=False)

    def as_string(self, *, p):
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


@attrs
class CollateConstraint(Node):
    sequence = attrib()

    def as_string(self, *, p):
        return f"COLLATE {self.sequence}"


@attrs
class ForeignKeyConstraint(Node):
    columns = attrib()
    foreign_table = attrib()
    foreign_columns = attrib()
    on_delete = attrib(default=None)
    on_update = attrib(default=None)
    match = attrib(default=None)
    deferrable = attrib(default=None)
    initially_deferred = attrib(default=None)

    def as_string(self, *, p):
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


@attrs
class UniqueConstraint(Node):
    on_conflict = attrib(default=None)

    def as_string(self, *, p):
        if self.on_conflict is not None:
            return f"UNIQUE {self.on_conflict}"
        else:
            return "UNIQUE"


@attrs
class GeneratedColumnConstraint(Node):
    expression = attrib()
    storage = attrib(default=None)

    def as_string(self, *, p):
        e = self.expression.as_string(p=False)
        storage_string = "" if self.storage is None else " " + str(self.storage)
        return f"GENERATED ALWAYS AS ({e}){storage_string}"


@attrs
class Infix(Node):
    operator = attrib()
    left = attrib()
    right = attrib()

    def as_string(self, *, p):
        left = self.left.as_string(p=True)
        right = self.right.as_string(p=True)
        core = f"{left} {self.operator} {right}"
        return f"({core})" if p else core


@attrs
class ExpressionList(Node):
    values = attrib()

    def as_string(self, *, p):
        return "(" + ", ".join(v.as_string(p=False) for v in self.values) + ")"


@attrs
class Identifier(Node):
    value = attrib()

    def as_string(self, *, p):
        return quote(self.value)


@attrs
class String(Node):
    value = attrib()

    def as_string(self, *, p):
        escaped = self.value.replace("'", "''")
        return f"'{escaped}'"


@attrs
class Blob(Node):
    value = attrib()

    def as_string(self, *, p):
        return "X'" + "".join(f"{hex(b)[2:]:0>2}" for b in self.value) + "'"


@attrs
class Integer(Node):
    value = attrib()

    def as_string(self, *, p):
        return str(self.value)


@attrs
class Null(Node):
    def as_string(self, *, p):
        return "NULL"


@attrs
class Boolean(Node):
    value = attrib()

    def as_string(self, *, p):
        return "TRUE" if self.value else "FALSE"


@attrs
class TableName(Node):
    schema_name = attrib()
    table_name = attrib()

    def as_string(self, *, p):
        return f"{quote(self.schema_name)}.{quote(self.table_name)}"
