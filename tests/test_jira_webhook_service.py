import hashlib
import hmac
import importlib
import json
import sys
from unittest.mock import patch


def load_service_module(monkeypatch, **extra_env):
    base_env = {
        "JIRA_URL": "https://team-example.atlassian.net",
        "JIRA_EMAIL": "dev@example.com",
        "JIRA_API_TOKEN": "token-123",
        "JIRA_PROJECT_KEY": "DEV",
        "GITHUB_WEBHOOK_SECRET": "webhook-secret",
        "METRICS_TOKEN": "metrics-secret",
        "ALLOWED_GITHUB_REPOS": "trusted/repo",
        "FLASK_ENV": "testing",
        "RATELIMIT_STORAGE_URI": "memory://",
    }
    base_env.update(extra_env)

    for key, value in base_env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
            continue
        monkeypatch.setenv(key, value)

    sys.modules.pop("src.jira_webhook_service", None)
    module = importlib.import_module("src.jira_webhook_service")
    return importlib.reload(module)


def signed_headers(secret, payload):
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-GitHub-Event": "issue_comment",
        "X-Hub-Signature-256": f"sha256={signature}",
    }


def test_metrics_requires_shared_token(monkeypatch):
    service = load_service_module(monkeypatch)
    client = service.app.test_client()

    forbidden = client.get("/metrics")
    allowed = client.get("/metrics", headers={"X-Metrics-Token": "metrics-secret"})

    assert forbidden.status_code == 403
    assert allowed.status_code == 200


def test_create_ticket_rejects_repositories_outside_allowlist(monkeypatch):
    service = load_service_module(monkeypatch)
    client = service.app.test_client()

    payload = json.dumps(
        {
            "repository": {"full_name": "untrusted/repo"},
            "comment": {"body": "/jira please create this"},
        }
    ).encode()

    with patch("src.jira_webhook_service.requests.post") as mocked_post:
        response = client.post(
            "/create_jira_ticket",
            data=payload,
            headers=signed_headers("webhook-secret", payload),
        )

    assert response.status_code == 403
    mocked_post.assert_not_called()


def test_create_ticket_fails_closed_when_allowlist_missing_in_production(monkeypatch):
    service = load_service_module(monkeypatch, ALLOWED_GITHUB_REPOS="")
    service.app.config["FLASK_ENV"] = "production"
    service.app.config["REQUIRE_REPO_ALLOWLIST"] = True
    service.app.config["ALLOWED_GITHUB_REPOS"] = set()
    client = service.app.test_client()

    payload = json.dumps(
        {
            "repository": {"full_name": "trusted/repo"},
            "comment": {"body": "/jira please create this"},
        }
    ).encode()

    with patch("src.jira_webhook_service.requests.post") as mocked_post:
        response = client.post(
            "/create_jira_ticket",
            data=payload,
            headers=signed_headers("webhook-secret", payload),
        )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Repository allowlist not configured."
    mocked_post.assert_not_called()


def test_create_ticket_allows_empty_allowlist_in_development(monkeypatch):
    service = load_service_module(
        monkeypatch, ALLOWED_GITHUB_REPOS="", FLASK_ENV="development"
    )
    client = service.app.test_client()

    payload = json.dumps(
        {
            "repository": {"full_name": "lab/repo"},
            "comment": {"body": "/jira please create this"},
        }
    ).encode()

    with patch("src.jira_webhook_service.requests.post") as mocked_post:
        mocked_post.return_value.ok = True
        mocked_post.return_value.status_code = 201
        mocked_post.return_value.json.return_value = {"key": "DEV-124"}

        response = client.post(
            "/create_jira_ticket",
            data=payload,
            headers=signed_headers("webhook-secret", payload),
        )

    assert response.status_code == 201
    assert response.get_json()["key"] == "DEV-124"


def test_create_ticket_allows_trusted_repository(monkeypatch):
    service = load_service_module(monkeypatch)
    client = service.app.test_client()

    payload = json.dumps(
        {
            "repository": {"full_name": "trusted/repo"},
            "comment": {"body": "/jira please create this"},
        }
    ).encode()

    with patch("src.jira_webhook_service.requests.post") as mocked_post:
        mocked_post.return_value.ok = True
        mocked_post.return_value.status_code = 201
        mocked_post.return_value.json.return_value = {"key": "DEV-123"}

        response = client.post(
            "/create_jira_ticket",
            data=payload,
            headers=signed_headers("webhook-secret", payload),
        )

    assert response.status_code == 201
    assert response.get_json()["key"] == "DEV-123"


def test_service_import_fails_closed_without_persistent_ratelimit_storage(
    monkeypatch,
):
    sys.modules.pop("src.jira_webhook_service", None)

    try:
        load_service_module(
            monkeypatch,
            FLASK_ENV="production",
            RATELIMIT_STORAGE_URI=None,
        )
    except ValueError as exc:
        assert "RATELIMIT_STORAGE_URI is required" in str(exc)
    else:
        raise AssertionError("Expected production import to fail without rate-limit storage")
