# Job Heartbeat

> **Deprecated for new Claude Code integrations — 2026-09-22.** Retained as an
> Apache-2.0 reference project. Public launch remains deferred and the repository
> remains private. This is a maintainer status decision, not a claim that Claude
> Code replaces every capability. No ongoing feature work or support is promised.

A cooperative heartbeat and completion marker for shell jobs. A job reports its
progress; observers see whether the last report is fresh, late, or terminal.
Restarting a name creates a new generation, so an old worker cannot overwrite the
new run.

**Private candidate: 0.1.0rc1; Apache-2.0 licensed; public launch deferred.** Requires Python
3.9+ on macOS or Linux with local advisory `flock`. No packages, account, network,
model, daemon, or process discovery are involved. Windows is unsupported.

## Start, report, finish

All output is JSON. Storage is always explicit; there is no default in your home
directory or temporary directory.

```sh
HEARTBEAT="$PWD/bin/job-heartbeat"
STATE='./job state'
receipt=$("$HEARTBEAT" --dir "$STATE" start build --ttl 60)
generation=$(printf '%s' "$receipt" | python3 -c 'import json,sys; print(json.load(sys.stdin)["record"]["generation"])')
"$HEARTBEAT" --dir "$STATE" touch build "$generation" --note 'compiled sources'
"$HEARTBEAT" --dir "$STATE" read build
"$HEARTBEAT" --dir "$STATE" finish build "$generation" --outcome succeeded
"$HEARTBEAT" --dir "$STATE" list
```

An existing name cannot start accidentally. To deliberately replace its current
run, use `start build --replace "$generation" --ttl 60`. The returned generation
must be passed to subsequent `touch` and `finish` commands. A late worker carrying
the old generation receives exit 3. Starting state does not launch an OS process.

A **late** report means its configured freshness window expired. A **missing**
report means no record was found. Neither proves that a process died. A **finished**
report records the caller's terminal declaration, including `failed` or `cancelled`
outcomes; it does not certify successful work or check an OS process.

## Install and verify

```sh
make test
make demo
make install PREFIX="$HOME/.local"
```

The single `bin/job-heartbeat` executable is self-contained and can also be copied
alone. `DESTDIR` supports staged installation. The synthetic suite uses private
temporary directories, and its interruption test signals only a child it created.

The suite has been executed on macOS and in an unprivileged Alpine Linux
container with Python 3.14. See [documentation](docs/README.md)
for the CLI, schema, failure handling, and trust boundaries, and
[provenance](PROVENANCE.md) for the adaptation.

## License and maintenance

Copyright 2026 Aditya Dalmia. Licensed under [Apache-2.0](LICENSE), with
[attribution](NOTICE) and [source provenance](PROVENANCE.md). Public launch is
deferred; repository access remains private. See the [release preparation index](docs/release/README.md),
[contributing guide](CONTRIBUTING.md), and [security contact](SECURITY.md).
