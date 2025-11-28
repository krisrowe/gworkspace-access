import logging
from ..mail import _get_gmail_service # Changed to relative import
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

def _ensure_label_exists(service, label_name: str):
    """
    Ensures a label with the given name exists and returns its ID.
    If the label does not exist, it creates it.
    """
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    
    # Check if label already exists
    for label in labels:
        if label['name'] == label_name:
            logger.debug(f"Label '{label_name}' already exists with ID: {label['id']}")
            return label['id']

    # If not found, create the label
    logger.debug(f"Label '{label_name}' not found. Creating it.")
    create_label_body = {
        'name': label_name,
        'labelListVisibility': 'labelShow', # Options: labelShow, labelShowIfUnread
        'messageListVisibility': 'show' # Options: show, hide
    }
    created_label = service.users().labels().create(userId='me', body=create_label_body).execute()
    logger.debug(f"Created label '{label_name}' with ID: {created_label['id']}")
    return created_label['id']


def modify_message_labels(message_id: str, label_name: str, add: bool = True):
    """
    Adds or removes a label from a specific Gmail message.
    :param message_id: The ID of the message to modify.
    :param label_name: The name of the label to add or remove.
    :param add: If True, add the label; if False, remove the label.
    :returns: The updated message resource dictionary if successful, None otherwise.
    """
    try:
        service = _get_gmail_service()
        
        # Ensure the label exists and get its ID
        label_id = _ensure_label_exists(service, label_name)

        # Get existing labels to ensure we only try to remove labels that are present
        message = service.users().messages().get(userId='me', id=message_id, fields='labelIds').execute()
        current_labels = message.get('labelIds', [])

        labels_to_add = []
        labels_to_remove = []

        if add:
            if label_id not in current_labels: # Use label_id for comparison
                labels_to_add.append(label_id)
                logger.debug(f"Adding label '{label_name}' (ID: {label_id}) to message ID: {message_id}")
            else:
                logger.debug(f"Label '{label_name}' (ID: {label_id}) already present on message ID: {message_id}. No action needed.")
                # Return the full message object to indicate success and provide context
                return service.users().messages().get(userId='me', id=message_id, format='full').execute()
        else: # remove
            if label_id in current_labels: # Use label_id for comparison
                labels_to_remove.append(label_id)
                logger.debug(f"Removing label '{label_name}' (ID: {label_id}) from message ID: {message_id}")
            else:
                logger.debug(f"Label '{label_name}' (ID: {label_id}) not present on message ID: {message_id}. No action needed.")
                # Return the full message object to indicate success and provide context
                return service.users().messages().get(userId='me', id=message_id, format='full').execute()

        if labels_to_add or labels_to_remove:
            body = {
                'addLabelIds': labels_to_add,
                'removeLabelIds': labels_to_remove
            }
            updated_message = service.users().messages().modify(userId='me', id=message_id, body=body).execute()
            logger.debug(f"Successfully modified labels for message ID: {message_id}.")
            return updated_message
        
        # If no labels were added/removed (e.g., already in desired state),
        # return the current message to indicate no error occurred.
        return service.users().messages().get(userId='me', id=message_id, format='full').execute()

    except HttpError as error:
        logger.error(f"An error occurred with the Gmail API while modifying labels for message {message_id}: {error}")
        # Specific error for invalid label name
        if error.resp.status == 400 and 'Invalid label name' in str(error):
            logger.error("Please ensure the label name is valid and exists in your Gmail account.")
        raise
    except FileNotFoundError as e:
        logger.error(f"Missing required file: {e}")
        raise
    except Exception as e:
        logger.critical(f"An unexpected error occurred during label modification for ID {message_id}: {e}", exc_info=True)
        raise