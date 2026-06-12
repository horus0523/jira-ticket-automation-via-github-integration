#!/bin/bash
set -euo pipefail

APP_DIR="/opt/jira-webhook-service"
ENV_SOURCE_FILE=".env"
ENV_TARGET_FILE="$APP_DIR/.env"

require_env() {
    local name="$1"
    local value="${!name:-}"

    if [[ -z "$value" ]]; then
        echo "ERROR: Missing required variable: $name"
        exit 1
    fi

    case "$value" in
        your_jira_api_token_here|your-email@domain.com|your_webhook_secret_here|your_metrics_token_here|PROJECT|https://your-domain.atlassian.net)
            echo "ERROR: $name still uses the placeholder value from .env.example"
            exit 1
            ;;
    esac
}

echo "Setting up production environment..."

if [[ ! -f "$ENV_SOURCE_FILE" ]]; then
    echo "ERROR: Missing .env file in the repository root."
    echo "  Create it manually from .env.example, replace all placeholders, and rerun this script."
    exit 1
fi

set -a
source "$ENV_SOURCE_FILE"
set +a

require_env JIRA_URL
require_env JIRA_EMAIL
require_env JIRA_API_TOKEN
require_env JIRA_PROJECT_KEY
require_env GITHUB_WEBHOOK_SECRET
require_env METRICS_TOKEN
require_env RATELIMIT_STORAGE_URI

if [[ "$RATELIMIT_STORAGE_URI" == "memory://" ]]; then
    echo "ERROR: RATELIMIT_STORAGE_URI must use persistent storage in production."
    exit 1
fi

if [[ ! "$RATELIMIT_STORAGE_URI" =~ ^[a-zA-Z][a-zA-Z0-9+.-]*:// ]]; then
    echo "ERROR: RATELIMIT_STORAGE_URI must be a valid storage URI."
    exit 1
fi

if [[ ! "$JIRA_URL" =~ ^https://[a-z0-9][a-z0-9-]*\.atlassian\.net/?$ ]]; then
    echo "ERROR: JIRA_URL must be an Atlassian Cloud HTTPS URL (https://<tenant>.atlassian.net)."
    exit 1
fi

mkdir -p "$APP_DIR"

# Create venv
python3 -m venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install service
cp -r src "$APP_DIR/"
cp deployment/JiraWebhookService.service /etc/systemd/system/
cp "$ENV_SOURCE_FILE" "$ENV_TARGET_FILE"

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable JiraWebhookService
systemctl restart JiraWebhookService

echo "OK: Production setup complete"
