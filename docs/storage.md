# Storage, trust, and recovery

Use a trusted directory on a local filesystem controlled by one OS account.
The tool creates new stores with mode 0700 and files with mode 0600, subject to the
process umask. Existing directory permissions are not changed. No environment
variable selects storage, job identity, or a global session registry.

All operations serialize through one persistent `.lock` using kernel advisory
`flock`. This includes reads and whole-store lists, so a listing is a consistent
snapshot among cooperating writers. Waiting uses a monotonic clock, independent
of heartbeat wall-clock age. Reads of a missing store create nothing; reads of an
existing store may create its `.lock`. A refused write may create the storage
directory and lock but never publishes a job record.

The final storage component cannot be a symlink. Lock and record files must be
regular, singly linked files; symlinks and special files are refused without
blocking on FIFOs. Directory file descriptors anchor file operations to the opened
store. Ancestor paths and concurrent external directory replacement are trusted,
not hardened against a hostile local user. Advisory locks do not stop writers
that bypass this protocol. Never delete or replace `.lock` while clients exist:
different inodes can otherwise allow independent writers under the same pathname.

Each update writes complete JSON to a unique `.pending.*` file inside the store,
closes it, and replaces the old record using same-directory rename. Readers using
the protocol see the prior or new complete record. The implementation does not
`fsync` files or directories and provides no power-loss durability guarantee.
The current record is replaced, so previous generations and notes are not retained.

INT, TERM, and HUP handlers unwind ordinary Python cleanup, release owned file
descriptors, and remove an unpublished temporary file. SIGKILL, machine failure,
and signals in the tiny interval around temporary-file acquisition can leave a
`.pending.*` file. Such files are ignored by readers and do not become a heartbeat.
Kernel locks are released when their descriptors close; no PID file is reaped.
An unavailable/closed stdout is rejected before storage is allocated or a job is
mutated. Successful JSON output is explicitly flushed so a broken pipe returns
exit 1 instead of being deferred to interpreter shutdown. A closed stderr never
redirects plain-text diagnostics into the JSON stdout channel.

An interruption or a pipe that fails after rename can still leave a successful mutation
without a receipt. Read the current record before retrying. Blindly retrying an
ordinary touch can increment the revision again; a repeated identical finish is
idempotent.

Malformed or future-dated records block their mutations, including replacement;
the tool never silently repairs them. Stop all users of the store, copy the state
for inspection, and deliberately restore a valid record or remove an unusable one.
Only then resume clients. Removing a record discards its generation history and
requires a new explicit start. Old generation tokens still cannot match the new
random generation. `.pending.*` files can be removed while all users are stopped.

A heartbeat proves only that a caller supplied the matching token and published a
report. Tokens are coordination values, not credentials. All users able to edit
the directory can forge reports. A terminal declaration is not evidence that an
OS process exited or that its work was correct.
