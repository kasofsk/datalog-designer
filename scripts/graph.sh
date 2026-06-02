#!/usr/bin/env bash
# Render a behavioral spec to SVG + PNG via Soufflé -> DOT -> Graphviz.
#
# Usage:
#   scripts/graph.sh            # renders all views
#   scripts/graph.sh states     # one view: states | features | all

set -euo pipefail

OUT="out"
mkdir -p "$OUT"

# Evaluate, exporting the relations the renderer needs.
souffle --no-warn scripts/viz.dl -D "$OUT" 2>/dev/null

render() {
  local view="$1"
  python3 scripts/graph.py "$OUT" "$view" > "$OUT/spec-$view.dot"
  dot -Tsvg "$OUT/spec-$view.dot" -o "$OUT/spec-$view.svg"
  dot -Tpng -Gdpi=120 "$OUT/spec-$view.dot" -o "$OUT/spec-$view.png"
  echo "wrote $OUT/spec-$view.{dot,svg,png}"
}

if [[ $# -ge 1 ]]; then
  render "$1"
else
  render states
  render features
  render all
fi
