import pytest

from src.config import (
    load_runtime_config,
    parse_allowed_repos,
    require_non_placeholder,
    validate_bind_host,
    validate_port,
    validate_jira_url,
)


def test_validate_jira_url_accepts_atlassian_cloud_hosts():
    assert validate_jira_url("https://team-example.atlassian.net/") == (
        "https://team-example.atlassian.net"
    )


@pytest.mark.parametrize(
    "value",
    [
        "http://team-example.atlassian.net",
        "https://jira.example.com",
        "https://your-domain.atlassian.net",
    ],
)
def test_validate_jira_url_rejects_invalid_hosts_and_placeholders(value):
    with pytest.raises(ValueError):
        validate_jira_url(value)


def test_require_non_placeholder_rejects_example_values():
    with pytest.raises(ValueError):
        require_non_placeholder("METRICS_TOKEN", "your_metrics_token_here")


def test_parse_allowed_repos_normalizes_and_validates_values():
    assert parse_allowed_repos("Owner/Repo, another-org/second_repo") == {
        "owner/repo",
        "another-org/second_repo",
    }

    with pytest.raises(ValueError):
        parse_allowed_repos("not-a-valid-repo-name")


def test_load_runtime_config_builds_validated_mapping():
    config = load_runtime_config(
        {
            "JIRA_URL": "https://team-example.atlassian.net",
            "JIRA_EMAIL": "dev@example.com",
            "JIRA_API_TOKEN": "token-123",
            "JIRA_PROJECT_KEY": "DEV",
            "GITHUB_WEBHOOK_SECRET": "secret-123",
            "ALLOWED_GITHUB_REPOS": "owner/repo",
            "METRICS_TOKEN": "metrics-secret",
        }
    )

    assert config["JIRA_URL"] == "https://team-example.atlassian.net"
    assert config["ALLOWED_GITHUB_REPOS"] == {"owner/repo"}
    assert config["REQUIRE_REPO_ALLOWLIST"] is True
    assert config["APP_HOST"] == "127.0.0.1"
    assert config["APP_PORT"] == 5000


def test_load_runtime_config_relaxes_repo_allowlist_only_in_development():
    config = load_runtime_config(
        {
            "JIRA_URL": "https://team-example.atlassian.net",
            "JIRA_EMAIL": "dev@example.com",
            "JIRA_API_TOKEN": "token-123",
            "JIRA_PROJECT_KEY": "DEV",
            "GITHUB_WEBHOOK_SECRET": "secret-123",
            "METRICS_TOKEN": "metrics-secret",
            "FLASK_ENV": "development",
        }
    )

    assert config["ALLOWED_GITHUB_REPOS"] == set()
    assert config["REQUIRE_REPO_ALLOWLIST"] is False


def test_validate_bind_host_defaults_to_loopback_and_allows_explicit_broad_bind():
    assert validate_bind_host(None) == "127.0.0.1"
    assert validate_bind_host("0.0.0.0") == "0.0.0.0"


def test_validate_bind_host_rejects_invalid_values():
    with pytest.raises(ValueError):
        validate_bind_host("not-a-host")


def test_validate_port_accepts_default_and_rejects_invalid_values():
    assert validate_port(None) == 5000
    assert validate_port("8080") == 8080

    with pytest.raises(ValueError):
        validate_port("70000")
