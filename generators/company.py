"""Generate company organizational data."""

from __future__ import annotations

import random
import uuid
from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import CompanyConfig

# Department weight distributions — how headcount splits across departments
DEPARTMENT_WEIGHTS = {
    "Engineering": 0.22,
    "Sales": 0.13,
    "Operations": 0.12,
    "Marketing": 0.08,
    "Finance": 0.08,
    "Customer Support": 0.07,
    "Product": 0.06,
    "Human Resources": 0.05,
    "IT": 0.06,
    "Legal": 0.04,
    "Research & Development": 0.04,
    "Security": 0.03,
    "Executive": 0.02,
}

# Title templates per department, by seniority level
TITLES = {
    "Engineering": {
        "executive": ["VP of Engineering"],
        "director": ["Director of Engineering", "Director of Platform"],
        "manager": ["Engineering Manager", "Tech Lead"],
        "senior": [
            "Senior Software Engineer",
            "Senior Backend Engineer",
            "Senior Frontend Engineer",
            "Staff Engineer",
        ],
        "mid": [
            "Software Engineer",
            "Backend Engineer",
            "Frontend Engineer",
            "Full Stack Engineer",
        ],
        "junior": ["Junior Software Engineer", "Associate Engineer"],
    },
    "Sales": {
        "executive": ["VP of Sales"],
        "director": ["Sales Director", "Director of Business Development"],
        "manager": ["Sales Manager", "Regional Sales Manager"],
        "senior": ["Senior Account Executive", "Enterprise Account Executive"],
        "mid": ["Account Executive", "Business Development Representative"],
        "junior": ["Sales Development Representative", "Inside Sales Rep"],
    },
    "Operations": {
        "executive": ["VP of Operations", "COO"],
        "director": ["Director of Operations"],
        "manager": ["Operations Manager", "Program Manager"],
        "senior": ["Senior Operations Analyst", "Senior Program Manager"],
        "mid": ["Operations Analyst", "Operations Coordinator"],
        "junior": ["Operations Associate", "Operations Intern"],
    },
    "Marketing": {
        "executive": ["VP of Marketing", "CMO"],
        "director": ["Director of Marketing", "Director of Growth"],
        "manager": ["Marketing Manager", "Content Manager"],
        "senior": ["Senior Marketing Analyst", "Senior Content Strategist"],
        "mid": ["Marketing Analyst", "Content Strategist", "SEO Specialist"],
        "junior": ["Marketing Coordinator", "Marketing Associate"],
    },
    "Finance": {
        "executive": ["VP of Finance", "CFO"],
        "director": ["Director of Finance", "Controller"],
        "manager": ["Finance Manager", "Accounting Manager"],
        "senior": ["Senior Financial Analyst", "Senior Accountant"],
        "mid": ["Financial Analyst", "Staff Accountant"],
        "junior": ["Junior Accountant", "Finance Associate"],
    },
    "Customer Support": {
        "executive": ["VP of Customer Success"],
        "director": ["Director of Support"],
        "manager": ["Support Manager", "Customer Success Manager"],
        "senior": ["Senior Support Engineer", "Senior CSM"],
        "mid": ["Support Engineer", "Customer Success Associate"],
        "junior": ["Support Specialist", "Support Representative"],
    },
    "Product": {
        "executive": ["VP of Product", "CPO"],
        "director": ["Director of Product"],
        "manager": ["Product Manager", "Senior Product Manager"],
        "senior": ["Senior Product Manager", "Principal PM"],
        "mid": ["Product Manager", "Product Analyst"],
        "junior": ["Associate Product Manager"],
    },
    "Human Resources": {
        "executive": ["VP of People", "CHRO"],
        "director": ["Director of HR"],
        "manager": ["HR Manager", "Recruiting Manager"],
        "senior": ["Senior HR Business Partner", "Senior Recruiter"],
        "mid": ["HR Business Partner", "Recruiter", "Benefits Specialist"],
        "junior": ["HR Coordinator", "Recruiting Coordinator"],
    },
    "IT": {
        "executive": ["VP of IT", "CIO"],
        "director": ["Director of IT", "Director of Infrastructure"],
        "manager": ["IT Manager", "Systems Manager"],
        "senior": ["Senior Systems Administrator", "Senior Network Engineer"],
        "mid": ["Systems Administrator", "Network Engineer", "IT Specialist"],
        "junior": ["IT Support Specialist", "Help Desk Analyst"],
    },
    "Legal": {
        "executive": ["General Counsel", "VP of Legal"],
        "director": ["Director of Legal"],
        "manager": ["Legal Operations Manager"],
        "senior": ["Senior Corporate Counsel", "Senior Paralegal"],
        "mid": ["Corporate Counsel", "Paralegal", "Compliance Analyst"],
        "junior": ["Legal Assistant", "Compliance Associate"],
    },
    "Research & Development": {
        "executive": ["VP of R&D"],
        "director": ["Director of Research"],
        "manager": ["R&D Manager", "Research Lead"],
        "senior": ["Senior Research Scientist", "Senior Data Scientist"],
        "mid": ["Research Scientist", "Data Scientist", "ML Engineer"],
        "junior": ["Research Associate", "Junior Data Scientist"],
    },
    "Security": {
        "executive": ["CISO", "VP of Security"],
        "director": ["Director of Security"],
        "manager": ["Security Manager", "Security Operations Manager"],
        "senior": ["Senior Security Engineer", "Senior SOC Analyst"],
        "mid": ["Security Engineer", "SOC Analyst", "Threat Analyst"],
        "junior": ["Junior Security Analyst", "Security Associate"],
    },
    "Executive": {
        "executive": ["CEO", "President"],
        "director": ["Chief of Staff"],
        "manager": ["Executive Assistant"],
        "senior": [],
        "mid": [],
        "junior": [],
    },
}

# Seniority level distribution within each department
LEVEL_WEIGHTS = {
    "executive": 0.02,
    "director": 0.04,
    "manager": 0.10,
    "senior": 0.28,
    "mid": 0.38,
    "junior": 0.18,
}

LOCATIONS = [
    "New York, NY",
    "San Francisco, CA",
    "Austin, TX",
    "Chicago, IL",
    "Seattle, WA",
    "Denver, CO",
    "Boston, MA",
    "Atlanta, GA",
    "Los Angeles, CA",
    "Miami, FL",
    "Portland, OR",
    "Remote",
]

SERVICE_ACCOUNT_TEMPLATES = [
    ("jenkins-ci", "Jenkins CI/CD pipeline"),
    ("github-actions", "GitHub Actions automation"),
    ("terraform-prod", "Terraform production deployments"),
    ("terraform-staging", "Terraform staging deployments"),
    ("datadog-agent", "Datadog monitoring agent"),
    ("pagerduty-integration", "PagerDuty alerting integration"),
    ("slack-bot", "Slack bot notifications"),
    ("backup-service", "Automated backup service"),
    ("log-shipper", "Log aggregation pipeline"),
    ("vulnerability-scanner", "Security vulnerability scanner"),
    ("sso-sync", "SSO directory sync service"),
    ("billing-processor", "Automated billing processor"),
]


def generate_departments(config: CompanyConfig) -> list[dict]:
    """Generate department list with headcount distribution."""
    departments = []
    remaining = config.size

    dept_items = list(DEPARTMENT_WEIGHTS.items())
    for i, (name, weight) in enumerate(dept_items):
        if i == len(dept_items) - 1:
            headcount = remaining
        else:
            headcount = max(1, round(config.size * weight))
            remaining -= headcount

        departments.append(
            {
                "name": name,
                "budget_code": f"{name[:3].upper()}-{random.randint(1000, 9999)}",
                "headcount": headcount,
                "head_id": None,  # filled in after employees are generated
            }
        )

    return departments


def _pick_title(department: str, level: str) -> str:
    """Pick a title for a given department and seniority level."""
    dept_titles = TITLES.get(department, TITLES["Operations"])
    candidates = dept_titles.get(level, [])
    if not candidates:
        return f"{level.title()} {department} Specialist"
    return random.choice(candidates)


def _pick_level() -> str:
    """Pick a seniority level based on distribution weights."""
    levels = list(LEVEL_WEIGHTS.keys())
    weights = list(LEVEL_WEIGHTS.values())
    return random.choices(levels, weights=weights, k=1)[0]


def _apply_employee_imperfections(employee: dict, hire_date: date, fake) -> None:
    """Apply realistic imperfections to an employee record."""
    # MFA enrollment — 80% enrolled, 10% pending, 10% not enrolled
    mfa_roll = random.random()
    if mfa_roll < 0.80:
        employee["mfa_enrolled"] = True
    elif mfa_roll < 0.90:
        employee["mfa_enrolled"] = "pending"
    else:
        employee["mfa_enrolled"] = False

    # 10% missing phone
    if random.random() > 0.10:
        employee["phone"] = fake.basic_phone_number()

    # 5% terminated employees (still in the system)
    earliest_term = hire_date + timedelta(days=90)
    if random.random() < 0.05 and earliest_term < date.today():
        employee["status"] = "terminated"
        term_date = fake.date_between(
            start_date=earliest_term,
            end_date=date.today(),
        )
        employee["termination_date"] = term_date.isoformat()

    # 3% on leave
    if employee["status"] == "active" and random.random() < 0.03:
        employee["status"] = "on_leave"


def _build_manager_hierarchy(dept_employees: list[dict]) -> None:
    """Assign manager_id based on seniority levels within a department."""
    execs = [e for e in dept_employees if e["level"] == "executive"]
    directors = [e for e in dept_employees if e["level"] == "director"]
    managers = [e for e in dept_employees if e["level"] == "manager"]
    ics = [e for e in dept_employees if e["level"] in ("senior", "mid", "junior")]

    for d in directors:
        if execs:
            d["manager_id"] = execs[0]["employee_id"]

    report_to = directors or execs
    for m in managers:
        if report_to:
            m["manager_id"] = random.choice(report_to)["employee_id"]

    report_to = managers or directors or execs
    for ic in ics:
        # Imperfection: 8% missing manager_id
        if report_to and random.random() > 0.08:
            ic["manager_id"] = random.choice(report_to)["employee_id"]


def generate_employees(
    config: CompanyConfig,
    departments: list[dict],
    fake,
) -> list[dict]:
    """Generate employee records with realistic org structure."""
    employees = []
    emp_id_counter = 1000

    for dept in departments:
        dept_name = dept["name"]
        dept_employees = []

        for _ in range(dept["headcount"]):
            emp_id = f"EMP-{emp_id_counter:06d}"
            emp_id_counter += 1
            level = _pick_level()
            first_name = fake.first_name()
            last_name = fake.last_name()
            email_user = f"{first_name.lower()}.{last_name.lower()}"

            hire_date = fake.date_between(
                start_date=date.today() - timedelta(days=2500),
                end_date=date.today() - timedelta(days=30),
            )

            employee = {
                "employee_id": emp_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": f"{email_user}@{config.domain}",
                "department": dept_name,
                "title": _pick_title(dept_name, level),
                "level": level,
                "hire_date": hire_date.isoformat(),
                "location": random.choice(LOCATIONS),
                "status": "active",
            }

            _apply_employee_imperfections(employee, hire_date, fake)
            dept_employees.append(employee)

        # Department head and manager hierarchy
        dept_head = dept_employees[0]
        for e in dept_employees:
            if e["level"] == "executive":
                dept_head = e
                break
        dept["head_id"] = dept_head["employee_id"]

        _build_manager_hierarchy(dept_employees)
        employees.extend(dept_employees)

    return employees


def generate_groups(employees: list[dict]) -> list[dict]:
    """Generate security/access groups based on employee data."""
    active = [e for e in employees if e["status"] == "active"]
    engineers = [e for e in active if e["department"] == "Engineering"]
    it_staff = [e for e in active if e["department"] == "IT"]
    security = [e for e in active if e["department"] == "Security"]
    managers_up = [
        e for e in active if e["level"] in ("manager", "director", "executive")
    ]

    groups = [
        {
            "group_id": f"GRP-{uuid.uuid4().hex[:8]}",
            "name": "all-employees",
            "description": "All active employees",
            "members": [e["employee_id"] for e in active],
            "created_date": "2020-03-15",
        },
        {
            "group_id": f"GRP-{uuid.uuid4().hex[:8]}",
            "name": "engineering-team",
            "description": "Engineering department members",
            "members": [e["employee_id"] for e in engineers],
            "created_date": "2020-03-15",
        },
        {
            "group_id": f"GRP-{uuid.uuid4().hex[:8]}",
            "name": "aws-admins",
            "description": "AWS administrator access",
            "members": [e["employee_id"] for e in (it_staff + security)[:8]],
            "created_date": "2020-06-01",
        },
        {
            "group_id": f"GRP-{uuid.uuid4().hex[:8]}",
            "name": "vpn-users",
            "description": "VPN access for remote workers",
            "members": [
                e["employee_id"]
                for e in active
                if e["location"] == "Remote" or random.random() < 0.6
            ],
            "created_date": "2020-04-01",
        },
        {
            "group_id": f"GRP-{uuid.uuid4().hex[:8]}",
            "name": "prod-readonly",
            "description": "Read-only access to production systems",
            "members": [
                e["employee_id"] for e in engineers if e["level"] in ("mid", "junior")
            ],
            "created_date": "2021-01-10",
        },
        {
            "group_id": f"GRP-{uuid.uuid4().hex[:8]}",
            "name": "prod-deploy",
            "description": "Production deployment access",
            "members": [
                e["employee_id"]
                for e in engineers
                if e["level"] in ("senior", "manager", "director", "executive")
            ],
            "created_date": "2021-01-10",
        },
        {
            "group_id": f"GRP-{uuid.uuid4().hex[:8]}",
            "name": "leadership",
            "description": "Manager level and above",
            "members": [e["employee_id"] for e in managers_up],
            "created_date": "2020-03-15",
        },
        {
            "group_id": f"GRP-{uuid.uuid4().hex[:8]}",
            "name": "data-access",
            "description": "Access to data warehouse and analytics",
            "members": [
                e["employee_id"]
                for e in active
                if e["department"]
                in ("Engineering", "Product", "Research & Development", "Finance")
                and random.random() < 0.5
            ],
            "created_date": "2022-03-20",
        },
    ]

    return groups  # noqa: RET504


def generate_service_accounts(
    config: CompanyConfig,
    employees: list[dict],
    fake,
) -> list[dict]:
    """Generate service accounts tied to real employee owners."""
    active_engineers = [
        e
        for e in employees
        if e["department"] in ("Engineering", "IT", "Security")
        and e["status"] == "active"
        and e["level"] in ("senior", "manager", "director")
    ]

    # Pick a subset of service account templates
    count = min(len(SERVICE_ACCOUNT_TEMPLATES), max(4, config.size // 100))
    templates = random.sample(SERVICE_ACCOUNT_TEMPLATES, count)

    accounts = []
    for name, description in templates:
        owner = random.choice(active_engineers) if active_engineers else None
        created = fake.date_between(
            start_date=date.today() - timedelta(days=1500),
            end_date=date.today() - timedelta(days=180),
        )
        last_rotated = fake.date_between(
            start_date=created,
            end_date=date.today(),
        )

        account = {
            "account_id": f"SVC-{name}",
            "name": name,
            "description": description,
            "owner_id": owner["employee_id"] if owner else None,
            "created_date": created.isoformat(),
            "last_rotated": last_rotated.isoformat(),
            "status": "active",
        }

        # Imperfection: one service account has a stale rotation (>365 days)
        if name == "backup-service":
            account["last_rotated"] = (
                date.today() - timedelta(days=random.randint(400, 600))
            ).isoformat()

        accounts.append(account)

    # Imperfection: duplicate near-identical service account
    if accounts:
        dup = dict(accounts[0])
        dup["account_id"] = f"SVC-{dup['name']}-legacy"
        dup["name"] = f"{dup['name']}-legacy"
        dup["description"] = dup["description"] + " (deprecated)"
        dup["status"] = "active"  # still active despite being deprecated
        accounts.append(dup)

    return accounts


def generate_company(config: CompanyConfig, fake) -> dict:
    """Generate all company organizational data."""
    departments = generate_departments(config)
    employees = generate_employees(config, departments, fake)
    groups = generate_groups(employees)
    service_accounts = generate_service_accounts(config, employees, fake)

    return {
        "employees": employees,
        "departments": departments,
        "groups": groups,
        "service_accounts": service_accounts,
    }
