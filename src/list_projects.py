"""
Lists all Jira Cloud projects accessible with the provided credentials using the Jira REST API.
"""

# Import required libraries
import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env file at the project root
load_dotenv()

# Retrieve Jira credentials and base URL from environment variables
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# Construct the Jira Cloud API endpoint for listing projects
url = f"{JIRA_URL}/rest/api/3/project"

# Set up authentication for the API request
auth = (JIRA_EMAIL, JIRA_API_TOKEN)

# Define request headers to accept JSON responses
headers = {
    "Accept": "application/json"
}

# Send the GET request to retrieve the list of Jira projects
response = requests.get(
    url,
    headers=headers,
    auth=auth,
    timeout=10  # Fail if no response within 10 seconds
)

# Parse the JSON response containing the list of projects
projects = response.json()

# Print the name of each project to the console
for project in projects:
    print(project.get("name"))
