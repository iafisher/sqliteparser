def quote(s):
    """
    Quotes the identifier.

    This ensures that the identifier is valid to use in SQL statements even if it
    contains special characters or is a SQL keyword.
    """
    if not (s.startswith('"') and s.endswith('"')):
        return '"' + s.replace('"', '""') + '"'
    else:
        return s
