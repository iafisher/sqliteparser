import enum

from attr import attrib, attrs


class OnConflict(enum.Enum):
    ROLLBACK = enum.auto()
    ABORT = enum.auto()
    FAIL = enum.auto()
    IGNORE = enum.auto()
    REPLACE = enum.auto()


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
class Column:
    name = attrib()
    type = attrib()
    constraints = attrib(factory=list)


@attrs
class CheckConstraint:
    expr = attrib()


@attrs
class NamedConstraint:
    constraint = attrib()


@attrs
class NotNullConstraint:
    on_conflict = attrib(default=OnConflict.ABORT)


@attrs
class PrimaryKeyConstraint:
    ascending = attrib(default=True)
    on_conflict = attrib(default=OnConflict.ABORT)
    autoincrement = attrib(default=False)


@attrs
class Infix:
    operator = attrib()
    left = attrib()
    right = attrib()


@attrs
class Identifier:
    value = attrib()


@attrs
class StringLiteral:
    value = attrib()
