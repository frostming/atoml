# Change Log

## v1.0.0(2021/5/19)

- **Refactor**: Switch to new implemtation which is forked from [tomlkit](https://github.com/sdispater/tomlkit.git)
- **Refactor**: Tables and arrays now are subclasses of corresponding containers of `collections.abc` to reduce the inconsistency.
- **Bugfix**: Correctly raise `EmptyTableNameError` when one empty table name follows another table.
- **Bugfix**: Fix a bug that top level keys are added into the table unexpectedly.
- **Bugfix**: Fix the duplicate indent added to the child tables.
