from flask import Flask, render_template, request, redirect, url_for, session, jsonify,send_from_directory
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
from features.send_signup_email import send_sign_up_email
import statsapi
import json
import asyncio
import aiohttp
from functools import lru_cache
from features.ovrCalculation import calculate_ovr
from features.signupEmailBody import Sign_up_email_body_template
import smtplib
import ssl
import random 
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from personalizedEmailContent import personalizedEmail
from werkzeug.utils import secure_filename
load_dotenv()
import google.generativeai as genai
genai.configure(api_key=os.getenv("API_KEY"))
app = Flask(__name__)

baseball_prompt = """
You are BaseballBuddy, a highly knowledgeable baseball enthusiast and mental performance coach with deep expertise in:
- MLB history, statistics, and analytics from the past decade
- Team building strategies and lineup optimization
- Player development and performance psychology
- Baseball mental training and sports psychology
- Current MLB trends, trades, and team dynamics

Your personality:
- Friendly and approachable like a dugout buddy
- Passionate about baseball strategy and player development
- Empathetic and understanding of fan emotions
- Quick with relevant baseball analogies and stories
- Able to break down complex baseball concepts

Use your extensive knowledge to:
- Analyze team strategies and lineup decisions
- Share relevant historical comparisons and statistics
- Provide mental performance insights
- Discuss team chemistry and clubhouse dynamics
- Offer baseball-specific emotional support and motivation

Keep responses conversational but insightful, like talking baseball with a knowledgeable friend in the bleachers.
"""

generation_config = {
    "temperature": 0.9,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
    system_instruction=baseball_prompt
)



email_sender = os.getenv('EMAIL_USER')
sender_password = os.getenv('EMAIL_PASS')

def generate_user_email_data():
    """
    Generates email data for each user based on their profile questions.
    """
    user_email_data = {}
    with open("database/users.json", "r") as user_file:
        users = json.load(user_file)
    for user in users:
        username = user["username"]
        details_path = f"database/details/{username}.json"
        if os.path.exists(details_path):
            with open(details_path, "r") as details_file:
                user_details = json.load(details_file)
            eligible_questions = [q for q in user_details["questions"] if q["id"] != "notifications"]
            if not eligible_questions:
                print(f"No eligible questions found for user '{username}'. Skipping.")
                continue
            random_question = random.choice(eligible_questions)
            question_id = random_question["id"]
            print(question_id)
            if question_id in ["favorite_teams", "favorite_players"]:
                 if not random_question["answer"]: # handle case of no favorite_teams or no favorite_player
                  print(f"No favorite teams/players found, skipping email sending to '{username}'.")
                  continue 
                 answer = random.choice(random_question["answer"])
            else:
                 answer = random_question["answer"]
            notification_answer = next(q["answer"] for q in user_details["questions"] if q["id"] == "notifications")
            selected_team = next((q["answer"] for q in user_details["questions"] if q["id"] == "selected_team"), None)
            user_email_data[username] = {
                "question_id": question_id,
                "answer": answer,
                "notification_frequency": notification_answer,
                "selected_team": selected_team,
            }
        else:
            print(f"Details file for user '{username}' does not exist.\n")
            user_email_data[username] = None
    return user_email_data


def load_users():
    """Loads user data from database/users.json."""
    with open("database/users.json", "r") as user_file:
        return json.load(user_file)

def load_email_notification_history():
    """Loads the email notification history for all users."""
    history_path = "database/details/email/notification.json"
    if os.path.exists(history_path):
      with open(history_path, "r") as f:
        history = json.load(f)
      print(f"Loaded existing email history: {history}")  
      return history

    else:
       print("No existing notification.json,  creating")
       return {}


def save_email_notification_history(history):
    """Saves the email notification history for all users."""
    history_path = "database/details/email/notification.json"
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "w") as f:
        json.dump(history, f, indent=4)
    print(f"Email history saved to {history_path}: {history}")



def check_due_email_notification(username, user_data, email_history):
    """Checks if a user is due for an email notification based on their history and frequency."""
    print(f"Checking if email is due for user: {username}, with data: {user_data}")

    if not user_data:
        print(f"Skipping due check as no user_data")
        return False


    notification_frequency = user_data["notification_frequency"].lower()
    print(f"Notification frequency for {username}: {notification_frequency}")

    if username not in email_history:
       print(f"no previous history exists for {username}, first time email due")
       return True
       

    last_notification_str = email_history[username].get("last_sent_date")
    
    if not last_notification_str:
      print(f"Last sent notification data not available, {username} emails due now ")
      return True

    if notification_frequency == "never":
        print(f"Notification is 'never' for {username}, skipping due check.")
        return False
    

    last_notification = datetime.fromisoformat(last_notification_str)
    now = datetime.now()

    if notification_frequency == "daily":
      print (f"Last sent at:{last_notification}, Now: {now} : diff={(now - last_notification) >= timedelta(days=1)}, frequency daily check result ")
      return (now - last_notification) >= timedelta(days=1)
    elif notification_frequency == "weekly":
        print(f"Last sent at:{last_notification}, Now: {now} : diff={(now - last_notification) >= timedelta(weeks=1)}, frequency weekly check result")
        return (now - last_notification) >= timedelta(weeks=1)
    elif notification_frequency == "monthly":
        print(f"Last sent at:{last_notification}, Now: {now} : diff={(now - last_notification) >= timedelta(days=30)}, frequency monthly check result")
        return (now - last_notification) >= timedelta(days=30) #Approximate

    print(f"Invalid Notification Frequency skipping for user: {username}")
    return False

def send_email(recipient_email, username, sender_email, sender_password, subject, body):
    """Sends a formatted HTML email."""
    
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.sendmail(sender_email, recipient_email, message.as_string())
        print(f"Email sent successfully to {username}!")
        return True
    except Exception as e:
        print(f"Error sending email to {username}: {e}")
        return False


def personailzednofity():
    user_email_data = generate_user_email_data()
    email_history = load_email_notification_history()
    users = load_users()

    for username, user_data in user_email_data.items():
        if user_data:
            if check_due_email_notification(username, user_data, email_history):
                 print(f" Email due check returned true: will process email send for {username} user")
                # Fetch email for the recipient
                 recipient_email = None
                 for user in users:
                    if user['username'] == username:
                         recipient_email = user['email']
                         break
                 if recipient_email:
                    question_id = user_data["question_id"]
                    answer = user_data["answer"]
                    selected_team = user_data["selected_team"]
                    
                    subject, body = personalizedEmail(username, question_id, answer, selected_team)

                    if send_email(recipient_email, username, email_sender, sender_password, subject, body):
                        # Update Email history
                       if username not in email_history:
                          print(f"Creating new notification record for {username}")
                          email_history[username] = {
                               "notification_history":[],
                             "last_sent_date" : datetime.now().isoformat(),
                            }
                       else :
                           email_history[username]["last_sent_date"] = datetime.now().isoformat()
                           print(f"updating sent date for {username}: {email_history[username]['last_sent_date']}")
                       email_history[username]["notification_history"].append({
                                  "question_id": question_id,
                                  "timestamp": datetime.now().isoformat(),
                       })

                       save_email_notification_history(email_history)
                    else:
                       print(f"email sending failed to {username}")

                 else:
                      print(f"Could not find email address for user {username}")

            else:
               print(f"Email notification not due for {username} yet based on  check_due_email_notification method")
        else:
           print(f"No user data for {username}, skipping process user email  process")

personailzednofity()
def strftime(date, format_string):
    return date.strftime(format_string)
# Load the JSON data from a file
with open('dataset/team.json', 'r') as file:
    teams_name_id = json.load(file)

from pathlib import Path

app.secret_key = secrets.token_hex(16)
app.jinja_env.filters['strftime'] = strftime
MLB_API_URL = 'https://statsapi.mlb.com/api/v1/schedule'
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
                "answer": data.get('selected_team')

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
            body = Sign_up_email_body_template(username)
            # Send a confirmation email after questionnaire completion
            send_sign_up_email(email,username,body,email_sender,sender_password)
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
@app.route('/uploads/<filename>')
def serve_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


import os
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_file', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to prevent duplicates
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Return the complete URL path
            file_url = url_for('static', filename=f'uploads/{filename}')
            return jsonify({
                'success': True,
                'file_url': file_url
            })
        
        return jsonify({'success': False, 'error': 'Invalid file type'}), 400
    
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.json
        friend = data.get('friend')
        message = data.get('message', '')
        file_url = data.get('file_url')  # Get file_url from the request

        # Load existing chats
        chats = load_json('chats.json')
        chat_id = '_'.join(sorted([session['username'], friend]))
        
        if chat_id not in chats:
            chats[chat_id] = []
        
        # Create new message
        new_message = {
            'from': session['username'],
            'message': message,
            'timestamp': datetime.now().strftime('%I:%M %p')
        }

        # Add file URL if it exists
        if file_url:
            new_message['file_url'] = file_url
        
        # Add message to chat
        chats[chat_id].append(new_message)
        save_json(chats, 'chats.json')

        return jsonify({'success': True, 'message': new_message})

    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
                    home_team = game.get('teams', {}).get('home', {}).get('team', {})
                    away_team = game.get('teams', {}).get('away', {}).get('team', {})
                    
                    games.append({
                        'gamePk': game.get('gamePk'),
                        'gameDate': game.get('gameDate'),
                        'status': game.get('status', {}).get('abstractGameState'),
                        'homeTeam': home_team.get('name'),
                        'awayTeam': away_team.get('name'),
                        'homeTeamId': home_team.get('id'),
                        'awayTeamId': away_team.get('id'),
                        'homeTeamLogo': f"https://www.mlbstatic.com/team-logos/{home_team.get('id')}.svg",
                        'awayTeamLogo': f"https://www.mlbstatic.com/team-logos/{away_team.get('id')}.svg",
                        'venue': game.get('venue', {}).get('name'),
                        'homeScore': game.get('teams', {}).get('home', {}).get('score', 0),
                        'awayScore': game.get('teams', {}).get('away', {}).get('score', 0)
                    })
                    
        games.sort(key=lambda x: x['gameDate'])
        upcoming_games = [g for g in games if g['status'] == 'Preview'][:4]
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
    user_data = load_user_team_data()
    username = session['username']
    
    # Get team names and overviews if user exists
    if username in user_data:
        user_teams = user_data[username]
        team_names = list(user_teams.keys())
        team_ovrs = {}
        
        for team_name, team_data in user_teams.items():
            total_weighted_ovr = 0
            total_weights = 0
            
            for player in team_data['selected_players']:
                ovr_data = calculate_ovr(player['id'], player['position'])
                ovr_rating = int(ovr_data['overall_rating'] if isinstance(ovr_data, dict) else 0)
                position_weight = POSITION_WEIGHTS.get(player['position'], 0)
                
                total_weighted_ovr += ovr_rating * position_weight
                total_weights += position_weight
            
            team_ovr = int(total_weighted_ovr / total_weights if total_weights else 0)
            team_ovrs[team_name] = team_ovr
    else:
        team_names = []
        team_ovrs = {}
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
        selected_players_count=len(selected_player_names),
        team_ovrs=team_ovrs,
        team_names=team_names  # Added team names to template
    )

def load_user_team_data():
    with open('database/user_teams/user_team_data.json', 'r') as file:
        return json.load(file)
    
# Define positional weights for the team OVR calculation
POSITION_WEIGHTS = {
    'Pitcher': 0.25,
    'Catcher': 0.15,
    'First Base': 0.10,
    'Second Base': 0.10,
    'Third Base': 0.10,
    'Shortstop': 0.10,
    'Left Fielder': 0.05,
    'Center Fielder': 0.10,
    'Right Fielder': 0.05
}


@app.route('/<username>/my_team', methods=['GET', 'POST'])
def myteam(username):
    # Check if user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Load users data to check friendship
    users = load_json('users.json')
    
    # Check if the requested username exists
    if username not in users:
        return "User not found", 404
    
    # Check if the viewer is the profile owner or a friend
    current_user = session['username']
    if current_user != username and current_user not in users[username]['friends']:
        return "You must be friends with this user to view their teams", 403
    
    user_data = load_user_team_data()
    
    # Check if the requested username exists in team data
    if username not in user_data:
        return "No teams found for this user", 404
    
    # Get all teams for the requested user
    user_teams = user_data[username]
    team_names = list(user_teams.keys())
    teams_players = {}
    team_ovrs = {}

    for team_name, team_data in user_teams.items():
        players = []
        total_weighted_ovr = 0
        total_weights = 0

        for player in team_data['selected_players']:
            ovr_data = calculate_ovr(player['id'], player['position'])
            ovr_rating = int(ovr_data['overall_rating'] if isinstance(ovr_data, dict) else 0)
            position_weight = POSITION_WEIGHTS.get(player['position'], 0)
            
            total_weighted_ovr += ovr_rating * position_weight
            total_weights += position_weight
            
            player_info = {
                'name': player['name'],
                'position': player['position'],
                'headshot_url': player['headshot_url'],
                'ovr': int(ovr_rating)
            }
            players.append(player_info)

        team_ovr = int(total_weighted_ovr / total_weights if total_weights else 0)
        teams_players[team_name] = players
    
    return render_template('my_team.html', 
                         team_names=team_names, 
                         teams_players=teams_players, 
                         team_ovrs=int(team_ovr),
                         profile_username=username)

@app.route('/my_team')
def redirect_to_myteam():
    if 'username' in session:
        return redirect(url_for('myteam', username=session['username']))
    return redirect(url_for('login'))

@app.route('/player_stats/<int:player_id>', methods=['GET'])
def get_player_stats(player_id):
    try:
        # Fetch player data using statsapi
        player_data = statsapi.player_stat_data(player_id)
        
        # Extract relevant stats
        stats = {
            'player_info': {
                'id': player_id,
                'name': player_data.get('first_name', '') + ' ' + player_data.get('last_name', ''),
                'position': player_data.get('position', ''),
                'team': player_data.get('current_team', ''),
            },
            'hitting_stats': extract_hitting_stats(player_data),
            'fielding_stats': extract_fielding_stats(player_data)
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_hitting_stats(player_data):
    hitting_stats = {}
    for stat_group in player_data.get('stats', []):
        if stat_group.get('group') == 'hitting' and stat_group.get('type') == 'season':
            stats = stat_group.get('stats', {})
            hitting_stats = {
                'avg': stats.get('avg', '.000'),
                'hr': stats.get('homeRuns', 0),
                'rbi': stats.get('rbi', 0),
                'obp': stats.get('obp', '.000'),
                'slg': stats.get('slg', '.000'),
                'ops': stats.get('ops', '.000'),
                'sb': stats.get('stolenBases', 0),
                'runs': stats.get('runs', 0)
            }
            break
    return hitting_stats

def extract_fielding_stats(player_data):
    fielding_stats = {}
    for stat_group in player_data.get('stats', []):
        if stat_group.get('group') == 'fielding' and stat_group.get('type') == 'season':
            stats = stat_group.get('stats', {})
            fielding_stats = {
                'fielding_pct': stats.get('fielding', '.000'),
                'assists': stats.get('assists', 0),
                'putouts': stats.get('putOuts', 0),
                'errors': stats.get('errors', 0),
                'double_plays': stats.get('doublePlays', 0),
                'range_factor': stats.get('rangeFactorPerGame', '0.00')
            }
            break
    return fielding_stats

@app.route('/get_position_headshots/<team_name>/<position>')
def get_position_headshots(team_name, position):
    user_data = load_user_team_data()
    user_name = session['username']
    
    # Get the specific team data
    team_data = user_data[user_name][team_name]
    
    # Filter players by position and get their headshot URLs along with OVR
    position_headshots = []
    for player in team_data['selected_players']:
        if player['position'].upper() == position.upper():
            # Calculate OVR for each player
            ovr_data = calculate_ovr(player['id'], player['position'])
            ovr_rating = ovr_data['overall_rating'] if isinstance(ovr_data, dict) else 'N/A'
            
            position_headshots.append({
                'name': player['name'],
                'position': player['position'],
                'headshot_url': player['headshot_url'],
                'ovr': ovr_rating  # Include OVR in the response
            })
    
    return jsonify({
        'team_name': team_name,
        'position': position,
        'players': position_headshots
    })

@app.route('/generate_team_link/<username>')
def generate_team_link(username):
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Generate a unique token for sharing
    share_token = secrets.token_urlsafe(16)
    
    # Store the share token with expiration time (24 hours from now)
    share_links = load_json('share_links.json')
    share_links[share_token] = {
        'username': username,
        'expires': (datetime.now() + timedelta(days=1)).timestamp()
    }
    save_json(share_links, 'share_links.json')
    
    # Generate the shareable link
    share_url = url_for('view_shared_team', share_token=share_token, _external=True)
    return jsonify({'share_url': share_url})

@app.route('/shared_team/<share_token>')
def view_shared_team(share_token):
    share_links = load_json('share_links.json')
    
    # Check if token exists and is valid
    if share_token not in share_links:
        return "Invalid or expired link", 404
    
    share_data = share_links[share_token]
    
    # Check if link has expired
    if datetime.now().timestamp() > share_data['expires']:
        del share_links[share_token]
        save_json(share_links, 'share_links.json')
        return "Link has expired", 404
    
    username = share_data['username']
    user_data = load_user_team_data()
    
    if username not in user_data:
        return "No teams found for this user", 404
    
    # Get all teams for the requested user
    user_teams = user_data[username]
    team_names = list(user_teams.keys())
    teams_players = {}
    team_ovrs = {}

    for team_name, team_data in user_teams.items():
        players = []
        total_weighted_ovr = 0
        total_weights = 0

        for player in team_data['selected_players']:
            ovr_data = calculate_ovr(player['id'], player['position'])
            ovr_rating = int(ovr_data['overall_rating'] if isinstance(ovr_data, dict) else 0)
            position_weight = POSITION_WEIGHTS.get(player['position'], 0)
            
            total_weighted_ovr += ovr_rating * position_weight
            total_weights += position_weight
            
            player_info = {
                'name': player['name'],
                'position': player['position'],
                'headshot_url': player['headshot_url'],
                'ovr': int(ovr_rating)
            }
            players.append(player_info)

        team_ovr = int(total_weighted_ovr / total_weights if total_weights else 0)
        teams_players[team_name] = players
    
    return render_template('my_team.html', 
                         team_names=team_names, 
                         teams_players=teams_players, 
                         team_ovrs=int(team_ovr),
                         profile_username=username)

@app.route('/highlights', methods=['GET', 'POST'])
def highlights():
    season = request.form.get('season', 2024)  # Default season
    home_team_filter = request.form.get('home_team', None)
    away_team_filter = request.form.get('away_team', None)

    response = requests.get(f"{MLB_API_URL}?sportId=1&season={season}")
    games_data = response.json().get("dates", [])

    matches = []
    for date_info in games_data:
        for game in date_info["games"]:
            home_team = game['teams']['home']['team']['name']
            away_team = game['teams']['away']['team']['name']
            home_score = game['teams']['home'].get('score', 'N/A')
            away_score = game['teams']['away'].get('score', 'N/A')
            
            game_date = game['gameDate']
            venue = game.get('venue', {}).get('name', 'N/A')
            game_pk = game['gamePk']

            home_team_logo = f'https://www.mlbstatic.com/team-logos/{game["teams"]["home"]["team"]["id"]}.svg'
            away_team_logo = f'https://www.mlbstatic.com/team-logos/{game["teams"]["away"]["team"]["id"]}.svg'

            # Apply filters
            if home_team_filter and home_team_filter != home_team:
                continue
            if away_team_filter and away_team_filter != away_team:
                continue

            matches.append({
            'home_team': home_team,
            'away_team': away_team,
            'home_score': home_score,
            'away_score': away_score,
            'game_date': game_date,
            'venue': venue,
            'game_pk': game_pk,
            'home_team_logo': home_team_logo,
            'away_team_logo': away_team_logo,
            'highlights_url': f"/game/{game_pk}"  # Link to game highlights
})


    return render_template('highlight.html', matches=matches, teams_data=teams_name_id)

@app.route('/game/<int:game_pk>', methods=['GET'])
def game_details(game_pk):
    response = requests.get(f"{MLB_API_URL}?gamePk={game_pk}")
    game_info = response.json().get("dates", [])[0].get("games", [])[0]
    
    game_data = {
        'home_team': game_info['teams']['home']['team']['name'],
        'away_team': game_info['teams']['away']['team']['name'],
        'home_score': game_info['teams']['home'].get('score', 0),
        'away_score': game_info['teams']['away'].get('score', 0),
        'game_date': game_info['gameDate'],
        'venue': game_info.get('venue', {}).get('name', 'N/A'),
        'home_team_logo': f'https://www.mlbstatic.com/team-logos/{game_info["teams"]["home"]["team"]["id"]}.svg',
        'away_team_logo': f'https://www.mlbstatic.com/team-logos/{game_info["teams"]["away"]["team"]["id"]}.svg',
        'status': game_info.get('status', {}).get('detailedState', 'N/A')
    }
    
    highlights_data = extract_highlights(game_pk)
    video_highlights = fetch_video_highlights(game_pk)

    # Initialize running scores
    running_away_score = 0
    running_home_score = 0

    # Process each highlight
    for highlight in highlights_data:
        # Update scores based on the play result
        if 'scores' in highlight.get('description', '').lower():
            if 'home' in highlight.get('description', '').lower():
                running_home_score += 1
            else:
                running_away_score += 1
        
        # Add current scores to highlight
        highlight['away_score'] = running_away_score
        highlight['home_score'] = running_home_score
        highlight['time'] = highlight['time'][11:19] if isinstance(highlight['time'], str) else highlight['time']

    return render_template('GameHighlights.html', 
                         game_pk=game_pk,
                         game_data=game_data,
                         highlights_data=highlights_data, 
                         video_highlights=video_highlights,
                         previous_away_score=0,
                         previous_home_score=0)



def fetch_video_highlights(game_pk):
    video_highlights = []
    
    # Get raw highlights data
    raw_highlights = statsapi.game_highlights(game_pk)
    
    # Split the raw text into lines
    lines = raw_highlights.split('\n')
    
    current_title = None
    current_description = None
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Check if line contains video URL
        if line.startswith('https://') and line.endswith('.mp4'):
            if current_title and current_description:
                video_highlights.append({
                    'title': current_title,
                    'description': current_description,
                    'video_url': line.strip()
                })
            current_title = None
            current_description = None
            
        # Check if line contains title (they typically end with duration in parentheses)
        elif '(' in line and ')' in line and any(x in line for x in ['00:', '01:', '02:']):
            current_title = line.strip()
            
        # If not a URL or title, it's likely a description
        elif current_title and not current_description:
            current_description = line.strip()
    
    return video_highlights
def extract_video_urls(highlights_data):
    video_urls = []
    for highlight in highlights_data:
        if 'video_url' in highlight and highlight['video_url'].startswith('https://') and highlight['video_url'].endswith('.mp4'):
            video_urls.append(highlight['video_url'])
    return video_urls

def extract_highlights(game_pk):
    highlights = []
    try:
        # Get live game data
        game = statsapi.get('game', {'gamePk': game_pk})
        all_plays = game.get('liveData', {}).get('plays', {}).get('allPlays', [])
        
        for play in all_plays:
            if play.get('about', {}).get('isComplete', False):
                result = play.get('result', {})
                about = play.get('about', {})
                
                highlight = {
                    'description': result.get('description', ''),
                    'score': f"Away: {result.get('awayScore', 0)}, Home: {result.get('homeScore', 0)}",
                    'inning': f"{'Top' if about.get('halfInning') == 'top' else 'Bottom'} of the {about.get('inning')} inning",
                    'time': about.get('endTime', '')
                }
                highlights.append(highlight)
                
    except Exception as e:
        print(f"Error extracting highlights: {e}")
    
    return highlights




#TEAM COMPARE
def initialize_stats():
    return {
        'batting': {'avg': 0, 'obp': 0, 'slg': 0, 'ops': 0, 'count': 0},
        'pitching': {'era': 0, 'whip': 0, 'k9': 0, 'baa': 0, 'count': 0},
        'fielding': {'fpct': 0, 'assists': 0, 'putouts': 0, 'count': 0},
        'catching': {'cs_pct': 0, 'pb': 0, 'fpct': 0, 'count': 0}
    }

async def fetch_stats_async(session, url):
    async with session.get(url) as response:
        return await response.json()

async def get_team_stats_async(team_id, season=2024):
    async with aiohttp.ClientSession() as session:
        roster_url = f'https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?season={season}'
        roster_response = await fetch_stats_async(session, roster_url)
        
        tasks = []
        for player in roster_response.get('roster', []):
            player_id = player['person']['id']
            stats_url = f'https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&season={season}'
            tasks.append(fetch_stats_async(session, stats_url))
        
        player_stats_responses = await asyncio.gather(*tasks)
        
        stats = initialize_stats()
        for player_stats, player in zip(player_stats_responses, roster_response.get('roster', [])):
            process_player_stats(player_stats, player['position']['abbreviation'], stats)
        
        return calculate_team_metrics(stats)

def process_player_stats(stats_data, position, team_stats):
    if not stats_data.get('stats'):
        return
        
    if position == 'P':
        process_pitcher_stats(stats_data, team_stats)
    elif position == 'C':
        process_catcher_stats(stats_data, team_stats)
        process_fielder_stats(stats_data, team_stats)
    else:
        process_batter_stats(stats_data, team_stats)
        process_fielder_stats(stats_data, team_stats)

def process_batter_stats(stats_data, team_stats):
    hitting_stats = next((group for group in stats_data['stats'] 
                         if group['group']['displayName'] == 'hitting'), None)
    if hitting_stats and hitting_stats.get('splits'):
        stats = hitting_stats['splits'][0]['stat']
        team_stats['batting']['avg'] += float(stats.get('avg', 0))
        team_stats['batting']['obp'] += float(stats.get('obp', 0))
        team_stats['batting']['slg'] += float(stats.get('slg', 0))
        team_stats['batting']['ops'] += float(stats.get('ops', 0))
        team_stats['batting']['count'] += 1

def process_pitcher_stats(stats_data, team_stats):
    pitching_stats = next((group for group in stats_data['stats'] 
                          if group['group']['displayName'] == 'pitching'), None)
    if pitching_stats and pitching_stats.get('splits'):
        stats = pitching_stats['splits'][0]['stat']
        team_stats['pitching']['era'] += float(stats.get('era', 0))
        team_stats['pitching']['whip'] += float(stats.get('whip', 0))
        team_stats['pitching']['k9'] += float(stats.get('strikeoutsPer9Inn', 0))
        team_stats['pitching']['baa'] += float(stats.get('avg', 0))
        team_stats['pitching']['count'] += 1

def process_fielder_stats(stats_data, team_stats):
    fielding_stats = next((group for group in stats_data['stats'] 
                          if group['group']['displayName'] == 'fielding'), None)
    if fielding_stats and fielding_stats.get('splits'):
        stats = fielding_stats['splits'][0]['stat']
        team_stats['fielding']['fpct'] += float(stats.get('fielding', 0))
        team_stats['fielding']['assists'] += float(stats.get('assists', 0))
        team_stats['fielding']['putouts'] += float(stats.get('putOuts', 0))
        team_stats['fielding']['count'] += 1

def process_catcher_stats(stats_data, team_stats):
    catching_stats = next((group for group in stats_data['stats'] 
                          if group['group']['displayName'] == 'catching'), None)
    if catching_stats and catching_stats.get('splits'):
        stats = catching_stats['splits'][0]['stat']
        team_stats['catching']['cs_pct'] += float(stats.get('catcherCaughtStealing', 0))
        team_stats['catching']['pb'] += float(stats.get('passedBalls', 0))
        team_stats['catching']['fpct'] += float(stats.get('fielding', 0))
        team_stats['catching']['count'] += 1

def calculate_team_metrics(stats):
    metrics = {}
    
    for category in stats:
        if stats[category]['count'] > 0:
            if category == 'batting':
                metrics[category] = {
                    'value': (
                        (stats[category]['avg'] / stats[category]['count']) * 0.3 +
                        (stats[category]['obp'] / stats[category]['count']) * 0.35 +
                        (stats[category]['slg'] / stats[category]['count']) * 0.35
                    ) * 100
                }
            elif category == 'pitching':
                metrics[category] = {
                    'value': (
                        (1 - (stats[category]['era'] / stats[category]['count'])/5.0) * 0.4 +
                        (1 - (stats[category]['whip'] / stats[category]['count'])/1.5) * 0.3 +
                        ((stats[category]['k9'] / stats[category]['count'])/9.0) * 0.3
                    ) * 100
                }
            elif category == 'fielding':
                metrics[category] = {
                    'value': (stats[category]['fpct'] / stats[category]['count']) * 100
                }
            else:  # catching
                metrics[category] = {
                    'value': (stats[category]['cs_pct'] / stats[category]['count']) * 100
                }
        else:
            metrics[category] = {'value': 0}
    
    return metrics


@app.route('/compare', methods=['POST'])
async def compare_teams():
    home_team = request.form.get('home_team')
    away_team = request.form.get('away_team')
    
    home_stats, away_stats = await asyncio.gather(
        get_team_stats_async(home_team),
        get_team_stats_async(away_team)
    )
    
    return jsonify({
        'home': home_stats,
        'away': away_stats
    })

@app.route('/team_compare')
def teaam_compare():
    return render_template('teamcompare.html')


def fetch_first_highlight(game_pk):
    highlights = []
    raw_highlights = statsapi.game_highlights(game_pk)
    lines = raw_highlights.split('\n')
    current_title, current_description = None, None
    
    for line in lines:
        if not line.strip():
            continue
        if line.startswith('https://') and line.endswith('.mp4'):
            if current_title and current_description:
                highlights.append({
                    'title': current_title,
                    'description': current_description,
                    'video_url': line.strip()
                })
            break  # Only need the first highlight
        elif '(' in line and ')' in line and any(x in line for x in ['00:', '01:', '02:']):
            current_title = line.strip()
        elif current_title and not current_description:
            current_description = line.strip()
    
    return highlights[0] if highlights else None
def get_latest_completed_game():
    # Fetch schedule data
    schedule_data = statsapi.get('schedule', {'sportId': 1, 'season': 2024, 'gameType': 'R'})
    
    # Get dates array
    dates = schedule_data.get('dates', [])
    
    # Sort dates in reverse order to get most recent first
    dates.sort(key=lambda x: x['date'], reverse=True)
    
    for date in dates:
        games = date.get('games', [])
        for game in games:
            # Check if game is completed
            if game.get('status', {}).get('statusCode') == 'F':
                return game.get('gamePk')
    
    return None
def get_game_info():
    schedule_data = statsapi.get('schedule', {'sportId': 1, 'season': 2024, 'gameType': 'R'})
    dates = sorted(schedule_data.get('dates', []), key=lambda x: x['date'], reverse=True)
    
    for date in dates:
        games = date.get('games', [])
        for game in games:
            if game.get('status', {}).get('statusCode') == 'F':
                game_pk = game.get('gamePk')
                game_data = statsapi.get('game', {'gamePk': game_pk})
                teams = game_data.get('gameData', {}).get('teams', {})
                
                home_team = teams.get('home', {})
                away_team = teams.get('away', {})
                
                home_team_name = home_team.get('name', 'Unknown')
                away_team_name = away_team.get('name', 'Unknown')
                home_team_id = home_team.get('id')
                away_team_id = away_team.get('id')
                first_highlight = fetch_first_highlight(game_pk)
                
                return home_team_name, away_team_name, first_highlight, game_data, home_team_id, away_team_id ,game_pk
    
    return None, None, None, None, None, None,None


from deep_translator import GoogleTranslator


def translate_text(text, target_language):
    try:
        translated = GoogleTranslator(target=target_language).translate(text)
        return translated
    except Exception as e:
        return f"Error: {e}"
    
@app.route('/geminichat', methods=['POST'])
def gemini_chat():  # Renamed the function to avoid conflicts
    data = request.json
    user_message = data.get('message')
    
    try:
        chat_session = model.start_chat()
        response = chat_session.send_message(user_message)
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get MLB data
    languages = [
        ('en', 'English'),
        ('ja', 'Japanese'),
        ('es', 'Spanish'),
        ('de', 'German'),
        ('ko', 'Korean'),
        ('fr', 'French'),
        ('hi', 'Hindi')
    ]
    
    # Get selected language
    lang = request.args.get('lang', 'en')
   
    lang = request.args.get('lang', 'en')
    upcoming_games = get_schedule()
    news = fetch_latest_news()
    home_team, away_team, highlight, game_data, home_team_id, away_team_id, game_pk = get_game_info()
    if lang != 'en':
        # Translate news
        for article in news:
            article['title'] = translate_text(article['title'], lang)
        
        # Translate highlight if exists
        if highlight:
            highlight['title'] = translate_text(highlight['title'], lang)
            highlight['description'] = translate_text(highlight['description'], lang)
        
        # Translate group info
        for group in my_groups:
            group['name'] = translate_text(group['name'], lang)
            group['description'] = translate_text(group['description'], lang)
        
        for group in available_groups:
            group['name'] = translate_text(group['name'], lang)
            group['description'] = translate_text(group['description'], lang)

    latest_game = {
        'home_team': home_team,
        'away_team': away_team,
        'home_team_logo': f"https://www.mlbstatic.com/team-logos/{home_team_id}.svg" if home_team_id else None,
        'away_team_logo': f"https://www.mlbstatic.com/team-logos/{away_team_id}.svg" if away_team_id else None,
        'highlights_url': highlight['video_url'] if highlight else None,
        'venue': game_data.get('venue', {}).get('name', 'Unknown Stadium') if game_data else 'Unknown Stadium',
        'game_date': game_data.get('gameDate', '') if game_data else '',
        'game_pk': game_pk
    }
    
    # Get social data
    users = load_json('users.json')
    requests = load_json('friend_requests.json')
    groups = load_json('groups.json')
    
    pending_requests = [req for req in requests.get(session['username'], [])]
    friends = users[session['username']]['friends']
    
    # Get team data
    user_data = load_user_team_data()
    username = session['username']
    
    if username in user_data:
        user_teams = user_data[username]
        team_names = list(user_teams.keys())
        teams_players = {}
        team_ovrs = {}

        for team_name, team_data in user_teams.items():
            players = []
            total_weighted_ovr = 0
            total_weights = 0

            for player in team_data['selected_players']:
                ovr_data = calculate_ovr(player['id'], player['position'])
                ovr_rating = int(ovr_data['overall_rating'] if isinstance(ovr_data, dict) else 0)
                position_weight = POSITION_WEIGHTS.get(player['position'], 0)
                
                total_weighted_ovr += ovr_rating * position_weight
                total_weights += position_weight
                
                player_info = {
                    'name': player['name'],
                    'position': player['position'],
                    'headshot_url': player['headshot_url'],
                    'ovr': int(ovr_rating)
                }
                players.append(player_info)

            team_ovr = int(total_weighted_ovr / total_weights if total_weights else 0)
            teams_players[team_name] = players
            team_ovrs[team_name] = team_ovr
    else:
        team_names = []
        teams_players = {}
        team_ovrs = {}
    
    # Process groups
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
            if session['username'] != group_data['creator']:
                group_info['joined_at'] = group_data['created_at']
            my_groups.append(group_info)
        else:
            available_groups.append(group_info)
    
    my_groups.sort(key=lambda x: x['created_at'], reverse=True)
    available_groups.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('hometest.html',
                         upcoming_games=upcoming_games,
                         news=news,
                         lang=lang,
                         latest_game=latest_game,
                         highlight=highlight,
                         pending_requests=pending_requests,
                         friends=friends,
                         my_groups=my_groups,
                         available_groups=available_groups,
                         team_names=team_names,
                         teams_players=teams_players,
                         team_ovrs=team_ovrs,
                         profile_username=username)

if __name__ == '__main__':
    app.run(debug=True)