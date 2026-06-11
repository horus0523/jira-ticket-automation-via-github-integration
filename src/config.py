"""Runtime configuration helpers for the Jira webhook service."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse


PLACEHOLDER_VALUES = {
    "",
    "change-me",
    "replace-me",
    "your-domain.atlassian.net",
    "https://your-domain.atlassian.net",
    "your_jira_api_token_here",
    "your-email@domain.com",
    "your_webhook_secret_here",
    "your_metrics_token_here",
    "project",
}

REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ATLASSIAN_CLOUD_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.atlassian\.net$"
)


def require_non_placeholder(name: str, value: str | None) -> str:
    """Ensure an environment variable is present and not an example placeholder."""
    normalized = (value or "").strip()
    if normalized.lower() in PLACEHOLDER_VALUES:
        raise ValueError(
            f"{name} is required and must not use example placeholder values"
        )
    return normalized


def validate_jira_url(value: str) -> str:
    """Accept only HTTPS Atlassian Cloud Jira URLs."""
    normalized = require_non_placeholder("JIRA_URL", value)
    parsed = urlparse(normalized)

    if parsed.scheme != "https":
        raise ValueError("JIRA_URL must use https")

    hostname = (parsed.hostname or "").lower()
    if not ATLASSIAN_CLOUD_PATTERN.fullmatch(hostname):
        raise ValueError(
            "JIRA_URL must point to an Atlassian Cloud host (*.atlassian.net)"
        )

    return f"https://{hostname}"


def parse_allowed_repos(value: str | None) -> set[str]:
    """Parse owner/repo CSV values into a normalized allowlist."""
    if not value or not value.strip():
        return set()

    repos: set[str] = set()
    for raw_repo in value.split(","):
        repo = raw_repo.strip().lower()
        if not repo:
            continue
        if not REPO_PATTERN.fullmatch(repo):
            raise ValueError(
                "ALLOWED_GITHUB_REPOS must be a comma-separated list of owner/repo values"
            )
        repos.add(repo)

    return repos


def load_runtime_config(environ: dict[str, str] | None = None) -> dict[str, object]:
    """Load and validate runtime configuration from the environment."""
    env = environ or os.environ
    flask_env = (env.get("FLASK_ENV") or "production").strip().lower()

    return {
        "JIRA_URL": validate_jira_url(env.get("JIRA_URL")),
        "JIRA_EMAIL": require_non_placeholder("JIRA_EMAIL", env.get("JIRA_EMAIL")),
        "JIRA_API_TOKEN": require_non_placeholder(
            "JIRA_API_TOKEN", env.get("JIRA_API_TOKEN")
        ),
        "JIRA_PROJECT_KEY": require_non_placeholder(
            "JIRA_PROJECT_KEY", env.get("JIRA_PROJECT_KEY")
        ),
        "GITHUB_WEBHOOK_SECRET": require_non_placeholder(
            "GITHUB_WEBHOOK_SECRET", env.get("GITHUB_WEBHOOK_SECRET")
        ),
        "ALLOWED_GITHUB_REPOS": parse_allowed_repos(env.get("ALLOWED_GITHUB_REPOS")),
        "REQUIRE_REPO_ALLOWLIST": flask_env != "development",
        "METRICS_TOKEN": require_non_placeholder(
            "METRICS_TOKEN", env.get("METRICS_TOKEN")
        ),
        "FLASK_ENV": flask_env,
        "VERSION": env.get("VERSION", "1.0.0"),
    }
