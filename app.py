from flask import Flask, render_template, request, redirect, url_for, session, jsonify
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
def save_questionnaire_csv(username, data):
    csv_path = f'database/details/{username}.csv'
    questions = [
        ['Question', 'Text', 'Answer'],
        ['Fan Duration', 'For how long have you been a fan of MLB?', data.get('fan_duration', '')],
        ['Favorite Teams', 'Name 5 teams you like', ','.join(data.get('favorite_teams', []))],
        ['Favorite Players', 'Name 5 favorite players', ','.join(data.get('favorite_players', []))],
        ['Selected Team', 'Which team do you want to select?', data.get('selected_team', '')],
        ['Favorite Match', 'Which match did you like the most?', data.get('favorite_match', '')],
        ['Notifications', 'Select notification frequency', data.get('notification_frequency', '')]
    ]
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(questions)
    
    return csv_path
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    if request.method == 'POST':
        try:
            # Get JSON data from request
            data = request.get_json()
            
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            
            # Validate required fields
            if not all([username, email, password]):
                return jsonify({
                    'success': False,
                    'error': 'All fields are required'
                }), 400
            
            # Load existing users from both directories
            fanlink_users = load_json('users.json', 'database/fanlink')
            database_users = load_json('users.json', 'database')
            
            if not isinstance(database_users, list):
                database_users = []
            
            # Check if username already exists in fanlink
            if username in fanlink_users:
                return jsonify({
                    'success': False,
                    'error': 'Username already exists'
                }), 400
            
            # Create new user data for fanlink/users.json
            fanlink_users[username] = {
                'email': email,
                'password': password,  # In production, this should be hashed
                'friends': [],
                'profile_pic': '/static/default.png'
            }
            
            # Create new user data for database/users.json
            database_user = {
                'username': username,
                'email': email,
                'password': password,
                'signup_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'questionnaire_file': save_questionnaire_csv(username, data),

            }
            
            # Save to both locations
            save_json(fanlink_users, 'users.json', 'database/fanlink')
            database_users.append(database_user)
            save_json(database_users, 'users.json', 'database')
            
            # Initialize session data for questionnaire
            session['user_data'] = {
                'username': username,
                'email': email,
                'password': password
            }
            
            return jsonify({
                'success': True,
                'message': 'Signup successful'
            })
            
        except Exception as e:
            print(f"Error during signup: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'An error occurred during signup'
            }), 500
        
def get_user_profile(username):
    # Get basic info from users.json
    with open('database/users.json', 'r') as f:
        users = json.load(f)
        user_data = next((user for user in users if user['username'] == username), None)
    
    # Get detailed info from CSV
    csv_path = f'database/details/{username}.csv'
    questionnaire_data = {}
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                questionnaire_data[row['Question']] = row['Answer']
    except FileNotFoundError:
        questionnaire_data = {}
    
    # Combine all data
    profile_data = {
        'name': user_data['username'],
        'email': user_data['email'],
        'signup_date': user_data['signup_date'],
        'fan_duration': questionnaire_data.get('Fan Duration', ''),
        'favorite_team': questionnaire_data.get('Selected Team', ''),
        'notification_frequency': questionnaire_data.get('Notifications', '')
    }
    
    return profile_data

def update_user_profile(username, updated_data):
    # Update users.json
    with open('database/users.json', 'r+') as f:
        users = json.load(f)
        user_index = next((index for (index, user) in enumerate(users) 
                          if user['username'] == username), None)
        if user_index is not None:
            users[user_index].update({
                'email': updated_data.get('email', users[user_index]['email'])
            })
        f.seek(0)
        json.dump(users, f, indent=4)
        f.truncate()
    
    # Update CSV
    csv_path = f'database/details/{username}.csv'
    rows = []
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
    for row in rows:
        if row[0] == 'Fan Duration':
            row[2] = updated_data.get('fan_duration', row[2])
        elif row[0] == 'Selected Team':
            row[2] = updated_data.get('favorite_team', row[2])
        elif row[0] == 'Notifications':
            row[2] = updated_data.get('notification_frequency', row[2])
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

@app.route('/profile')
def view_profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user_data = get_user_profile(session['username'])
    return render_template('profile.html', user=user_data)

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        updated_data = {
            'email': request.form.get('email'),
            'fan_duration': request.form.get('fan_duration'),
            'favorite_teams': [team.strip() for team in request.form.get('favorite_teams', '').split(',') if team.strip()],
            'favorite_players': [player.strip() for player in request.form.get('favorite_players', '').split(',') if player.strip()],
            'selected_team': request.form.get('selected_team'),
            'favorite_match': request.form.get('favorite_match'),
            'notification_frequency': request.form.get('notification_frequency')
        }
        
        update_user_profile(session['username'], updated_data)
        return redirect(url_for('view_profile'))
    
    user_data = get_user_profile(session['username'])
    return render_template('edit_profile.html', user=user_data)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_json('users.json')
        username = request.form['username']
        password = request.form['password']
        
        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('index'))
        return "Invalid credentials"
    
    return render_template('login.html')

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