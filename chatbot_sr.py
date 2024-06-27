import os
import re
import spacy
import sqlite3
import pyttsx3
from fuzzywuzzy import fuzz, process
from flask import Flask, render_template
from flask_socketio import SocketIO, send
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError
from spellchecker import SpellChecker
import speech_recognition as sr

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
nlp = spacy.load('en_core_web_sm')

# Patterns to look for in the user's query using regex
PATTERNS = [
    r'search files named (.+)',
    r'search for file named (.+)',
    r'find file named (.+)',
    r'look for file named (.+)',
    r'search files called (.+)',
    r'search for file called (.+)',
    r'find file called (.+)',
    r'look for file called (.+)',
    r'search files',
    r'search for file',
    r'find file',
    r'look for file',
    r'hello',
    r'hi',
    r'hey',
    r'bye',
    r'goodbye',
    r'what is your name',
    r'what do you do',
    r'how are you',
    r'thank you',
    r'thanks',
    r'help',
]

def chatbot_response(message):
    print("Inside chatbot_response function")
    print("Received message:", message)

    doc = nlp(message.lower())

    if re.search(r'hello|hi|hey', message, re.IGNORECASE):
        return 'Hello! Welcome to Jio Networking Academy. How can I help you?'
    elif re.search(r'bye|goodbye', message, re.IGNORECASE):
        return 'Goodbye! Have a great day!'
    elif re.search(r'what is your name', message, re.IGNORECASE):
        return 'I am Saarthi.'
    elif re.search(r'what do you do', message, re.IGNORECASE):
        return 'I am a search engine chatbot.'
    elif re.search(r'how are you', message, re.IGNORECASE):
        return 'I am just a bot, but I am here to help you!'
    elif re.search(r'thank you|thanks', message, re.IGNORECASE):
        return 'You\'re welcome!'
    elif re.search(r'help', message, re.IGNORECASE):
        return 'How can I assist you today?'
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
    elif re.search(r'extract metadata', message, re.IGNORECASE):
        file_list = metadrive()
        metadata_list = process_files(file_list)
        response_lines = [
            f"Metadata for file ID {item['file_id']}:\nTitle: {item['metadata']['title']}\nDate: {item['metadata']['date']}\nMIME Type: {item['metadata']['mimeType']}"
            for item in metadata_list
        ]
        return '\n\n'.join(response_lines)
    elif any(re.search(pattern, message, re.IGNORECASE) for pattern in PATTERNS):
        print("Calling extract_query function")
        query = extract_query(message)
        print("Received query from extract_query function:", query)
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

spell = SpellChecker()

def extract_query(message):
    print("Inside extract_query function")
    print("Received message:", message)
    
    # Use fuzzy matching to find the closest pattern
    matched_pattern, confidence = process.extractOne(message.lower(), PATTERNS, scorer=fuzz.partial_ratio)
    if confidence > 70:  # Adjust the confidence threshold as needed
        return message.lower().split(matched_pattern, 1)[1].strip()

    # Fuzzy match with existing file names
    file_names = [file['name'].lower() for file in file_list]
    query = process.extractOne(message.lower(), file_names)[0]
    
    # Spell check the query
    corrected_query = spell.correction(query)
    print("Original query:", query)
    print("Corrected query:", corrected_query)
    
    # If the corrected query differs significantly from the original query, return the corrected one
    if fuzz.ratio(query, corrected_query) < 90:
        return corrected_query
    else:
        return query

# Ensure database search is effective
def search_metadata(query):
    conn = sqlite3.connect('drive_metadata.db')
    c = conn.cursor()
    c.execute("SELECT * FROM metadata WHERE name LIKE ?", ('%' + query + '%',))
    results = c.fetchall()
    conn.close()
    return results

def gdrive():
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

@socketio.on('message')
def handleMessage(msg):
    print(f'Message: {msg}')
    response = chatbot_response(msg)
    send(response, broadcast=True)

@app.route('/')
def index():
    return render_template('app.html')

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)

# Initialize the recognizer 
r = sr.Recognizer() 

# Function to convert text to speech
def SpeakText(command):
    # Initialize the engine
    engine = pyttsx3.init()
    engine.say(command) 
    engine.runAndWait()

# Function to process speech input
def process_speech():
    while True: 
        try:
            # use the microphone as source for input.
            with sr.Microphone() as source2:
                # wait for a second to let the recognizer
                # adjust the energy threshold based on
                # the surrounding noise level 
                r.adjust_for_ambient_noise(source2, duration=0.2)
                
                # listens for the user's input 
                audio2 = r.listen(source2)
                
                # Using google to recognize audio
                MyText = r.recognize_google(audio2)
                MyText = MyText.lower()

                print("Did you say:", MyText)
                SpeakText(MyText)
                
                # Send the recognized text to the chatbot
                response = chatbot_response(MyText)
                SpeakText(response)
                
        except sr.RequestError as e:
            print("Could not request results; {0}".format(e))
            
        except sr.UnknownValueError:
            print("unknown error occurred")

# Run the speech processing in a separate thread to not block the main app
import threading
speech_thread = threading.Thread(target=process_speech)
speech_thread.start()
