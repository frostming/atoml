# Change Log

## Unreleased

### Bugfixes

- Fix a bug that empty keys aren't quoted correctly. [#23](https://github.com/frostming/atoml/issues/23)
- Fix the table name when it has been moved. [#24](https://github.com/frostming/atoml/issues/24)
- Fix a bug that replacing existing item with a table should make sure it appear after all plain values. [#25](https://github.com/frostming/atoml/issues/25)

## v1.0.3(2021/7/17)

- **Bugfix**: Fix multiline array format issue when an element is removed. [#19](https://github.com/frostming/atoml/issues/19)

## v1.0.2(2021/6/1)

- **Bugfix**: Fix multiline array format issue when a new value is appended. [#12](https://github.com/frostming/atoml/issues/12)

## v1.0.1(2021/5/20)

- **Bugfix**: Add `__repr__()` to tables and containers.
- **Bugfix**: Correctly set data into dict so that deepcopy and work rightly.

## v1.0.0(2021/5/19)

- **Refactor**: Switch to new implemtation which is forked from [tomlkit](https://github.com/sdispater/tomlkit.git)
- **Refactor**: Tables and arrays now are subclasses of corresponding containers of `collections.abc` to reduce the inconsistency.
- **Bugfix**: Correctly raise `EmptyTableNameError` when one empty table name follows another table.
- **Bugfix**: Fix a bug that top level keys are added into the table unexpectedly.
- **Bugfix**: Fix the duplicate indent added to the child tables.
