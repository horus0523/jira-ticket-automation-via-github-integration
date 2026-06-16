"""
Creates a Jira issue for manual testing purposes.
Accepts optional ticket metadata via CLI args to simulate webhook-triggered creation.
"""

import argparse
import os
import json
from dotenv import load_dotenv
import requests
from src.config import validate_jira_url, require_non_placeholder

load_dotenv()

JIRA_URL = validate_jira_url(os.getenv("JIRA_URL"))
JIRA_EMAIL = require_non_placeholder("JIRA_EMAIL", os.getenv("JIRA_EMAIL"))
JIRA_API_TOKEN = require_non_placeholder("JIRA_API_TOKEN", os.getenv("JIRA_API_TOKEN"))
JIRA_PROJECT_KEY = require_non_placeholder(
    "JIRA_PROJECT_KEY", os.getenv("JIRA_PROJECT_KEY")
)


def build_ticket_payload(summary: str, description: str) -> dict:
    """Construct the ADF payload for Jira issue creation."""
    return {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": "Task"},
        }
    }


def create_jira_issue(summary: str, description: str) -> requests.Response:
    """POST the issue to Jira Cloud REST API v3. Raises on HTTP errors."""
    jira_api_endpoint = f"{JIRA_URL}/rest/api/3/issue"
    jira_auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    request_headers = {"Accept": "application/json", "Content-Type": "application/json"}

    response = requests.post(
        jira_api_endpoint,
        headers=request_headers,
        auth=jira_auth,
        json=build_ticket_payload(summary, description),
        timeout=10,
    )

    if not response.ok:
        error_body = response.text.strip() or "<empty response body>"
        raise SystemExit(
            f"Jira issue creation failed with HTTP {response.status_code}: {error_body}"
        )

    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a test Jira ticket")
    parser.add_argument("--title", default="Test ticket from CLI")
    parser.add_argument("--body", default="Created via manual test script")
    args = parser.parse_args()

    # Build traceable summary when simulating webhook-triggered creation
    summary = f"{args.title} (CLI test)"
    response = create_jira_issue(summary, args.body)

    # SENIOR-NOTE: This is a script meant for manual testing. A real implementation
    # would log structured output (JSON) and exit with proper status codes.
    print(json.dumps(response.json(), sort_keys=True, indent=4, separators=(",", ": ")))
