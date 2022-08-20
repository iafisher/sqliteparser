# sqliteparser
A parser for SQLite's dialect of SQL. Built for use by [isqlite](https://github.com/iafisher/isqlite).

Unlike [python-sqlparse](https://sqlparse.readthedocs.io/en/latest/), sqliteparser returns a full structured abstract syntax tree. Its primary purpose is to parse the `CREATE TABLE` statements that SQLite stores as the database schema. Support for parsing other kinds of statements is limited.

## Installation
Install sqliteparser with Pip:

```shell
$ pip install sqliteparser
```

## Documentation
Documentation is available at https://sqliteparser.readthedocs.io/en/latest/.
