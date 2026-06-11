# Jira Webhook Service

---

## Purpose

Automate the creation of Jira tickets from GitHub issue comments. When a user comments `/jira` on an issue or pull request, this service receives a webhook, validates it, and creates a Jira issue with the comment content.

---

## Project Architecture

- **Flask API** running on an EC2 instance, exposed via HTTP.
- **GitHub Webhook** triggers the API when an issue comment is created.
- **Jira Cloud API** is used to create issues programmatically.
- **Systemd Service** ensures the Flask app runs as a background service.
- **Rate Limiting** and **Webhook Signature Validation** are part of the tracked service baseline.

---

## Specific Objectives

- Create Jira tickets from GitHub issue comments that contain `/jira`.
- Validate webhook signatures before calling Jira.
- Document the EC2/systemd deployment path without claiming managed production operations.

---

## Project Structure

The repository includes the application code, deployment helper, service unit,
tests, and CI workflow shown below.

```
jira-ticket-automation-via-github-integration/
│
├── deployment/
│   ├── deploy_ec2.sh
│   └── JiraWebhookService.service
│
├── scripts/
│   └── (deployment helper scripts)
│
├── src/
│   ├── config.py
│   ├── create_jira_ticket.py
│   ├── health.py
│   ├── jira_webhook_service.py
│   ├── list_projects.py
│   ├── logging_config.py
│   └── metrics.py
│
├── tests/
│   └── (test files)
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## Use Case

A developer or project manager comments `/jira` on a GitHub issue or PR. The service receives the webhook, validates the GitHub signature, and creates a Jira ticket with the comment as the description.

---

## Deliverables

- Flask API (`src/jira_webhook_service.py`) for webhook handling and Jira integration.
- Example scripts for Jira API usage (`src/create_jira_ticket.py`, `src/list_projects.py`).
- Deployment helper scripts and the checked-in systemd unit support the documented EC2 setup path.
- This README file.

---

## Technologies Used

**Python Libraries:**

- Flask
- Flask-Limiter
- requests
- python-dotenv

**Deployment/Infrastructure:**

- Python 3.11+
- systemd
- AWS EC2 (Ubuntu)

**Integrations:**

- Jira Cloud API
- GitHub Webhooks

---

## Initial Setup

### Prerequisites

- Active EC2 instance with SSH access (Ubuntu recommended)
- Git installed on the instance
- GitHub account configured
- GitHub Personal Access Token (PAT) or SSH keys configured
- Jira Cloud account and API token
- `.env` file with required variables

### Required `.env` keys

```dotenv
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@domain.com
JIRA_API_TOKEN=your_jira_api_token_here
JIRA_PROJECT_KEY=ENG
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
ALLOWED_GITHUB_REPOS=octo-org/example-repo
METRICS_TOKEN=your_metrics_token_here
APP_HOST=127.0.0.1
APP_PORT=5000
```

Notes:

- `JIRA_URL` must be an Atlassian Cloud URL: `https://<tenant>.atlassian.net`.
- `ALLOWED_GITHUB_REPOS` configures the repository allowlist.
- `APP_HOST` defaults to `127.0.0.1`; set `0.0.0.0` only when you explicitly need a non-loopback bind and the network path is restricted.
- `APP_PORT` defaults to `5000`.
- `VERSION` is optional and defaults to `1.0.0` when omitted.
- `METRICS_TOKEN` protects the metrics endpoint when that route is enabled in your deployment.

### Verification and CI

The repository includes tests and CI for the service baseline. Run the current
checks locally or in CI when you change application behavior.

| Area | Failure cases covered first | Success path |
|------|-----------------------------|--------------|
| Configuration (`tests/test_config.py`) | invalid Jira hosts, placeholder secrets, malformed allowlist entries | validated Atlassian Cloud URL and normalized repository allowlist |
| Webhook handling (`tests/test_jira_webhook_service.py`) | missing metrics token, repositories outside the allowlist, missing production allowlist | trusted repository with a signed `/jira` comment creates a Jira issue |

The checked-in `.github/workflows/jira-service-ci.yml` can run `flake8`,
`bandit -r src/`, and `pytest tests/ -v --tb=short`.

### Create AWS Infrastructure

#### Step 1: Sign in to AWS

1. Go to [https://aws.amazon.com/console/](https://aws.amazon.com/console/)
2. Sign in with your account

   - If you have an IAM user, **use it instead of the root account** for security

#### Step 2: Choose the Right Region

Make sure to select the region where you will create all resources:

- **US East (N. Virginia)** - `us-east-1`: Most commonly used with lower prices.
- **South America (São Paulo)** - `sa-east-1`: Better latency if you are in South America.

#### Step 3: Create Required Resources Before the Instance

##### Create the key pair (SSH key)

This key is necessary to connect to the server. It can only be downloaded once.

1. Search for **EC2** in the search bar and access the service
2. In the left menu, go to **Key Pairs** (under "Network & Security")
3. Click on **Create key pair**:

   - **Name**: `jira_webhook_service_key_pair`
   - **Type**: ED25519
   - **Format**:

     - `.pem` for Linux, macOS, or Windows with WSL
     - `.ppk` for PuTTY on Windows

4. Click on **Create key pair**

A `.pem` or `.ppk` file will be downloaded. **Save it carefully**. It's essential for connecting.

##### Create a Security Group

This allows you to define what traffic can access your instance.

1. In the left menu, go to **Security Groups** (under "Network & Security")

2. Click on **Create security group**

3. Configure as follows:

   - **Name**: `jira_webhook_service_security_group`
   - **Description**: Security Group for Jira Webhook Service
   - **VPC**: Leave the default

4. In **Inbound rules**, click "Add rule":

5. **Add rules:**

- **Type:** SSH  
  **Port:** 22  
  **Source type:** My IP

- **Type:** Custom TCP  
  **Port:** 5000  
  **Source:** Reverse proxy / load balancer / IPs confiables solamente

6. In **Outbound rules (verify they are present):**

- **Type:** All traffic  
  **Port:** All  
  **Destination:** 0.0.0.0/0

7. Click **Create security group**

#### Step 4: Create the EC2 Instance

##### Launch new instance

1. Go to **Instances** > **Launch instances**
2. Set a name like: `jira_webhook_service_ec2`

##### Choose operating system

Choose a **Free tier eligible** AMI, such as:

- **Ubuntu Server 24.04 LTS**

##### Select instance type

- Use **t2.micro** or **t3.micro**, both within the free tier

##### Choose key pair

- In **Key pair (login)**, choose:

  - **Choose existing key pair**
  - Select `jira_webhook_service_key_pair`

**Make sure you have the `.pem` or `.ppk` file saved**, or you won't be able to connect.

##### Configure network and security

- **VPC and subnet**: Leave the default values
- **Auto-assign public IP**: Enabled
- **Firewall (Security group)**:

  - Select **"Select existing security group"**
  - Check the `jira_webhook_service_security_group` group you created earlier

##### Additional configuration

- **Storage**: Leave the default 8 GB (free)
- **Tags (optional)**:

  - Key: `Name`, Value: `jira_webhook_service_ec2`

Click **Launch instance**

##### Wait and get IP

1. Go to **Instances** > **View all instances**
2. Wait for the status to be **Running** and the checks to be **2/2 passed**
3. Copy the **Public IPv4 address**
4. Besides the public IP, also copy the **Public DNS** of your EC2 instance (e.g., `ec2-xx-xx-xx-xx.compute-1.amazonaws.com`).  
   You can use this DNS instead of the IP to access your Flask service. For example:

```
http://<your-ec2-public-dns>:5000/create_jira_ticket
```

#### Step 5: Connect to the instance

##### From Linux, macOS or Windows with WSL

1. Open the terminal
2. Go to the directory where you saved your `.pem` file
3. Set permissions:

```bash
chmod 400 jira_webhook_service_key_pair.pem
```

4. Connect:

```bash
# Replace `YOUR_PUBLIC_IP` with the public IPv4 address you copied from your EC2 instance in the previous step.
ssh -i "jira_webhook_service_key_pair.pem" ubuntu@YOUR_PUBLIC_IP
```

## Installation and Usage

### Connect to EC2 Instance

```bash
# Replace `YOUR_PUBLIC_IP` with the public IPv4 address you copied from your EC2 instance in the previous step.
ssh -i "jira_webhook_service_key_pair.pem" ubuntu@YOUR_PUBLIC_IP
```

### Install Git (if not installed)

```bash
# For Ubuntu/Debian
sudo apt update
sudo apt install git -y

# Verify installation
git --version
```

### Configure Git (if not configured)

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
git config --list
```

### Clone the Original Repository

```bash
# Navigate to home directory
cd ~

# Clone the original repository
git clone https://github.com/horus0523/jira-ticket-automation-via-github-integration.git

# Enter the cloned directory
cd jira-ticket-automation-via-github-integration
```

### Generate Your Jira API Token

1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens) and **sign in to your Jira/Atlassian account** if you are not already logged in
2. Click **Create API token**
3. Enter a label (e.g., `jira_webhook_service`) and click **Create**
4. Copy the generated token and **save it securely** (you will not be able to see it again)
5. Open your `.env` file in the project root and set:
   ```
   JIRA_API_TOKEN=your_jira_api_token_here
   ```
6. Save the .env file

### Configure Your Jira Environment Variables

After generating your Jira API token, complete your `.env` file with the following variables:

```dotenv
JIRA_URL=https://acme.atlassian.net                # Your Jira Cloud site URL
JIRA_EMAIL=jira-bot@acme.example                   # The email used for Jira API access
JIRA_API_TOKEN=atlassian-api-token                 # The API token you just created
JIRA_PROJECT_KEY=ENG                               # The key of your Jira project (e.g., ENG, DEV)
GITHUB_WEBHOOK_SECRET=long-random-webhook-secret
ALLOWED_GITHUB_REPOS=acme/platform-service         # Required outside local development
METRICS_TOKEN=long-random-metrics-token
FLASK_ENV=production
VERSION=1.0.0                                      # Optional; defaults to 1.0.0 when omitted
```

#### How to find each value:

- **JIRA_URL:**  
  Log in to Jira Cloud in your browser. The URL in the address bar will look like `https://your-domain.atlassian.net`.  
  Use this full URL as the value.

- **JIRA_EMAIL:**  
  This is the email address you use to log in to Jira/Atlassian.

- **JIRA_API_TOKEN:**  
  The token you generated in the previous step.

- **JIRA_PROJECT_KEY:**  
  In Jira, open your project. The project key appears in the project’s URL and in the top-left corner of the project dashboard (e.g., `SMS`, `DEV`, etc.).

**Example .env section:**

```dotenv
JIRA_URL=https://acme.atlassian.net
JIRA_EMAIL=jira-bot@acme.example
JIRA_API_TOKEN=atlassian-api-token
JIRA_PROJECT_KEY=ENG
GITHUB_WEBHOOK_SECRET=long-random-webhook-secret
ALLOWED_GITHUB_REPOS=acme/platform-service
METRICS_TOKEN=long-random-metrics-token
FLASK_ENV=production
VERSION=1.0.0
```

### Create a New Repository on GitHub

1. Go to [https://github.com/](https://github.com/) and **sign in to your GitHub account** if you are not already logged in
2. Click the "+" button in the top right corner
3. Select "New repository"
4. Make sure you are in the correct organization or personal account where you want to add the repository
5. Name your repository (e.g., `my-jira-automation`)
6. **DO NOT initialize with README, .gitignore or license** (since you'll push existing code)
7. Click "Create repository"

### Setup GitHub Authentication

#### Option A: Personal Access Token (Recommended)

1. Go to [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. Click "Generate new token"
3. Name: "EC2_Development"
4. Select scopes: **repo** (full control)
5. Set expiration and generate
6. **Copy the token immediately**

#### Option B: SSH Keys (Alternative)

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your-email@example.com"

# Start SSH agent and add key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Copy public key to add to GitHub
cat ~/.ssh/id_ed25519.pub
```

Add the public key to GitHub → Settings → SSH and GPG keys

Notes:

- Use the same email address you use for your GitHub account.
- If you changed the filename or path when generating the key, update the ssh-add and cat commands accordingly.
- Add the displayed public key to your GitHub account under Settings > SSH and GPG keys.

### Configure Local Repository Remote

```bash
# Check current remote
git remote -v

# Change the origin remote URL to your new repository
# For HTTPS (using PAT):
git remote set-url origin https://github.com/your-username/my-jira-automation.git

# For SSH (if using SSH keys):
git remote set-url origin git@github.com:your-username/my-jira-automation.git

# Verify the change was made correctly
git remote -v
```

### Check Current Branch and Push

```bash
# Check current branch
git branch
```

```bash
# Check repository status
git status
```

```bash
# If there are uncommitted changes, commit them
git add .
git commit -m "Initial commit from cloned repository"
```

```bash
# Push to new repository (adjust branch name if needed)
git push -u origin main
```

##### Authentication During Push

When prompted for credentials:

- **Username**: your-github-username
- **Password**: your-personal-access-token (NOT your GitHub password)

### Verify on GitHub

Go to your repository on GitHub to confirm that all files were uploaded correctly.

## Troubleshooting Authentication

### If you get "Authentication failed":

```bash
# Clear any cached credentials
git config --global --unset credential.helper

# Try push again with fresh credentials
git push -u origin main
```

### If using SSH and getting "Permission denied":

```bash
# Test SSH connection
ssh -T git@github.com

# Should return: "Hi username! You've successfully authenticated..."
```

### Store credentials to avoid repeated prompts (HTTPS only):

```bash
# Store credentials for future use
git config --global credential.helper store

# Or use cache (temporary storage)
git config --global credential.helper cache
```

### "Permission denied" error:

```bash
# For application files
chmod +x executable-file
```

## Create the GitHub Webhook

1. Go to your repository on GitHub ([https://github.com/](https://github.com/))
2. Click **Settings > Webhooks > Add webhook** ([GitHub Webhooks documentation](https://docs.github.com/en/webhooks))
3. For **Payload URL**, enter:

```bash
http://<your-ec2-public-ip>:5000/create_jira_ticket
```

4. For **Content type**, select: `application/json`
5. For **Secret**, enter the same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
6. For **Which events would you like to trigger this webhook?**  
   Select: **Let me select individual events** and check **Issue comments**
7. Click **Add webhook** to save

## Running Scripts

### Option A: Test the code manually on the AWS Instance (Alternative)

```bash
# Install system dependencies (Python, pip, venv)
sudo apt update
sudo apt install -y python3-pip python3-venv
```

```bash
# Set up a Python virtual environment and activate it
cd ~/jira-ticket-automation-via-github-integration/
python3 -m venv venv
source venv/bin/activate
```

```bash
# Install Python dependencies from requirements.txt
pip install -r requirements.txt
```

```bash
# Run the script to list all Jira projects (for testing)
python3 ~/jira-ticket-automation-via-github-integration/src/list_projects.py
```

```bash
# Run the script to create a Jira ticket (for testing)
python3 ~/jira-ticket-automation-via-github-integration/src/create_jira_ticket.py
```

```bash
# (Optional) Run the Flask webhook service manually for testing
python3 ~/jira-ticket-automation-via-github-integration/src/jira_webhook_service.py
```

### Option B: Deploy with the helper script

```bash
# Make the deployment script executable
chmod +x ~/jira-ticket-automation-via-github-integration/deployment/deploy_ec2.sh
```

```bash
# Run the deployment script to automate setup and service creation
~/jira-ticket-automation-via-github-integration/deployment/deploy_ec2.sh
```

## Test the Integration

- Comment `/jira` on any issue in your GitHub repository
- Verify that your endpoint receives the request and a ticket is created in

---

## Configuration Variables

Example `.env`:

```dotenv
JIRA_URL=https://acme.atlassian.net
JIRA_EMAIL=jira-bot@acme.example
JIRA_API_TOKEN=atlassian-api-token
JIRA_PROJECT_KEY=ENG
GITHUB_WEBHOOK_SECRET=long-random-webhook-secret
ALLOWED_GITHUB_REPOS=acme/platform-service
METRICS_TOKEN=long-random-metrics-token
FLASK_ENV=production
VERSION=1.0.0
```

---

## Useful Commands

- **Start the service:**

  ```bash
  sudo systemctl start JiraWebhookService
  ```

- **Stop the service:**

  ```bash
  sudo systemctl stop JiraWebhookService
  ```

- **Check the service status:**

  ```bash
  sudo systemctl status JiraWebhookService
  ```

- **Restart the service:**

  ```bash
  sudo systemctl restart JiraWebhookService
  ```

- **View logs:**
  ```bash
  sudo journalctl -u JiraWebhookService -e
  ```

---

## Security

- Webhook requests are validated with `GITHUB_WEBHOOK_SECRET` and the `X-Hub-Signature-256` header.
- Rate limiting is part of the tracked Flask service baseline.
- Security groups should restrict access to trusted ingress such as a reverse proxy or load balancer.
- Never commit `.env` files or secrets to public repositories.
- Use HTTPS termination and operational monitoring before exposing the service beyond a lab environment.
- Configure allowlist enforcement and `/metrics` token protection before exposing the service beyond a trusted environment.

---

## Troubleshooting

- **Webhook not triggering?**  
  Check your GitHub webhook settings and ensure the event is `issue_comment`.
- **Service not running?**  
  Check `sudo systemctl status JiraWebhookService` and logs with `journalctl`.
- **Jira ticket not created?**  
  Verify your Jira credentials and project key in `.env`.
- **Rate limit errors?**  
  Wait a minute and try again, or adjust the rate limit in the Flask app if needed.

---

## Additional Resources

- [Jira Cloud REST API documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)
- [GitHub Webhooks documentation](https://docs.github.com/en/webhooks)
- [Flask documentation](https://flask.palletsprojects.com/)
- [Flask-Limiter documentation](https://flask-limiter.readthedocs.io/)
- [AWS EC2 documentation](https://docs.aws.amazon.com/ec2/)

---
### Production bootstrap

- Create `.env` manually and replace every placeholder before any deployment.

### Metrics access

Protect metrics access with `METRICS_TOKEN` and network restrictions when you
enable that endpoint.
