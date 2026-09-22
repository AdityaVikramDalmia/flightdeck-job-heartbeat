# Commands and exit codes

Global arguments precede the command: `job-heartbeat --dir PATH
[--lock-timeout SECONDS] COMMAND`. The lock wait defaults to five seconds and must
be finite and nonnegative. `--version` and `--help` work without a storage path.

| Command | Behavior |
| --- | --- |
| `start JOB [--ttl SECONDS] [--note TEXT]` | Create a new generation; refuse if a record already exists |
| `start JOB --replace GENERATION ...` | Replace exactly that current generation, running or finished |
| `touch JOB GENERATION [--note TEXT]` | Refresh a running generation and increment its revision |
| `finish JOB GENERATION [--outcome VALUE] [--note TEXT]` | Declare the generation terminal |
| `read JOB` | Emit one report |
| `list` | Emit an array of reports for stored JSON records |

TTL defaults to 60 seconds and must be finite and greater than zero. Outcomes are
`succeeded` (default), `failed`, or `cancelled`. Notes are capped at 4096 UTF-8
bytes; an omitted note retains the previous note on touch/finish. This is current
state, not an event history. Use a separate ledger if every transition must remain.

Names are 1–128 ASCII letters, digits, dots, underscores, or hyphens and must begin
with a letter or digit. Names are exact and case-sensitive even on case-insensitive
filesystems. Spaces, slashes, traversal paths, and control characters are rejected.
The storage directory itself may contain spaces. Generations are opaque 32-character
lowercase hexadecimal values; callers must use the value returned by `start`.

A repeated `finish` for the same generation and outcome is idempotent: timestamps,
revision, and note remain unchanged, including when the retry supplied a new note.
A different outcome is refused. `touch` never revives a terminal generation.
`--replace` provides comparison against current state; two callers replacing the
same old generation cannot both succeed.

| Exit | Meaning |
| ---: | --- |
| 0 | Operation completed; read/list may still report `late`, `missing`, or a failed outcome |
| 1 | Storage, schema, clock, interruption, or I/O error; read/list report `unknown` where possible |
| 2 | Invalid CLI arguments |
| 3 | Missing generation, stale generation, existing-job start, or terminal-state conflict |
| 75 | Storage lock timed out; operation was not performed |

Errors print a diagnostic to stderr when it is available. Closed stderr suppresses
the diagnostic rather than contaminating JSON stdout. A missing stdout refuses
the command with exit 1 before mutation; a later output failure also returns 1. Read/list preserve known reports when another
record is corrupt and return 1 if any report is unknown. Timeout emits no report;
callers must inspect the exit code, not interpret absent output as missing state.
