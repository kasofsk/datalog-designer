#!/usr/bin/env bash
# Verify a behavioral spec: run Soufflé and report invariant violations.
# Usage: scripts/check.sh plans/pomodoro.dl

set -euo pipefail

PLAN="${1:-plans/pomodoro.dl}"
OUT="out"

if [[ ! -f "$PLAN" ]]; then
  echo "error: plan not found: $PLAN" >&2
  exit 2
fi

mkdir -p "$OUT"
rm -f "$OUT"/*.csv 2>/dev/null || true

if ! souffle --no-warn "$PLAN" -D "$OUT" 2>&1; then
  echo "error: souffle evaluation failed" >&2
  exit 2
fi

# Invariant relations that MUST be empty for the spec to be valid.
INVARIANTS=(
  unknown_state_in_transition
  unknown_action_in_transition
  action_without_actor
  invalid_actor
  invalid_ftype
  bad_initial_count
  dead_end_state
  unreachable_state
  missing_reach
  forbidden_available
  only_in_violation
  field_bounds_swapped
  field_default_out_of_range
  edit_while_running
  bad_pomodoro_count
  orphan_feature
  unknown_feature_state
  unknown_feature_action
  unknown_feature_field
  flow_step_not_a_transition
  flow_discontinuity
)

VIOLATIONS=0
for rel in "${INVARIANTS[@]}"; do
  f="$OUT/$rel.csv"
  if [[ -s "$f" ]]; then
    echo "VIOLATION: $rel"
    sed 's/^/    /' "$f"
    VIOLATIONS=$((VIOLATIONS + 1))
  fi
done

echo
echo "--- reachable states ---"
[[ -s "$OUT/reachable.csv" ]] && cat "$OUT/reachable.csv" || echo "(none)"

echo
echo "--- user can do (state -> action) ---"
[[ -s "$OUT/user_available.csv" ]] && cat "$OUT/user_available.csv" || echo "(none)"

echo
if (( VIOLATIONS > 0 )); then
  echo "FAILED: $VIOLATIONS invariant violation(s)"
  exit 1
fi
echo "OK: spec is consistent"
