from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from concurrent.futures import ThreadPoolExecutor
import json
import os
from datetime import datetime, timedelta
import secrets
import uuid
import pytz
from bs4 import BeautifulSoup
from googletrans import Translator
import requests
import csv 
from features.sendemail import send_email_function

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Ensure database directories exist
os.makedirs('database/fanlink', exist_ok=True)
os.makedirs('database', exist_ok=True)

def load_json(filename, base_path='database/fanlink'):
    filepath = f'{base_path}/{filename}'
    if not os.path.exists(filepath):
        # Create empty file with valid JSON
        with open(filepath, 'w') as f:
            if base_path == 'database':
                json.dump([], f)  # Empty list for database/users.json
            else:
                json.dump({}, f)  # Empty dict for fanlink/users.json
        return [] if base_path == 'database' else {}
        
    with open(filepath, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # Handle invalid JSON by returning empty structure
            return [] if base_path == 'database' else {}

def save_json(data, filename, base_path='database/fanlink'):
    filepath = f'{base_path}/{filename}'
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

import json
from datetime import datetime
from pathlib import Path

def save_questionnaire_json(username, data):
    """
    Save questionnaire data to a JSON file with user details and questions/answers.
    Returns the path to the saved JSON file.
    """
    json_path = f'database/details/{username}.json'
    
    # Create the questionnaire structure
    questionnaire_data = {
        "user_id": str(hash(username + str(datetime.now()))),  # Simple unique ID generation
        "username": username,
        "email": data.get('email', ''),
        "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "questions": [
            {
                "id": "fan_duration",
                "question": "For how long have you been a fan of MLB?",
                "answer": data.get('fan_duration', '')
            },
            {
                "id": "favorite_teams",
                "question": "Name 5 teams you like",
                "answer": data.get('favorite_teams', [])
            },
            {
                "id": "favorite_players",
                "question": "Name 5 favorite players",
                "answer": data.get('favorite_players', [])
            },
            {
                "id": "selected_team",
                "question": "Which team do you want to select?",
                "answer": data.get('selected_team', '')
            },
            {
                "id": "favorite_match",
                "question": "Which match did you like the most?",
                "answer": data.get('favorite_match', '')
            },
            {
                "id": "notifications",
                "question": "Select notification frequency",
                "answer": data.get('notification_frequency', '')
            }
        ]
    }
    
    # Ensure directory exists
    Path('database/details').mkdir(parents=True, exist_ok=True)
    
    # Save to JSON file
    with open(json_path, 'w') as f:
        json.dump(questionnaire_data, f, indent=4)
    
    return json_path

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')

            if not all([username, email, password]):
                return jsonify({'success': False, 'error': 'All fields are required'}), 400

            fanlink_users = load_json('users.json', 'database/fanlink')
            database_users = load_json('users.json', 'database')

            if username in fanlink_users:
                return jsonify({'success': False, 'error': 'Username already exists'}), 400

            user_id = str(uuid.uuid4())
            fanlink_users[username] = {
                'user_id': user_id,
                'email': email,
                'password': password,
                'friends': [],
                'profile_pic': '/static/default.png'
            }

            database_user = {
                'user_id': user_id,
                'username': username,
                'email': email,
                'password': password,
                'signup_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            save_json(fanlink_users, 'users.json', 'database/fanlink')
            database_users.append(database_user)
            save_json(database_users, 'users.json', 'database')

            session['user_data'] = {
                'username': username,
                'email': email,
                'user_id': user_id
            }

            return jsonify({'success': True, 'redirect': '/questionnaire'})
        except Exception as e:
            print(f"Error during signup: {str(e)}")
            return jsonify({'success': False, 'error': 'An error occurred during signup'}), 500
            
            
@app.route('/questionnaire', methods=['GET', 'POST'])
def questionnaire():
    if request.method == 'GET':
        return render_template('questionnaire.html')

    if request.method == 'POST':
        try:
            user_data = session.get('user_data')
            if not user_data:
                return jsonify({'success': False, 'error': 'User not logged in'}), 403

            data = request.get_json()
            username = user_data['username']
            email = user_data['email']

            save_questionnaire_json(username, data)

            # Send a confirmation email after questionnaire completion
            subject = "Registration Successful"
            body = f"""
            Hi {username},
            
            Congratulations on successfully completing your registration process with us! 
            We are excited to have you onboard.
            
            Click the link below to visit our website:
            [Visit Our Website](https://yourwebsite.com)
            
            Best regards,
            The Team
            """
            send_email_function(email, subject, body)

            return jsonify({'success': True, 'redirect': '/login'})
        except Exception as e:
            print(f"Error during questionnaire: {str(e)}")
            return jsonify({'success': False, 'error': 'An error occurred'}), 500

            
            
@app.route('/profile')
def view_profile():
    # Check if user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        # Print debug information
        print("Current session username:", session['username'])
        
        # Load users from users.json to verify username
        users_path = 'database/users.json'
        print("Attempting to load users from:", users_path)
        
        with open(users_path, 'r') as f:
            users = json.load(f)
        
        # Get current username from session
        username = session['username']
        
        print("Username to search:", username)
        
        # Verify username exists in users database
        user_exists = any(user['username'] == username for user in users)
        if not user_exists:
            print(f"User {username} not found in users database")
            return "User not found", 404
        
        # Load user details from specific user's JSON file
        details_path = f'database/details/{username}.json'
        print("Attempting to load user details from:", details_path)
        
        with open(details_path, 'r') as f:
            user_details = json.load(f)
        
        
        # Helper function to get the email associated with a username
        def get_user_email(username):
            users_path = 'database/users.json'
            try:
                with open(users_path, 'r') as f:
                    users = json.load(f)

                for user in users:
                    if user['username'] == username:
                        return user['email']
            except FileNotFoundError:
                print(f"File {users_path} not found.")
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {users_path}.")
            return 'Email not found'
        
        # Prepare user data dictionary for template
        user_data = {
            'name': username,
            'email': get_user_email(f'{username}'),
            'fan_duration': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'fan_duration'), 'Not specified'),
            'favorite_teams': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'favorite_teams'), []),
            'favorite_players': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'favorite_players'), []),
            'selected_team': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'selected_team'), 'Not chosen'),
            'favorite_match': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'favorite_match'), 'Not specified'),
            'notification_frequency': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'notifications'), 'Not set'),
            'signup_date': next((user['signup_date'] for user in users if user['username'] == username), 'Unknown')
        }
        
        return render_template('profile.html', user=user_data)
    
    except FileNotFoundError as e:
        print(f"File not found error: {e}")
        return f"File not found: {e}", 404
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
        return f"Invalid JSON file: {e}", 500
    except Exception as e:
        print(f"Unexpected error loading profile: {e}")
        return f"An error occurred while loading profile: {e}", 500
    
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    details_path = f'database/details/{username}.json'
    users_path = 'database/users.json'

    if request.method == 'GET':
        try:
            with open(details_path, 'r') as f:
                user_details = json.load(f)
            
            # Get email from users.json
            with open(users_path, 'r') as f:
                users = json.load(f)
                email = next((user['email'] for user in users if user['username'] == username), '')

            edit_data = {
                'email': email,  # Use email from users.json
                'fan_duration': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'fan_duration'), ''),
                'favorite_teams': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'favorite_teams'), []),
                'favorite_players': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'favorite_players'), []),
                'selected_team': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'selected_team'), ''),
                'favorite_match': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'favorite_match'), ''),
                'notification_frequency': next((q['answer'] for q in user_details.get('questions', []) if q['id'] == 'notifications'), '')
            }

            return render_template('edit_profile.html', user=edit_data)

        except Exception as e:
            return f"Error loading edit profile: {e}", 500

    if request.method == 'POST':
        try:
            # Update details file
            with open(details_path, 'r') as f:
                user_details = json.load(f)

            # Get new email from the form
            new_email = request.form.get('email')
            if not new_email:
                return "Email is required", 400

            # Update questions in user details
            for question in user_details['questions']:
                if question['id'] == 'fan_duration':
                    question['answer'] = request.form.get('fan_duration', question['answer'])
                elif question['id'] == 'favorite_teams':
                    question['answer'] = request.form.getlist('favorite_teams')
                elif question['id'] == 'favorite_players':
                    question['answer'] = request.form.getlist('favorite_players')
                elif question['id'] == 'selected_team':
                    question['answer'] = request.form.get('selected_team', question['answer'])
                elif question['id'] == 'favorite_match':
                    question['answer'] = request.form.get('favorite_match', question['answer'])
                elif question['id'] == 'notifications':
                    question['answer'] = request.form.get('notification_frequency', question['answer'])

            # Save updated user details
            with open(details_path, 'w') as f:
                json.dump(user_details, f, indent=4)

            # Update email in users.json
            with open(users_path, 'r') as f:
                users = json.load(f)

            for user in users:
                if user['username'] == username:
                    user['email'] = new_email
                    break

            with open(users_path, 'w') as f:
                json.dump(users, f, indent=4)

            print(f"Email updated for {username} to {new_email}")

            return redirect(url_for('view_profile'))

        except Exception as e:
            print(f"Error updating profile: {e}")
            return f"Error updating profile: {e}", 500
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_json('users.json')
        username = request.form['username']
        password = request.form['password']
        
        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['user_id'] = users[username].get('id', 'default_user')
            print(f"username: {session['username']} user-id :{session['user_id']}")
            return redirect(url_for('index'))
        return "Invalid credentials"
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('login'))

@app.route('/Chat_dashboard')
def Chat_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))


    # Load all required data
    users = load_json('users.json')
    requests = load_json('friend_requests.json')
    groups = load_json('groups.json')
    
    # Get friend-related data
    pending_requests = [req for req in requests.get(session['username'], [])]
    friends = users[session['username']]['friends']
    
    # Process groups data
    my_groups = []
    available_groups = []
    
    for group_id, group_data in groups.items():
        group_info = {
            'id': group_id,
            'name': group_data['name'],
            'description': group_data['description'],
            'member_count': len(group_data['members']),
            'creator': group_data['creator'],
            'created_at': group_data['created_at']
        }
        
        if session['username'] in group_data['members']:
            # Add joined_at date if the user is not the creator
            if session['username'] != group_data['creator']:
                # In a real app, you'd store join dates. This is a simplification
                group_info['joined_at'] = group_data['created_at']
            my_groups.append(group_info)
        else:
            available_groups.append(group_info)
    
    # Sort groups by creation date (newest first)
    my_groups.sort(key=lambda x: x['created_at'], reverse=True)
    available_groups.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('dashboard.html',
                         pending_requests=pending_requests,
                         friends=friends,
                         my_groups=my_groups,
                         available_groups=available_groups)

@app.route('/search_users', methods=['GET'])
def search_users():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    query = request.args.get('query', '').lower()
    
    try:
        users = load_json('users.json')  # Load users data
        groups = load_json('groups.json')  # Load groups data

        # Filter users based on query
        filtered_users = [user for user in users if query in user.lower()]

        # Find groups matching the query
        matching_groups = []
        for group_id, group in groups.items():
            if query in group['name'].lower() or query in group['description'].lower():
                matching_groups.append({
                    'group_id': group_id,
                    'group_name': group['name'],
                    'description': group['description']
                })

        return jsonify({'users': filtered_users, 'groups': matching_groups})
    
    except Exception as e:
        print(f"Error searching users: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to search users'}), 500

@app.route('/send_request', methods=['POST'])
def send_request():
    if 'username' not in session:
        return jsonify({'success': False})
    
    to_user = request.form['to_user']
    requests = load_json('friend_requests.json')
    
    if to_user not in requests:
        requests[to_user] = []
    
    if session['username'] not in requests[to_user]:
        requests[to_user].append(session['username'])
        save_json(requests, 'friend_requests.json')
    
    return jsonify({'success': True})

@app.route('/accept_request', methods=['POST'])
def accept_request():
    if 'username' not in session:
        return jsonify({'success': False})
    
    from_user = request.form['from_user']
    requests = load_json('friend_requests.json')
    users = load_json('users.json')
    
    if from_user in requests.get(session['username'], []):
        requests[session['username']].remove(from_user)
        users[session['username']]['friends'].append(from_user)
        users[from_user]['friends'].append(session['username'])
        
        save_json(requests, 'friend_requests.json')
        save_json(users, 'users.json')
    
    return jsonify({'success': True})

@app.route('/chat/<friend>')
def chat(friend):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    users = load_json('users.json')
    if friend not in users[session['username']]['friends']:
        return "Not friends with this user"
    
    chats = load_json('chats.json')
    chat_id = '_'.join(sorted([session['username'], friend]))
    
    if chat_id not in chats:
        chats[chat_id] = []
    
    return render_template('chat.html', 
                         friend=friend, 
                         messages=chats[chat_id])


@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        friend = data.get('friend')
        message = data.get('message')
        
        if not friend or not message:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Load existing chats
        chats = load_json('chats.json')
        chat_id = '_'.join(sorted([session['username'], friend]))
        
        if chat_id not in chats:
            chats[chat_id] = []
        
        # Add new message
        new_message = {
            'from': session['username'],
            'message': message,
            'timestamp': datetime.now().strftime('%I:%M %p')  # 12-hour format with AM/PM
        }
        
        chats[chat_id].append(new_message)
        save_json(chats, 'chats.json')
        
        return jsonify({'success': True, 'message': new_message})
        
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to send message'}), 500

@app.route('/get_new_messages/<friend>')
def get_new_messages(friend):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        last_timestamp = request.args.get('last_timestamp')
        
        # Load chats
        chats = load_json('chats.json')
        chat_id = '_'.join(sorted([session['username'], friend]))
        
        if chat_id not in chats:
            return jsonify({'messages': []})
        
        # Get messages after last_timestamp
        new_messages = []
        for msg in chats[chat_id]:
            if not last_timestamp or msg['timestamp'] > last_timestamp:
                new_messages.append(msg)
        
        # Get typing status
        typing_status = load_json('typing_status.json')
        is_typing = typing_status.get(friend, {}).get(session['username'], False)
        
        return jsonify({
            'messages': new_messages,
            'typing_status': is_typing
        })
        
    except Exception as e:
        print(f"Error fetching messages: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to fetch messages'}), 500

@app.route('/typing_status', methods=['POST'])
def typing_status():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        friend = data.get('friend')
        status = data.get('status') == 'typing'
        
        # Load typing status
        typing_status = load_json('typing_status.json')
        
        if friend not in typing_status:
            typing_status[friend] = {}
            
        typing_status[friend][session['username']] = status
        save_json(typing_status, 'typing_status.json')
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error updating typing status: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to update typing status'}), 500


# New group-related routes
@app.route('/create_group', methods=['POST'])
def create_group():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        group_name = data.get('group_name')
        description = data.get('description', '')
        
        if not group_name:
            return jsonify({'success': False, 'error': 'Group name is required'}), 400
            
        groups = load_json('groups.json')
        
        # Generate unique group ID
        group_id = str(uuid.uuid4())
        
        # Create new group
        groups[group_id] = {
            'name': group_name,
            'description': description,
            'creator': session['username'],
            'members': [session['username']],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        save_json(groups, 'groups.json')
        
        # Initialize group chat
        chats = load_json('group_chats.json')
        chats[group_id] = []
        save_json(chats, 'group_chats.json')
        
        return jsonify({
            'success': True,
            'group_id': group_id,
            'message': 'Group created successfully'
        })
        
    except Exception as e:
        print(f"Error creating group: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to create group'}), 500

@app.route('/join_group/<group_id>', methods=['POST'])
def join_group(group_id):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        groups = load_json('groups.json')
        
        if group_id not in groups:
            return jsonify({'success': False, 'error': 'Group not found'}), 404
            
        if session['username'] in groups[group_id]['members']:
            return jsonify({'success': False, 'error': 'Already a member'}), 400
            
        # Add user to group
        groups[group_id]['members'].append(session['username'])
        save_json(groups, 'groups.json')
        
        # Add system message to group chat
        chats = load_json('group_chats.json')
        chats[group_id].append({
            'type': 'system',
            'message': f"{session['username']} joined the group",
            'timestamp': datetime.now().strftime('%I:%M %p')
        })
        save_json(chats, 'group_chats.json')
        
        return jsonify({'success': True, 'message': 'Joined group successfully'})
        
    except Exception as e:
        print(f"Error joining group: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to join group'}), 500

@app.route('/leave_group/<group_id>', methods=['POST'])
def leave_group(group_id):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        groups = load_json('groups.json')
        
        if group_id not in groups:
            return jsonify({'success': False, 'error': 'Group not found'}), 404
            
        if session['username'] not in groups[group_id]['members']:
            return jsonify({'success': False, 'error': 'Not a member'}), 400
            
        # Remove user from group
        groups[group_id]['members'].remove(session['username'])
        
        # If creator leaves and there are other members, assign new creator
        if session['username'] == groups[group_id]['creator'] and groups[group_id]['members']:
            groups[group_id]['creator'] = groups[group_id]['members'][0]
            
        # If no members left, delete group
        if not groups[group_id]['members']:
            del groups[group_id]
            chats = load_json('group_chats.json')
            if group_id in chats:
                del chats[group_id]
            save_json(chats, 'group_chats.json')
        else:
            # Add system message about user leaving
            chats = load_json('group_chats.json')
            chats[group_id].append({
                'type': 'system',
                'message': f"{session['username']} left the group",
                'timestamp': datetime.now().strftime('%I:%M %p')
            })
            save_json(chats, 'group_chats.json')
            
        save_json(groups, 'groups.json')
        
        return jsonify({'success': True, 'message': 'Left group successfully'})
        
    except Exception as e:
        print(f"Error leaving group: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to leave group'}), 500

@app.route('/group_chat/<group_id>')
def group_chat(group_id):
    if 'username' not in session:
        return redirect(url_for('login'))
        
    groups = load_json('groups.json')
    
    if group_id not in groups:
        return "Group not found", 404
        
    if session['username'] not in groups[group_id]['members']:
        return "Not a member of this group", 403
        
    chats = load_json('group_chats.json')
    group_messages = chats.get(group_id, [])
    
    return render_template('group_chat.html',
                         group=groups[group_id],
                         group_id=group_id,
                         messages=group_messages)

@app.route('/send_group_message', methods=['POST'])
def send_group_message():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        group_id = data.get('group_id')
        message = data.get('message')
        
        if not group_id or not message:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            
        groups = load_json('groups.json')
        
        if group_id not in groups:
            return jsonify({'success': False, 'error': 'Group not found'}), 404
            
        if session['username'] not in groups[group_id]['members']:
            return jsonify({'success': False, 'error': 'Not a member'}), 403
            
        # Add message to group chat
        chats = load_json('group_chats.json')
        new_message = {
            'type': 'message',
            'from': session['username'],
            'message': message,
            'timestamp': datetime.now().strftime('%I:%M %p')
        }
        
        chats[group_id].append(new_message)
        save_json(chats, 'group_chats.json')
        
        return jsonify({'success': True, 'message': new_message})
        
    except Exception as e:
        print(f"Error sending group message: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to send message'}), 500





def fetch_latest_news():
    url = "https://www.mlb.com/news/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('article', class_='article-item', limit=4)
    news_list = []
    
    for article in articles:
        title = article.find('h1', class_='article-item__headline').get_text(strip=True)
       
        news_list.append({
            'title': title,
            'link': "https://www.mlb.com/news/"
        })
    
    return news_list

def get_schedule():
    season = 2025
    url = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={season}'
    try:
        response = requests.get(url)
        data = response.json()
        games = []

        if 'dates' in data:
            for date in data['dates']:
                for game in date.get('games', []):
                    games.append({
                        'gamePk': game.get('gamePk'),
                        'gameDate': game.get('gameDate'),
                        'status': game.get('status', {}).get('abstractGameState'),
                        'homeTeam': game.get('teams', {}).get('home', {}).get('team', {}).get('name'),
                        'awayTeam': game.get('teams', {}).get('away', {}).get('team', {}).get('name'),
                        'venue': game.get('venue', {}).get('name'),
                        'homeScore': game.get('teams', {}).get('home', {}).get('score', 0),
                        'awayScore': game.get('teams', {}).get('away', {}).get('score', 0)
                    })

        games.sort(key=lambda x: x['gameDate'])
        upcoming_games = [g for g in games if g['status'] == 'Preview'][:4]  # Show 4 upcoming games
        return upcoming_games
    except:
        return []

# Load team mapping
with open('dataset/team.json', 'r') as f:
    team_mapping = json.load(f)

def get_team_logo(team_id):
    return f'https://www.mlbstatic.com/team-logos/{team_id}.svg'

@app.route('/save_team_data', methods=['POST'])
def save_team_data():
    data = request.json
    
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
    user_name = session['username']
    file_path = 'database/user_teams/user_team_data.json'
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        with open(file_path, 'r') as f:
            all_data = json.load(f)
            # Convert list to dict if necessary
            if isinstance(all_data, list):
                all_data = {}
    except (FileNotFoundError, json.JSONDecodeError):
        all_data = {}

    team_name = list(data['user_team'].keys())[0]
    new_players = data['user_team'][team_name]['selected_players']

    # Initialize user and team data
    if user_name not in all_data:
        all_data[user_name] = {}
    if team_name not in all_data[user_name]:
        all_data[user_name][team_name] = {"selected_players": []}

    # Track existing players
    existing_player_ids = {
        player['id'] 
        for player in all_data[user_name][team_name]['selected_players']
    }

    # Add new players
    for player in new_players:
        if player['id'] not in existing_player_ids:
            all_data[user_name][team_name]['selected_players'].append(player)
            existing_player_ids.add(player['id'])

    # Save the updated data
    with open(file_path, 'w') as f:
        json.dump(all_data, f, indent=4)

    return jsonify({'success': True, 'message': 'Team data saved successfully'})

@app.route('/check_session')
def check_session():
    return jsonify({
        'user_data': session.get('user_data'),
        'session_keys': list(session.keys())
    })


@app.route('/team_players', methods=['GET', 'POST'])
def team_players():
    team_id = request.args.get('team_id') or session.get('team_id')
    if not team_id:
        team_id = 119  # Default to Dodgers

    session['team_id'] = team_id

    status_filter = request.args.get('status', 'All')
    role_filters = request.args.getlist('roles')  # Get multiple roles

    # Fetch the team roster
    team_roster_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?season=2024"
    response = requests.get(team_roster_url)
    roster_data = response.json()

    # Fetch player details concurrently
    def fetch_player_details(player):
        player_id = player["person"]["id"]
        player_name = player["person"]["fullName"]
        player_position = player["position"]["name"]
        player_status = player["status"]["description"]
        player_jersey = player.get("jerseyNumber", "N/A")
        player_response = requests.get(f"https://statsapi.mlb.com/api/v1/people/{player_id}")
        player_details = player_response.json()["people"][0]
        return {
            "id": player_id,
            "name": player_name,
            "position": player_position,
            "type": player["position"].get("type", "N/A"),
            "status": player_status,
            "jersey_number": player_jersey,
            "dob": player_details["birthDate"],
            "height": player_details["height"],
            "weight": player_details["weight"],
            "bat_side": player_details["batSide"]["description"],
            "pitch_side": player_details["pitchHand"]["description"],
            "strike_zone_top": player_details.get("strikeZoneTop", "N/A"),
            "strike_zone_bottom": player_details.get("strikeZoneBottom", "N/A"),
            "headshot_url": f'https://securea.mlb.com/mlb/images/players/head_shot/{player_id}.jpg'
        }

    with ThreadPoolExecutor() as executor:
        players_info = list(executor.map(fetch_player_details, roster_data["roster"]))

    # Filter players
    if status_filter != 'All':
        players_info = [p for p in players_info if p["status"] == status_filter]
    if role_filters:
        players_info = [p for p in players_info if p["position"] in role_filters]

    team_logo = get_team_logo(team_id)

    # Save only player names
    selected_player_names = []
    if 'user_id' in session:
        team_file = os.path.join('details/user_teams', f'{session["user_id"]}_selected_team.json')
        if os.path.exists(team_file):
            with open(team_file, 'r') as f:
                saved_team = json.load(f)
                # Map saved player names instead of full player details
                selected_player_names = saved_team.get('player_names', [])

    # Save the selected player names
    if request.method == 'POST':
        selected_players = request.form.getlist('selected_players')  # Expect player names from frontend
        team_file = os.path.join('details/user_teams', f'{session["user_id"]}_selected_team.json')
        with open(team_file, 'w') as f:
            json.dump({"player_names": selected_players}, f)

    return render_template(
        'players.html',
        players=players_info,
        team_logo=team_logo,
        team_mapping=team_mapping,
        selected_team=int(team_id),
        selected_status=status_filter,
        selected_roles=role_filters,
        selected_players=selected_player_names,
        selected_players_count=len(selected_player_names)
    )

def load_user_team_data():
    with open('database/user_teams/user_team_data.json', 'r') as file:
        return json.load(file)
    
@app.route('/my_team', methods=['GET', 'POST'])
def myteam():
    user_data = load_user_team_data()
    user_name = session['username']
    
    # Get all teams for the user
    user_teams = user_data[user_name]
    
    # Prepare a list of team names
    team_names = list(user_teams.keys())

    # Prepare a dictionary of players for each team
    teams_players = {}
    for team_name, team_data in user_teams.items():
        players = []
        for player in team_data['selected_players']:
            players.append({
                'name': player['name'],
                'position': player['position'],
                'headshot_url': player['headshot_url']
            })
        teams_players[team_name] = players
    
    return render_template('test.html', team_names=team_names, teams_players=teams_players)

@app.route('/get_position_headshots/<team_name>/<position>')
def get_position_headshots(team_name, position):
    user_data = load_user_team_data()
    user_name = session['username']
    
    # Get the specific team data
    team_data = user_data[user_name][team_name]
    
    # Filter players by position and get their headshot URLs
    position_headshots = []
    for player in team_data['selected_players']:
        if player['position'].upper() == position.upper():
            position_headshots.append({
                'name': player['name'],
                'headshot_url': player['headshot_url']
            })
    
    return jsonify({
        'team_name': team_name,
        'position': position,
        'players': position_headshots
    })

# @app.route('/my_team', methods=['GET', 'POST'])
# def myteam():
#     # Load user team data
#     user_data = load_user_team_data()
#     user_name = session['username']
    
#     # Get all teams for the user
#     user_teams = user_data[user_name]
    
#     # Prepare a dictionary of players for each position
#     position_players = {
#         'Baseman': [],
#         'Two-Way Man': [],
#         'Hitter': [],
#         'Pitcher': [],
#         'Catcher': [],
#         'Shortstop': [],
#         'First Base': [],
#         'Second Base': [],
#         'Third Base': [],
#         'Outfielder': []  # Catch-all for all outfielders (Left, Right, Center)
#     }
    
#     # Classify players into their respective positions
#     for team_name, team_data in user_teams.items():
#         for player in team_data['selected_players']:
#             position = player['position']
            
#             # Handle outfielders separately and assign them to 'Outfielder'
#             if position in ['Left Field', 'Right Field', 'Center Field']:
#                 position = 'Outfielder'  # Assign outfield positions to the 'Outfielder' group

#             if position in position_players:
#                 position_players[position].append({
#                     'name': player['name'],
#                     'position': position,
#                     'headshot_url': player['headshot_url']
#                 })
    
#     # Handle special conditions:
#     # 1. If there are more than 3 basemen (1st Base, 2nd Base, 3rd Base, etc.), set one as Hitter.
#     if len(position_players['First Base']) + len(position_players['Second Base']) + len(position_players['Third Base']) > 3:
#         # Move one Baseman to Hitter position (if there's a sufficient number of Basemen)
#         if position_players['Baseman']:
#             position_players['Hitter'].append(position_players['Baseman'].pop())

#     # 2. If there are any 2-Way players, set one as Pitcher and the rest as Hitter
#     if position_players['Two-Way Player']:
#         # Move the 2-Way player to Pitcher if possible
#         position_players['Pitcher'].append(position_players['Two-Way Player'].pop())

#     # Prepare a list of team names
#     team_names = list(user_teams.keys())
    
#     return render_template('my_team.html', team_names=team_names, position_players=position_players)

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    lang = request.args.get('lang', 'en')
    upcoming_games = get_schedule()
    news = fetch_latest_news()
    
    # Translate content if language is not English
    
    return render_template('home.html',
                         upcoming_games=upcoming_games,
                         news=news,
                         lang=lang,
    )

if __name__ == '__main__':
    app.run(debug=True)