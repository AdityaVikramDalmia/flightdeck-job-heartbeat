# Job Heartbeat

Use [.agents/skills/job-heartbeat-maintainer/SKILL.md](.agents/skills/job-heartbeat-maintainer/SKILL.md)
for work in this repository. Contracts and installation start at [README.md](README.md).

- Preserve generation checks, serialized updates, terminal states, and explicit storage. A late heartbeat is not proof that a process died.
- Release record: [docs/release/README.md](docs/release/README.md).
- Run `make test` and relevant documented demos before committing changes.
- Keep tests synthetic and isolated; preserve unrelated user edits.
- Keep source-history dates truthful and retain license/notice attribution.
- The repository is public. Do not change visibility or modify the original
  Flightdeck runtime while maintaining this component.

These are deprecated reference artifacts for new Claude Code integrations as of
2026-09-22. Preserve that status in README, examples, skills, and release material;
do not imply native feature equivalence without evidence.
