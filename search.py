import os
import sqlite3
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

def create_db():
    conn = sqlite3.connect('drive_metadata.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            id TEXT PRIMARY KEY,
            name TEXT,
            mimeType TEXT,
            createdTime TEXT
        )
    ''')
    conn.commit()
    conn.close()

def retrieve_all_files():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("drive", "v3", credentials=creds)
        all_files = []
        page_token = None

        while True:
            response = service.files().list(
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, createdTime)",
                pageToken=page_token
            ).execute()
            items = response.get('files', [])
            all_files.extend(items)
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break
        
        return all_files

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def insert_metadata(file_list):
    conn = sqlite3.connect('drive_metadata.db')
    c = conn.cursor()
    for file in file_list:
        c.execute('''
            INSERT OR REPLACE INTO metadata (id, name, mimeType, createdTime)
            VALUES (?, ?, ?, ?)
        ''', (file['id'], file['name'], file['mimeType'], file['createdTime']))
    conn.commit()
    conn.close()

def search_metadata(query):
    conn = sqlite3.connect('drive_metadata.db')
    c = conn.cursor()
    c.execute("SELECT * FROM metadata WHERE name LIKE ?", ('%' + query + '%',))
    results = c.fetchall()
    conn.close()
    return results

# Create database and table
create_db()

# Retrieve all files from Google Drive
file_list = retrieve_all_files()

# Insert metadata into the database
insert_metadata(file_list)

# Example search
search_results = search_metadata('ping')
for result in search_results:
    print(f"File ID: {result[0]}, Name: {result[1]}, MIME Type: {result[2]}, Created Time: {result[3]}")
