# GitHub MCP (Model Control Plane) README


Welcome to the **GitHub MCP (Model Control Plane)** server! This server serves as the backbone for managing, deploying, and monitoring your AI/ML models on GitHub-based infrastructures. This README will guide you through understanding, setting up, and leveraging the GitHub MCP in your workflow.

---

## 📚 Overview

- **Purpose:** Centralizes control of AI/ML models, automating deployments, scaling, and monitoring through GitHub.
- **Scope:** Ideal for teams or projects needing robust lifecycle management of models with tight DevOps integration.

---

## 🚀 Features

- We have functionality for the following github functions:

Here are the main GitHub MCP functions organized by category:

### 📝 Issues & Comments
- `add_issue_comment` — Add a comment to an issue
- `assign_copilot_to_issue` — Assign Copilot to an issue
- `issue_read` — Read issue details
- `issue_write` — Write/update an issue
- `sub_issue_write` — Create/update a sub-issue

### 🔍 Search
- `search_code` — Search code in repositories
- `search_issues` — Search for issues
- `search_pull_requests` — Search pull requests
- `search_repositories` — Search repositories
- `search_users` — Search for users

### 🌿 Branches, Commits & Tags
- `create_branch` — Create a new branch
- `list_branches` — List all branches
- `list_commits` — List repository commits
- `get_commit` — Get a particular commit
- `get_tag` — Get tag details
- `list_tags` — List all tags

### 📂 Files & Repositories
- `create_or_update_file` — Create or update a file
- `delete_file` — Delete a file
- `get_file_contents` — Retrieve contents of a file
- `push_files` — Push files to the repository
- `create_repository` — Create a new repository
- `fork_repository` — Fork an existing repository

### 📦 Releases
- `get_latest_release` — Get the latest release
- `get_release_by_tag` — Get a release by tag
- `list_releases` — List all releases

### 🔖 Labels & Teams
- `get_label` — Get a label
- `get_teams` — List teams
- `get_team_members` — List team members

### 👤 User Info
- `get_me` — Get user credentials/info

### 🔀 Pull Requests
- `create_pull_request` — Create a pull request
- `list_pull_requests` — List pull requests
- `update_pull_request` — Update a pull request
- `merge_pull_request` — Merge a pull request
- `update_pull_request_branch` — Update PR branch from base
- `pull_request_read` — Read pull request details
- `pull_request_review_write` — Submit or edit a PR review
- `add_comment_to_pending_review` — Add comment to a pending PR review
- `request_copilot_review` — Request Copilot review for a PR

### ℹ️ Other
- `list_issue_types` — List all issue types


---

## 📦 Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) or [Python](https://www.python.org/) (depending on the implementation)
- [Docker](https://www.docker.com/get-started) (optional, recommended)
- GitHub account with sufficient repository permissions
- (Optional) Access to cloud platforms (e.g., AWS, GCP, Azure) for deployment integrations

### Installation

#### 1. Clone the repository

```bash
git clone https://github.com/YOUR_ORG/github-mcp.git
cd github-mcp
```

#### 2. Install dependencies

For Node.js:
```bash
npm install
```
For Python:
```bash
pip install -r requirements.txt
```

#### 3. Set up environment variables

Copy `.env.example` to `.env` and edit as needed.

#### 4. Start the server

```bash
npm start
```
or  
```bash
python app.py
```

---

## 🛠️ Deployment

- **Required:**
    - User must set GITHUB_PERSONAL_ACCESS_TOKEN in order to use this tool.

All the MCP Servers are running in similar ways. 

The MCP (Multi-Cloud Platform) servers are designed to run as simple, stateless web services that can be deployed on any standard infrastructure—locally, on VMs, or in containers. Each server listens for HTTP requests and exposes endpoints for processing GitHub metadata, repository events, or user-specified automations.

**How MCP Servers Run:**

1. **Start via CLI or Docker:**  
   MCP servers can be started with `npm start`, `python app.py`, or via a Docker container, depending on your setup.

2. **Environment Configuration:**  
   Critical configuration, such as GitHub tokens, endpoint URLs, and cloud provider credentials, are provided through environment variables (see `.env.example`). This allows secure and flexible deployment.

3. **Stateless Operation:**  
   Servers do not persist data internally; instead, they interact with GitHub APIs and any configured cloud backends in real-time. State is managed either externally (e.g., via GitHub Issues, metadata in cloud storage, etc.) or passed per request.

4. **Modular Design:**  
   Each MCP server runs independently and has a modular, plug-in-based backend integration model. You can enable or disable cloud and CI/CD integrations via config.

5. **Secure Web Server:**  
   The server exposes a secured HTTP API, typically protected with GitHub OAuth or personal access token validation. No requests are processed without proper authentication.

6. **Logs and Monitoring:**  
   All runtime logs are output to the console or can be redirected to logging systems or file storage, depending on deployment standards.

**Example:**

- For local runs, after installing dependencies and configuring `.env`, run `npm start` (Node.js) or `python app.py` (Python).
- For Docker deployments:  
  - Build the image (e.g., `docker build -t github-mcp .`)
  - Run with environment variables:  
    `docker run -p 8080:8080 --env-file .env github-mcp`

Once started, the server will listen for HTTP requests and handle events as configured.

**Note**

In order to get the correct output for the LLM when using LlamaStack or OGX be sure to enable tool outputs. 
For example for `LLM=llama-3-2-3b-instruct` you must set:

```yaml
args:
  - --enable-auto-tool-choice          # Enables automatic tool selection
  - --chat-template                     # Specifies template path
  - /vllm-workspace/examples/tool_chat_template_llama3.2_json.jinja
  - --tool-call-parser                  # Parser for Llama 3.2 JSON format
  - llama3_json
  - --max-model-len                     # Max context length
  - "30444"
```

## Building

```bash
podman build --no-cache --platform linux/amd64 \
  -t quay.io/rh-ai-quickstart/github-mcp:0.5.7 \
  -f mcp-servers/github-mcp/Containerfile \
  mcp-servers/github-mcp/
```