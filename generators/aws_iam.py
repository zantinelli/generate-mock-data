"""Generate AWS IAM data: users, roles, policies, and cloud resources."""

from __future__ import annotations

import random
import uuid
from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import CompanyConfig

# Realistic AWS managed policy names
AWS_MANAGED_POLICIES = [
    "AdministratorAccess",
    "PowerUserAccess",
    "ReadOnlyAccess",
    "AmazonS3FullAccess",
    "AmazonS3ReadOnlyAccess",
    "AmazonEC2FullAccess",
    "AmazonEC2ReadOnlyAccess",
    "IAMFullAccess",
    "IAMReadOnlyAccess",
    "CloudWatchFullAccess",
    "CloudWatchReadOnlyAccess",
    "AmazonRDSFullAccess",
    "AmazonDynamoDBFullAccess",
    "AWSLambdaFullAccess",
    "AmazonSQSFullAccess",
    "AmazonSNSFullAccess",
    "AmazonVPCFullAccess",
    "SecurityAudit",
    "ViewOnlyAccess",
]

# Policy assignment by department/level
POLICY_MAP = {
    ("Engineering", "senior"): ["PowerUserAccess", "AmazonS3FullAccess"],
    ("Engineering", "mid"): ["AmazonS3ReadOnlyAccess", "AmazonEC2ReadOnlyAccess"],
    ("Engineering", "junior"): ["ReadOnlyAccess"],
    ("Engineering", "manager"): ["PowerUserAccess", "AmazonS3FullAccess"],
    ("Engineering", "director"): ["PowerUserAccess", "IAMReadOnlyAccess"],
    ("Engineering", "executive"): ["AdministratorAccess"],
    ("IT", "senior"): ["AdministratorAccess"],
    ("IT", "mid"): ["PowerUserAccess", "IAMReadOnlyAccess"],
    ("IT", "junior"): ["AmazonEC2ReadOnlyAccess", "CloudWatchReadOnlyAccess"],
    ("IT", "manager"): ["AdministratorAccess"],
    ("IT", "director"): ["AdministratorAccess"],
    ("IT", "executive"): ["AdministratorAccess"],
    ("Security", "senior"): ["SecurityAudit", "IAMReadOnlyAccess"],
    ("Security", "mid"): ["SecurityAudit", "ViewOnlyAccess"],
    ("Security", "manager"): ["SecurityAudit", "IAMFullAccess"],
    ("Security", "director"): ["AdministratorAccess"],
    ("Security", "executive"): ["AdministratorAccess"],
    ("Finance", "senior"): ["AmazonS3ReadOnlyAccess"],
    ("Finance", "mid"): ["AmazonS3ReadOnlyAccess"],
    ("Product", "senior"): ["AmazonS3ReadOnlyAccess", "CloudWatchReadOnlyAccess"],
    ("Product", "mid"): ["ReadOnlyAccess"],
    ("Research & Development", "senior"): [
        "AmazonS3FullAccess",
        "AWSLambdaFullAccess",
    ],
    ("Research & Development", "mid"): ["AmazonS3ReadOnlyAccess"],
}

# S3 bucket templates — {company} gets replaced
S3_BUCKET_TEMPLATES = [
    ("{slug}-prod-data", "Production data store", "private", True),
    ("{slug}-staging-data", "Staging environment data", "private", True),
    ("{slug}-logs", "Application and access logs", "private", True),
    ("{slug}-backups", "Database backups", "private", True),
    ("{slug}-ml-models", "Machine learning model artifacts", "private", False),
    ("{slug}-static-assets", "Public static website assets", "public-read", True),
    ("{slug}-config", "Application configuration", "private", True),
    ("{slug}-temp", "Temporary processing files", "private", False),
    ("{slug}-reports", "Business reports and analytics", "private", True),
    ("{slug}-compliance-docs", "Compliance documentation", "private", True),
]

EC2_INSTANCE_TEMPLATES = [
    ("web-server", "t3.medium", "Web application server"),
    ("api-server", "t3.large", "REST API server"),
    ("worker", "c5.xlarge", "Background job processor"),
    ("database", "r5.xlarge", "Primary database"),
    ("database-replica", "r5.large", "Read replica"),
    ("bastion", "t3.micro", "SSH bastion host"),
    ("monitoring", "t3.medium", "Monitoring and alerting"),
    ("ci-runner", "c5.2xlarge", "CI/CD build runner"),
    ("ml-training", "p3.2xlarge", "ML model training"),
    ("etl-processor", "m5.xlarge", "ETL data pipeline"),
]


def _generate_user_id() -> str:
    """Generate a realistic AWS IAM user ID."""
    return f"AIDA{uuid.uuid4().hex[:16].upper()}"


def _get_policies(department: str, level: str) -> list[str]:
    """Get appropriate policies for a department/level combo."""
    key = (department, level)
    policies = POLICY_MAP.get(key)
    if policies:
        return list(policies)

    # Default: read-only for departments without explicit mapping
    if level in ("executive", "director"):
        return ["ReadOnlyAccess"]
    return []


def generate_iam_users(
    config: CompanyConfig,
    employees: list[dict],
    service_accounts: list[dict],
    fake,
) -> list[dict]:
    """Generate IAM users mapped to employees and service accounts."""
    iam_users = []
    account_id = config.aws_account_id

    # Not every employee has an IAM user — typically engineering, IT,
    # security, product, R&D, and some leadership
    aws_departments = {
        "Engineering",
        "IT",
        "Security",
        "Product",
        "Research & Development",
        "Finance",
        "Executive",
    }

    for emp in employees:
        has_aws = emp["department"] in aws_departments
        # Some people outside AWS depts still have accounts (10%)
        if not has_aws and random.random() > 0.10:
            continue

        username = emp["email"].split("@")[0]
        policies = _get_policies(emp["department"], emp["level"])
        create_date = fake.date_between(
            start_date=date.fromisoformat(emp["hire_date"]),
            end_date=date.fromisoformat(emp["hire_date"]) + timedelta(days=14),
        )

        user = {
            "UserName": username,
            "UserId": _generate_user_id(),
            "Arn": f"arn:aws:iam::{account_id}:user/{username}",
            "CreateDate": f"{create_date.isoformat()}T09:00:00Z",
            "employee_id": emp["employee_id"],
            "Tags": [
                {"Key": "Department", "Value": emp["department"]},
                {"Key": "employee_id", "Value": emp["employee_id"]},
            ],
            "AttachedPolicies": [
                {
                    "PolicyName": p,
                    "PolicyArn": f"arn:aws:iam::aws:policy/{p}",
                }
                for p in policies
            ],
        }

        # Imperfection: inconsistent tag naming (some use camelCase)
        if random.random() < 0.15:
            user["Tags"].append(
                {"Key": "costCenter", "Value": emp["department"][:3].upper()}
            )
        elif random.random() < 0.3:
            user["Tags"].append(
                {"Key": "cost_center", "Value": emp["department"][:3].upper()}
            )

        # Imperfection: some resources have no tags beyond the basics
        if random.random() < 0.08:
            user["Tags"] = []

        # MFA devices — mirror employee MFA status
        if emp.get("mfa_enrolled") is True:
            user["MFADevices"] = [
                {
                    "SerialNumber": (f"arn:aws:iam::{account_id}:mfa/{username}"),
                    "EnableDate": f"{create_date.isoformat()}T09:00:00Z",
                }
            ]
        else:
            user["MFADevices"] = []

        # Imperfection: terminated employees still have active IAM users
        # (no deprovisioning — realistic gap)
        if emp["status"] == "terminated":
            user["_stale"] = True  # internal flag for scenario use

        iam_users.append(user)

    # Service account IAM users
    for svc in service_accounts:
        user = {
            "UserName": svc["name"],
            "UserId": _generate_user_id(),
            "Arn": f"arn:aws:iam::{account_id}:user/{svc['name']}",
            "CreateDate": f"{svc['created_date']}T00:00:00Z",
            "service_account_id": svc["account_id"],
            "Tags": [
                {"Key": "ServiceAccount", "Value": "true"},
                {"Key": "Owner", "Value": svc.get("owner_id", "unknown")},
            ],
            "AttachedPolicies": [
                {
                    "PolicyName": "PowerUserAccess",
                    "PolicyArn": "arn:aws:iam::aws:policy/PowerUserAccess",
                }
            ],
            "MFADevices": [],
        }
        iam_users.append(user)

    return iam_users


def generate_roles(config: CompanyConfig) -> list[dict]:
    """Generate IAM roles for common patterns."""
    account_id = config.aws_account_id
    roles = [
        {
            "RoleName": "EC2-WebServer-Role",
            "RoleId": f"AROA{uuid.uuid4().hex[:16].upper()}",
            "Arn": f"arn:aws:iam::{account_id}:role/EC2-WebServer-Role",
            "Description": "Role for EC2 web server instances",
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "ec2.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            },
            "AttachedPolicies": ["AmazonS3ReadOnlyAccess", "CloudWatchFullAccess"],
        },
        {
            "RoleName": "Lambda-Execution-Role",
            "RoleId": f"AROA{uuid.uuid4().hex[:16].upper()}",
            "Arn": f"arn:aws:iam::{account_id}:role/Lambda-Execution-Role",
            "Description": "Execution role for Lambda functions",
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            },
            "AttachedPolicies": [
                "AWSLambdaFullAccess",
                "AmazonDynamoDBFullAccess",
            ],
        },
        {
            "RoleName": "CrossAccount-Audit-Role",
            "RoleId": f"AROA{uuid.uuid4().hex[:16].upper()}",
            "Arn": f"arn:aws:iam::{account_id}:role/CrossAccount-Audit-Role",
            "Description": "Cross-account audit access",
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "arn:aws:iam::987654321098:root"},
                        "Action": "sts:AssumeRole",
                        "Condition": {"Bool": {"aws:MultiFactorAuthPresent": "true"}},
                    }
                ],
            },
            "AttachedPolicies": ["SecurityAudit", "ViewOnlyAccess"],
        },
        {
            # Imperfection: overly permissive role
            "RoleName": "Legacy-Admin-Role",
            "RoleId": f"AROA{uuid.uuid4().hex[:16].upper()}",
            "Arn": f"arn:aws:iam::{account_id}:role/Legacy-Admin-Role",
            "Description": "Legacy admin role - DO NOT USE",
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": f"arn:aws:iam::{account_id}:root"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            },
            "AttachedPolicies": ["AdministratorAccess"],
        },
    ]

    return roles  # noqa: RET504


def generate_policies(config: CompanyConfig) -> list[dict]:
    """Generate custom IAM policies."""
    account_id = config.aws_account_id
    slug = config.name.lower().replace(" ", "-")

    policies = [
        {
            "PolicyName": f"{slug}-s3-data-access",
            "PolicyId": f"ANPA{uuid.uuid4().hex[:16].upper()}",
            "Arn": f"arn:aws:iam::{account_id}:policy/{slug}-s3-data-access",
            "Description": "Access to company S3 data buckets",
            "PolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject", "s3:ListBucket"],
                        "Resource": [
                            f"arn:aws:s3:::{slug}-prod-data",
                            f"arn:aws:s3:::{slug}-prod-data/*",
                        ],
                    }
                ],
            },
        },
        {
            "PolicyName": f"{slug}-deploy-policy",
            "PolicyId": f"ANPA{uuid.uuid4().hex[:16].upper()}",
            "Arn": f"arn:aws:iam::{account_id}:policy/{slug}-deploy-policy",
            "Description": "Production deployment permissions",
            "PolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ec2:*",
                            "ecs:*",
                            "ecr:*",
                            "s3:PutObject",
                        ],
                        "Resource": "*",
                    },
                ],
            },
        },
        {
            # Imperfection: overly broad policy with Resource: *
            "PolicyName": f"{slug}-legacy-full-access",
            "PolicyId": f"ANPA{uuid.uuid4().hex[:16].upper()}",
            "Arn": (f"arn:aws:iam::{account_id}:policy/{slug}-legacy-full-access"),
            "Description": "Legacy full access policy - needs review",
            "PolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "*",
                        "Resource": "*",
                    }
                ],
            },
        },
    ]

    return policies  # noqa: RET504


def generate_resources(config: CompanyConfig, fake) -> dict:
    """Generate S3 buckets and EC2 instances."""
    slug = config.name.lower().replace(" ", "-").replace("'", "")

    buckets = []
    for template, desc, acl, versioned in S3_BUCKET_TEMPLATES:
        name = template.format(slug=slug)
        created = fake.date_between(
            start_date=date.today() - timedelta(days=1200),
            end_date=date.today() - timedelta(days=60),
        )

        bucket = {
            "BucketName": name,
            "CreationDate": created.isoformat(),
            "Region": config.aws_region,
            "ACL": acl,
            "VersioningEnabled": versioned,
            "Description": desc,
        }

        # Imperfection: inconsistent tagging
        if random.random() < 0.6:
            bucket["Tags"] = {
                "Environment": random.choice(["production", "prod", "staging", "dev"]),
                "Team": random.choice(
                    ["engineering", "Engineering", "eng", "platform"]
                ),
            }
        elif random.random() < 0.3:
            bucket["Tags"] = {}  # no tags at all

        # Imperfection: encryption not enabled on some buckets
        bucket["ServerSideEncryption"] = random.random() > 0.15

        buckets.append(bucket)

    instances = []
    for name, itype, desc in EC2_INSTANCE_TEMPLATES:
        instance_id = f"i-{uuid.uuid4().hex[:17]}"
        launch_date = fake.date_between(
            start_date=date.today() - timedelta(days=365),
            end_date=date.today() - timedelta(days=7),
        )

        instance = {
            "InstanceId": instance_id,
            "Name": f"{slug}-{name}",
            "InstanceType": itype,
            "State": "running",
            "LaunchTime": f"{launch_date.isoformat()}T08:00:00Z",
            "PrivateIpAddress": (
                f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}"
            ),
            "SubnetId": f"subnet-{uuid.uuid4().hex[:8]}",
            "VpcId": f"vpc-{uuid.uuid4().hex[:8]}",
            "SecurityGroups": [
                f"sg-{uuid.uuid4().hex[:8]}",
            ],
            "Description": desc,
        }

        # Imperfection: some instances missing tags
        if random.random() > 0.20:
            instance["Tags"] = {
                "Name": f"{slug}-{name}",
                "Environment": random.choice(["prod", "staging"]),
            }

        # Imperfection: a stopped instance still in inventory
        if name == "ml-training":
            instance["State"] = "stopped"

        instances.append(instance)

    return {"s3_buckets": buckets, "ec2_instances": instances}


def generate_iam(
    config: CompanyConfig,
    company_data: dict,
    fake,
) -> dict:
    """Generate all IAM data."""
    users = generate_iam_users(
        config,
        company_data["employees"],
        company_data["service_accounts"],
        fake,
    )
    roles = generate_roles(config)
    policies = generate_policies(config)
    resources = generate_resources(config, fake)

    return {
        "users": users,
        "roles": roles,
        "policies": policies,
        "resources": resources,
    }
