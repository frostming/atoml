# Change Log

## Unreleased

- Refactor: Switch to new implemtation which is forked from [tomlkit](https://github.com/sdispater/tomlkit.git)
- Refactor: Tables and arrays now are subclasses of corresponding containers of `collections.abc` to reduce the inconsistency.
- Bugfix: Correctly raise `EmptyTableNameError` when one empty table name follows another table.
