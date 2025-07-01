"""
This script creates a new Jira issue in a specified Jira Cloud project using the Jira REST API.
"""

import os
import json
from dotenv import load_dotenv
import requests

# Load environment variables from .env at the root of the project
load_dotenv()

# Retrieve Jira credentials and project key from environment variables
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

# Construct the Jira Cloud API endpoint for issue creation
url = f"{JIRA_URL}/rest/api/3/issue"

# Set up authentication using email and API token
auth = (JIRA_EMAIL, JIRA_API_TOKEN)

# Define request headers for JSON content
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Build the payload for the new Jira issue
payload = {
    "fields": {
        "project": {
            "key": JIRA_PROJECT_KEY
        },
        "summary": "First Jira ticket from script",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "This is a test ticket automatically created by the automation script."
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

# Send the POST request to create the Jira issue
response = requests.post(
    url,
    headers=headers,
    auth=auth,
    json=payload,
    timeout=10  # Fail if no response within 10 seconds
)

# Print the formatted JSON response and the response object
print(json.dumps(response.json(), sort_keys=True, indent=4, separators=(",", ": ")))
print(response)
