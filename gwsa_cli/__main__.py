import argparse
import logging
import os
import sys
import json
from dotenv import load_dotenv

# Import setup_local for the setup command from within the package
from . import setup_local

# Import mail operations modules from within the package
from .mail import search
from .mail import read
from .mail import label

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
    """
    Checks if user_token.json exists. This is a basic check;
    full validity is handled by ensure_user_token_json in setup_local.
    """
    return os.path.exists(setup_local.USER_TOKEN_FILE)

def cli():
    parser = argparse.ArgumentParser(description="Gmail Workspace Assistant (GWSA) CLI")
    
    # Move subparsers definition inside cli()
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up local environment and credentials.")
    setup_parser.add_argument("--new-user", action="store_true", 
                              help="Force a new user authentication flow, ignoring any existing user_token.json.") # Added --new-user flag
    
    # Mail command parser
    mail_parser = subparsers.add_parser("mail", help="Operations related to Gmail.")
    mail_subparsers = mail_parser.add_subparsers(dest="mail_command", help="Mail commands")

    # Mail search command
    mail_search_parser = mail_subparsers.add_parser("search", help="Search for emails. Output is in JSON format.")
    mail_search_parser.add_argument("query", type=str, help='The Gmail search query string (e.g., "after:2025-11-27 -label:Processed").')

    # Mail read command
    mail_read_parser = mail_subparsers.add_parser("read", help="Read a specific email by ID.")
    mail_read_parser.add_argument("message_id", type=str, help="The ID of the message to read.")

    # Mail label command
    mail_label_parser = mail_subparsers.add_parser("label", help="Add or remove labels from an email.")
    mail_label_parser.add_argument("message_id", type=str, help="The ID of the message to label.")
    mail_label_parser.add_argument("label_name", type=str, help="The name of the label to add or remove.")
    mail_label_parser.add_argument("--remove", action="store_true", help="Remove the label instead of adding it.")

    args = parser.parse_args()

    # Handle the setup command
    if args.command == "setup":
        if setup_local.run_setup(new_user=args.new_user): # Pass new_user flag to run_setup
            logger.info("GWSA setup completed successfully.")
        else:
            logger.error("GWSA setup failed. Please check logs for details.")
            sys.exit(1)
    else:
        # Pre-check for user_token.json for all other commands
        if not check_user_token_exists():
            logger.error(f"Error: User credentials file '{setup_local.USER_TOKEN_FILE}' not found.")
            logger.error("Please run 'gwsa setup' to set up your credentials first.")
            sys.exit(1)

        # Dispatch other commands
        if args.command == "mail":
            if args.mail_command == "search":
                try:
                    logger.debug(f"Executing mail search with query: '{args.query}'")
                    messages = search.search_messages(args.query)
                    print(json.dumps(messages, indent=2))
                except FileNotFoundError as e:
                    logger.error(f"Error: {e}")
                    logger.error(f"This usually means client credentials ('{setup_local.LOCAL_CREDS_FILE}') are missing.")
                    logger.error("Please run 'gwsa setup' to ensure all credentials are in place.")
                    sys.exit(1)
                except Exception as e:
                    logger.critical(f"An error occurred during mail search: {e}", exc_info=True)
                    sys.exit(1)
            elif args.mail_command == "read":
                try:
                    logger.info(f"Executing mail read for message ID: '{args.message_id}'")
                    message_details = read.read_message(args.message_id)
                    print(json.dumps(message_details, indent=2))
                except FileNotFoundError as e:
                    logger.error(f"Error: {e}")
                    logger.error(f"This usually means client credentials ('{setup_local.LOCAL_CREDS_FILE}') are missing.")
                    logger.error("Please run 'gwsa setup' to ensure all credentials are in place.")
                    sys.exit(1)
                except Exception as e:
                    logger.critical(f"An error occurred during mail read for ID {args.message_id}: {e}", exc_info=True)
                    sys.exit(1)
            elif args.mail_command == "label":
                try:
                    action = "removing" if args.remove else "adding"
                    logger.info(f"{action.capitalize()} label '{args.label_name}' for message ID: '{args.message_id}'")
                    updated_message = label.modify_message_labels(args.message_id, args.label_name, add=not args.remove)
                    if updated_message:
                        print(json.dumps(updated_message, indent=2))
                    else:
                        # This case may occur if the label was already present/absent, and no API call was made.
                        # We can construct a success message.
                        logger.info(f"Label '{args.label_name}' was already in the desired state for message ID '{args.message_id}'.")
                        # Or, to be more consistent, fetch the message and print it
                        message_details = read.read_message(args.message_id)
                        print(json.dumps(message_details, indent=2))

                except FileNotFoundError as e:
                    logger.error(f"Error: {e}")
                    logger.error(f"This usually means client credentials ('{setup_local.LOCAL_CREDS_FILE}') are missing.")
                    logger.error("Please run 'gwsa setup' to ensure all credentials are in place.")
                    sys.exit(1)
                except Exception as e:
                    logger.critical(f"An error occurred during mail label for ID {args.message_id}: {e}", exc_info=True)
                    sys.exit(1)
            else:
                mail_parser.print_help()
        else:
            parser.print_help()

if __name__ == "__main__":
    load_dotenv()
    cli()
