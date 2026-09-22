# Provenance

Adapted from the cooperative contract-state mechanism in `bin/lane-state.sh` and
its contract assertions in `bin/lane-state-test.sh`, source revision
`494799eea3b9e7ce8686506a288c297ccf96be8d`.

This is a new standalone Python implementation, not a drop-in copy. It retains
caller-written heartbeat and terminal reports, age-based freshness, missing-state
uncertainty, and refusal to heartbeat after completion. It introduces explicit
storage and job names, generation comparison for safe restart, serialized updates,
validated atomic JSON publication, and explicit future-clock/corruption handling.

Agent session discovery, registry updates, transcript inspection, patrol policies,
watcher rosters, automatic nudges, and environment-specific paths were omitted.
Tests and examples use only newly generated synthetic state. No private runtime
state or service credentials are included.

Private candidate; redistribution license pending. The owner must choose licensing
and publication terms before wider distribution.
