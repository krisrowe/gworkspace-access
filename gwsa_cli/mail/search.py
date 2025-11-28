import logging
import json
from ..mail import _get_gmail_service # Changed to relative import

logger = logging.getLogger(__name__)

def search_messages(query_string: str):
    """
    Searches for Gmail messages matching the given query string.
    Returns a list of dictionaries, each representing a message.
    """
    try:
        service = _get_gmail_service()
        logger.debug("Gmail API service built successfully.")
        logger.debug(f"Searching for emails with query: '{query_string}'")

        results = service.users().messages().list(userId="me", q=query_string).execute()
        messages = results.get("messages", [])

        if not messages:
            logger.debug("No messages found matching the criteria.")
            return []
        else:
            logger.debug(f"Found {len(messages)} messages matching criteria:")
            parsed_messages = []
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id'], format='metadata').execute()
                headers = msg['payload']['headers']
                
                subject = "N/A"
                sender = "N/A"
                date = "N/A"
                
                for header in headers:
                    if header['name'] == 'Subject':
                        subject = header['value']
                    elif header['name'] == 'From':
                        sender = header['value']
                    elif header['name'] == 'Date':
                        date = header['value']
                
                parsed_messages.append({
                    "id": message['id'],
                    "subject": subject,
                    "sender": sender,
                    "date": date
                })
                logger.debug(f"- Subject: {subject}, From: {sender}, Date: {date}")
            return parsed_messages

    except Exception as e: # Catch all exceptions, including HttpError from _get_gmail_service
        logger.critical(f"An unexpected error occurred during message search: {e}", exc_info=True)
        raise