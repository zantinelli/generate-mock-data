"""Inject security-relevant scenarios into baseline data."""

from __future__ import annotations

import logging
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import CompanyConfig

logger = logging.getLogger(__name__)


def _pick_target(employees: list[dict], departments: list[str] | None = None) -> dict:
    """Pick a random active employee, optionally from specific departments."""
    active = [e for e in employees if e["status"] == "active"]
    if departments:
        active = [e for e in active if e["department"] in departments]
    return random.choice(active) if active else random.choice(employees)


def _find_iam_user(iam_users: list[dict], employee: dict) -> dict | None:
    """Find the IAM user matching an employee."""
    username = employee["email"].split("@")[0]
    for user in iam_users:
        if user["UserName"] == username:
            return user
    return None


def _pick_scenario_day(start_date: date, activity_days: int) -> date:
    """Pick a random day in the middle of the activity window for a scenario."""
    offset = random.randint(activity_days // 4, 3 * activity_days // 4)
    return start_date + timedelta(days=offset)


def inject_over_permissioned(
    config: CompanyConfig,
    company_data: dict,
    iam_data: dict,
    start_date: date,
) -> dict:
    """Scenario 1: Junior non-technical user has AdministratorAccess."""
    target = _pick_target(
        company_data["employees"],
        ["Marketing", "Sales", "Human Resources", "Customer Support"],
    )
    iam_user = _find_iam_user(iam_data["users"], target)

    if not iam_user:
        # Create IAM user for this non-technical employee
        username = target["email"].split("@")[0]
        iam_user = {
            "UserName": username,
            "UserId": f"AIDA{uuid.uuid4().hex[:16].upper()}",
            "Arn": f"arn:aws:iam::{config.aws_account_id}:user/{username}",
            "CreateDate": f"{target['hire_date']}T09:00:00Z",
            "employee_id": target["employee_id"],
            "Tags": [
                {"Key": "Department", "Value": target["department"]},
                {"Key": "employee_id", "Value": target["employee_id"]},
            ],
            "AttachedPolicies": [],
            "MFADevices": [],
        }
        iam_data["users"].append(iam_user)

    # Attach AdministratorAccess — the over-permissioning
    iam_user["AttachedPolicies"] = [
        {
            "PolicyName": "AdministratorAccess",
            "PolicyArn": "arn:aws:iam::aws:policy/AdministratorAccess",
        }
    ]

    logger.info(
        "Scenario: over-permissioned user %s (%s in %s) has AdministratorAccess",
        target["employee_id"],
        target["title"],
        target["department"],
    )

    return {
        "scenario": "over_permissioned_user",
        "severity": "HIGH",
        "target_employee": target["employee_id"],
        "target_name": f"{target['first_name']} {target['last_name']}",
        "description": (
            f"{target['title']} in {target['department']} has "
            "AdministratorAccess policy attached but only performs "
            "basic read operations"
        ),
        "iam_user": iam_user["UserName"],
        "policy": "AdministratorAccess",
        "detected_date": _pick_scenario_day(
            start_date,
            config.activity_days,
        ).isoformat(),
    }


def inject_impossible_travel(
    config: CompanyConfig,
    company_data: dict,
    auth_events: dict[str, list[dict]],
    start_date: date,
) -> dict:
    """Scenario 2: User logs in from two distant locations within 20 minutes."""
    target = _pick_target(company_data["employees"])
    scenario_day = _pick_scenario_day(start_date, config.activity_days)
    day_key = scenario_day.isoformat()

    # Create two auth events 20 minutes apart from distant locations
    base_hour = random.randint(9, 17)
    ts1 = datetime(
        scenario_day.year,
        scenario_day.month,
        scenario_day.day,
        base_hour,
        15,
        0,
        tzinfo=timezone.utc,
    )
    ts2 = ts1 + timedelta(minutes=20)

    login_nyc = {
        "timestamp": ts1.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event_id": f"auth-{uuid.uuid4().hex[:12]}",
        "event_type": "login_success",
        "user_id": target["employee_id"],
        "email": target["email"],
        "source_ip": "203.0.113.50",
        "geo": {
            "city": "New York",
            "country": "US",
            "latitude": 40.7128,
            "longitude": -74.0060,
        },
        "device": {
            "type": "laptop",
            "os": "macOS 14.3",
            "browser": "Chrome 122",
        },
        "session_id": f"sess-{uuid.uuid4().hex[:12]}",
        "mfa_used": True,
        "risk_score": 0.15,
    }

    login_singapore = {
        "timestamp": ts2.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event_id": f"auth-{uuid.uuid4().hex[:12]}",
        "event_type": "login_success",
        "user_id": target["employee_id"],
        "email": target["email"],
        "source_ip": "118.189.42.100",
        "geo": {
            "city": "Singapore",
            "country": "SG",
            "latitude": 1.3521,
            "longitude": 103.8198,
        },
        "device": {
            "type": "desktop",
            "os": "Windows 11",
            "browser": "Firefox 123",
        },
        "session_id": f"sess-{uuid.uuid4().hex[:12]}",
        "mfa_used": False,
        "risk_score": 0.85,
    }

    if day_key not in auth_events:
        auth_events[day_key] = []
    auth_events[day_key].extend([login_nyc, login_singapore])
    auth_events[day_key].sort(key=lambda e: e["timestamp"])

    logger.info(
        "Scenario: impossible travel for %s on %s (NYC → Singapore in 20min)",
        target["employee_id"],
        day_key,
    )

    return {
        "scenario": "impossible_travel",
        "severity": "CRITICAL",
        "target_employee": target["employee_id"],
        "target_name": f"{target['first_name']} {target['last_name']}",
        "description": (
            f"Login from New York at {ts1.strftime('%H:%M')} UTC, "
            f"then Singapore at {ts2.strftime('%H:%M')} UTC "
            "(20 minutes apart, ~15,000 km distance)"
        ),
        "detected_date": day_key,
        "locations": ["New York, US", "Singapore, SG"],
        "time_gap_minutes": 20,
    }


def inject_off_hours_access(
    config: CompanyConfig,
    company_data: dict,
    cloudtrail_events: dict[str, list[dict]],
    iam_data: dict,
    start_date: date,
) -> dict:
    """Scenario 3: Engineer accessing prod resources at 2-4am."""
    target = _pick_target(company_data["employees"], ["Engineering"])
    iam_user = _find_iam_user(iam_data["users"], target)
    scenario_day = _pick_scenario_day(start_date, config.activity_days)
    day_key = scenario_day.isoformat()

    if not iam_user:
        return _empty_finding("off_hours_access", "No IAM user found for target")

    if day_key not in cloudtrail_events:
        cloudtrail_events[day_key] = []

    # Generate 8-15 API calls between 2-4am
    buckets = iam_data["resources"].get("s3_buckets", [])
    instances = iam_data["resources"].get("ec2_instances", [])
    num_events = random.randint(8, 15)

    for _ in range(num_events):
        hour = random.randint(2, 3)
        minute = random.randint(0, 59)
        dt = datetime(
            scenario_day.year,
            scenario_day.month,
            scenario_day.day,
            hour,
            minute,
            random.randint(0, 59),
            tzinfo=timezone.utc,
        )

        # Mix of S3 and EC2 access
        if random.random() < 0.6 and buckets:
            bucket = next(
                (b for b in buckets if "prod" in b["BucketName"]),
                random.choice(buckets),
            )
            event_name = random.choice(["GetObject", "ListObjects", "PutObject"])
            source = "s3.amazonaws.com"
            params = {"bucketName": bucket["BucketName"], "key": "data/export.csv"}
        elif instances:
            instance = random.choice(instances)
            event_name = random.choice(
                [
                    "DescribeInstances",
                    "StartInstances",
                    "StopInstances",
                ]
            )
            source = "ec2.amazonaws.com"
            params = {
                "instancesSet": {"items": [{"instanceId": instance["InstanceId"]}]}
            }
        else:
            continue

        event = {
            "eventVersion": "1.08",
            "userIdentity": {
                "type": "IAMUser",
                "principalId": iam_user["UserId"],
                "arn": iam_user["Arn"],
                "accountId": config.aws_account_id,
                "userName": iam_user["UserName"],
            },
            "eventTime": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "eventSource": source,
            "eventName": event_name,
            "awsRegion": config.aws_region,
            "sourceIPAddress": "198.51.100.77",
            "userAgent": "aws-cli/2.15.0 Python/3.11.6 Darwin/23.2.0",
            "requestParameters": params,
            "responseElements": None,
            "requestID": str(uuid.uuid4()),
            "eventID": str(uuid.uuid4()),
            "readOnly": event_name.startswith(("Get", "List", "Describe")),
            "eventType": "AwsApiCall",
            "recipientAccountId": config.aws_account_id,
        }
        cloudtrail_events[day_key].append(event)

    cloudtrail_events[day_key].sort(key=lambda e: e["eventTime"])

    logger.info(
        "Scenario: off-hours access by %s on %s (2-4am UTC)",
        target["employee_id"],
        day_key,
    )

    return {
        "scenario": "off_hours_access",
        "severity": "MEDIUM",
        "target_employee": target["employee_id"],
        "target_name": f"{target['first_name']} {target['last_name']}",
        "description": (
            f"Engineer accessed production S3 and EC2 resources "
            f"between 2:00-4:00 AM UTC on {day_key}, "
            "outside their normal working pattern"
        ),
        "detected_date": day_key,
        "num_events": num_events,
        "time_range": "02:00-04:00 UTC",
    }


def inject_privilege_escalation(
    config: CompanyConfig,
    company_data: dict,
    cloudtrail_events: dict[str, list[dict]],
    iam_data: dict,
    start_date: date,
) -> dict:
    """Scenario 4: User modifies their own IAM policy, then accesses new resources."""
    target = _pick_target(company_data["employees"], ["Engineering", "IT"])
    iam_user = _find_iam_user(iam_data["users"], target)
    scenario_day = _pick_scenario_day(start_date, config.activity_days)
    day_key = scenario_day.isoformat()

    if not iam_user:
        return _empty_finding("privilege_escalation", "No IAM user found")

    if day_key not in cloudtrail_events:
        cloudtrail_events[day_key] = []

    base_hour = random.randint(10, 16)

    # Step 1: User modifies their own policy
    escalation_events = [
        {
            "eventVersion": "1.08",
            "userIdentity": {
                "type": "IAMUser",
                "principalId": iam_user["UserId"],
                "arn": iam_user["Arn"],
                "accountId": config.aws_account_id,
                "userName": iam_user["UserName"],
            },
            "eventTime": datetime(
                scenario_day.year,
                scenario_day.month,
                scenario_day.day,
                base_hour,
                12,
                0,
                tzinfo=timezone.utc,
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "eventSource": "iam.amazonaws.com",
            "eventName": "PutUserPolicy",
            "awsRegion": config.aws_region,
            "sourceIPAddress": "203.0.113.200",
            "userAgent": "aws-cli/2.15.0 Python/3.11.6 Darwin/23.2.0",
            "requestParameters": {
                "userName": iam_user["UserName"],
                "policyName": "self-admin-policy",
                "policyDocument": (
                    '{"Version":"2012-10-17","Statement":'
                    '[{"Effect":"Allow","Action":"*","Resource":"*"}]}'
                ),
            },
            "responseElements": None,
            "requestID": str(uuid.uuid4()),
            "eventID": str(uuid.uuid4()),
            "readOnly": False,
            "eventType": "AwsApiCall",
            "recipientAccountId": config.aws_account_id,
        },
        {
            "eventVersion": "1.08",
            "userIdentity": {
                "type": "IAMUser",
                "principalId": iam_user["UserId"],
                "arn": iam_user["Arn"],
                "accountId": config.aws_account_id,
                "userName": iam_user["UserName"],
            },
            "eventTime": datetime(
                scenario_day.year,
                scenario_day.month,
                scenario_day.day,
                base_hour,
                14,
                0,
                tzinfo=timezone.utc,
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "eventSource": "iam.amazonaws.com",
            "eventName": "AttachUserPolicy",
            "awsRegion": config.aws_region,
            "sourceIPAddress": "203.0.113.200",
            "userAgent": "aws-cli/2.15.0 Python/3.11.6 Darwin/23.2.0",
            "requestParameters": {
                "userName": iam_user["UserName"],
                "policyArn": "arn:aws:iam::aws:policy/AdministratorAccess",
            },
            "responseElements": None,
            "requestID": str(uuid.uuid4()),
            "eventID": str(uuid.uuid4()),
            "readOnly": False,
            "eventType": "AwsApiCall",
            "recipientAccountId": config.aws_account_id,
        },
    ]

    # Step 2: Access new resources they couldn't before (15 min later)
    for i in range(5):
        dt = datetime(
            scenario_day.year,
            scenario_day.month,
            scenario_day.day,
            base_hour,
            30 + i * 3,
            0,
            tzinfo=timezone.utc,
        )
        escalation_events.append(
            {
                "eventVersion": "1.08",
                "userIdentity": {
                    "type": "IAMUser",
                    "principalId": iam_user["UserId"],
                    "arn": iam_user["Arn"],
                    "accountId": config.aws_account_id,
                    "userName": iam_user["UserName"],
                },
                "eventTime": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "eventSource": random.choice(
                    [
                        "iam.amazonaws.com",
                        "secretsmanager.amazonaws.com",
                        "kms.amazonaws.com",
                    ]
                ),
                "eventName": random.choice(
                    [
                        "ListUsers",
                        "GetSecretValue",
                        "Decrypt",
                        "ListRoles",
                    ]
                ),
                "awsRegion": config.aws_region,
                "sourceIPAddress": "203.0.113.200",
                "userAgent": "aws-cli/2.15.0 Python/3.11.6 Darwin/23.2.0",
                "requestParameters": {},
                "responseElements": None,
                "requestID": str(uuid.uuid4()),
                "eventID": str(uuid.uuid4()),
                "readOnly": True,
                "eventType": "AwsApiCall",
                "recipientAccountId": config.aws_account_id,
            }
        )

    cloudtrail_events[day_key].extend(escalation_events)
    cloudtrail_events[day_key].sort(key=lambda e: e["eventTime"])

    logger.info(
        "Scenario: privilege escalation by %s on %s",
        target["employee_id"],
        day_key,
    )

    return {
        "scenario": "privilege_escalation",
        "severity": "CRITICAL",
        "target_employee": target["employee_id"],
        "target_name": f"{target['first_name']} {target['last_name']}",
        "description": (
            "User modified their own IAM policy via PutUserPolicy "
            "and AttachUserPolicy, then accessed secrets and KMS "
            "resources they previously could not"
        ),
        "detected_date": day_key,
        "actions": ["iam:PutUserPolicy", "iam:AttachUserPolicy"],
    }


def inject_credential_stuffing(
    config: CompanyConfig,
    company_data: dict,
    auth_events: dict[str, list[dict]],
    start_date: date,
) -> dict:
    """Scenario 5: Burst of failed logins from one IP, then 1-2 successes."""
    scenario_day = _pick_scenario_day(start_date, config.activity_days)
    day_key = scenario_day.isoformat()
    attacker_ip = "185.220.101.42"
    base_hour = random.randint(1, 5)  # late night / early morning

    if day_key not in auth_events:
        auth_events[day_key] = []

    # Pick 15-20 target accounts for the spray
    active = [e for e in company_data["employees"] if e["status"] == "active"]
    targets = random.sample(active, min(20, len(active)))

    # Generate 50+ failed logins across targets
    failed_events = []
    for i in range(random.randint(50, 75)):
        target = random.choice(targets)
        minute = i  # roughly 1 per minute
        if minute >= 60:
            minute = minute % 60
        dt = datetime(
            scenario_day.year,
            scenario_day.month,
            scenario_day.day,
            base_hour + (i // 60),
            minute,
            random.randint(0, 59),
            tzinfo=timezone.utc,
        )
        failed_events.append(
            {
                "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "event_id": f"auth-{uuid.uuid4().hex[:12]}",
                "event_type": "login_failure",
                "user_id": target["employee_id"],
                "email": target["email"],
                "source_ip": attacker_ip,
                "geo": {
                    "city": "Unknown",
                    "country": "RU",
                    "latitude": 55.7558,
                    "longitude": 37.6173,
                },
                "device": {
                    "type": "unknown",
                    "os": "Linux",
                    "browser": "python-requests/2.31.0",
                },
                "session_id": None,
                "mfa_used": False,
                "risk_score": 0.95,
            }
        )

    # 1-2 successful logins at the end
    compromised = random.sample(targets, min(2, len(targets)))
    success_events = []
    for j, target in enumerate(compromised):
        dt = datetime(
            scenario_day.year,
            scenario_day.month,
            scenario_day.day,
            base_hour + 1,
            30 + j * 5,
            0,
            tzinfo=timezone.utc,
        )
        success_events.append(
            {
                "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "event_id": f"auth-{uuid.uuid4().hex[:12]}",
                "event_type": "login_success",
                "user_id": target["employee_id"],
                "email": target["email"],
                "source_ip": attacker_ip,
                "geo": {
                    "city": "Unknown",
                    "country": "RU",
                    "latitude": 55.7558,
                    "longitude": 37.6173,
                },
                "device": {
                    "type": "unknown",
                    "os": "Linux",
                    "browser": "python-requests/2.31.0",
                },
                "session_id": f"sess-{uuid.uuid4().hex[:12]}",
                "mfa_used": False,
                "risk_score": 0.98,
            }
        )

    auth_events[day_key].extend(failed_events + success_events)
    auth_events[day_key].sort(key=lambda e: e["timestamp"])

    logger.info(
        "Scenario: credential stuffing on %s (%d failed, %d succeeded)",
        day_key,
        len(failed_events),
        len(success_events),
    )

    return {
        "scenario": "credential_stuffing",
        "severity": "CRITICAL",
        "description": (
            f"{len(failed_events)} failed login attempts from {attacker_ip} "
            f"against {len(targets)} accounts, followed by "
            f"{len(success_events)} successful logins"
        ),
        "detected_date": day_key,
        "source_ip": attacker_ip,
        "source_geo": "Russia",
        "failed_attempts": len(failed_events),
        "successful_logins": len(success_events),
        "compromised_accounts": [
            {
                "employee_id": t["employee_id"],
                "name": f"{t['first_name']} {t['last_name']}",
            }
            for t in compromised
        ],
    }


def inject_data_exfiltration(
    config: CompanyConfig,
    company_data: dict,
    cloudtrail_events: dict[str, list[dict]],
    iam_data: dict,
    start_date: date,
) -> dict:
    """Scenario 6: Sudden spike in S3 GetObject calls to sensitive bucket."""
    target = _pick_target(company_data["employees"], ["Engineering", "IT"])
    iam_user = _find_iam_user(iam_data["users"], target)
    scenario_day = _pick_scenario_day(start_date, config.activity_days)
    day_key = scenario_day.isoformat()

    if not iam_user:
        return _empty_finding("data_exfiltration", "No IAM user found")

    if day_key not in cloudtrail_events:
        cloudtrail_events[day_key] = []

    # Find the sensitive bucket
    buckets = iam_data["resources"].get("s3_buckets", [])
    sensitive_bucket = next(
        (b for b in buckets if "prod-data" in b["BucketName"]),
        buckets[0] if buckets else None,
    )

    if not sensitive_bucket:
        return _empty_finding("data_exfiltration", "No S3 buckets found")

    # Generate 300-500 GetObject calls in a 2-hour window
    num_calls = random.randint(300, 500)
    base_hour = random.randint(14, 18)
    file_prefixes = [
        "customers/",
        "transactions/",
        "pii/",
        "exports/",
        "reports/",
        "financial/",
        "users/",
        "accounts/",
    ]

    exfil_events = []
    for i in range(num_calls):
        minute = (i * 120 // num_calls) % 60
        hour = base_hour + (i * 120 // num_calls) // 60
        dt = datetime(
            scenario_day.year,
            scenario_day.month,
            scenario_day.day,
            min(hour, 23),
            minute,
            random.randint(0, 59),
            tzinfo=timezone.utc,
        )

        exfil_events.append(
            {
                "eventVersion": "1.08",
                "userIdentity": {
                    "type": "IAMUser",
                    "principalId": iam_user["UserId"],
                    "arn": iam_user["Arn"],
                    "accountId": config.aws_account_id,
                    "userName": iam_user["UserName"],
                },
                "eventTime": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "eventSource": "s3.amazonaws.com",
                "eventName": "GetObject",
                "awsRegion": config.aws_region,
                "sourceIPAddress": "198.51.100.50",
                "userAgent": "aws-cli/2.15.0 Python/3.11.6 Darwin/23.2.0",
                "requestParameters": {
                    "bucketName": sensitive_bucket["BucketName"],
                    "key": f"{random.choice(file_prefixes)}file_{i:04d}.csv",
                },
                "responseElements": None,
                "requestID": str(uuid.uuid4()),
                "eventID": str(uuid.uuid4()),
                "readOnly": True,
                "eventType": "AwsApiCall",
                "recipientAccountId": config.aws_account_id,
            }
        )

    cloudtrail_events[day_key].extend(exfil_events)
    cloudtrail_events[day_key].sort(key=lambda e: e["eventTime"])

    logger.info(
        "Scenario: data exfiltration by %s on %s (%d GetObject calls)",
        target["employee_id"],
        day_key,
        num_calls,
    )

    return {
        "scenario": "data_exfiltration",
        "severity": "CRITICAL",
        "target_employee": target["employee_id"],
        "target_name": f"{target['first_name']} {target['last_name']}",
        "description": (
            f"{num_calls} S3 GetObject calls to {sensitive_bucket['BucketName']} "
            f"in a 2-hour window (normal baseline: 5-10/day)"
        ),
        "detected_date": day_key,
        "bucket": sensitive_bucket["BucketName"],
        "num_calls": num_calls,
        "time_window_hours": 2,
    }


def _empty_finding(scenario: str, reason: str) -> dict:
    """Return a placeholder finding when scenario injection fails."""
    return {
        "scenario": scenario,
        "severity": "INFO",
        "description": f"Scenario skipped: {reason}",
    }


def inject_scenarios(
    config: CompanyConfig,
    company_data: dict,
    iam_data: dict,
    cloudtrail_events: dict[str, list[dict]],
    auth_events: dict[str, list[dict]],
    start_date: date,
) -> list[dict]:
    """Inject all security scenarios. Returns list of findings/alerts."""
    findings = []

    findings.append(
        inject_over_permissioned(
            config,
            company_data,
            iam_data,
            start_date,
        )
    )
    findings.append(
        inject_impossible_travel(
            config,
            company_data,
            auth_events,
            start_date,
        )
    )
    findings.append(
        inject_off_hours_access(
            config,
            company_data,
            cloudtrail_events,
            iam_data,
            start_date,
        )
    )
    findings.append(
        inject_privilege_escalation(
            config,
            company_data,
            cloudtrail_events,
            iam_data,
            start_date,
        )
    )
    findings.append(
        inject_credential_stuffing(
            config,
            company_data,
            auth_events,
            start_date,
        )
    )
    findings.append(
        inject_data_exfiltration(
            config,
            company_data,
            cloudtrail_events,
            iam_data,
            start_date,
        )
    )

    return findings
