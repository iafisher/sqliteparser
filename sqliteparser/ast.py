from attr import attrib, attrs


@attrs
class CreateStatement:
    name = attrib()
    columns = attrib()
    constraints = attrib()
    as_select = attrib()
    temporary = attrib()
    without_rowid = attrib()
    if_not_exists = attrib()


@attrs
class Column:
    name = attrib()
    type = attrib()
