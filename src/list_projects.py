"""
Lists all Jira Cloud projects accessible with the provided credentials using the Jira REST API.
"""

import os
import sys
from dotenv import load_dotenv
import requests


def require_env(name: str) -> str:
    """Validate that a required environment variable is present."""
    value = os.getenv(name)
    if not value:
        print(f"ERROR: {name} environment variable is required", file=sys.stderr)
        sys.exit(1)
    return value


# Load environment variables from .env file at the project root
load_dotenv()

# Validate required environment variables
JIRA_URL = require_env("JIRA_URL")
JIRA_EMAIL = require_env("JIRA_EMAIL")
JIRA_API_TOKEN = require_env("JIRA_API_TOKEN")

# Construct the Jira Cloud API endpoint for listing projects
url = f"{JIRA_URL}/rest/api/3/project"

# Set up authentication for the API request
auth = (JIRA_EMAIL, JIRA_API_TOKEN)

# Define request headers to accept JSON responses
headers = {"Accept": "application/json"}

# Send the GET request to retrieve the list of Jira projects
response = requests.get(
    url,
    headers=headers,
    auth=auth,
    timeout=10,  # Fail if no response within 10 seconds
)

# Parse the JSON response containing the list of projects
projects = response.json()

# Print the name of each project to the console
for project in projects:
    print(project.get("name"))
