# generate-mock-data

A Claude Code skill that generates realistic security demo data for fictional companies. Feed it a short prompt like `500 person healthcare company` and it produces internally consistent CloudTrail logs, auth events, endpoint telemetry, IAM configurations, and embedded security scenarios — all with the realistic imperfections (missing fields, stale accounts, inconsistent tags) that make demo data believable.

## Overview

This tool solves a common problem: most demo environments fail because the data is either too clean or obviously fake. This generator creates a complete, internally consistent security environment for a fictional company with the intentionally flawed data throughout (orphaned accounts, inconsistent tags, partial MFA rollouts).

The primary interface is a **Claude Code skill** that accepts a natural-language prompt. Python generators handle the actual data creation, producing both JSON and YAML output across 6 data types and 6 security scenarios.

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Project overview, installation, usage, and output reference |
| [ASSIGNMENT.md](ASSIGNMENT.md) | Original assignment and evaluation criteria |
| [PLAN.md](PLAN.md) | Implementation plan — architecture, data flow, skill design, and verification steps |
| [NOTES.md](NOTES.md) | Design decisions, tradeoffs, and what was intentionally left out |

## Requirements

- **Python 3.10+** (tested on 3.14.3)
- **Claude Code** (for the `/generate-mock-data` skill interface)

### Python Dependencies

- `faker` (>=28.0) — realistic identity data generation
- `pyyaml` (>=6.0) — YAML output serialization

## Installation

### From GitHub Release

1. Download the latest release (`.zip` or `.tar.gz`) from the [Releases](../../releases) page
2. Extract the archive:
   ```bash
   # zip
   unzip generate-mock-data-v0.1.0.zip
   cd generate-mock-data-v0.1.0

   # or tarball
   tar -xzf generate-mock-data-v0.1.0.tar.gz
   cd generate-mock-data-v0.1.0
   ```
3. Install Python dependencies:
   ```bash
   pip install faker pyyaml
   ```

### From Source

```bash
git clone https://github.com/zantinelli/generate-mock-data.git
cd generate-mock-data
pip install faker pyyaml
```

### Claude Code Setup

The skill is automatically available when you open this project in Claude Code. No additional configuration needed — Claude Code detects the `.claude/skills/` directory.

## Usage

### Via Claude Code Skill (primary interface)

```
/generate-mock-data 500 person healthcare company
```

Or with no prompt for fully random defaults (random industry, random size 100-2000):

```
/generate-mock-data
```

The skill validates the prompt format and will re-prompt if the input doesn't match the expected pattern.

**Supported industries:** fintech, healthcare, construction, manufacturing, retail, logistics, education, insurance, energy, defense, media, legal, real-estate, saas, biotech, consulting, telecom, aerospace, agriculture, hospitality

### Via Python Directly

```bash
python main.py --size 500 --industry healthcare
python main.py --size 150 --industry fintech --name NovaPay --seed 42
python main.py --days 14 --output my_data  # custom window and output dir
python main.py  # random industry + size 100-2000
```

| Flag | Default | Description |
|------|---------|-------------|
| `--size` | Random 100-2000 | Number of employees |
| `--industry` | Random | Company industry |
| `--name` | Generated | Company name |
| `--seed` | None | Random seed for reproducible output |
| `--days` | 30 | Days of activity to generate |
| `--output` | `data` | Output directory |

## Eample output

Output is written to `data/` with every data source in both JSON and YAML:

```
data/
├── company/
│   ├── employees.{json,yaml}          # full employee directory
│   ├── departments.{json,yaml}        # org structure with headcount
│   ├── groups.{json,yaml}             # security/access groups
│   └── service_accounts.{json,yaml}   # CI/CD and integration accounts
├── cloud/aws/
│   ├── iam/
│   │   ├── users.{json,yaml}          # IAM users mapped to employees
│   │   ├── roles.{json,yaml}          # IAM roles (incl. legacy)
│   │   ├── policies.{json,yaml}       # custom policies (some overly broad)
│   │   └── resources.{json,yaml}      # S3 buckets + EC2 instances
│   └── cloudtrail/
│       └── YYYY-MM-DD.{json,yaml}     # daily API event logs
├── identity/
│   └── auth_events/
│       └── YYYY-MM-DD.{json,yaml}     # login/MFA/session events
├── endpoints/
│   ├── devices.{json,yaml}            # device inventory
│   └── process_events/
│       └── YYYY-MM-DD.{json,yaml}     # process execution telemetry
└── alerts/
    └── security_findings.{json,yaml}  # findings from embedded scenarios
```

## Embedded Security Scenarios

Six scenarios are injected into the baseline activity at specific points in the 30-day timeline:

| Scenario | Severity | What to look for |
|----------|----------|------------------|
| Over-permissioned user | HIGH | Non-technical employee with `AdministratorAccess`, only doing basic S3 reads |
| Impossible travel | CRITICAL | Login from NYC then Singapore 20 minutes later, different device, no MFA |
| Off-hours prod access | MEDIUM | Engineer hitting prod S3/EC2 at 2-4am UTC |
| Privilege escalation | CRITICAL | User calls `iam:PutUserPolicy` on their own account, then accesses secrets |
| Credential stuffing | CRITICAL | 50-75 failed logins from single IP, then 1-2 successes |
| Data exfiltration | CRITICAL | 300-500 S3 GetObject calls in 2 hours (baseline: 5-10/day) |

Each scenario references real employees and IAM users from the generated data, so the findings are traceable end-to-end.

## Realistic Imperfections

The data intentionally includes the kinds of messiness found in real environments:

- **Missing fields**: 5-15% of records omit optional fields (phone, manager, userAgent, serial number)
- **Stale accounts**: Terminated employees still have active IAM users and assigned devices
- **Tag inconsistency**: Mix of `costCenter`, `cost_center`, and missing tags across resources
- **Legacy artifacts**: Admin role marked "DO NOT USE" still active; deprecated service account still running
- **Partial MFA**: 80% enrolled, 10% pending, 10% not enrolled
- **Stale credentials**: Backup service account not rotated in 400+ days
- **Timezone drift**: ~3% of timestamps use local offset instead of UTC
- **Duplicate entries**: Service account exists under two names (original + `-legacy`), both active

## Example Output

See `examples/` for sample output from a 150-person fintech company (seed 42):

- `examples/alerts/security_findings.json` — all 6 scenario findings
- `examples/company/employees.json` — employee directory with imperfections
- `examples/identity/auth_events/2026-04-09.json` — day with credential stuffing attack
- `examples/cloud/aws/cloudtrail/2026-04-09.json` — CloudTrail events

## Project Structure

```
generate-mock-data/
├── main.py                 # orchestration + dual-format file output
├── config.py               # company profile dataclass + defaults
├── generators/
│   ├── company.py          # employees, departments, groups, service accounts
│   ├── aws_iam.py          # IAM users, roles, policies, S3/EC2 resources
│   ├── aws_cloudtrail.py   # daily CloudTrail event generation
│   ├── auth_events.py      # login/MFA/session events
│   ├── endpoints.py        # device inventory + process events
│   └── scenarios.py        # 6 security anomaly injections
├── .claude/skills/
│   └── generate-mock-data/
│       └── SKILL.md        # Claude Code skill definition
├── examples/               # committed sample output
├── pyproject.toml          # dependencies + ruff config
├── ASSIGNMENT.md           # original assignment brief
├── PLAN.md                 # implementation plan and architecture
└── NOTES.md                # design decisions and tradeoffs
```
