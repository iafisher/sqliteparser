def quote(s: str) -> str:
    """
    Quotes the identifier.

    This ensures that the identifier is valid to use in SQL statements even if it
    contains special characters or is a SQL keyword.

    It DOES NOT protect against malicious input. DO NOT use this function with untrusted
    input.
    """
    if not (s.startswith('"') and s.endswith('"')):
        return '"' + s.replace('"', '""') + '"'
    else:
        return s
