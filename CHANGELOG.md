# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

## Added

- `run`, which is like `shell` but runs a program with a list of arguments rather than a shell command line, so arguments never need quoting. It runs in the srcdir by default and strips its output by default.

## Fixed

- Escaping throughout Bob's generated commands and Ninja files, so paths with spaces, quotes, `$` or a leading `-` work:
  - Paths in the Ninja file starting with `$name` are no longer expanded as Ninja variables, and paths with newlines are rejected.
  - A single `Path` or target as a variable's value is now shell-quoted, like the elements of a list.
  - Bob's own commands pass `--` before operands (`cmp`, `mv`, `rm`, `sh -c`, and targets passed to Ninja) and attach option values with `=`.
  - Ninja's `builddir` (where it keeps its log) is escaped.
- `shell` commands can now contain `$` (e.g. `shell("echo $HOME")`). Previously Ninja interpreted it, so such commands either failed to configure or reconfigured forever.
- Reconfiguring now respects `--builddir` (and `--allow-build-outside-builddir`); previously editing a Bobfile broke builds in any non-default build directory. Build directories configured by older versions must be cleaned once.
- Using a Bobfile outside the current directory (e.g. `bob build -f sub/Bobfile`) no longer loops reconfiguring forever.
- `shell_output_rule` commands that fail now fail the build, and `shell(..., check=False)` with a failing command no longer reconfigures forever.
- `-j` is now passed to Ninja when not using a jobserver, `-j 0` (unlimited jobs) works, and a negative `-j` is rejected.
- `compile_commands.json` is created after Ninja reconfigures, so it's no longer one build behind; `bob compdb` reconfigures if needed.
- A failing `bob compdb` reports Ninja's error and keeps the previous `compile_commands.json`.
- Building with an `always` rule no longer appends to the caller's `implicit` list, and a `Rule` no longer shares the `implicit`, `order_only` and `implicit_outputs` lists passed to it.
- Variables passed to `ScopedRule.build` take precedence over scoped variables, and the caller's dictionary is no longer mutated.
- `description` and `pool` are rejected as variable names, like the other special Ninja variables.
- Rule descriptions with non-ASCII letters (e.g. `ÜBERSETZEN`) no longer produce invalid Ninja rule names.
- `rootdir()` is now correct for srcdirs outside of the root or given as absolute paths.
- `include` no longer overwrites the includer's `__file__` and other module metadata.
- The jobserver restores a pre-existing `MAKEFLAGS` rather than deleting it.
- Pretty printing now shows failures of `shell` commands, and handles very narrow terminals.
- With `-B .`, pretty printing no longer shows the progress of `shell` and `run` commands, and tab completion no longer offers Bob's internal targets.
- `rootdir()` no longer fails on Windows when the srcdir is on another drive; it's absolute instead.
- `shell` and `run` commands whose output depends on `FORCE_COLOR` or `CLICOLOR_FORCE` no longer reconfigure forever. Bob sets these for its own output, so captured commands no longer see them, nor `NINJA_STATUS`.
- Version checks accept versions such as `0.2.0.dev1`. A pre-release doesn't satisfy a requirement of the version it precedes (`0.2.0.dev1` doesn't satisfy `0.2.0`).
- Clearer errors for malformed `-c` configs, missing required configs, `--use-current-configs` before configuring, and rules of the wrong kind set on a `ScopedRule`.
- `bob completions fish` works when Bob's path contains spaces.
- The tour's `Makefile` is now committed, and the README's `bob compdb` example uses the current subbob build directory.

## Changed

- **Breaking:** `-c KEY` without `=` is now an error rather than setting `KEY` to an empty string. Use `-c KEY=` for an empty value.
- Rule inputs, implicit dependencies, implicit outputs, variables and `subbob` configs now accept any `Sequence`/`Mapping`, so e.g. a `list[FileTarget]` or the result of `glob` type-checks as inputs. A single string (e.g. `inputs="main.c"`) raises a `TypeError` rather than being split into characters.
- `ScopedValue.get()` is typed as returning the value (not `None`) when required, and `default` is only accepted with `required=False`.
- `Variable.add` is now typed, and raises a `TypeError` when adding a list to a string variable or vice versa.
- `shell_output_rule` accepts `check`.
- `shell` now reruns its command on every build through Bob itself (`python -m bob._capture`) rather than through a shell pipeline, so the configure-time and build-time runs are identical. The command's standard error is now shown while configuring.

## Deprecated

- `Context.variables` and `Context.srcdir`, which Bob no longer uses. They will be removed in 0.2. Bob's own counters (`rule_index`, `shell_index` and `subbob_index`) are no longer kept in `Context.variables`.


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
