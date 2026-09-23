# Job Heartbeat

A cooperative heartbeat and completion marker for shell jobs: a job reports its
progress, and observers see whether its last report is fresh, late, or terminal.

> **Status:** public Apache-2.0 reference implementation, deprecated for new Claude Code
> integrations as of 2026-09-22. Not a claim that Claude Code replaces every capability; no
> ongoing feature work or support is promised.

## What it does

- `start` creates a named run with a new generation and a freshness window (`--ttl`
  seconds); `touch` refreshes it; `finish` declares it `succeeded`, `failed`, or
  `cancelled`.
- `read` and `list` report each job as `fresh`, `late`, `finished`, `missing`, or
  `unknown`.
- All output is JSON. Storage is always explicit; there is no default in your home
  directory or temporary directory.

## Why it exists

From outside, a job that is still working and a job that has gone quiet look the
same, and a restarted job's old worker can still write over the new run. Job
Heartbeat makes the age of the last report visible, and restarting a name creates a
new generation, so an old worker cannot overwrite the new run: a late worker carrying
the old generation receives exit 3.

## Install

Version 0.1.0rc1. Requires Python 3.9+ on macOS or Linux with local advisory `flock`.
No packages, account, network, model, daemon, or process discovery are involved.
Windows is unsupported.

```sh
git clone https://github.com/AdityaVikramDalmia/flightdeck-job-heartbeat.git
cd flightdeck-job-heartbeat
make install PREFIX="$HOME/.local"
```

The single `bin/job-heartbeat` executable is self-contained and can also be copied
alone. `DESTDIR` supports staged installation.

## Quick use

Start, report, and finish a job from the checkout:

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
must be passed to subsequent `touch` and `finish` commands. `make demo` runs a
self-contained synthetic example of a replacement refusing the stale worker.

See [documentation](docs/README.md) for the CLI, schema, failure handling, and trust
boundaries, and [provenance](PROVENANCE.md) for the adaptation.

## Limits

- Starting state does not launch an OS process.
- A **late** report means its configured freshness window expired. A **missing**
  report means no record was found. Neither proves that a process died.
- A **finished** report records the caller's terminal declaration, including
  `failed` or `cancelled` outcomes; it does not certify successful work or check an
  OS process.

## Test

```sh
make test
make demo
```

The synthetic suite uses private temporary directories, and its interruption test
signals only a child it created. The suite has been executed on macOS and in an
unprivileged Alpine Linux container with Python 3.14.

## License and maintenance

Copyright 2026 Aditya Dalmia. Licensed under [Apache-2.0](LICENSE), with
[attribution](NOTICE) and [source provenance](PROVENANCE.md). This is a public
reference implementation, deprecated for new Claude Code integrations as of 2026-09-22. See the [release preparation index](docs/release/README.md),
[contributing guide](CONTRIBUTING.md), and [security contact](SECURITY.md).
