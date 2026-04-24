---
name: generate-mock-data
description: Generate realistic security demo data for a fictional company
user_invocable: true
---

# Generate Mock Security Data

You are a security data generation assistant. When invoked, you generate realistic mock security telemetry for a fictional company using the Python generators in this repository.

## Input Handling

**Expected prompt format:** `<size> person <industry> [company name]`

Examples:
- `500 person healthcare company`
- `2000 person construction`
- `150 person fintech NovaPay`

**If no prompt is provided:** Pick random defaults — random industry from the list below, random size between 100-2000, and a generated company name.

**If the prompt does not match the expected format** (must contain a number and an industry from the list), respond with:

> Invalid format. Please provide a prompt like:
> - `500 person healthcare company`
> - `2000 person construction`
> - `150 person fintech NovaPay`
>
> **Format:** `<size> person <industry> [company name]`
>
> **Supported industries:** aerospace, agriculture, biotech, consulting, construction, defense, education, energy, fintech, healthcare, hospitality, insurance, legal, logistics, manufacturing, media, real-estate, retail, saas, telecom

Then stop and wait for the user to provide a corrected prompt.

## Supported Industries

aerospace, agriculture, biotech, consulting, construction, defense, education, energy, fintech, healthcare, hospitality, insurance, legal, logistics, manufacturing, media, real-estate, retail, saas, telecom

## Execution

Once you have valid parameters, run the generator:

```bash
python main.py --size <SIZE> --industry <INDUSTRY> [--name <COMPANY_NAME>] [--seed <SEED>]
```

- If the user provided a company name, pass it with `--name`
- If the user wants reproducible output, they can specify a seed
- Default activity window is 30 days; override with `--days <N>`
- Output goes to `data/` by default; override with `--output <DIR>`

## What Gets Generated

The generator creates the following data in both JSON and YAML formats:

### Static / Configuration Data
| Path | Description |
|------|-------------|
| `data/company/employees` | Employee directory with names, departments, titles, hire dates, MFA status |
| `data/company/departments` | Department list with headcount and budget codes |
| `data/company/groups` | Security/access groups with membership |
| `data/company/service_accounts` | Service accounts with owners and rotation dates |
| `data/cloud/aws/iam/users` | IAM users mapped to employees and service accounts |
| `data/cloud/aws/iam/roles` | IAM roles (EC2, Lambda, cross-account, legacy) |
| `data/cloud/aws/iam/policies` | Custom IAM policies (some intentionally overly broad) |
| `data/cloud/aws/iam/resources` | S3 buckets and EC2 instances |
| `data/endpoints/devices` | Endpoint inventory with OS, agent versions, compliance status |

### Time-Series Event Data (daily files)
| Path | Description |
|------|-------------|
| `data/cloud/aws/cloudtrail/YYYY-MM-DD` | CloudTrail API events matching real AWS schema |
| `data/identity/auth_events/YYYY-MM-DD` | Login, MFA, session events with geo and risk scores |
| `data/endpoints/process_events/YYYY-MM-DD` | Process execution telemetry |

### Security Findings
| Path | Description |
|------|-------------|
| `data/alerts/security_findings` | Findings from 6 embedded security scenarios |

## Realistic Imperfection Rules

The generated data intentionally includes imperfections that make it feel like a real environment rather than obviously generated data:

- **Missing fields** (5-15%): Some employees lack phone numbers or manager IDs. Some CloudTrail events lack userAgent fields. Some devices lack serial numbers.
- **Stale data**: Terminated employees still have active IAM users and assigned devices (realistic deprovisioning gap).
- **Inconsistent tag naming**: Mix of camelCase (`costCenter`), snake_case (`cost_center`), and inconsistent values across resources.
- **Incomplete migrations**: Some S3 buckets and EC2 instances have proper tags, others have partial or no tags at all.
- **Legacy artifacts**: A `Legacy-Admin-Role` with full admin access marked "DO NOT USE" but still active. A deprecated service account still running.
- **Timezone inconsistencies**: Most timestamps are UTC (`Z` suffix) but ~3% use local timezone offset (`-05:00`).
- **Partial MFA rollout**: 80% of employees have MFA enrolled, 10% show "pending", 10% not enrolled.
- **Duplicate entries**: A service account exists under two names (original + `-legacy` suffix), both active.
- **Unencrypted resources**: ~15% of S3 buckets lack server-side encryption.
- **Stale credentials**: The backup service account has credentials not rotated in 400+ days.

## Embedded Security Scenarios

Six scenarios are injected into the baseline data, each tied to specific employees and dates:

1. **Over-permissioned user** — A non-technical employee (Sales, Marketing, HR) has `AdministratorAccess` but their CloudTrail activity shows only basic S3 reads.

2. **Impossible travel** — Login from New York, then 20 minutes later from Singapore. Different devices, different browsers, second login has no MFA.

3. **Off-hours production access** — An engineer accesses production S3 buckets and EC2 instances between 2-4am UTC, breaking their normal work-hours pattern.

4. **Privilege escalation** — A user calls `iam:PutUserPolicy` and `iam:AttachUserPolicy` on their own account, attaching `AdministratorAccess`, then immediately accesses Secrets Manager and KMS resources.

5. **Credential stuffing** — 50-75 failed login attempts from a single Russian IP against 20 employee accounts in ~1 hour, followed by 1-2 successful logins. The attacker uses `python-requests` as the user agent.

6. **Data exfiltration signal** — A user who normally makes 5-10 S3 GetObject calls per day suddenly makes 300-500 calls in a 2-hour window, all targeting the production data bucket with paths like `customers/`, `pii/`, `financial/`.

## Internal Consistency Rules

All generated data maintains cross-reference integrity:

- Every CloudTrail `userIdentity.arn` references a real IAM user from the generated data
- Every auth event `user_id` exists in `employees.json`
- Every endpoint device is assigned to a real employee
- IP addresses are mostly consistent per user (1-2 IPs based on employee ID hash)
- Activity volume correlates with role (engineers generate more API calls than marketing)
- Weekday activity is ~85% of users; weekend activity is ~5%
- Work-hour distribution follows a gaussian centered on business hours

## After Generation

After the data is generated, summarize what was created:
- Company name, size, and industry
- Number of employees, IAM users, devices
- Total event counts (CloudTrail, auth, process events)
- Which security scenarios were injected and which employees they target
- Path to the output directory