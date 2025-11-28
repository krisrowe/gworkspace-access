# Google Workspace Access CLI (`gwsa`)

This project provides a Command Line Interface (CLI) tool, `gwsa`, to search and manage your Gmail account using the Google Gmail API. It centralizes all environment and credential setup within a dedicated `gwsa setup` command.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Google Cloud CLI (`gcloud`)**:
    *   Install the `gcloud` CLI: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
    *   Initialize `gcloud` and authenticate:
        ```bash
        gcloud init
        gcloud auth application-default login
        ```
2.  **Python 3 (Recommended: 3.11 or higher)**:
    *   Ensure Python 3 is installed. For optimal compatibility and to avoid potential issues with Google Cloud client libraries, Python 3.11 or higher is recommended.

    *   **Upgrading Python with `pyenv` (Recommended)**:
        `pyenv` allows you to easily switch between multiple Python versions.
        If you don't have `pyenv` installed, follow its official installation guide: [https://github.com/pyenv/pyenv#installation](https://github.com/pyenv/pyenv#installation)

        Once `pyenv` is installed, you can upgrade Python and set it globally with:
        ```bash
        pyenv install 3.11
        pyenv global 3.11
        python3 --version # Verify the active Python version
        ```
3.  **`pip`**:
    *   Python's package installer.

## First-Time Setup

This process walks through installing the `gwsa` tool and configuring it for the first time.

### 1. Choose a Project Identification Method

The `gwsa` tool needs to know which Google Cloud Project to use. You have two options:

**Option A: Project Labels (Recommended)**

Label your Google Cloud project. The setup script will automatically discover and save the project ID for you. This is the easiest method and simplifies setting up other workstations later.

```bash
gcloud alpha projects update YOUR_GCP_PROJECT_ID --update-labels=gws-access=default
```
> Replace `YOUR_GCP_PROJECT_ID` with your actual project ID.

**Option B: Manual `.env` Configuration**

If you prefer not to label your project, you can create a file named `.env` in the root of this directory and add your project ID to it.

```dotenv
# .env
WORKSPACE_ACCESS_PROJECT="YOUR_GCP_PROJECT_ID"
```

### 2. Generate and Secure Client Credentials

Next, you need to get OAuth 2.0 client credentials from the Google Cloud Console.

1.  Navigate to your project in the [Google Cloud Console](https://console.developers.google.com/).
2.  Ensure the **Gmail API** and **Secret Manager API** are enabled.
3.  Go to "APIs & Services" -> "Credentials".
4.  Click "Create Credentials" -> "OAuth client ID".
5.  Select **"Desktop app"** as the Application type and give it a name.
6.  Click "Create". On the next screen, click **"Download JSON"**.
7.  Rename the downloaded file to `credentials.json` and place it in the root of this project directory.

> **Important: Backing Up Your Credentials**
> You can only download the `credentials.json` file once. The `gwsa setup` command (run in a later step) will automatically back up this file as a secret in Google Secret Manager. This makes it easy to set up `gwsa` on a new workstation in the future without having to generate new credentials.

### 3. Install the CLI Tool

Install the `gwsa` tool and its dependencies using `pip`.

```bash
# Recommended for development (your code changes are reflected immediately)
pip install -e .

# For a regular installation
# pip install .
```

### 4. Run Initial Setup

Now, run the central `gwsa setup` command.

```bash
gwsa setup
```

This is the most important step and must be run before any other `gwsa` command. See the section below for a detailed explanation of what it does.

## What `gwsa setup` Does

The `gwsa setup` command is the heart of this tool's configuration. It must be run first because it performs several critical actions to bootstrap the environment:

1.  **Ensures a Project ID is Set**: It finds the Google Cloud project ID using either the labeled project (recommended) or the `.env` file.
2.  **Enables Cloud APIs**: It automatically enables the Gmail API and Secret Manager API on your project if they are not already active.
3.  **Secures Client Credentials**: It checks for `credentials.json` and synchronizes it with Google Secret Manager, creating a secure backup.
4.  **Manages User Authorization**: It triggers a browser-based OAuth 2.0 flow to get your permission for the tool to access your Google account. This interactive sign-in process is what generates the user-specific `user_token.json` file.
5.  **Refreshes Tokens**: On subsequent runs, it will automatically refresh your user token if it has expired.

Without running `setup` first, the tool has no project context and lacks the necessary client and user credentials to communicate with Google APIs.

## Using the `gwsa` CLI Tool

Once setup is complete, you can use the `gwsa` tool. All `mail` sub-commands output their results in JSON format, allowing for easy parsing and integration with other tools like `jq`.

**Search for Emails:**
```bash
gwsa mail search "after:2025-11-27 -label:Processed"
```

**Read a Specific Email:**
```bash
gwsa mail read MESSAGE_ID
```
> Replace `MESSAGE_ID` with an ID from the search results.

**Label an Email:**
To add a label:
```bash
gwsa mail label MESSAGE_ID MyCustomLabel
```
To remove a label:
```bash
gwsa mail label MESSAGE_ID MyCustomLabel --remove
```

**Debugging:**
You can set the `LOG_LEVEL` environment variable to `DEBUG` to get detailed logging output.
```bash
LOG_LEVEL=DEBUG gwsa mail search "after:2025-11-27"
```

---
## Advanced Usage

### Setting Up a New Workstation

Once you have completed the first-time setup, configuring `gwsa` on another machine is much simpler.

1.  Clone this repository to your new machine.
2.  Ensure the [Prerequisites](#prerequisites) (Google Cloud CLI, Python) are met.
3.  Install the tool: `pip install -e .`
4.  Run the setup command:
    ```bash
    gwsa setup
    ```
That's it. Because you already have a labeled project and your client credentials are saved in Secret Manager, the script will automatically:
- Discover your Google Cloud project.
- Create the `.env` file with the correct project ID.
- Download `credentials.json` from Google Secret Manager.
- Initiate the browser flow to get a fresh `user_token.json` for the new machine.

### Re-authenticating or Switching Users

If you need to regenerate your user token, switch to a different Google account, or fix a corrupted `user_token.json`, you can force a new authentication flow by using the `--new-user` flag with the `setup` command. This will delete the existing token and trigger the browser sign-in process again.

```bash
gwsa setup --new-user
```
---