import click
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
import json

# Path to the user token
TOKEN_PATH = os.path.expanduser('~/.config/gworkspace-access/user_token.json')

def get_credentials():
    """Gets user credentials from the stored token."""
    if not os.path.exists(TOKEN_PATH):
        raise click.ClickException("User token not found. Please run 'gwsa setup' first.")
    
    with open(TOKEN_PATH, 'r') as token:
        creds_data = json.load(token)
    
    # The stored token might not have the 'client_id', 'client_secret', 'scopes', etc.
    # The Credentials object can be created from the access token, refresh token, and token_uri
    creds = Credentials(
        token=creds_data.get('token'),
        refresh_token=creds_data.get('refresh_token'),
        token_uri=creds_data.get('token_uri'),
        client_id=creds_data.get('client_id'),
        client_secret=creds_data.get('client_secret'),
        scopes=creds_data.get('scopes')
    )
    return creds

@click.group()
def sheets():
    """Commands for interacting with Google Sheets."""
    pass

@sheets.command('list')
def list_sheets():
    """Lists the user's Google Sheets."""
    creds = get_credentials()
    drive_service = build('drive', 'v3', credentials=creds)
    
    try:
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.spreadsheet'",
            fields="files(id, name)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            click.echo("No Google Sheets found.")
        else:
            click.echo("Google Sheets:")
            for item in items:
                click.echo(f"- {item['name']} (ID: {item['id']})")

    except Exception as e:
        raise click.ClickException(f"An error occurred: {e}")

@sheets.command('read')
@click.argument('spreadsheet_id')
@click.argument('range_name')
def read_sheet(spreadsheet_id, range_name):
    """Reads data from a specific sheet and range."""
    creds = get_credentials()
    sheets_service = build('sheets', 'v4', credentials=creds)
    
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            click.echo(f"No data found in range '{range_name}'.")
        else:
            for row in values:
                click.echo('\t'.join(map(str, row)))

    except Exception as e:
        raise click.ClickException(f"An error occurred: {e}")

@sheets.command('update-cell')
@click.argument('spreadsheet_id')
@click.argument('range_name')
@click.argument('value')
def update_cell(spreadsheet_id, range_name, value):
    """Updates a specific cell with a new value."""
    creds = get_credentials()
    sheets_service = build('sheets', 'v4', credentials=creds)
    
    try:
        body = {
            'values': [[value]]
        }
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        click.echo(f"Cell '{range_name}' updated successfully.")

    except Exception as e:
        raise click.ClickException(f"An error occurred: {e}")

if __name__ == '__main__':
    sheets()
