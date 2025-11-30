"""GWSA CLI - Gmail Workspace Assistant command-line interface."""

import logging
import os
import sys
import json
from functools import wraps
from dotenv import load_dotenv
import click

from . import setup_local
from . import __version__
from .mail import search as search_module
from .mail import read as read_module
from .mail import label as label_module


# Configure logging at the application level
if not logging.root.handlers:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, LOG_LEVEL),
                        format='%(asctime)s - %(levelname)s - %(message)s')
# Suppress noisy INFO logs from googleapiclient and google_auth_oauthlib
logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.WARNING)
logging.getLogger('google_auth_oauthlib.flow').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def check_user_token_exists():
    """Check if user_token.json exists."""
    return os.path.exists(setup_local.USER_TOKEN_FILE)


def require_user_credentials(f):
    """Decorator to ensure user credentials exist before running command."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_user_token_exists():
            logger.error(f"Error: User credentials file '{setup_local.USER_TOKEN_FILE}' not found.")
            logger.error("Please run 'gwsa setup' to set up your credentials first.")
            sys.exit(1)
        return f(*args, **kwargs)
    return decorated_function


@click.group()
def gwsa():
    """Gmail Workspace Assistant (GWSA) CLI.

    A personal Gmail Workspace Assistant for managing emails via command line.
    """
    pass


# Setup command
@click.command()
@click.option('--new-user', is_flag=True,
              help='Force a new user authentication flow, ignoring any existing user_token.json.')
@click.option('--client-creds', type=click.Path(exists=True),
              help='Path to client_secrets.json file to use for OAuth setup.')
@click.option('--status', is_flag=True,
              help='Show configuration status (read-only, no setup).')
def setup(new_user, client_creds, status):
    """Set up local environment and credentials, or check status."""
    if not setup_local.run_setup(new_user=new_user, client_creds=client_creds, status_only=status):
        if not status:
            logger.error("GWSA setup failed. Please check logs for details.")
        sys.exit(1)


# Mail group
@click.group()
def mail():
    """Operations related to Gmail."""
    pass


# Mail search command
@click.command()
@click.argument('query')
@click.option('--page-token', default=None,
              help="Token for pagination (from previous search's nextPageToken).")
@click.option('--max-results', type=int, default=25,
              help='Maximum number of messages to return (default 25, due to body extraction cost).')
@click.option('--format', type=click.Choice(['full', 'metadata']), default='full',
              help="'full' includes body and snippet (slower); 'metadata' is fast with headers and labelIds only.")
@require_user_credentials
def search(query, page_token, max_results, format):
    """Search for emails. Output is in JSON format."""
    try:
        logger.debug(f"Executing mail search with query: '{query}'")
        messages, metadata = search_module.search_messages(query, page_token=page_token, max_results=max_results, format=format)
        logger.info(f"Found {len(messages)} messages (estimated total: {metadata['resultSizeEstimate']})")
        if metadata.get('nextPageToken'):
            logger.info(f"More pages available. Use --page-token {metadata['nextPageToken']} to fetch next page")
        click.echo(json.dumps(messages, indent=2))
    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        logger.error(f"This usually means client credentials ('{setup_local.CLIENT_SECRETS_FILE}') are missing.")
        logger.error("Please run 'gwsa setup' to ensure all credentials are in place.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An error occurred during mail search: {e}", exc_info=True)
        sys.exit(1)


# Mail read command
@click.command()
@click.argument('message_id')
@require_user_credentials
def read_command(message_id):
    """Read a specific email by ID."""
    try:
        logger.info(f"Executing mail read for message ID: '{message_id}'")
        message_details = read_module.read_message(message_id)
        click.echo(json.dumps(message_details, indent=2))
    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        logger.error(f"This usually means client credentials ('{setup_local.CLIENT_SECRETS_FILE}') are missing.")
        logger.error("Please run 'gwsa setup' to ensure all credentials are in place.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An error occurred during mail read for ID {message_id}: {e}", exc_info=True)
        sys.exit(1)


# Mail label command
@click.command()
@click.argument('message_id')
@click.argument('label_name')
@click.option('--remove', is_flag=True,
              help='Remove the label instead of adding it.')
@require_user_credentials
def label_command(message_id, label_name, remove):
    """Add or remove labels from an email."""
    try:
        action = "removing" if remove else "adding"
        logger.info(f"{action.capitalize()} label '{label_name}' for message ID: '{message_id}'")
        updated_message = label_module.modify_message_labels(message_id, label_name, add=not remove)
        if updated_message:
            click.echo(json.dumps(updated_message, indent=2))
        else:
            logger.info(f"Label '{label_name}' was already in the desired state for message ID '{message_id}'.")
            message_details = read_module.read_message(message_id)
            click.echo(json.dumps(message_details, indent=2))
    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        logger.error(f"This usually means client credentials ('{setup_local.CLIENT_SECRETS_FILE}') are missing.")
        logger.error("Please run 'gwsa setup' to ensure all credentials are in place.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An error occurred during mail label for ID {message_id}: {e}", exc_info=True)
        sys.exit(1)


# Add commands to groups using add_command()
gwsa.add_command(setup, name='setup')
gwsa.add_command(mail)

mail.add_command(search)
mail.add_command(read_command, name='read')
mail.add_command(label_command, name='label')


def main():
    """Entry point for the CLI."""
    load_dotenv()
    gwsa()


if __name__ == "__main__":
    main()
