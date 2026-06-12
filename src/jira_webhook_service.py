"""Flask service that validates GitHub webhooks and creates Jira tickets."""

import hmac
import hashlib
import time
from dotenv import load_dotenv
import requests
from flask import Flask, jsonify, request, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.metrics import (
    webhooks_received,
    jira_tickets_created,
    webhook_processing_time,
    metrics_endpoint,
)
from src.logging_config import setup_logging
from src.health import health_bp
from src.config import load_runtime_config
import structlog

logger = structlog.get_logger()
load_dotenv()


def verify_github_signature(req, secret):
    """
    Verify the GitHub webhook signature using the shared secret.
    """
    signature = req.headers.get("X-Hub-Signature-256")
    if signature is None or not secret:
        return False
    try:
        sha_name, signature_hash = signature.split("=")
    except ValueError:
        return False
    if sha_name != "sha256":
        return False
    mac = hmac.new(secret.encode(), msg=req.data, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature_hash)


def create_app() -> Flask:
    """Create and configure the Flask application."""
    runtime_config = load_runtime_config()
    setup_logging()

    app = Flask(__name__)
    app.config.update(runtime_config)
    app.register_blueprint(health_bp)

    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["10 per minute"],
        storage_uri=app.config["RATELIMIT_STORAGE_URI"],
    )

    @app.route("/create_jira_ticket", methods=["POST"])
    @limiter.limit("5 per minute")
    def create_jira_ticket():
        # Validates GitHub signature, extracts /jira command from issue_comment webhook, creates Jira Task
        start = time.time()
        webhooks_received.labels(source="github").inc()

        logger.info("webhook_received", github_event="issue_comment", source="github")

        if not verify_github_signature(request, app.config["GITHUB_WEBHOOK_SECRET"]):
            logger.warning("webhook_auth_failed", reason="invalid_signature")
            abort(401, description="Unauthorized.")

        event = request.headers.get("X-GitHub-Event", "")
        if event != "issue_comment":
            logger.info("webhook_ignored", reason="event_not_supported", event=event)
            return jsonify({"message": "Event not allowed."}), 400

        data = request.get_json(silent=True) or {}
        repository_full_name = (
            data.get("repository", {}).get("full_name", "").strip().lower()
        )
        allowed_repos = app.config["ALLOWED_GITHUB_REPOS"]
        if app.config["REQUIRE_REPO_ALLOWLIST"] and not allowed_repos:
            logger.warning(
                "webhook_auth_failed",
                reason="repository_allowlist_not_configured",
                environment=app.config["FLASK_ENV"],
            )
            return jsonify({"error": "Repository allowlist not configured."}), 403

        if allowed_repos and repository_full_name not in allowed_repos:
            logger.warning(
                "webhook_auth_failed",
                reason="repository_not_allowed",
                repository=repository_full_name or "missing",
            )
            return jsonify({"error": "Repository not allowed."}), 403

        comment_body = data.get("comment", {}).get("body", "")
        if "/jira" not in comment_body.lower():
            logger.info("webhook_skipped", reason="keyword_not_found")
            return jsonify(
                {"message": "Keyword '/jira' not found in comment. No ticket created."}
            ), 200

        jira_api_url = f"{app.config['JIRA_URL']}/rest/api/3/issue"
        auth = (app.config["JIRA_EMAIL"], app.config["JIRA_API_TOKEN"])
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        issue_title = data.get("issue", {}).get("title", "")
        repository_full_name = data.get("repository", {}).get("full_name", "")
        summary = (
            f"[GitHub] {issue_title} ({repository_full_name})"
            if issue_title
            else "Ticket created from GitHub comment"
        )
        payload = {
            "fields": {
                "project": {"key": app.config["JIRA_PROJECT_KEY"]},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": comment_body}],
                        }
                    ],
                },
                "issuetype": {"name": "Task"},
            }
        }

        try:
            logger.info("creating_jira_ticket", project=app.config["JIRA_PROJECT_KEY"])
            response = requests.post(
                jira_api_url, headers=headers, auth=auth, json=payload, timeout=10
            )
            if not response.ok:
                jira_tickets_created.labels(result="failure").inc()
                logger.error(
                    "jira_ticket_creation_failed", status_code=response.status_code
                )
                return jsonify(
                    {"error": "Failed to create Jira ticket."}
                ), response.status_code

            response_json = response.json()
            jira_tickets_created.labels(result="success").inc()
            logger.info("jira_ticket_created", ticket_key=response_json.get("key"))
        except requests.exceptions.RequestException:
            jira_tickets_created.labels(result="error").inc()
            response_json = {"error": "Internal error while processing the request."}
            logger.error("jira_ticket_creation_error", error="request_exception")
            return jsonify(response_json), 500

        webhook_processing_time.labels(command_type="jira").observe(time.time() - start)
        return jsonify(response_json), response.status_code

    @app.route("/metrics")
    def metrics():
        # Token-gated /metrics to prevent exposure to unauthorized scrapers
        provided_token = request.headers.get("X-Metrics-Token", "")
        if not hmac.compare_digest(provided_token, app.config["METRICS_TOKEN"]):
            abort(403, description="Forbidden.")
        return metrics_endpoint()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=app.config["APP_HOST"], port=app.config["APP_PORT"])
