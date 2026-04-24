"""Generate AWS CloudTrail event logs."""

from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import CompanyConfig

# CloudTrail event templates — (eventSource, eventName, readOnly)
COMMON_EVENTS = [
    ("s3.amazonaws.com", "GetObject", True),
    ("s3.amazonaws.com", "PutObject", False),
    ("s3.amazonaws.com", "ListBuckets", True),
    ("s3.amazonaws.com", "ListObjects", True),
    ("s3.amazonaws.com", "DeleteObject", False),
    ("s3.amazonaws.com", "GetBucketAcl", True),
    ("ec2.amazonaws.com", "DescribeInstances", True),
    ("ec2.amazonaws.com", "DescribeSecurityGroups", True),
    ("ec2.amazonaws.com", "StartInstances", False),
    ("ec2.amazonaws.com", "StopInstances", False),
    ("ec2.amazonaws.com", "RunInstances", False),
    ("ec2.amazonaws.com", "TerminateInstances", False),
    ("iam.amazonaws.com", "ListUsers", True),
    ("iam.amazonaws.com", "GetUser", True),
    ("iam.amazonaws.com", "ListRoles", True),
    ("iam.amazonaws.com", "ListPolicies", True),
    ("iam.amazonaws.com", "GetPolicy", True),
    ("iam.amazonaws.com", "CreateUser", False),
    ("iam.amazonaws.com", "AttachUserPolicy", False),
    ("iam.amazonaws.com", "PutUserPolicy", False),
    ("sts.amazonaws.com", "AssumeRole", True),
    ("sts.amazonaws.com", "GetCallerIdentity", True),
    ("signin.amazonaws.com", "ConsoleLogin", True),
    ("lambda.amazonaws.com", "Invoke", False),
    ("lambda.amazonaws.com", "ListFunctions", True),
    ("dynamodb.amazonaws.com", "GetItem", True),
    ("dynamodb.amazonaws.com", "PutItem", False),
    ("dynamodb.amazonaws.com", "Query", True),
    ("cloudwatch.amazonaws.com", "DescribeAlarms", True),
    ("cloudwatch.amazonaws.com", "GetMetricData", True),
    ("logs.amazonaws.com", "DescribeLogGroups", True),
    ("logs.amazonaws.com", "GetLogEvents", True),
    ("rds.amazonaws.com", "DescribeDBInstances", True),
    ("kms.amazonaws.com", "Decrypt", True),
    ("kms.amazonaws.com", "Encrypt", False),
    ("secretsmanager.amazonaws.com", "GetSecretValue", True),
]

# Event weights by role type
# Engineers do more, non-technical roles do fewer AWS calls
EVENTS_PER_DAY = {
    "Engineering": (5, 25),
    "IT": (3, 20),
    "Security": (2, 15),
    "Research & Development": (3, 15),
    "Product": (1, 5),
    "Finance": (0, 3),
    "Executive": (0, 2),
}

USER_AGENTS = [
    "aws-cli/2.15.0 Python/3.11.6 Darwin/23.2.0",
    "aws-cli/2.13.0 Python/3.11.4 Linux/5.15.0",
    "console.amazonaws.com",
    "Boto3/1.34.0 Python/3.11.6",
    "Boto3/1.28.0 Python/3.9.18",
    "terraform/1.7.0",
    "aws-sdk-go/1.50.0 (go1.21; linux; amd64)",
    "[S3Console/0.4, aws-internal/3 aws-sdk-java/1.12.600]",
]


def _generate_event_time(day: date) -> str:
    """Generate a realistic timestamp biased toward business hours."""
    if day.weekday() < 5:
        # Weekday — gaussian centered on 1pm, stddev 3 hours
        hour = int(random.gauss(13, 3))
        hour = max(6, min(23, hour))
    else:
        # Weekend — sparse, mostly off-hours
        hour = random.randint(8, 22)

    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    dt = datetime(
        day.year,
        day.month,
        day.day,
        hour,
        minute,
        second,
        tzinfo=timezone.utc,
    )
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


_SERVICE_ACCOUNT_EVENTS = {
    "terraform": [
        ("ec2.amazonaws.com", "DescribeInstances", True),
        ("ec2.amazonaws.com", "RunInstances", False),
        ("s3.amazonaws.com", "PutObject", False),
        ("iam.amazonaws.com", "ListRoles", True),
        ("sts.amazonaws.com", "AssumeRole", True),
    ],
    "datadog": [
        ("cloudwatch.amazonaws.com", "GetMetricData", True),
        ("cloudwatch.amazonaws.com", "DescribeAlarms", True),
        ("logs.amazonaws.com", "GetLogEvents", True),
        ("ec2.amazonaws.com", "DescribeInstances", True),
    ],
    "backup": [
        ("s3.amazonaws.com", "PutObject", False),
        ("s3.amazonaws.com", "GetObject", True),
        ("rds.amazonaws.com", "DescribeDBInstances", True),
    ],
}

_DEFAULT_SVC_EVENTS = [
    ("sts.amazonaws.com", "AssumeRole", True),
    ("s3.amazonaws.com", "GetObject", True),
]

_BASIC_USER_EVENTS = [
    ("signin.amazonaws.com", "ConsoleLogin", True),
    ("s3.amazonaws.com", "ListBuckets", True),
    ("s3.amazonaws.com", "GetObject", True),
]

_TECHNICAL_DEPTS = {"Engineering", "IT", "Security", "Research & Development"}
_READONLY_DEPTS = {"Finance", "Product"}


def _pick_events_for_user(iam_user: dict) -> list[tuple]:
    """Select appropriate event types for a given user."""
    # Service accounts use specific event sets
    if iam_user.get("service_account_id"):
        name = iam_user["UserName"]
        for keyword, events in _SERVICE_ACCOUNT_EVENTS.items():
            if keyword in name:
                return events
        return _DEFAULT_SVC_EVENTS

    # Human users: filter by department
    dept = ""
    for tag in iam_user.get("Tags", []):
        if tag.get("Key") == "Department":
            dept = tag["Value"]
            break

    if dept in _TECHNICAL_DEPTS:
        return COMMON_EVENTS
    if dept in _READONLY_DEPTS:
        return [e for e in COMMON_EVENTS if e[2]]
    return _BASIC_USER_EVENTS


def _build_request_params(
    event_source: str,
    event_name: str,
    resources: dict,
) -> dict | None:
    """Build realistic request parameters for an event."""
    if event_source == "s3.amazonaws.com" and resources.get("s3_buckets"):
        bucket = random.choice(resources["s3_buckets"])
        if event_name in ("GetObject", "PutObject", "DeleteObject"):
            return {
                "bucketName": bucket["BucketName"],
                "key": random.choice(
                    [
                        "reports/daily-summary.csv",
                        "exports/users.json",
                        "logs/app.log",
                        "config/settings.yaml",
                        "data/transactions.parquet",
                        "backups/db-snapshot.sql.gz",
                    ]
                ),
            }
        if event_name in ("ListObjects", "ListBuckets"):
            return {"bucketName": bucket["BucketName"]}

    if event_source == "ec2.amazonaws.com" and resources.get("ec2_instances"):
        instance = random.choice(resources["ec2_instances"])
        if event_name in ("StartInstances", "StopInstances", "TerminateInstances"):
            return {"instancesSet": {"items": [{"instanceId": instance["InstanceId"]}]}}
        if event_name == "DescribeInstances":
            return {}

    return None


def generate_cloudtrail_day(
    day: date,
    config: CompanyConfig,
    iam_users: list[dict],
    resources: dict,
) -> list[dict]:
    """Generate CloudTrail events for a single day."""
    events = []
    is_weekday = day.weekday() < 5

    for iam_user in iam_users:
        # Determine how many events this user generates today
        dept = ""
        for tag in iam_user.get("Tags", []):
            if tag.get("Key") == "Department":
                dept = tag["Value"]
                break

        min_events, max_events = EVENTS_PER_DAY.get(dept, (0, 3))

        # Weekend: 90% of users don't generate events
        if not is_weekday and random.random() < 0.90:
            continue

        # Skip some users on any given day (not everyone is active)
        if random.random() < 0.30:
            continue

        # Terminated/stale users still generate some events (realistic gap)
        if iam_user.get("_stale") and random.random() < 0.85:
            continue

        num_events = random.randint(min_events, max_events)
        if num_events == 0:
            continue

        available_events = _pick_events_for_user(iam_user)
        octets = [
            random.randint(50, 220),
            random.randint(1, 254),
            random.randint(1, 254),
            random.randint(1, 254),
        ]
        user_ip = ".".join(str(o) for o in octets)

        for _ in range(num_events):
            source, name, read_only = random.choice(available_events)
            request_params = _build_request_params(source, name, resources)

            event = {
                "eventVersion": "1.08",
                "userIdentity": {
                    "type": "IAMUser",
                    "principalId": iam_user["UserId"],
                    "arn": iam_user["Arn"],
                    "accountId": config.aws_account_id,
                    "userName": iam_user["UserName"],
                },
                "eventTime": _generate_event_time(day),
                "eventSource": source,
                "eventName": name,
                "awsRegion": config.aws_region,
                "sourceIPAddress": user_ip,
                "userAgent": random.choice(USER_AGENTS),
                "requestParameters": request_params,
                "responseElements": None if read_only else {"status": "Success"},
                "requestID": str(uuid.uuid4()),
                "eventID": str(uuid.uuid4()),
                "readOnly": read_only,
                "eventType": "AwsApiCall",
                "recipientAccountId": config.aws_account_id,
            }

            # Imperfection: 5% missing userAgent
            if random.random() < 0.05:
                del event["userAgent"]

            # Imperfection: occasional error responses
            if random.random() < 0.03:
                event["errorCode"] = random.choice(
                    [
                        "AccessDenied",
                        "NoSuchBucket",
                        "ThrottlingException",
                        "InvalidParameterValue",
                    ]
                )
                event["errorMessage"] = "Access Denied"

            events.append(event)

    # Sort by time
    events.sort(key=lambda e: e["eventTime"])
    return events


def generate_cloudtrail(
    config: CompanyConfig,
    iam_data: dict,
    start_date: date,
) -> dict[str, list[dict]]:
    """Generate CloudTrail events for the full activity window."""
    daily_events = {}

    for day_offset in range(config.activity_days):
        day = start_date + timedelta(days=day_offset)
        events = generate_cloudtrail_day(
            day,
            config,
            iam_data["users"],
            iam_data["resources"],
        )
        daily_events[day.isoformat()] = events

    return daily_events
