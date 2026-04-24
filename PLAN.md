# Plan: Security Demo Data Generator

## Context
The primary interface is a **Claude Code skill** — the user feeds it a short prompt describing the company context, and the skill guides Claude to generate realistic, imperfect security data using Python generators underneath.

## Core Concept
**Skill as playbook, Python as toolkit.** The Claude skill (`.claude/skills/generate-mock-data/SKILL.md`) contains all the domain knowledge: what data types to generate, what schemas to follow, how to introduce realistic imperfections, and what security scenarios to embed. The Python generators (`generators/*.py`) are the execution layer the skill instructs Claude to call.

**Usage flow:**
```
User: /generate-mock-data 500 person healthcare company

Claude: [reads skill] → [validates prompt format] → [runs Python generators] → data/ populated
```

**If no prompt or invalid prompt:**
```
User: /generate-mock-data

Claude: [reads skill] → [picks random industry + size 100-2000] → [generates] → data/ populated
```

```
User: /generate-mock-data make me some data please

Claude: "Invalid format. Please provide a prompt like: '500 person healthcare company'
         or '2000 person construction'. Format: <size> person <industry> [company]"
```

## Architecture

### Project Structure
```
generate-mock-data/
├── main.py                          # Standalone CLI entry point (also works without skill)
├── pyproject.toml                   # Dependencies + metadata
├── config.py                        # Company profile + generation parameters
├── generators/
│   ├── __init__.py
│   ├── company.py                   # Employees, departments, groups, service accounts
│   ├── aws_iam.py                   # IAM users, roles, policies, cloud resources
│   ├── aws_cloudtrail.py            # CloudTrail event logs (time-series)
│   ├── auth_events.py               # Login/SSO/MFA events (time-series)
│   ├── endpoints.py                 # Devices + process execution events
│   └── scenarios.py                 # Security anomaly injection
├── .claude/
│   └── skills/
│       └── generate-mock-data/
│           └── SKILL.md             # The skill — primary interface
├── examples/                        # Committed example outputs
└── data/                            # Generated output (gitignored)
```

### Output Folder Structure
```
data/
├── company/
│   ├── employees.json + employees.yaml
│   ├── departments.json + departments.yaml
│   ├── groups.json + groups.yaml
│   └── service_accounts.json + service_accounts.yaml
├── cloud/
│   └── aws/
│       ├── iam/
│       │   ├── users.json + users.yaml
│       │   ├── roles.json + roles.yaml
│       │   ├── policies.json + policies.yaml
│       │   └── resources.json + resources.yaml
│       └── cloudtrail/
│           └── YYYY-MM-DD.json + YYYY-MM-DD.yaml
├── identity/
│   └── auth_events/
│       └── YYYY-MM-DD.json + YYYY-MM-DD.yaml
├── endpoints/
│   ├── devices.json + devices.yaml
│   └── process_events/
│       └── YYYY-MM-DD.json + YYYY-MM-DD.yaml
└── alerts/
    └── security_findings.json + security_findings.yaml
```

## The Skill Definition

The skill file (`.claude/skills/generate-mock-data/SKILL.md`) is the heart of this project. It contains:

### 1. Input Handling & Validation
- **Expected prompt format**: `<size> person <industry> [company name]`
  - Examples: `500 person healthcare company`, `2000 person construction`, `150 person fintech NovaPay`
- **Validation guardrails**: If the prompt doesn't match the expected pattern (must contain a number + an industry from the maintained list), reject and re-prompt with instructions
- **No prompt = random defaults**: Pick a random industry from the maintained list + random size between 100-2000 + generate a company name with Faker
- **Maintained industry list**: fintech, healthcare, construction, manufacturing, retail, logistics, education, insurance, energy, defense, media, legal, real-estate, saas, biotech, consulting, telecom, aerospace, agriculture, hospitality
- Company name: extracted from prompt if provided, otherwise generated

### 2. Standard Data Types & Schemas
Guidelines for each data type — what fields to include, what format to follow:

- **Employees**: name, email, employee_id, department, title, manager, hire_date, location, status, mfa_enrolled
- **AWS IAM**: users, roles, policies following real AWS IAM JSON structure
- **CloudTrail**: events matching real CloudTrail schema (eventVersion, eventSource, eventName, awsRegion, sourceIPAddress, userAgent, requestParameters, responseElements)
- **Auth events**: timestamp, user, event_type (login_success, login_failure, mfa_challenge, password_reset), source_ip, geo, device_fingerprint, session_id
- **Endpoints**: hostname, os, agent_version, last_seen, user_assigned
- **Process events**: timestamp, hostname, pid, ppid, process_name, command_line, user, hash

### 3. Realistic Imperfection Rules
This is what makes the data feel real vs. obviously generated:

- **Missing fields**: 5-15% of records should have optional fields omitted (e.g., missing `manager` for some employees, missing `userAgent` in some CloudTrail events)
- **Stale data**: Some terminated employees still have active IAM users or devices assigned
- **Inconsistent formatting**: Mix of naming conventions (some tags use camelCase, some use snake_case, some kebab-case)
- **Incomplete migrations**: Some resources have proper tags, others have partial or no tags
- **Legacy artifacts**: Old security groups still referenced, deprecated role names alongside new ones
- **Timezone inconsistencies**: Most timestamps UTC but a few in local time
- **Partial MFA rollout**: 80% of users have MFA, some in "enrolled but not activated" state
- **Duplicate/near-duplicate entries**: A service account that exists under two slightly different names

### 4. Security Scenarios
Scenarios injected into the timeline, each tied to specific employees:

1. **Over-permissioned user** — Junior marketing employee has AdministratorAccess. Their activity only shows basic S3 reads.
2. **Impossible travel** — Auth events show login from NYC then Singapore 20 min later.
3. **Off-hours prod access** — Engineer accessing prod S3/EC2 at 2-4am, breaking their normal pattern.
4. **Privilege escalation** — User calls iam:PutUserPolicy on their own account, then accesses new resources.
5. **Credential stuffing** — 50+ failed logins from one IP against multiple accounts, then 1-2 successes.
6. **Data exfiltration signal** — User goes from 5-10 S3 GetObject/day to 500+ targeting a sensitive bucket.

### 5. Internal Consistency Rules
- Every CloudTrail userIdentity.arn must reference a real IAM user/role from generated IAM data
- Every auth event user must exist in employees.json
- Every endpoint device must be assigned to a real employee
- IP addresses for a given user should be mostly consistent (1-2 IPs per user, from same geo)
- Activity volume should correlate with role (engineers make more API calls than marketing)
- Work-hour distribution: ~80% of activity between 8am-6pm user's local time

## Data Generation Flow
1. **Parse context** — Extract company profile from user prompt or CLI args
2. **Generate company** — Org structure first (this is the source of truth)
3. **Provision cloud** — IAM users/roles/policies + resources, referencing company data
4. **Generate devices** — Endpoint inventory mapped to employees
5. **Generate baseline activity** — CloudTrail, auth events, process events over 30-day window
6. **Inject scenarios** — Layer anomalies into the timeline at specific points
7. **Generate alerts** — Security findings that a SIEM would produce from the scenarios
8. **Write output** — Serialize to data/ folder structure

## Config Defaults
- **Company size**: Random 100-2000 if not specified
- **Industry**: Random from maintained list if not specified
- **Company name**: Generated via Faker if not specified
- **Activity window**: 30 days
- **Seed**: Optional for reproducibility (random if not provided)

## Output Formats
Every data type is generated in **both JSON and YAML**. Each output file gets a `.json` and `.yaml` version side by side. This gives the user flexibility to consume whichever format their tooling expects.

## Dependencies
- `faker` — Realistic identity data (seeded for reproducibility)
- `pyyaml` — YAML serialization for config/inventory data
- Standard library only otherwise (`json`, `random`, `datetime`, `pathlib`, `argparse`, `dataclasses`)

## Implementation Order
1. `config.py` — Company profile dataclass + generation params
2. `generators/company.py` — Org structure
3. `generators/aws_iam.py` — IAM + cloud resources
4. `generators/aws_cloudtrail.py` — CloudTrail events
5. `generators/auth_events.py` — Auth events
6. `generators/endpoints.py` — Devices + process events
7. `generators/scenarios.py` — Anomaly injection
8. `main.py` — CLI orchestration + file output
9. `.claude/skills/generate-mock-data/SKILL.md` — The skill definition
10. `README.md` — Usage, decisions, example outputs
11. Generate example output, commit to `examples/`
12. Run `ruff check --output-format=concise`, fix all issues

## Verification
1. Invoke skill with prompt: `/generate-mock-data 500 person healthcare company`
2. Invoke skill with no prompt (random defaults): `/generate-mock-data`
3. Invoke skill with bad prompt (rejected with help text): `/generate-mock-data make me stuff`
4. Test standalone CLI: `python main.py --size 150 --industry fintech`
5. Spot-check data for internal consistency (user IDs match across files, data meets requirements)
6. Verify security scenarios are detectable in the output
7. Confirm realistic imperfections exist (missing fields, stale data, etc.)
8. Run `ruff check --output-format=concise` — zero issues
