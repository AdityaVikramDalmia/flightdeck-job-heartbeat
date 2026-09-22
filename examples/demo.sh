#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
HEARTBEAT="$ROOT/bin/job-heartbeat"
fixture=$(mktemp -d "${TMPDIR:-/tmp}/job-heartbeat-demo.XXXXXX")
trap 'rm -rf -- "$fixture"' EXIT
trap 'exit 130' INT HUP TERM
state="$fixture/job state"
extract_generation() { python3 -c 'import json,sys; print(json.load(sys.stdin)["record"]["generation"])'; }
first=$("$HEARTBEAT" --dir "$state" start report-build --ttl 30 --note 'starting synthetic work')
generation=$(printf '%s' "$first" | extract_generation)
"$HEARTBEAT" --dir "$state" touch report-build "$generation" --note 'wrote fixture document' >/dev/null
second=$("$HEARTBEAT" --dir "$state" start report-build --replace "$generation" --ttl 30)
replacement=$(printf '%s' "$second" | extract_generation)
if "$HEARTBEAT" --dir "$state" touch report-build "$generation" >"$fixture/stale.out" 2>"$fixture/stale.err"; then
  printf 'stale writer unexpectedly succeeded\n' >&2; exit 1
else
  [ "$?" -eq 3 ]
fi
"$HEARTBEAT" --dir "$state" finish report-build "$replacement" --outcome succeeded >/dev/null
"$HEARTBEAT" --dir "$state" read report-build | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["status"] == "finished" and r["record"]["outcome"] == "succeeded"'
if "$HEARTBEAT" --dir "$state" touch report-build "$replacement" >"$fixture/terminal.out" 2>"$fixture/terminal.err"; then
  printf 'terminal generation unexpectedly revived\n' >&2; exit 1
else
  [ "$?" -eq 3 ]
fi
printf 'PASS: current generation finished; stale and terminal writers refused\n'
