"""Generate endpoint telemetry: device inventory and process execution events."""

from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import CompanyConfig

DEVICE_MODELS = {
    "macos": [
        ("MacBook Pro 16-inch", "macOS 14.3.1"),
        ("MacBook Pro 14-inch", "macOS 14.2"),
        ("MacBook Air M2", "macOS 14.3"),
        ("MacBook Air M1", "macOS 13.6.4"),
        ("iMac 24-inch", "macOS 14.1"),
    ],
    "windows": [
        ("Dell Latitude 5540", "Windows 11 23H2"),
        ("Dell XPS 15", "Windows 11 22H2"),
        ("Lenovo ThinkPad X1 Carbon", "Windows 11 23H2"),
        ("HP EliteBook 840", "Windows 10 22H2"),
        ("Surface Pro 9", "Windows 11 23H2"),
    ],
    "linux": [
        ("Dell Precision 5570", "Ubuntu 22.04.3 LTS"),
        ("Lenovo ThinkPad T14s", "Ubuntu 22.04.2 LTS"),
        ("System76 Lemur Pro", "Pop!_OS 22.04"),
    ],
}

# OS distribution by department
OS_WEIGHTS = {
    "Engineering": {"macos": 0.55, "linux": 0.30, "windows": 0.15},
    "IT": {"macos": 0.20, "linux": 0.40, "windows": 0.40},
    "Security": {"macos": 0.30, "linux": 0.45, "windows": 0.25},
    "Research & Development": {"macos": 0.40, "linux": 0.40, "windows": 0.20},
    "_default": {"macos": 0.35, "windows": 0.55, "linux": 0.10},
}

AGENT_VERSIONS = [
    "7.52.1",
    "7.52.0",
    "7.51.3",
    "7.50.2",
    "7.49.0",  # older version — imperfection
]

# Process templates: (name, command_line_template, common_parent)
BASELINE_PROCESSES = {
    "macos": [
        (
            "Google Chrome",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "launchd",
        ),
        ("Slack", "/Applications/Slack.app/Contents/MacOS/Slack", "launchd"),
        ("python3", "/usr/local/bin/python3 {script}", "zsh"),
        ("node", "/usr/local/bin/node {script}", "zsh"),
        ("docker", "/usr/local/bin/docker {cmd}", "zsh"),
        ("git", "/usr/bin/git {cmd}", "zsh"),
        ("ssh", "/usr/bin/ssh {host}", "zsh"),
        ("brew", "/usr/local/bin/brew {cmd}", "zsh"),
        (
            "code",
            "/Applications/Visual Studio Code.app/Contents/MacOS/Electron",
            "launchd",
        ),
        ("zoom.us", "/Applications/zoom.us.app/Contents/MacOS/zoom.us", "launchd"),
    ],
    "windows": [
        (
            "chrome.exe",
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "explorer.exe",
        ),
        (
            "slack.exe",
            "C:\\Users\\{user}\\AppData\\Local\\slack\\slack.exe",
            "explorer.exe",
        ),
        ("python.exe", "C:\\Python311\\python.exe {script}", "cmd.exe"),
        (
            "outlook.exe",
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
            "explorer.exe",
        ),
        (
            "teams.exe",
            "C:\\Users\\{user}\\AppData\\Local\\Microsoft\\Teams\\current\\Teams.exe",
            "explorer.exe",
        ),
        (
            "powershell.exe",
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            "explorer.exe",
        ),
        ("git.exe", "C:\\Program Files\\Git\\cmd\\git.exe {cmd}", "cmd.exe"),
        (
            "code.exe",
            "C:\\Users\\{user}\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
            "explorer.exe",
        ),
    ],
    "linux": [
        ("chrome", "/usr/bin/google-chrome-stable", "systemd"),
        ("python3", "/usr/bin/python3 {script}", "bash"),
        ("node", "/usr/bin/node {script}", "bash"),
        ("docker", "/usr/bin/docker {cmd}", "bash"),
        ("git", "/usr/bin/git {cmd}", "bash"),
        ("ssh", "/usr/bin/ssh {host}", "bash"),
        ("vim", "/usr/bin/vim {file}", "bash"),
        ("kubectl", "/usr/local/bin/kubectl {cmd}", "bash"),
        ("terraform", "/usr/local/bin/terraform {cmd}", "bash"),
    ],
}

SCRIPT_NAMES = [
    "data_export.py",
    "sync_db.py",
    "run_tests.py",
    "deploy.py",
    "analyze.py",
    "cleanup.py",
    "migrate.py",
    "report.py",
    "server.js",
    "build.js",
    "index.js",
    "worker.js",
]

GIT_COMMANDS = ["pull", "push", "commit", "status", "diff", "checkout main", "fetch"]
DOCKER_COMMANDS = ["ps", "build .", "run -d app", "compose up", "logs app"]
KUBECTL_COMMANDS = ["get pods", "get svc", "describe pod app", "logs app-pod"]
SSH_HOSTS = ["bastion.internal", "prod-db.internal", "staging-api.internal"]


def _pick_os(department: str) -> str:
    """Pick an OS type based on department."""
    weights = OS_WEIGHTS.get(department, OS_WEIGHTS["_default"])
    return random.choices(
        list(weights.keys()),
        weights=list(weights.values()),
        k=1,
    )[0]


def generate_devices(
    config: CompanyConfig,
    employees: list[dict],
    fake,
) -> list[dict]:
    """Generate device inventory — one device per active employee."""
    devices = []

    for emp in employees:
        # Terminated employees: some still have devices assigned (imperfection)
        if emp["status"] == "terminated" and random.random() < 0.70:
            continue

        os_type = _pick_os(emp["department"])
        model, os_version = random.choice(DEVICE_MODELS[os_type])

        last_name = emp["last_name"]
        first_initial = emp["first_name"][0]
        hostname = (
            f"{config.name[:8].upper().replace(' ', '')}-{first_initial}{last_name}-"
        )
        hostname += {"macos": "MBP", "windows": "PC", "linux": "LNX"}[os_type]

        device = {
            "device_id": f"DEV-{uuid.uuid4().hex[:8]}",
            "hostname": hostname,
            "os": os_version,
            "os_type": os_type,
            "model": model,
            "agent_version": random.choice(AGENT_VERSIONS),
            "last_seen": fake.date_time_between(
                start_date="-7d",
                end_date="now",
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "assigned_user": emp["employee_id"],
            "serial_number": fake.bothify("??##??##??##").upper(),
            "disk_encrypted": random.random() > 0.05,
            "compliant": random.random() > 0.10,
        }

        # Imperfection: 15% have outdated agent
        if random.random() < 0.15:
            device["agent_version"] = AGENT_VERSIONS[-1]

        # Imperfection: some devices missing serial
        if random.random() < 0.05:
            del device["serial_number"]

        devices.append(device)

    return devices


def _fill_command(template: str, username: str) -> str:
    """Fill in command line template placeholders."""
    cmd = template
    if "{script}" in cmd:
        cmd = cmd.replace("{script}", random.choice(SCRIPT_NAMES))
    if "{cmd}" in cmd:
        if "docker" in template.lower():
            cmd = cmd.replace("{cmd}", random.choice(DOCKER_COMMANDS))
        elif "git" in template.lower():
            cmd = cmd.replace("{cmd}", random.choice(GIT_COMMANDS))
        elif "kubectl" in template.lower():
            cmd = cmd.replace("{cmd}", random.choice(KUBECTL_COMMANDS))
        elif "brew" in template.lower():
            cmd = cmd.replace(
                "{cmd}", random.choice(["update", "upgrade", "install jq"])
            )
        elif "terraform" in template.lower():
            cmd = cmd.replace("{cmd}", random.choice(["plan", "apply", "init"]))
        else:
            cmd = cmd.replace("{cmd}", "run")
    if "{host}" in cmd:
        cmd = cmd.replace("{host}", random.choice(SSH_HOSTS))
    if "{user}" in cmd:
        cmd = cmd.replace("{user}", username)
    if "{file}" in cmd:
        cmd = cmd.replace("{file}", random.choice(SCRIPT_NAMES))
    return cmd


def generate_process_events_day(
    day: date,
    devices: list[dict],
    employees: list[dict],
) -> list[dict]:
    """Generate process execution events for a single day."""
    events = []
    is_weekday = day.weekday() < 5

    # Build employee lookup
    emp_lookup = {e["employee_id"]: e for e in employees}

    for device in devices:
        emp_id = device["assigned_user"]
        emp = emp_lookup.get(emp_id)
        if not emp or emp["status"] != "active":
            continue

        # Weekend: 95% of devices quiet
        if not is_weekday and random.random() < 0.95:
            continue

        # Weekday: sample 30-50% of devices
        if is_weekday and random.random() < 0.50:
            continue

        os_type = device["os_type"]
        available_procs = BASELINE_PROCESSES.get(os_type, BASELINE_PROCESSES["linux"])
        num_events = random.randint(2, 8)
        username = emp["email"].split("@")[0]

        for _ in range(num_events):
            proc_name, cmd_template, parent = random.choice(available_procs)
            hour = int(random.gauss(13, 3))
            hour = max(7, min(22, hour))
            dt = datetime(
                day.year,
                day.month,
                day.day,
                hour,
                random.randint(0, 59),
                random.randint(0, 59),
                tzinfo=timezone.utc,
            )

            event = {
                "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "event_id": f"proc-{uuid.uuid4().hex[:12]}",
                "device_id": device["device_id"],
                "hostname": device["hostname"],
                "pid": random.randint(1000, 65000),
                "ppid": random.randint(1, 999),
                "process_name": proc_name,
                "command_line": _fill_command(cmd_template, username),
                "user": username,
                "parent_process": parent,
                "hash_sha256": uuid.uuid4().hex + uuid.uuid4().hex[:32],
            }

            events.append(event)

    events.sort(key=lambda e: e["timestamp"])
    return events


def generate_endpoints(
    config: CompanyConfig,
    company_data: dict,
    fake,
    start_date: date,
) -> dict:
    """Generate all endpoint data."""
    devices = generate_devices(config, company_data["employees"], fake)

    process_events = {}
    for day_offset in range(config.activity_days):
        day = start_date + timedelta(days=day_offset)
        events = generate_process_events_day(
            day,
            devices,
            company_data["employees"],
        )
        process_events[day.isoformat()] = events

    return {
        "devices": devices,
        "process_events": process_events,
    }
