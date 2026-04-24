"""Company profile and generation parameters."""

from __future__ import annotations

import random
from dataclasses import dataclass

INDUSTRIES = [
    "aerospace",
    "agriculture",
    "biotech",
    "construction",
    "consulting",
    "defense",
    "education",
    "energy",
    "fintech",
    "healthcare",
    "hospitality",
    "insurance",
    "legal",
    "logistics",
    "manufacturing",
    "media",
    "real-estate",
    "retail",
    "saas",
    "telecom",
]


@dataclass
class CompanyConfig:
    name: str = ""
    size: int = 0
    industry: str = ""
    domain: str = ""
    aws_account_id: str = ""
    aws_region: str = "us-east-1"
    seed: int | None = None
    activity_days: int = 30
    output_dir: str = "data"

    def resolve_defaults(self, fake) -> None:
        """Fill in missing fields with generated defaults."""
        if not self.industry:
            self.industry = random.choice(INDUSTRIES)
        if not self.size:
            self.size = random.randint(100, 2000)
        if not self.name:
            self.name = fake.company().split(",")[0].split(" and ")[0]
        if not self.domain:
            slug = (
                self.name.lower()
                .replace(" ", "")
                .replace(",", "")
                .replace(".", "")
                .replace("'", "")
                .replace("-", "")
            )
            self.domain = f"{slug}.io"
        if not self.aws_account_id:
            self.aws_account_id = str(random.randint(100000000000, 999999999999))
