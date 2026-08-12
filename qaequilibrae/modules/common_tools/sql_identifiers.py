def quote_identifier(name) -> str:
    """Quotes a table or column name so it can be interpolated into a statement safely.

    SQLite cannot bind an identifier the way it binds a value, so statements that name a table or
    a column have to build that part of the text themselves. Doubling any embedded quote stops a
    name from closing the identifier early and turning the rest of itself into SQL, which matters
    because some of these names reach us from user-supplied layers.
    """
    return '"' + str(name).replace('"', '""') + '"'
