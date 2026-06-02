#!/usr/bin/env python3
"""
graph.py — render a behavioral spec as a Graphviz graph.

Reads Soufflé CSV output from out/ (produced by running scripts/viz.dl)
and emits a DOT graph to stdout.

Views (2nd arg, default "states"):
  states    the state machine: modes as nodes, transitions as edges.
              - initial state : double border, green
              - running state : amber
              - unreachable   : red border (a spec bug)
              - user action   : solid dark edge
              - system action : dashed teal edge
              - counts a pomodoro : green edge labeled +1
            An invariants box lists must-reach / forbidden / only-in.
  features  feature coverage: each feature linked to the states,
            actions, and fields it is grounded in (typed by shape).

Usage:
  souffle scripts/viz.dl -D out
  python3 scripts/graph.py out states > out/spec-states.dot
  dot -Tsvg out/spec-states.dot -o out/spec-states.svg
"""
import csv
import os
import sys

# ---- palette (single source of truth; legend reads from here) ----
C_INITIAL = "#bbf7b0"
C_RUNNING = "#ffedd5"
C_STATE = "#eef2ff"
C_FEATURE = "#f5f3ff"
C_ACTION = "#fde68a"
C_FIELD = "#d1fae5"
E_USER = "#111827"
E_SYSTEM = "#0e7490"
E_COUNTS = "#15803d"
BORDER_BAD = "#dc2626"


def load(out_dir, name):
    path = os.path.join(out_dir, f"{name}.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return [row for row in csv.reader(f, delimiter="\t") if row]


def col(rows, i=0):
    return {r[i] for r in rows}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def qesc(s):
    return s.replace('"', '\\"')


def label(s):
    for p in ("S_", "A_", "F_", "f_"):
        if s.startswith(p):
            return s[len(p):].replace("_", " ")
    return s.replace("_", " ")


# ----------------------------------------------------------------------
def draw_state_machine(out_dir, p):
    """Draw the state nodes, transition edges, and invariants box.
    Shared by the 'states' and 'all' views (no header/legend/close)."""
    states = sorted(col(load(out_dir, "state")))
    initial = col(load(out_dir, "initial_state"))
    running = col(load(out_dir, "running_state"))
    reachable = col(load(out_dir, "reachable"))
    transitions = load(out_dir, "transition")            # from, via, to
    actor = {r[0]: r[1] for r in load(out_dir, "actor")}
    guards = {(r[0], r[1], r[2]): r[3] for r in load(out_dir, "guard")}
    counts = {(r[0], r[1], r[2]) for r in load(out_dir, "counts_pomodoro")}

    must_reach = sorted(col(load(out_dir, "must_reach")))
    never_action = sorted(col(load(out_dir, "never_action")))
    only_in = load(out_dir, "only_in")                   # action, state

    # state nodes
    p("\n  // states")
    for s in states:
        if s in initial:
            fill, extra = C_INITIAL, ", peripheries=2"
        elif s in running:
            fill, extra = C_RUNNING, ""
        else:
            fill, extra = C_STATE, ""
        border = f', color="{BORDER_BAD}", penwidth=2' if s not in reachable else ""
        tag = "initial" if s in initial else ("running" if s in running else "screen")
        p(f'  "{qesc(s)}" [shape=box, style="rounded,filled", fillcolor="{fill}"{extra}{border}, '
          f'label=<<b>{esc(label(s))}</b><br/>'
          f'<font point-size="8" color="#666666">{tag}</font>>];')

    # transition edges
    p("\n  // transitions")
    for fr, via, to in transitions:
        who = actor.get(via, "user")
        if (fr, via, to) in counts:
            color, style = E_COUNTS, "solid"
        elif who == "system":
            color, style = E_SYSTEM, "dashed"
        else:
            color, style = E_USER, "solid"
        parts = [f'<b>{esc(label(via))}</b>']
        g = guards.get((fr, via, to))
        if g:
            parts.append(f'<font point-size="7" color="#888888">{esc(g)}</font>')
        if (fr, via, to) in counts:
            parts.append(f'<font point-size="8" color="{E_COUNTS}">+1 pomodoro</font>')
        lbl = "<br/>".join(parts)
        p(f'  "{qesc(fr)}" -> "{qesc(to)}" '
          f'[color="{color}", style={style}, fontcolor="{color}", label=<{lbl}>];')

    # invariants box (what users can / can't do, declared)
    inv_lines = []
    for t in must_reach:
        inv_lines.append(f"always able to reach: {label(t)}")
    for a in never_action:
        inv_lines.append(f"can never: {label(a)}")
    for a, s in only_in:
        inv_lines.append(f"{label(a)} only in: {label(s)}")
    if inv_lines:
        body = "".join(f"  • {esc(x)}<br align=\"left\"/>" for x in inv_lines)
        p("\n  // invariants")
        p('  "invariants" [shape=note, fillcolor="#fef9c3", '
          f'label=<<b>Invariants (verified)</b><br align="left"/>{body}>];')


def states_legend(p):
    p("\n  // legend")
    p('  subgraph cluster_legend {')
    p('    label="Legend"; style="rounded,filled"; fillcolor="#ffffff"; color="#999999"; fontsize=11;')
    p(f'    lg_init [shape=box, style="rounded,filled", fillcolor="{C_INITIAL}", peripheries=2, label="initial state", fontsize=9];')
    p(f'    lg_run  [shape=box, style="rounded,filled", fillcolor="{C_RUNNING}", label="running state", fontsize=9];')
    p(f'    lg_scr  [shape=box, style="rounded,filled", fillcolor="{C_STATE}", label="screen", fontsize=9];')
    p('    lg_u1 [label="x", shape=point, style=invis]; lg_u2 [label="y", shape=point, style=invis];')
    p('    lg_s1 [label="x", shape=point, style=invis]; lg_s2 [label="y", shape=point, style=invis];')
    p('    lg_c1 [label="x", shape=point, style=invis]; lg_c2 [label="y", shape=point, style=invis];')
    p(f'    lg_u1 -> lg_u2 [color="{E_USER}", label="user action", fontsize=8, fontcolor="{E_USER}"];')
    p(f'    lg_s1 -> lg_s2 [color="{E_SYSTEM}", style=dashed, label="system action", fontsize=8, fontcolor="{E_SYSTEM}"];')
    p(f'    lg_c1 -> lg_c2 [color="{E_COUNTS}", label="counts a pomodoro", fontsize=8, fontcolor="{E_COUNTS}"];')
    p('    lg_init -> lg_run [style=invis]; lg_run -> lg_scr [style=invis];')
    p('  }')


def render_states(out_dir, p):
    p("digraph spec {")
    p('  rankdir=LR;')
    p('  label="Pomodoro — state machine (what the app does)"; labelloc=t; labeljust=l;')
    p('  graph [fontname="Helvetica", fontsize=14, ranksep=1.0, nodesep=0.5];')
    p('  node  [fontname="Helvetica", fontsize=11, style=filled];')
    p('  edge  [fontname="Helvetica", fontsize=9];')
    draw_state_machine(out_dir, p)
    states_legend(p)
    p("}")


# ----------------------------------------------------------------------
def render_all(out_dir, p):
    """State machine + config fields (with constraints) + feature layer."""
    fields = sorted(col(load(out_dir, "field")))
    ftype = {r[0]: r[1] for r in load(out_dir, "field_type")}
    fdef = {r[0]: r[1] for r in load(out_dir, "field_default")}
    fmin = {r[0]: r[1] for r in load(out_dir, "field_min")}
    fmax = {r[0]: r[1] for r in load(out_dir, "field_max")}
    editable_in = load(out_dir, "editable_in")           # field, state

    features = sorted(col(load(out_dir, "feature")))
    f_state = load(out_dir, "feature_state")
    f_field = load(out_dir, "feature_field")

    p("digraph spec {")
    p('  rankdir=LR;')
    p('  label="Pomodoro — full spec (behavior + config + features)"; labelloc=t; labeljust=l;')
    p('  graph [fontname="Helvetica", fontsize=14, ranksep=1.1, nodesep=0.45];')
    p('  node  [fontname="Helvetica", fontsize=11, style=filled];')
    p('  edge  [fontname="Helvetica", fontsize=9];')

    # --- the state machine core ---
    draw_state_machine(out_dir, p)

    # --- config fields, each showing its constraints ---
    p("\n  // config fields")
    p('  subgraph cluster_fields {')
    p('    label="Config fields"; style="rounded,filled"; fillcolor="#f0fdf4"; color="#86efac"; fontsize=11;')
    for x in fields:
        t = ftype.get(x, "?")
        if x in fmin and x in fmax:
            rng = f"{t} · {fmin[x]}–{fmax[x]} · default {fdef.get(x,'?')}"
        else:
            d = fdef.get(x, "")
            rng = f"{t} · default “{d}”" if d else f"{t}"
        p(f'    "{qesc(x)}" [shape=note, fillcolor="{C_FIELD}", '
          f'label=<<b>{esc(label(x))}</b><br/>'
          f'<font point-size="8" color="#555555">{esc(rng)}</font>>];')
    p('  }')
    # editable_in: field is editable in this state
    for x, s in editable_in:
        p(f'  "{qesc(x)}" -> "{qesc(s)}" '
          f'[style=dotted, color="#16a34a", arrowhead=none, label="editable in", fontsize=7, fontcolor="#16a34a"];')

    # --- features layer, grounded in states + fields ---
    p("\n  // features")
    p('  subgraph cluster_features {')
    p('    label="Features"; style="rounded,filled"; fillcolor="#faf5ff"; color="#d8b4fe"; fontsize=11;')
    for f in features:
        p(f'    "{qesc(f)}" [shape=ellipse, fillcolor="{C_FEATURE}", label="{qesc(label(f))}"];')
    p('  }')
    for f, s in f_state:
        p(f'  "{qesc(f)}" -> "{qesc(s)}" '
          f'[style=dashed, color="#c084fc", arrowhead=vee, fontsize=7];')
    for f, x in f_field:
        p(f'  "{qesc(f)}" -> "{qesc(x)}" '
          f'[style=dashed, color="#e9d5ff", arrowhead=vee];')

    states_legend(p)
    p("}")


# ----------------------------------------------------------------------
def render_features(out_dir, p):
    features = sorted(col(load(out_dir, "feature")))
    f_state = load(out_dir, "feature_state")
    f_action = load(out_dir, "feature_action")
    f_field = load(out_dir, "feature_field")

    states = {s for _, s in f_state}
    actions = {a for _, a in f_action}
    fields = {x for _, x in f_field}

    p("digraph spec {")
    p('  rankdir=LR;')
    p('  label="Pomodoro — feature coverage (features grounded in behavior)"; labelloc=t; labeljust=l;')
    p('  graph [fontname="Helvetica", fontsize=14, ranksep=1.4, nodesep=0.25];')
    p('  node  [fontname="Helvetica", fontsize=10, style=filled];')
    p('  edge  [fontname="Helvetica", fontsize=8, color="#9ca3af"];')

    p("\n  // features (left)")
    p("  { rank=source;")
    for f in features:
        p(f'    "{qesc(f)}" [shape=ellipse, fillcolor="{C_FEATURE}", label="{qesc(label(f))}"];')
    p("  }")

    p("\n  // states / actions / fields (right), typed by shape")
    for s in sorted(states):
        p(f'  "{qesc(s)}" [shape=box, style="rounded,filled", fillcolor="{C_STATE}", label="{qesc(label(s))}"];')
    for a in sorted(actions):
        p(f'  "{qesc(a)}" [shape=diamond, fillcolor="{C_ACTION}", label="{qesc(label(a))}"];')
    for x in sorted(fields):
        p(f'  "{qesc(x)}" [shape=note, fillcolor="{C_FIELD}", label="{qesc(label(x))}"];')

    p("\n  // grounding edges")
    for f, s in f_state:
        p(f'  "{qesc(f)}" -> "{qesc(s)}" [label="in"];')
    for f, a in f_action:
        p(f'  "{qesc(f)}" -> "{qesc(a)}" [label="via"];')
    for f, x in f_field:
        p(f'  "{qesc(f)}" -> "{qesc(x)}" [label="uses"];')

    p("\n  // legend")
    p('  subgraph cluster_legend {')
    p('    label="Legend"; style="rounded,filled"; fillcolor="#ffffff"; color="#999999"; fontsize=11;')
    p(f'    lg_f [shape=ellipse, fillcolor="{C_FEATURE}", label="feature", fontsize=9];')
    p(f'    lg_s [shape=box, style="rounded,filled", fillcolor="{C_STATE}", label="state", fontsize=9];')
    p(f'    lg_a [shape=diamond, fillcolor="{C_ACTION}", label="action", fontsize=9];')
    p(f'    lg_x [shape=note, fillcolor="{C_FIELD}", label="field", fontsize=9];')
    p('    lg_f -> lg_s [style=invis]; lg_s -> lg_a [style=invis]; lg_a -> lg_x [style=invis];')
    p('  }')
    p("}")


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "out"
    view = sys.argv[2] if len(sys.argv) > 2 else "states"
    if view not in ("states", "features", "all"):
        sys.exit(f"unknown view '{view}' (expected states|features|all)")
    if view == "states":
        render_states(out_dir, print)
    elif view == "features":
        render_features(out_dir, print)
    else:
        render_all(out_dir, print)


if __name__ == "__main__":
    main()
