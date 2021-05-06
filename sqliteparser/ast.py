import enum

from attr import attrib, attrs


class OnConflict(enum.Enum):
    ROLLBACK = enum.auto()
    ABORT = enum.auto()
    FAIL = enum.auto()
    IGNORE = enum.auto()
    REPLACE = enum.auto()


class OnDeleteOrUpdate(enum.Enum):
    SET_NULL = enum.auto()
    SET_DEFAULT = enum.auto()
    CASCADE = enum.auto()
    RESTRICT = enum.auto()
    NO_ACTION = enum.auto()


class ForeignKeyMatch(enum.Enum):
    SIMPLE = enum.auto()
    FULL = enum.auto()
    PARTIAL = enum.auto()


class CollatingSequence(enum.Enum):
    BINARY = enum.auto()
    NOCASE = enum.auto()
    RTRIM = enum.auto()


class GeneratedColumnStorage(enum.Enum):
    VIRTUAL = enum.auto()
    STORED = enum.auto()


class DefaultValue(enum.Enum):
    CURRENT_TIME = enum.auto()
    CURRENT_TIMESTAMP = enum.auto()
    CURRENT_DATE = enum.auto()


@attrs
class CreateStatement:
    name = attrib()
    columns = attrib()
    constraints = attrib(factory=list)
    as_select = attrib(default=None)
    temporary = attrib(default=False)
    without_rowid = attrib(default=False)
    if_not_exists = attrib(default=False)


@attrs
class SelectStatement:
    columns = attrib()


@attrs
class Column:
    name = attrib()
    type = attrib(default=None)
    default = attrib(default=None)
    constraints = attrib(factory=list)


@attrs
class CheckConstraint:
    expr = attrib()


@attrs
class NamedConstraint:
    constraint = attrib()


@attrs
class NotNullConstraint:
    on_conflict = attrib(default=None)


@attrs
class PrimaryKeyConstraint:
    ascending = attrib(default=None)
    on_conflict = attrib(default=None)
    autoincrement = attrib(default=False)


@attrs
class CollateConstraint:
    sequence = attrib()


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


@attrs
class UniqueConstraint:
    on_conflict = attrib()


@attrs
class GeneratedColumnConstraint:
    expression = attrib()
    storage = attrib(default=None)


@attrs
class Infix:
    operator = attrib()
    left = attrib()
    right = attrib()


@attrs
class Identifier:
    value = attrib()


@attrs
class String:
    value = attrib()


@attrs
class Blob:
    value = attrib()


@attrs
class Integer:
    value = attrib()


@attrs
class Null:
    pass


@attrs
class Boolean:
    value = attrib()


@attrs
class TableName:
    schema_name = attrib()
    table_name = attrib()
