#!/bin/bash
set -euo pipefail

# Script for deployment on EC2
echo "Deploying to EC2..."

APP_DIR="/opt/jira-webhook-service"
SERVICE_NAME="JiraWebhookService.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Install system dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv rsync

# Sync application into the service working directory expected by systemd
sudo mkdir -p "${APP_DIR}"
sudo rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'venv' \
  --exclude '__pycache__' \
  "${PROJECT_ROOT}/" "${APP_DIR}/"

# Configure application
sudo python3 -m venv "${APP_DIR}/venv"
sudo "${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

# Install the committed systemd unit so runtime settings stay aligned
sudo install -m 644 \
  "${APP_DIR}/deployment/${SERVICE_NAME}" \
  "/etc/systemd/system/${SERVICE_NAME}"

# Start service
sudo systemctl daemon-reload
sudo systemctl enable JiraWebhookService
sudo systemctl restart JiraWebhookService

echo "Deployment completed!"
