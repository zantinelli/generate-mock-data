"""Generate realistic security demo data for a fictional company.

Usage:
    python main.py --size 500 --industry healthcare
    python main.py --size 150 --industry fintech --name NovaPay --seed 42
    python main.py  # random defaults
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from datetime import date, timedelta
from pathlib import Path

import yaml
from faker import Faker

from config import INDUSTRIES, CompanyConfig
from generators.auth_events import generate_auth_events
from generators.aws_cloudtrail import generate_cloudtrail
from generators.aws_iam import generate_iam
from generators.company import generate_company
from generators.endpoints import generate_endpoints
from generators.scenarios import inject_scenarios

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def write_dual(path_stem: Path, data) -> None:
    """Write data as both JSON and YAML files."""
    path_stem.parent.mkdir(parents=True, exist_ok=True)

    json_path = path_stem.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    yaml_path = path_stem.with_suffix(".yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def write_daily_files(base_dir: Path, daily_data: dict[str, list]) -> None:
    """Write per-day event files in both formats."""
    base_dir.mkdir(parents=True, exist_ok=True)
    for day_str, events in daily_data.items():
        write_dual(base_dir / day_str, events)


def write_all_output(output_dir: Path, all_data: dict) -> None:
    """Write all generated data to the output directory structure."""
    logger.info("Writing output to %s", output_dir)

    # Company data
    company = all_data["company"]
    write_dual(output_dir / "company" / "employees", company["employees"])
    write_dual(output_dir / "company" / "departments", company["departments"])
    write_dual(output_dir / "company" / "groups", company["groups"])
    write_dual(
        output_dir / "company" / "service_accounts",
        company["service_accounts"],
    )

    # AWS IAM
    iam = all_data["iam"]
    write_dual(output_dir / "cloud" / "aws" / "iam" / "users", iam["users"])
    write_dual(output_dir / "cloud" / "aws" / "iam" / "roles", iam["roles"])
    write_dual(
        output_dir / "cloud" / "aws" / "iam" / "policies",
        iam["policies"],
    )
    write_dual(
        output_dir / "cloud" / "aws" / "iam" / "resources",
        iam["resources"],
    )

    # CloudTrail daily logs
    write_daily_files(
        output_dir / "cloud" / "aws" / "cloudtrail",
        all_data["cloudtrail"],
    )

    # Auth events daily logs
    write_daily_files(
        output_dir / "identity" / "auth_events",
        all_data["auth_events"],
    )

    # Endpoints
    endpoints = all_data["endpoints"]
    write_dual(output_dir / "endpoints" / "devices", endpoints["devices"])
    write_daily_files(
        output_dir / "endpoints" / "process_events",
        endpoints["process_events"],
    )

    # Security findings
    write_dual(
        output_dir / "alerts" / "security_findings",
        all_data["findings"],
    )


def generate(config: CompanyConfig) -> dict:
    """Run the full data generation pipeline."""
    # Set up random seeds
    if config.seed is not None:
        random.seed(config.seed)
        Faker.seed(config.seed)

    fake = Faker()
    config.resolve_defaults(fake)

    logger.info(
        "Generating data for %s (%d employees, %s industry)",
        config.name,
        config.size,
        config.industry,
    )

    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=config.activity_days)
    logger.info("Activity window: %s to %s", start_date, end_date)

    # Step 1: Company org structure
    logger.info("Generating company org structure")
    company_data = generate_company(config, fake)
    logger.info(
        "Created %d employees across %d departments",
        len(company_data["employees"]),
        len(company_data["departments"]),
    )

    # Step 2: AWS IAM
    logger.info("Generating AWS IAM data")
    iam_data = generate_iam(config, company_data, fake)
    logger.info("Created %d IAM users", len(iam_data["users"]))

    # Step 3: CloudTrail events
    logger.info("Generating CloudTrail events (%d days)", config.activity_days)
    cloudtrail = generate_cloudtrail(config, iam_data, start_date)
    total_ct = sum(len(v) for v in cloudtrail.values())
    logger.info("Generated %d CloudTrail events", total_ct)

    # Step 4: Auth events
    logger.info("Generating auth events")
    auth_events = generate_auth_events(config, company_data, start_date)
    total_auth = sum(len(v) for v in auth_events.values())
    logger.info("Generated %d auth events", total_auth)

    # Step 5: Endpoint telemetry
    logger.info("Generating endpoint telemetry")
    endpoint_data = generate_endpoints(config, company_data, fake, start_date)
    total_proc = sum(len(v) for v in endpoint_data["process_events"].values())
    logger.info(
        "Created %d devices, %d process events",
        len(endpoint_data["devices"]),
        total_proc,
    )

    # Step 6: Inject security scenarios
    logger.info("Injecting security scenarios")
    findings = inject_scenarios(
        config,
        company_data,
        iam_data,
        cloudtrail,
        auth_events,
        start_date,
    )
    logger.info("Injected %d security scenarios", len(findings))

    return {
        "company": company_data,
        "iam": iam_data,
        "cloudtrail": cloudtrail,
        "auth_events": auth_events,
        "endpoints": endpoint_data,
        "findings": findings,
    }


def parse_args(argv: list[str] | None = None) -> CompanyConfig:
    """Parse CLI arguments into CompanyConfig."""
    parser = argparse.ArgumentParser(
        description="Generate realistic security demo data",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=0,
        help="Number of employees (default: random 100-2000)",
    )
    parser.add_argument(
        "--industry",
        choices=INDUSTRIES,
        default="",
        help="Company industry (default: random)",
    )
    parser.add_argument("--name", default="", help="Company name")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Days of activity to generate (default: 30)",
    )
    parser.add_argument(
        "--output",
        default="data",
        help="Output directory (default: data)",
    )

    args = parser.parse_args(argv)

    return CompanyConfig(
        name=args.name,
        size=args.size,
        industry=args.industry,
        seed=args.seed,
        activity_days=args.days,
        output_dir=args.output,
    )


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    config = parse_args(argv)
    all_data = generate(config)

    output_dir = Path(config.output_dir)
    write_all_output(output_dir, all_data)

    logger.info("Done. Output written to %s/", output_dir)


if __name__ == "__main__":
    main()
