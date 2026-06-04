# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A design system that treats software plans as **formal, queryable Datalog specs** (evaluated with [Soufflé](https://souffle-lang.github.io/)) instead of prose. A "plan" is not a to-do list — it is a **state machine with invariants** describing what an app does: states (UI modes), actions (user/system), transitions, config fields, features, and declared invariants. Both verification and diagram rendering read the *same facts*, so the picture cannot drift from the source.

## Commands

Requires `souffle` and `graphviz` (`brew install souffle graphviz`).

```sh
scripts/check.sh                          # verify test_projects/pomodoro.dl
scripts/check.sh path/to/other.dl         # verify a different spec
scripts/graph.sh                          # render all three diagrams to out/
scripts/graph.sh states                   # render one view: states | features | all
```

`check.sh` exits non-zero on any invariant violation. Generated CSVs and diagrams land in `out/` (gitignored).

## Architecture

Three layers, in dependency order:

1. **`dsl/schema.dl`** — the vocabulary. Declares typed predicates (`state`, `action`, `transition`, `field`, `feature`, `must_reach`, `never_action`, `only_in`, `flow`, `step`, …). Anything outside this vocabulary is unsayable — extending the language means adding predicates here.

2. **`dsl/rules.dl`** — the semantics. Two kinds of derivations:
   - **Informational views** (`reachable`, `user_available`, `can_reach`, …) used by the renderer and by `check.sh`'s printed capability table.
   - **Invariant relations** (`unreachable_state`, `missing_reach`, `forbidden_available`, `only_in_violation`, `bad_pomodoro_count`, `flow_discontinuity`, …) — each one **must be empty** for the spec to be valid.

3. **`test_projects/*.dl`** — a concrete spec. `#include`s `schema.dl` and `rules.dl`, then asserts facts (`state(...)`, `transition(...)`, `feature_state(...)`, etc.). `pomodoro.dl` is the canonical example.

`scripts/viz.dl` is a thin wrapper that `#include`s the spec and adds `.output` directives for the relations the Python renderer consumes.

`scripts/graph.py` reads the Soufflé CSV output from `out/` and emits Graphviz DOT for three views: `states` (the state machine), `features` (feature coverage), `all` (combined).

## Adding things

- **New vocabulary** → add predicates/types to `dsl/schema.dl`.
- **New invariant** → add a derived "must be empty" relation in `dsl/rules.dl` with an `.output` directive at the bottom, AND list its name in the `INVARIANTS` array in `scripts/check.sh`. Both steps are required — Soufflé only writes the CSV if `.output` is declared, and `check.sh` only fails on relations it knows to check.
- **New spec** → add `test_projects/foo.dl` that `#include`s the DSL. To render it, update the `#include` in `scripts/viz.dl` (currently hardcoded to `pomodoro.dl`); to verify it, pass the path to `check.sh`.

## Conventions worth knowing

- **State names** are conventionally `S_*`; **action names** `A_*`. Some invariants in `rules.dl` reference these names as string literals (e.g. `bad_pomodoro_count` checks for `"S_work"` and `"A_complete"`) — domain-specific structural rules like this are tied to a particular spec and live alongside the generic checks.
- **`field_default` vs `field_default_num`** — `field_default` is the display form (any type as a string); `field_default_num` is the parallel numeric form used for range checking, so text fields with non-numeric defaults aren't accidentally parsed.
- **Behaviors are still prose.** `behavior(F, "...")` is documentation Soufflé can't verify. Making behaviors *structural* (the way `counts_pomodoro` + `bad_pomodoro_count` does) is the leverage move for making them checkable.
