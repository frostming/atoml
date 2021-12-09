# Change Log

## Unreleased

### Bugfixes

- Fix a bug that `OutOfTableProxy` causes the embeded element to be updated. [#43](https://github.com/frostming/atoml/issues/43)

## v1.1.0(2021/11/1)

### Features

- Add a new method `add_line` to `Array` to control the format. [#39](https://github.com/frostming/atoml/issues/39)

### Bugfixes

- Fix a bug that empty keys aren't quoted correctly. [#23](https://github.com/frostming/atoml/issues/23)
- Fix the table name when it has been moved. [#24](https://github.com/frostming/atoml/issues/24)
- Fix a bug that replacing existing item with a table should make sure it appear after all plain values. [#25](https://github.com/frostming/atoml/issues/25)
- Fix a bug when dumping lists containing both dicts and other items [#35](https://github.com/frostming/atoml/issues/35)
- Prevent sequence of actions (remove items, add whitespace, add table) to result in incorrect TOML. [#28](https://github.com/frostming/atoml/pull/28)
- Prevent dicts appended to existing array to result in invalid syntax. [#26](https://github.com/frostming/atoml/issues/26)
- Prevent invalid `","` to appear when inserting elements to empty array. [#27](https://github.com/frostming/atoml/pull/27)
- Fix a bug that missing `=` between k-v pair doesn't raise an parsing error.

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
