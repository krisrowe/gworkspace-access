import logging
import json
import base64 # Imported here as it's used within the function
from ..mail import _get_gmail_service # Changed to relative import

logger = logging.getLogger(__name__)

def read_message(message_id: str):
    """
    Retrieves the full content of a specific Gmail message.
    Returns a dictionary containing message details, including raw body and labels.
    """
    try:
        service = _get_gmail_service()
        logger.info(f"Retrieving message with ID: {message_id}")

        # Get the message in full format
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()

        # Extract relevant parts
        headers = msg['payload']['headers']
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'N/A')
        sender = next((header['value'] for header in headers if header['name'] == 'From'), 'N/A')
        date = next((header['value'] for header in headers if header['name'] == 'Date'), 'N/A')
        
        # Get the body. This can be complex due to MIME types.
        # For simplicity, we'll try to get the first plain text part.
        body = ""
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'body' in part and 'data' in part['body']:
                        body = part['body']['data']
                        break
        elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
            body = msg['payload']['body']['data']
        
        # Gmail API returns base64url encoded data
        if body:
            body = base64.urlsafe_b64decode(body).decode('utf-8')

        message_details = {
            "id": message_id,
            "subject": subject,
            "sender": sender,
            "date": date,
            "snippet": msg.get('snippet', ''),
            "body": body,
            "labelIds": msg.get('labelIds', []), # Added labelIds
            "raw": json.dumps(msg, indent=2) # Include raw message for detailed inspection
        }
        
        logger.debug(f"Successfully retrieved message: '{subject}' from '{sender}'")
        return message_details

    except HttpError as error:
        logger.error(f"An error occurred with the Gmail API while reading message {message_id}: {error}")
        raise
    except FileNotFoundError as e:
        logger.error(f"Missing required file: {e}")
        raise
    except Exception as e:
        logger.critical(f"An unexpected error occurred during message read for ID {message_id}: {e}", exc_info=True)
        raise
