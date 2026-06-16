import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = os.path.join("scripts", "setup_production.sh")


def run_setup_script(project_root, cwd, env_contents):
    env_file = cwd / ".env"
    env_file.write_text(env_contents, encoding="utf-8")

    return subprocess.run(
        ["bash", str(project_root / SCRIPT_PATH)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_setup_production_fails_closed_when_ratelimit_storage_missing(tmp_path):
    result = run_setup_script(
        PROJECT_ROOT,
        tmp_path,
        "\n".join(
            [
                "JIRA_URL=https://team-example.atlassian.net",
                "JIRA_EMAIL=dev@example.com",
                "JIRA_API_TOKEN=token-123",
                "JIRA_PROJECT_KEY=DEV",
                "GITHUB_WEBHOOK_SECRET=secret-123",
                "METRICS_TOKEN=metrics-secret",
            ]
        ),
    )

    assert result.returncode == 1
    assert "ERROR: Missing required variable: RATELIMIT_STORAGE_URI" in result.stdout
    assert "OK: Production setup complete" not in result.stdout


def test_setup_production_fails_closed_when_memory_storage_used(tmp_path):
    result = run_setup_script(
        PROJECT_ROOT,
        tmp_path,
        "\n".join(
            [
                "JIRA_URL=https://team-example.atlassian.net",
                "JIRA_EMAIL=dev@example.com",
                "JIRA_API_TOKEN=token-123",
                "JIRA_PROJECT_KEY=DEV",
                "GITHUB_WEBHOOK_SECRET=secret-123",
                "METRICS_TOKEN=metrics-secret",
                "RATELIMIT_STORAGE_URI=memory://",
            ]
        ),
    )

    assert result.returncode == 1
    assert "ERROR: RATELIMIT_STORAGE_URI must use persistent storage in production." in result.stdout
    assert "OK: Production setup complete" not in result.stdout
