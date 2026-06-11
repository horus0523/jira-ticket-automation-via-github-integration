#!/bin/bash
# Script for deployment on EC2
echo "Deploying to EC2..."

# Install system dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv

# Configure application
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/JiraWebhookService.service << EOL
[Unit]
Description=Jira Webhook Service

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python $(pwd)/src/jira_webhook_service.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL

# Start service
sudo systemctl daemon-reload
sudo systemctl enable JiraWebhookService
sudo systemctl restart JiraWebhookService

echo "Deployment completed!"
