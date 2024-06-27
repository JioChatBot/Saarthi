from flask import Flask, render_template, request
from flask_socketio import SocketIO, send

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('chat.html')

@socketio.on('message')
def handleMessage(msg):
    print(f'Message: {msg}')
    response = chatbot_response(msg)
    send(response, broadcast=True)

def chatbot_response(message):
    # Simple logic for chatbot response
    if 'hello' in message.lower():
        return 'Hello! Welcome to JIO. How can I help you?'
    elif 'bye' in message.lower():
        return 'Goodbye! Have a great day!'
    elif 'what is your name?' in message.lower():
        return 'I am Jio ChatBot.'
    elif 'what do you do?' in message.lower():
        return 'I am a search engine chatbot.'
    else:
        return 'Sorry, I did not understand that.'

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
