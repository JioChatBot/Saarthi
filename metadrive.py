import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]

# Load Google Drive API credentials
credentials = service_account.Credentials.from_service_account_file(
    'service_account_credentials.json',
    scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)

def gdrive():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("drive", "v3", credentials=creds)

        # Call the Drive v3 API
        results = (
            service.files()
            .list(pageSize=10, fields="nextPageToken, files(id, name, mimeType, createdTime)")
            .execute()
        )
        items = results.get("files", [])

        if not items:
            return "No files found."
        files_list = []
        for item in items:
            files_list.append(item)
        
        return files_list

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def extract_metadata_from_drive(file):
    metadata = {
        "title": file.get('name', 'Unknown'),
        "date": file.get('createdTime', 'Unknown'),
        "mimeType": file.get('mimeType', 'Unknown'),
        "id": file.get('id', 'Unknown')
    }
    return metadata

def process_files(file_list):
    metadata_list = []
    for file_info in file_list:
        try:
            metadata = extract_metadata_from_drive(file_info)
            metadata_list.append({"file_id": file_info['id'], "metadata": metadata})
        except Exception as e:
            print(f"Error processing {file_info['name']}: {e}")
    return metadata_list

# Example usage with files from Google Drive
file_list = gdrive()

metadata_list = process_files(file_list)
for item in metadata_list:
    print(f"Metadata for file ID {item['file_id']}: {item['metadata']}")
