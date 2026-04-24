# Notes

## Decisions & tradeoffs

**Claude Code skill vs Standalone Python** — Went back and forth on whether to just build a Python CLI. Ended up wrapping it with a Claude Code skill to expand on the AI skills conversation we had. The Python script still works standalone, for example: (`python main.py --size 500 --industry healthcare)

**Depth over breadth on data sources** — Considered adding Azure AD, network logs, vuln scans, etc. Decided 6 solid data types with realistic imperfections beats 12 shallow ones that all look fake. AWS CloudTrail + IAM + auth events + endpoints covers enough to make the security scenarios work.

**Imperfections baked in** — Each generator has intentional imperfections (missing fields, stale refs, inconsistent tags).

**Scenarios modify baseline data in-place** — The over-permissioned user is a real employee whose IAM policy gets swapped. The credential stuffing targets real accounts. Generating scenarios as separate event streams would make them obvious and disconnected. The whole point is traceability through the data.

**Both JSON and YAML output formats** — Originally planned to split (JSON for logs, YAML for config) to match conventions. But the consumer might be a SIEM, an IaC tool, or a person.

**Generic departments, not industry-specific** — Considered per-industry org charts (healthcare with "Nursing", construction with "Field Ops") but the security scenarios don't care what the department is called. Added complexity for no real improvement in the demo output.

## What I didn't implement

These are a few additional things I'd consider implementing for a real production generator:

- **Multi-cloud** — AWS only. Spreading across three cloud surfaces would dilute depth without adding much to the security demo.
- **Network/DNS logs** — All 6 scenarios are detectable through CloudTrail + auth + IAM. Network logs might be too noisy.
- **Per-scenario toggles** — All 6 run every time. Easy to add later but premature for a prototype.
- **Database layer** — Flat files are simpler, portable, and easy to inspect.

## Technical notes

- `--seed N` for reproducible output (seeds both `random` and Faker)
- Cross-references are enforced by generation order: company first, then IAM, then events that reference both
- 500 employees / 30 days produces ~25k events across all types, generates in ~10-40s
- Python 3.10+ compatible via `from __future__ import annotations`
- Full ruff coverage (pyflakes, pylint, bugbear, bandit, isort, etc.) — zero warnings (code quality is good and has been reviewed by a linter and myself)
