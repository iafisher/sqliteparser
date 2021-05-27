import enum

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


class OnDeleteOrUpdate(StringEnum):
    SET_NULL = enum.auto()
    SET_DEFAULT = enum.auto()
    CASCADE = enum.auto()
    RESTRICT = enum.auto()
    NO_ACTION = enum.auto()


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


@attrs
class CreateTableStatement:
    name = attrib()
    columns = attrib()
    constraints = attrib(factory=list)
    as_select = attrib(default=None)
    temporary = attrib(default=False)
    without_rowid = attrib(default=False)
    if_not_exists = attrib(default=False)

    def __str__(self):
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
class SelectStatement:
    columns = attrib()

    def __str__(self):
        raise NotImplementedError


@attrs
class Column:
    name = attrib()
    type = attrib(default=None)
    default = attrib(default=None)
    constraints = attrib(factory=list)

    def __str__(self):
        builder = [quote(self.name)]
        if self.type is not None:
            builder.append(" ")
            builder.append(str(self.type))

        if self.default is not None:
            builder.append(" DEFAULT ")
            builder.append(str(self.default))

        for constraint in self.constraints:
            builder.append(" ")
            builder.append(str(constraint))

        return "".join(builder)


@attrs
class CheckConstraint:
    expr = attrib()

    def __str__(self):
        return f"CHECK {self.expr}"


@attrs
class NamedConstraint:
    name = attrib()
    constraint = attrib()

    def __str__(self):
        return f"CONSTRAINT {quote(self.name)} {self.constraint}"


@attrs
class NotNullConstraint:
    on_conflict = attrib(default=None)

    def __str__(self):
        if self.on_conflict is not None:
            return f"NOT NULL {self.on_conflict}"
        else:
            return "NOT NULL"


@attrs
class PrimaryKeyConstraint:
    ascending = attrib(default=None)
    on_conflict = attrib(default=None)
    autoincrement = attrib(default=False)

    def __str__(self):
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
class CollateConstraint:
    sequence = attrib()

    def __str__(self):
        return f"COLLATE {self.sequence}"


@attrs
class ForeignKeyConstraint:
    columns = attrib()
    foreign_table = attrib()
    foreign_columns = attrib()
    on_delete = attrib(default=None)
    on_update = attrib(default=None)
    match = attrib(default=None)
    deferrable = attrib(default=None)
    initially_deferred = attrib(default=None)

    def __str__(self):
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
class UniqueConstraint:
    on_conflict = attrib(default=None)

    def __str__(self):
        if self.on_conflict is not None:
            return f"UNIQUE {self.on_conflict}"
        else:
            return "UNIQUE"


@attrs
class GeneratedColumnConstraint:
    expression = attrib()
    storage = attrib(default=None)

    def __str__(self):
        storage_string = "" if self.storage is None else " " + str(self.storage)
        return f"GENERATED ALWAYS AS ({self.expression}){storage_string}"


@attrs
class Infix:
    operator = attrib()
    left = attrib()
    right = attrib()

    def __str__(self):
        return f"({self.left}) {self.operator} ({self.right})"


@attrs
class Identifier:
    value = attrib()

    def __str__(self):
        return quote(self.value)


@attrs
class String:
    value = attrib()

    def __str__(self):
        escaped = self.value.replace("'", "''")
        return f"'{escaped}'"


@attrs
class Blob:
    value = attrib()

    def __str__(self):
        return "X'" + "".join(f"{hex(b)[2:]:0>2}" for b in self.value) + "'"


@attrs
class Integer:
    value = attrib()

    def __str__(self):
        return str(self.value)


@attrs
class Null:
    def __str__(self):
        return "NULL"


@attrs
class Boolean:
    value = attrib()

    def __str__(self):
        return "TRUE" if self.value else "FALSE"


@attrs
class TableName:
    schema_name = attrib()
    table_name = attrib()

    def __str__(self):
        return f"{quote(self.schema_name)}.{quote(self.table_name)}"
