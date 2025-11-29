import os
import re
import subprocess
import logging
import time
import json
import hashlib # For comparing file contents
from dotenv import load_dotenv, set_key

# Import mail related constants from the mail package's __init__.py
from .mail import USER_TOKEN_FILE, SCOPES # Import constants from the mail package
# --- Configuration ---
ENV_PATH = '.env'
GMAIL_CREDS_SECRET_NAME = "gmail-api-credentials"
GWS_ACCESS_LABEL_KEY = "gws-access"
GWS_ACCESS_LABEL_VALUE = "default"
SETUP_LOG_FILE = "setup_local.log" # Renamed log file

# --- Setup Logging ---
# Only configure basicConfig if a handler has not already been added
# This prevents re-configuring logging if a parent script (like a CLI) already set it up.
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(SETUP_LOG_FILE),
            logging.StreamHandler() # Also print to console
        ]
    )
logger = logging.getLogger(__name__)

# Use ~/.config/gworkspace-access for storing credentials
_CONFIG_DIR = os.path.expanduser("~/.config/gworkspace-access")
LOCAL_CREDS_FILE = os.path.join(_CONFIG_DIR, "credentials.json")


def update_env_variable(key, value):
    """Updates or adds a key-value pair in the .env file."""
    load_dotenv(ENV_PATH) # Reload to ensure latest state
    set_key(ENV_PATH, key, value)
    # Also update the current environment for immediate use
    os.environ[key] = value
    logger.info(f"Updated {key} in {ENV_PATH} and current environment.")

def get_env_variable(key):
    """Gets a variable from the .env file or environment."""
    load_dotenv(ENV_PATH)
    return os.getenv(key)

def run_gcloud_command(cmd, error_message, check_error=True):
    """Helper to run gcloud commands and log output/errors."""
    try:
        logger.info(f"Running gcloud command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=check_error)
        if result.stdout:
            logger.debug(f"gcloud stdout: {result.stdout.strip()}")
        if result.stderr:
            logger.debug(f"gcloud stderr: {result.stderr.strip()}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"{error_message}: {e}")
        logger.error(f"gcloud stderr: {e.stderr.strip()}")
        return None
    except FileNotFoundError:
        logger.error("Error: 'gcloud' command not found. Please ensure Google Cloud CLI is installed and in your PATH.")
        return None

def secret_exists(secret_name, project_id):
    """Checks if a secret exists in Secret Manager using list --filter."""
    cmd = [
        "gcloud", "secrets", "list",
        f"--filter=name:{secret_name}", # Corrected filter using the short secret name
        "--format=json",
        f"--project={project_id}" 
    ]
    output = run_gcloud_command(cmd, f"Error listing secrets for existence check of {secret_name}", check_error=False)
    if output:
        try:
            secrets_list = json.loads(output)
            return len(secrets_list) > 0
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from gcloud secrets list output for {secret_name}.")
            return False
    return False

def create_secret(secret_name, project_id, file_path):
    """Creates a secret in Secret Manager from a file."""
    logger.info(f"Creating secret '{secret_name}' in project '{project_id}' from file '{file_path}'...")
    cmd = [
        "gcloud", "secrets", "create", secret_name,
        f"--project={project_id}",
        f"--data-file={file_path}"
    ]
    stdout = run_gcloud_command(cmd, f"Failed to create secret '{secret_name}'")
    return stdout is not None

def add_secret_version(secret_name, project_id, file_path):
    """Adds a new version to an existing secret from a file."""
    logger.info(f"Adding new version to secret '{secret_name}' in project '{project_id}' from file '{file_path}'...")
    cmd = [
        "gcloud", "secrets", "versions", "add", secret_name,
        f"--project={project_id}",
        f"--data-file={file_path}"
    ]
    stdout = run_gcloud_command(cmd, f"Failed to add version to secret '{secret_name}'")
    return stdout is not None

def ensure_project_id():
    """
    Ensures WORKSPACE_ACCESS_PROJECT is set.
    If not, tries to find a project with the 'gws-access:default' label
    and updates the .env file.
    """
    project_id = get_env_variable("WORKSPACE_ACCESS_PROJECT")

    if project_id:
        logger.info(f"Using GCP project: {project_id}")
        return project_id

    logger.info("WORKSPACE_ACCESS_PROJECT is not set. Attempting to find a GCP project with 'gws-access:default' label...")
    
    cmd = [
        "gcloud", "projects", "list",
        f"--filter=labels.{GWS_ACCESS_LABEL_KEY}:{GWS_ACCESS_LABEL_VALUE}",
        "--format=value(projectId)"
    ]
    discovered_project_id = run_gcloud_command(cmd, "Error calling gcloud to list projects")

    if discovered_project_id:
        logger.info(f"Found project with '{GWS_ACCESS_LABEL_KEY}:{GWS_ACCESS_LABEL_VALUE}' label: {discovered_project_id}")
        update_env_variable("WORKSPACE_ACCESS_PROJECT", discovered_project_id)
        return discovered_project_id
    else:
        logger.error(f"Error: No GCP project found with the label '{GWS_ACCESS_LABEL_KEY}:{GWS_ACCESS_LABEL_VALUE}'.")
        logger.error("Please ensure you have a GCP project configured with this label.")
        logger.error("Alternatively, manually set WORKSPACE_ACCESS_PROJECT in your .env file or as an environment variable.")
        return None

def enable_gcp_apis(project_id):
    """Enables required GCP APIs for the given project ID."""
    apis_to_enable = [
        "gmail.googleapis.com",
        "secretmanager.googleapis.com"
    ]
    
    all_enabled = True
    for api in apis_to_enable:
        logger.info(f"Ensuring {api} is enabled for project {project_id}...")
        cmd = [
            "gcloud", "services", "enable", api,
            f"--project={project_id}", "--async"
        ]
        stdout = run_gcloud_command(cmd, f"Error enabling {api}")
        if stdout is None:
            all_enabled = False

    if not all_enabled:
        logger.error("Failed to enable one or more required APIs.")
    else:
        logger.info("All required APIs enablement initiated (asynchronous).")
    return all_enabled

def ensure_credentials_secret(project_id):
    """Ensures the gmail-api-credentials secret exists, retrieves credentials.json,
    and verifies it matches local content if present."""
    
    sm_credentials_content = None
    try:
        cmd = [
            "gcloud", "secrets", "versions", "access", "latest",
            f"--secret={GMAIL_CREDS_SECRET_NAME}",
            f"--project={project_id}"
        ]
        sm_credentials_content = run_gcloud_command(cmd, f"Failed to retrieve {LOCAL_CREDS_FILE} from Secret Manager", check_error=False)
    except subprocess.CalledProcessError as e:
        logger.debug(f"Initial retrieval attempt failed (expected for missing/empty secret): {e.stderr.strip()}")
        sm_credentials_content = None

    local_credentials_content = None
    if os.path.exists(LOCAL_CREDS_FILE):
        with open(LOCAL_CREDS_FILE, "r") as f:
            local_credentials_content = f.read()

    # --- Verification ---
    if sm_credentials_content and local_credentials_content:
        # Compare content. Normalize JSON to ignore formatting differences.
        try:
            sm_json = json.dumps(json.loads(sm_credentials_content), sort_keys=True)
            local_json = json.dumps(json.loads(local_credentials_content), sort_keys=True)
            if sm_json != local_json:
                logger.error(f"Error: Local '{LOCAL_CREDS_FILE}' does NOT match content in Secret Manager.")
                logger.error("Please ensure your local 'credentials.json' is the latest, then update the secret:")
                logger.error(f"  gcloud secrets versions add {GMAIL_CREDS_SECRET_NAME} --project={project_id} --data-file={LOCAL_CREDS_FILE}")
                return False
            else:
                logger.info(f"Local '{LOCAL_CREDS_FILE}' matches content in Secret Manager.")
        except json.JSONDecodeError:
            logger.error(f"Error: Could not parse '{LOCAL_CREDS_FILE}' or Secret Manager content as JSON. Manual inspection needed.")
            return False
    elif local_credentials_content and not sm_credentials_content:
        logger.error(f"Error: Local '{LOCAL_CREDS_FILE}' found, but no secret '{GMAIL_CREDS_SECRET_NAME}' in Secret Manager.")
        logger.error("Please push your local 'credentials.json' to Secret Manager:")
        logger.error(f"  gcloud secrets create {GMAIL_CREDS_SECRET_NAME} --project={project_id} --data-file={LOCAL_CREDS_FILE}")
        return False
    elif not local_credentials_content and sm_credentials_content:
        # If local file is missing but secret exists, retrieve it
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        with open(LOCAL_CREDS_FILE, "w") as f:
            f.write(sm_credentials_content)
        logger.info(f"{LOCAL_CREDS_FILE} retrieved from Secret Manager and saved locally.")
        return True
    elif not local_credentials_content and not sm_credentials_content:
        logger.error(f"Error: No local '{LOCAL_CREDS_FILE}' found, and secret '{GMAIL_CREDS_SECRET_NAME}' not found in Secret Manager.")
        logger.error("Please download your 'credentials.json' from Google Cloud Console (Desktop app type),")
        logger.error("place it in the current directory, then push it to Secret Manager manually:")
        logger.error(f"  gcloud secrets create {GMAIL_CREDS_SECRET_NAME} --project={project_id} --data-file={LOCAL_CREDS_FILE}")
        return False

    logger.info(f"Client credentials ({LOCAL_CREDS_FILE}) ensured.")
    return True

def ensure_user_token_json(new_user: bool = False):
    """
    Ensures user_token.json is present and valid, performing OAuth flow if necessary.
    This function will be interactive via a browser.
    :param new_user: If True, force a new OAuth flow by deleting any existing user_token.json.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    # Ensure config directory exists
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    logger.debug(f"Ensured config directory exists: {_CONFIG_DIR}")

    logger.info(f"Ensuring user credentials ({USER_TOKEN_FILE})...")

    if new_user and os.path.exists(USER_TOKEN_FILE):
        os.remove(USER_TOKEN_FILE)
        logger.info(f"Removed existing {USER_TOKEN_FILE} due to --new-user flag.")

    creds = None
    if os.path.exists(USER_TOKEN_FILE):
        logger.debug(f"Found {USER_TOKEN_FILE}. Attempting to load user credentials.")
        try:
            creds = Credentials.from_authorized_user_file(USER_TOKEN_FILE, SCOPES)
            logger.debug("User credentials loaded.")
        except Exception as e:
            logger.warning(f"Failed to load user credentials from {USER_TOKEN_FILE}: {e}")
            creds = None # Force re-auth
    else:
        logger.debug(f"{USER_TOKEN_FILE} not found. Will proceed with new user authorization flow.")

    if not creds or not creds.valid:
        logger.debug("User credentials not valid or not found. Checking for expiration/refresh.")
        if creds and creds.expired and creds.refresh_token:
            logger.info("User credentials expired, attempting to refresh token.")
            try:
                creds.refresh(Request())
                logger.info("User token refreshed successfully.")
            except Exception as e:
                logger.warning(f"Failed to refresh token: {e}. Initiating new authorization flow.")
                creds = None # Force new auth flow if refresh fails
        
        if not creds: # If refresh failed or creds were never valid
            logger.info("Initiating new user authorization flow via browser.")
            if not os.path.exists(LOCAL_CREDS_FILE):
                logger.error(f"Error: Client credentials file '{LOCAL_CREDS_FILE}' not found.")
                logger.error("Cannot initiate user authorization flow without client credentials.")
                logger.error(f"Please ensure '{LOCAL_CREDS_FILE}' is present (run 'gwsa setup' first if needed).")
                return False

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    LOCAL_CREDS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0) # Port 0 for dynamic port
                logger.info("New user authorization completed via browser.")
            except Exception as e:
                logger.error(f"Failed to complete new user authorization flow: {e}")
                return False
        
        with open(USER_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        logger.debug(f"User credentials saved to {USER_TOKEN_FILE}.")
    else:
        logger.info("User credentials are valid.")
    
    return True

def run_setup(new_user: bool = False, client_creds: str = None):
    logger.info("Starting local setup script...")

    # If client_creds path is provided, copy it to config directory
    if client_creds:
        if os.path.exists(client_creds):
            os.makedirs(_CONFIG_DIR, exist_ok=True)
            import shutil
            shutil.copy(client_creds, LOCAL_CREDS_FILE)
            logger.info(f"Client credentials copied from {client_creds} to {LOCAL_CREDS_FILE}")
        else:
            logger.error(f"Error: Client credentials file not found: {client_creds}")
            return False

    project_id = ensure_project_id()
    if not project_id:
        return False

    if not enable_gcp_apis(project_id):
        return False

    time.sleep(5)
    logger.info("Attempting to ensure client credentials secret after a short delay...")

    if not ensure_credentials_secret(project_id):
        return False

    logger.info("Client credentials (credentials.json) ensured.")

    # Now handle user credentials
    if not ensure_user_token_json(new_user=new_user): # Pass new_user flag
        return False

    logger.info("User credentials (user_token.json) ensured.")
    logger.info("Local setup script finished successfully.")
    return True

if __name__ == "__main__":
    import sys
    # Load .env variables at the very beginning
    load_dotenv()
    # This block won't have new_user flag available directly, as it's meant for CLI parsing.
    # When run directly, it will behave as if --new-user is not passed.
    if not run_setup():
        sys.exit(1)