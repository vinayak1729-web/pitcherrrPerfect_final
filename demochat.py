from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import uuid
import hashlib
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app)

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Create necessary directories
for directory in ['uploads/images', 'uploads/documents', 'database']:
    os.makedirs(directory, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database files
DB_FILES = {
    'users': 'database/users.json',
    'messages': 'database/messages.json',
    'groups': 'database/groups.json',
    'notifications': 'database/notifications.json',
    'chats': 'database/chats.json'
}

def init_db():
    """Initialize all database files"""
    for file_path in DB_FILES.values():
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump([], f)

def load_db(db_name):
    """Load database by name"""
    with open(DB_FILES[db_name], 'r') as f:
        return json.load(f)

def save_db(data, db_name):
    """Save database by name"""
    with open(DB_FILES[db_name], 'w') as f:
        json.dump(data, f, indent=4)

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """Decorator for routes that require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Authentication routes
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    users = load_db('users')
    
    # Validate required fields
    required_fields = ['username', 'email', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    # Check if username or email already exists
    if any(u['username'] == data['username'] for u in users):
        return jsonify({'success': False, 'message': 'Username already exists'})
    if any(u['email'] == data['email'] for u in users):
        return jsonify({'success': False, 'message': 'Email already exists'})
    
    # Create new user
    new_user = {
        'id': str(uuid.uuid4()),
        'username': data['username'],
        'email': data['email'],
        'password': hash_password(data['password']),
        'profile_photo': None,
        'created_at': datetime.now().isoformat(),
        'last_seen': datetime.now().isoformat()
    }
    
    users.append(new_user)
    save_db(users, 'users')
    
    return jsonify({'success': True, 'message': 'Registration successful'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    users = load_db('users')
    
    # Find user by username and check password
    user = next((u for u in users if u['username'] == data['username'] and 
                 u['password'] == hash_password(data['password'])), None)
    
    if not user:
        return jsonify({'success': False, 'message': 'Invalid credentials'})
    
    # Update last seen
    user_idx = next(i for i, u in enumerate(users) if u['id'] == user['id'])
    users[user_idx]['last_seen'] = datetime.now().isoformat()
    save_db(users, 'users')
    
    # Set session
    session['user_id'] = user['id']
    session['username'] = user['username']
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'profile_photo': user['profile_photo']
        }
    })

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

# Profile routes
@app.route('/profile', methods=['GET', 'PUT'])
@login_required
def profile():
    users = load_db('users')
    user = next((u for u in users if u['id'] == session['user_id']), None)
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'profile': {
                'username': user['username'],
                'email': user['email'],
                'profile_photo': user['profile_photo'],
                'created_at': user['created_at']
            }
        })
    
    # Handle profile update
    data = request.get_json()
    user_idx = next(i for i, u in enumerate(users) if u['id'] == session['user_id'])
    
    # Update allowed fields
    for field in ['email']:
        if field in data:
            users[user_idx][field] = data[field]
    
    save_db(users, 'users')
    return jsonify({'success': True, 'message': 'Profile updated successfully'})

# Chat routes
@app.route('/chat/start', methods=['POST'])
@login_required
def start_chat():
    data = request.get_json()
    recipient_id = data.get('recipient_id')
    
    chats = load_db('chats')
    
    # Check if chat already exists
    existing_chat = next((c for c in chats if sorted([c['user1_id'], c['user2_id']]) == 
                         sorted([session['user_id'], recipient_id])), None)
    
    if existing_chat:
        return jsonify({'success': True, 'chat_id': existing_chat['id']})
    
    # Create new chat
    new_chat = {
        'id': str(uuid.uuid4()),
        'user1_id': session['user_id'],
        'user2_id': recipient_id,
        'created_at': datetime.now().isoformat(),
        'last_message': None
    }
    
    chats.append(new_chat)
    save_db(chats, 'chats')
    
    return jsonify({'success': True, 'chat_id': new_chat['id']})

@app.route('/chat/<chat_id>/messages')
@login_required
def get_chat_messages(chat_id):
    messages = load_db('messages')
    chat_messages = [m for m in messages if m['chat_id'] == chat_id]
    
    return jsonify({
        'success': True,
        'messages': sorted(chat_messages, key=lambda x: x['created_at'])
    })

# WebSocket events
@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        join_room(session['user_id'])

@socketio.on('send_message')
def handle_message(data):
    if 'user_id' not in session:
        return
    
    messages = load_db('messages')
    chats = load_db('chats')
    
    # Create new message
    new_message = {
        'id': str(uuid.uuid4()),
        'chat_id': data['chat_id'],
        'sender_id': session['user_id'],
        'content': data['content'],
        'type': data['type'],  # 'text', 'image', or 'file'
        'file_url': data.get('file_url'),
        'created_at': datetime.now().isoformat()
    }
    
    messages.append(new_message)
    save_db(messages, 'messages')
    
    # Update chat's last message
    chat_idx = next(i for i, c in enumerate(chats) if c['id'] == data['chat_id'])
    chats[chat_idx]['last_message'] = new_message
    save_db(chats, 'chats')
    
    # Get recipient ID
    chat = chats[chat_idx]
    recipient_id = chat['user2_id'] if chat['user1_id'] == session['user_id'] else chat['user1_id']
    
    # Emit message to recipient
    emit('new_message', new_message, room=recipient_id)

@socketio.on('typing')
def handle_typing(data):
    chats = load_db('chats')
    chat = next((c for c in chats if c['id'] == data['chat_id']), None)
    
    if chat:
        recipient_id = chat['user2_id'] if chat['user1_id'] == session['user_id'] else chat['user1_id']
        emit('user_typing', {
            'chat_id': data['chat_id'],
            'username': session['username']
        }, room=recipient_id)

# File upload routes
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'File type not allowed'})
    
    # Generate unique filename
    filename = secure_filename(f"{session['user_id']}_{datetime.now().timestamp()}_{file.filename}")
    file_type = filename.rsplit('.', 1)[1].lower()
    
    # Determine subdirectory based on file type
    subdirectory = 'images' if file_type in {'png', 'jpg', 'jpeg', 'gif'} else 'documents'
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], subdirectory, filename)
    
    try:
        file.save(file_path)
        return jsonify({
            'success': True,
            'file_url': f'/uploads/{subdirectory}/{filename}',
            'file_type': subdirectory
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True)