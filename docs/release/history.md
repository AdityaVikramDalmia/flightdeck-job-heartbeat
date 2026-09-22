# Source history and attribution

The earliest tracked source evidence at the extraction base is below. Dates use
the original author timezone (Asia/Kolkata); the private history also retains
committer dates. Git metadata is evidence, not an independent timestamp service.

| Source mechanism | First recorded | Source commit | Latest source edit at extraction |
|---|---|---|---|
| `bin/lane-state.sh` | 2026-07-26 | `640265d89499ef5b29cc984b7e09dca007de3c4a` | 2026-07-31 |

Standalone extraction: **2026-09-22**, commit `01a3029d5736d5645902e021b051e6675e880d5e`.


The source mechanism's earlier date does not date every feature in the standalone
implementation. `PROVENANCE.md` distinguishes retained behavior, rewritten code,
and newly added contracts. In particular, portability and hardening work belongs
to the September extraction. Source history was not imported: it contains private
operational material outside this package.

Aditya Dalmia designed and maintains this work, with AI coding assistance during
implementation, extraction, and review. Upstream runtimes, language libraries, Git,
and operating-system facilities remain their authors' work. No authorship of
Claude Code or its native messaging feature is claimed.

On **2026-09-22**, the owner selected Apache-2.0 and requested private preparation
for a later public launch. This change adds the license, copyright notice, and
maintenance guidance in a new commit with its actual date. Existing history and
author/committer timestamps are preserved; the timeline is not a reconstructed
contribution graph.

The maintainer also marked all twelve repositories deprecated for new Claude Code
integrations on **2026-09-22**. This is a present maintenance decision, not a
historical claim that all utilities were replaced by native features.
