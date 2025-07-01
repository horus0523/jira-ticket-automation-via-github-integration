"""
Flask service to receive GitHub webhooks and create Jira tickets automatically
when a comment contains the '/jira' keyword.
"""

import os
import hmac
import hashlib
from dotenv import load_dotenv
import requests
from flask import Flask, jsonify, request, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize Flask app
app = Flask(__name__)

# Configure rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10 per minute"]
)

# Load environment variables from .env at the project root
load_dotenv()

# Retrieve configuration from environment variables
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")


def verify_github_signature(req):
    """
    Verify the GitHub webhook signature using the shared secret.
    """
    signature = req.headers.get('X-Hub-Signature-256')
    if signature is None or GITHUB_WEBHOOK_SECRET is None:
        return False
    try:
        sha_name, signature_hash = signature.split('=')
    except ValueError:
        return False
    if sha_name != 'sha256':
        return False
    mac = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        msg=req.data,
        digestmod=hashlib.sha256
    )
    return hmac.compare_digest(mac.hexdigest(), signature_hash)


@app.route('/create_jira_ticket', methods=['POST'])
@limiter.limit("5 per minute")
def create_jira_ticket():
    """
    Endpoint to create a Jira ticket from a GitHub issue comment webhook.
    Only creates a ticket if the comment contains '/jira'.
    """
    # Verify GitHub webhook signature
    if not verify_github_signature(request):
        abort(401, description="Unauthorized.")

    # Ensure the event is an issue comment
    event = request.headers.get("X-GitHub-Event", "")
    if event != "issue_comment":
        return jsonify({"message": "Event not allowed."}), 400

    data = request.get_json()
    comment_body = data.get("comment", {}).get("body", "")

    # Only create the ticket if the comment contains '/jira'
    if "/jira" not in comment_body.lower():
        return jsonify({"message": "Keyword '/jira' not found in comment. No ticket created."}), 200

    jira_api_url = f"{JIRA_URL}/rest/api/3/issue"
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "fields": {
            "project": {
                "key": JIRA_PROJECT_KEY
            },
            "summary": "Ticket created from GitHub comment",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment_body
                            }
                        ]
                    }
                ]
            },
            "issuetype": {
                "name": "Task"
            }
        }
    }
    try:
        response = requests.post(
            jira_api_url,
            headers=headers,
            auth=auth,
            json=payload,
            timeout=10
        )
        if not response.ok:
            return jsonify({"error": "Failed to create Jira ticket."}), response.status_code
        response_json = response.json()
    except requests.exceptions.RequestException:
        response_json = {
            "error": "Internal error while processing the request."
        }
        return jsonify(response_json), 500
    return jsonify(response_json), response.status_code


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
