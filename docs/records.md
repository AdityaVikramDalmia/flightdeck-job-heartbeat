# Record and freshness semantics

Every read result includes `job`, `status`, `age_seconds`, `reason`, and `record`.
`list` uses the same shape in an array; rows selected from hashed record filenames
also carry `storage_file` so a corrupt record can be located even when its job
identity cannot be trusted. Unexpected `.json` filenames produce an unknown row
with their filename in `reason`. An empty store produces `[]`.

| Status | Meaning |
| --- | --- |
| `fresh` | Running record, age is no greater than its TTL |
| `late` | Running record, age is greater than its TTL |
| `finished` | Terminal declaration with a valid timestamp, regardless of age |
| `missing` | No record for the requested job |
| `unknown` | Unreadable/corrupt state, unsupported schema, or a timestamp in the future |

Age is wall-clock seconds since `updated_at`. A future timestamp reports negative
age and unknown status even for a terminal record; its stored declaration remains
visible in `record`. No negative age is clamped to zero. Clock rollback makes
mutations refuse until the clock catches up or the state is deliberately repaired.
Forward clock jumps can make healthy jobs late. The tool cannot distinguish those
jumps from a real gap in reporting. It never kills, restarts, resumes, or probes a
process based on age.

The JSON record has exactly these fields:

| Field | Contract |
| --- | --- |
| `schema_version` | Integer `1` |
| `job` | Exact validated job name |
| `generation` | Random UUID hex for this run |
| `state` | `running` or `finished` |
| `started_at` | Nonnegative finite Unix wall-clock seconds |
| `updated_at` | Last accepted update time, at least `started_at` |
| `ttl_seconds` | Positive finite freshness window selected at start |
| `revision` | Positive integer; starts at 1 and increments per accepted update |
| `outcome` | Null while running; terminal outcome after finish |
| `note` | Bounded contextual text |

Record filenames are the SHA-256 of the exact ASCII job name plus `.json`. These
hashes provide stable filename mapping and case-sensitive identity, not secrecy or
authorization. The loader checks identity against the filename, exact fields,
numeric types, timestamp ordering, outcome consistency, and duplicate JSON keys.
Records larger than 64 KiB are rejected. A list is ordered by storage filename,
not by update time or human job name.
