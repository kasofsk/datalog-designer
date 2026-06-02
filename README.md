# Datalog Designer — statically verifiable design specs

A design system for writing software plans as **formal, queryable specifications**
instead of prose.

Markdown plans drift: a statement on page 1 quietly contradicts one on page 7 and
nothing catches it. Specs are written in **Datalog** (evaluated with
[Soufflé](https://souffle-lang.github.io/)), so every statement about the plan is
made in a formal language and can be *checked*: it either belongs to the language
or it doesn't, follows from the facts or it doesn't, is consistent with the rest of
the spec or it isn't.

A plan here is not a to-do list. It describes **what the app does** — its modes, the
actions a user or the system can take, the config the user controls, and the
**invariants** that say what users can and can't do. From the same facts we
*verify* the spec and *project* diagrams of it, so the picture can never drift from
the source.

## Why Datalog (not Prolog)

Verifiability is the whole point, and Datalog is decidable: every query terminates,
the full set of derivable facts is computable, and consistency can be checked
mechanically. Prolog trades all of that for Turing-completeness — "does X follow?"
can hang, and "is this consistent?" is undecidable in general. Soufflé adds types,
aggregation, and stratified negation, which closes most of the expressiveness gap
without giving up decidability.

## The model

A plan is a **state machine with invariants**. The vocabulary (the DSL) is defined
in `dsl/schema.dl`:

| Concept       | Predicate(s)                                  | Meaning                                          |
|---------------|-----------------------------------------------|--------------------------------------------------|
| **State**     | `state`, `initial_state`, `running_state`     | a mode the app can be in                         |
| **Action**    | `action`, `actor`                             | what causes a move; triggered by `user`/`system` |
| **Transition**| `transition`, `guard`, `effect`               | `(state, action) -> state`, optionally guarded   |
| **Field**     | `field`, `field_type`, `field_min/max`, …     | a config input and its constraints               |
| **Feature**   | `feature`, `feature_state/action/field`       | a user-visible capability, grounded in the above |
| **Invariant** | `must_reach`, `never_action`, `only_in`       | declared truths about what users can / can't do  |
| **Flow**      | `flow`, `step`                                | a named user journey (sequence of transitions)   |

Anything outside this vocabulary is unsayable — which is what makes the spec
checkable.

## Layout

```
dsl/
  schema.dl        # the DSL: predicates + types (the grammar of a spec)
  rules.dl         # derivations + invariant checks (the semantics)
test_projects/
  pomodoro.dl      # an example spec: a vanilla-web pomodoro timer
scripts/
  check.sh         # run Soufflé, report any invariant violation
  viz.dl           # re-exports the relations the renderer consumes
  graph.py         # CSV -> Graphviz DOT
  graph.sh         # check + render the diagrams (states / features / all)
out/               # generated CSVs and diagrams (gitignored)
```

A spec file is just **facts**: it `#include`s `dsl/schema.dl` (vocabulary) and
`dsl/rules.dl` (checks), then asserts the states, actions, transitions, fields,
features, invariants, and flows for that app.

## Usage

Requires `souffle` and `graphviz` (`brew install souffle graphviz`).

```sh
# verify a spec — fails if any invariant is violated
scripts/check.sh                          # defaults to test_projects/pomodoro.dl
scripts/check.sh test_projects/pomodoro.dl

# render the diagrams to out/spec-*.{svg,png}
scripts/graph.sh                          # all three views
scripts/graph.sh states                   # one view: states | features | all
```

`check.sh` prints any violations, then the derived **capability table**
("what the user can do in each state", computed from the transition relation) and
exits non-zero if the spec is inconsistent.

### Diagram views

- **states** — the state machine. Initial state has a double green border; running
  states are amber; an unreachable state would show a red border. User actions are
  solid edges, system actions dashed; edges that count a pomodoro are green. An
  invariants box lists the verified must-reach / forbidden / only-in rules.
- **features** — each feature linked to the states, actions, and fields it is
  grounded in (typed by shape).
- **all** — the state machine plus the config fields (with their constraints) and
  the feature layer, on one canvas.

## What gets verified

`dsl/rules.dl` derives a set of relations that **must be empty**; `check.sh` fails
the build if any is not. Among them:

- **Referential integrity** — transitions/features can't point at undeclared
  states, actions, or fields.
- **Well-formedness** — exactly one initial state; no dead-end (non-terminal state
  with no exit); no unreachable state.
- **Liveness** — `must_reach(home)`: from every reachable state the user can get
  back home (i.e. can always quit).
- **Capabilities** — `never_action(pause)`, `never_action(reset)`: these must not
  be available anywhere. `only_in(edit, home)`: config is editable only at home,
  never while a timer runs.
- **Field constraints** — min ≤ max, and each default within its range.
- **Domain rule (strict counter)** — only a `work --complete--> break` transition
  may count a pomodoro, so skipping or stopping structurally cannot inflate the
  count. A future edit that violated this would fail the build.
- **Flow integrity** — every step of a named flow is a real transition, and
  consecutive steps chain.

Because the diagrams and the checks read the *same facts*, they can't disagree with
each other or with the spec.

## Extending

- **New vocabulary** → add predicates/types to `dsl/schema.dl`.
- **New invariant** → add a derived "must be empty" relation to `dsl/rules.dl` and
  list it in the `INVARIANTS` array in `scripts/check.sh`.
- **New spec** → add a `*.dl` file under `test_projects/` that includes the DSL and
  asserts its facts. (Point `scripts/viz.dl` and `scripts/check.sh` at it, or pass
  the path to `check.sh`.)

## Status / known rough edges

- **Behaviors are still prose.** `behavior(F, "...")` is documentation Soufflé can't
  check against anything. The leverage move is making more behaviors *structural*
  (as the strict-counter rule already is) so they become verifiable.
- **Fact-level boilerplate.** A feature is ~6–10 facts. Fine at this scale; a thin
  authoring CLI or templating is where it would start to pay off.
- **`viz.dl` hardcodes one spec path.** Fine for a single example; would be
  parameterized for a multi-spec setup.
