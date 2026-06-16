#!/bin/bash
set -euo pipefail

# Script for deployment on EC2
echo "Deploying to EC2..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Install system dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv

# Delegate bootstrap and validation to the production setup script.
sudo bash -c "cd \"${PROJECT_ROOT}\" && ./scripts/setup_production.sh"

echo "Deployment completed!"
