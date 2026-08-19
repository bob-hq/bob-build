# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.1.8] - 2026-08-19

https://github.com/bob-hq/bob/compare/v0.1.7...v0.1.8

## Changed

- Bob now supports Python 3.10 or newer.


## [0.1.7] - 2026-08-03

https://github.com/bob-hq/bob/compare/v0.1.6...v0.1.7

## Fixed

- Glob is now correctly srcdir-relative.


## [0.1.6] - 2026-07-31

https://github.com/bob-hq/bob/compare/v0.1.5...v0.1.6

## Added

- You can now use `bob_required_package_version` for generic Python package versions which should be available in Bob's Python environment.
- You can now specify `rspfile` and `rspfile_content` for a Rule, and then use the `$rspfile` variable in the rule's command or variables.

## Fixed

- `bob_required_version` for 0 majors now correctly requires a required patch version as well.


## [0.1.5] - 2026-07-30

https://github.com/bob-hq/bob/compare/v0.1.4...v0.1.5

## Added

- A `Rule` can now have `implicit`, `order_only` and `implicit_output` that are templates which are added to each built target's implicit inputs, order only inputs, and implicit outputs.
- The `shell` function now accepts a `strip` parameter that will be True by default in `0.2`.

## Fixed

- Scopes of a `ScopeList` are now closed in reverse order, so `ScopeList` has been renamed to `ScopeStack`.
- Implicit outputs are now resolved to be inside the current build directory.


## [0.1.4] - 2026-07-17

https://github.com/bob-hq/bob/compare/v0.1.3...v0.1.4

## Added

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
