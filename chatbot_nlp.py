import os
import json
import sqlite3
import spacy
from fuzzywuzzy import fuzz, process
from flask import Flask, render_template
from flask_socketio import SocketIO, send
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError

app = Flask(__name__)
socketio = SocketIO(app)
SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]

# Load Google Drive API credentials
credentials = service_account.Credentials.from_service_account_file(
    'service_account_credentials.json',
    scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handleMessage(msg):
    print(f'Message: {msg}')
    response = chatbot_response(msg)
    send(response, broadcast=True)

def gdrive():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("drive", "v3", credentials=creds)
        results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get("files", [])

        if not items:
            return "No files found."
        files_list = [item['name'] for item in items]
        return files_list

    except HttpError as error:
        print(f"An error occurred: {error}")

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

def metadrive():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("drive", "v3", credentials=creds)
        results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name, mimeType, createdTime)").execute()
        items = results.get("files", [])

        if not items:
            return "No files found."
        return items

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

# Create database and table
create_db()

# Retrieve all files from Google Drive
file_list = metadrive()

# Insert metadata into the database
insert_metadata(file_list)

# Patterns to look for in the user's query
PATTERNS = [
    'search files named',
    'search for file named',
    'find file named',
    'look for file named',
    'search files called',
    'search for file called',
    'find file called',
    'look for file called',
    'search files',
    'search for file',
    'find file',
    'look for file'
]

def chatbot_response(message):
    doc = nlp(message.lower())
    
    if 'hello' in message.lower():
        return 'Hello! Welcome to Jio Networking Academy. How can I help you?'
    elif 'bye' in message.lower():
        return 'Goodbye! Have a great day!'
    elif 'what is your name?' in message.lower():
        return 'I am Jio ChatBot.'
    elif 'what do you do?' in message.lower():
        return 'I am a search engine chatbot.'
    elif any(token.lemma_ == 'list' and token.nbor().lemma_ == 'file' for token in doc):
        files = metadrive()
        if isinstance(files, str):
            return files
        response_lines = [
            f"<a href='https://drive.google.com/file/d/{file['id']}/view' target='_blank' class='file-block list-files'>"
            f"{file['name']}"
            f"</a>"
            for file in files
        ]
        return '\n\n'.join(response_lines)
    elif 'extract metadata' in message.lower():
        file_list = metadrive()
        metadata_list = process_files(file_list)
        response_lines = [
            f"Metadata for file ID {item['file_id']}:\nTitle: {item['metadata']['title']}\nDate: {item['metadata']['date']}\nMIME Type: {item['metadata']['mimeType']}"
            for item in metadata_list
        ]
        return '\n\n'.join(response_lines)
    elif any(token.lemma_ == 'search' and token.nbor().lemma_ == 'file' for token in doc) or 'search for file' in message.lower() or 'find file' in message.lower() or 'look for file' in message.lower():
        query = extract_query(message)
        if not query:
            return "Please provide a search term."
        search_results = search_metadata(query)
        if not search_results:
            return "No matching files found."
        response_lines = [
            f"<a href='https://drive.google.com/file/d/{result[0]}/view' target='_blank' class='file-block list-files'>"
            f"{result[1]}"
            f"</a>"
            for result in search_results
        ]
        return '\n\n'.join(response_lines)
    else:
        return 'Sorry, I did not understand that.'

def extract_query(message):
    # Use fuzzy matching to find the closest pattern
    pattern, confidence = process.extractOne(message.lower(), PATTERNS, scorer=fuzz.partial_ratio)
    if confidence > 70:  # Adjust the confidence threshold as needed
        return message.lower().split(pattern, 1)[1].strip()

    # Fallback: Look for any named entities that could be a file name
    doc = nlp(message.lower())
    for ent in doc.ents:
        if ent.label_ in {"ORG", "PRODUCT", "WORK_OF_ART"}:
            return ent.text.strip()

    return None

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
