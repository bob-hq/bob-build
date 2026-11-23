# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.1.15] - 2026-11-24

https://github.com/bob-hq/bob/compare/v0.1.14...v0.1.15

## Added

- `shell_output_rule` now accepts `check`, which fails the build when the command fails.
- Bob now shows "Configuring" while configuring outside of Ninja when pretty is on.

## Changed

- Rule inputs, implicit dependencies, outputs, variables and `subbob` configs now accept any `Sequence` or `Mapping`. A single string where a list is expected now raises a `TypeError`.

## Fixed

- `-c KEY` without `=` is now an error rather than setting `KEY` to an empty string. Use `-c KEY=` for an empty value.
- Paths starting with `$name` are no longer expanded as Ninja variables.
- A single `Path` or target as a variable's value is now shell-quoted.
- Bob's own commands now pass `--` before operands, so paths and targets starting with `-` work.
- `-j` is now passed to Ninja when not using a jobserver, and `-j 0` works.
- `shell(..., check=False)` with a failing command no longer reconfigures forever.
- Pretty output now shows failures of `shell` commands, and no longer breaks in very narrow terminals.


## [0.1.14] - 2026-11-23

https://github.com/bob-hq/bob/compare/v0.1.13...v0.1.14

## Fixed

- Reconfiguring no longer loops forever when the Bobfile is in another directory, and now passes the build directory.
- `rootdir()` now works for source directories outside the root or given as absolute paths.
- `$` is now escaped in `shell` commands.
- `ScopedRule.build` variables now override scoped ones.
- `always` rules no longer append to the caller's `implicit` list.
- `description` and `pool` are now rejected as variable names.
- A pre-existing `MAKEFLAGS` is now restored after running the jobserver.
- `compile_commands.json` is now created after Ninja runs, and the previous one is kept when `bob compdb` fails.
- Added `__init__.py` to all subpackages so pyright resolves them.


## [0.1.13] - 2026-11-21

https://github.com/bob-hq/bob/compare/v0.1.12...v0.1.13

## Fixed

- Various issues regarding usage of scope stacks and in particular using `|` between scopes.


## [0.1.12] - 2026-10-18

https://github.com/bob-hq/bob/compare/v0.1.11...v0.1.12

## Fixed

- Some of the configure implicit dependencies are now added as phony, so Bob reconfigures if they are deleted.
- Type annotations are now accurate and work with pyright.


## [0.1.11] - 2026-10-06

https://github.com/bob-hq/bob/compare/v0.1.10...v0.1.11

## Changed

- Bob's pretty output now automatically trims the outputs when they overflow the terminal width.


## [0.1.10] - 2026-09-24

https://github.com/bob-hq/bob/compare/v0.1.9...v0.1.10

## Added

- You can now use `rootdir` in cases when you want to get out of the srcdir.


## [0.1.9] - 2026-09-19

https://github.com/bob-hq/bob/compare/v0.1.8...v0.1.9

### Added

- You can now set `unique_builddir` to False in `subbob` to make it build in the current build directory rather than a unique directory.

### Changed

- Bob's reserved build subdirectory is now `bob` instead of `.bob`.
- Subbobs are now built inside Bob's reserved build subdirectory.


## [0.1.8] - 2026-08-19

https://github.com/bob-hq/bob/compare/v0.1.7...v0.1.8

### Changed

- Bob now supports Python 3.10 or newer.


## [0.1.7] - 2026-08-03

https://github.com/bob-hq/bob/compare/v0.1.6...v0.1.7

### Fixed

- Glob is now correctly srcdir-relative.


## [0.1.6] - 2026-07-31

https://github.com/bob-hq/bob/compare/v0.1.5...v0.1.6

### Added

- You can now use `bob_required_package_version` for generic Python package versions which should be available in Bob's Python environment.
- You can now specify `rspfile` and `rspfile_content` for a Rule, and then use the `$rspfile` variable in the rule's command or variables.

### Fixed

- `bob_required_version` for 0 majors now correctly requires a required patch version as well.


### [0.1.5] - 2026-07-30

https://github.com/bob-hq/bob/compare/v0.1.4...v0.1.5

### Added

- A `Rule` can now have `implicit`, `order_only` and `implicit_output` that are templates which are added to each built target's implicit inputs, order only inputs, and implicit outputs.
- The `shell` function now accepts a `strip` parameter that will be True by default in `0.2`.

### Fixed

- Scopes of a `ScopeList` are now closed in reverse order, so `ScopeList` has been renamed to `ScopeStack`.
- Implicit outputs are now resolved to be inside the current build directory.


## [0.1.4] - 2026-07-17

https://github.com/bob-hq/bob/compare/v0.1.3...v0.1.4

### Added

- The compdb command now supports emitting the compilation database for specific targets only.

### Fixed

- The compilation database now includes the expanded value of variables correctly.


## [0.1.3] - 2026-07-07

https://github.com/bob-hq/bob/compare/v0.1.2...v0.1.3

### Fixed

- The Ninja binary that's installed by the Python package is now used for emitting the compilation database as well.


## [0.1.2] - 2026-07-07

https://github.com/bob-hq/bob/compare/v0.1.1...v0.1.2

### Fixed

- The Ninja binary that's installed by the Python package is now used when building.


## [0.1.1] - 2026-07-07

https://github.com/bob-hq/bob/compare/v0.1.0...v0.1.1

### Added

- The output of bob build is now pretty, pass `--no-pretty` or set the environment variable `BOB_NO_PRETTY` to disable it.
- The [tour](./tour) for demonstrating the syntax and featrues to new users.
- `bob_required_version` now verifies the current version of Bob when building a Bobfile.
- You can now supply Ninja arguments after `--` in the build command.

### Fixed

- The used configs are now correctly saved and restored when subbobing.
- Variables with string values no longer resolve to paths relative to the current source directory.
- You can initialize variables with `RuleInput.Multiple` in the `Rule` constructor.


## [0.1.0] - 2026-06-29

Initial release of Bob.
