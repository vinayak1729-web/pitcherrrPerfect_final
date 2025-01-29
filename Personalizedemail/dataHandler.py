# email_automation/data_handler.py
import json
import os
from datetime import datetime
import random
def generate_user_email_data(usersdb,usersDetailsdb):
    """
    Generates email data for each user based on their profile questions.
    """
    user_email_data = {}
    with open(usersdb, "r") as user_file:
        users = json.load(user_file)
    for user in users:
        username = user["username"]
        details_path = usersDetailsdb
        if os.path.exists(details_path):
            with open(details_path, "r") as details_file:
                user_details = json.load(details_file)
            eligible_questions = [q for q in user_details["questions"] if q["id"] != "notifications"]
            if not eligible_questions:
                print(f"No eligible questions found for user '{username}'. Skipping.")
                continue
            random_question = random.choice(eligible_questions)
            question_id = random_question["id"]
            if question_id in ["favorite_teams", "favorite_players"]:
                random_ans = random.choice(random_question["answer"])
                answer = random.choice(random_ans)
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


def load_users(usersdb):
    """Loads user data from database/users.json."""
    with open(usersdb, "r") as user_file:
        return json.load(user_file)

def load_email_notification_history(history_path):
    """Loads the email notification history for all users."""
    if os.path.exists(history_path):
        with open(history_path, "r") as f:
            return json.load(f)
    return {}

def save_email_notification_history(history,history_path):
    """Saves the email notification history for all users."""
    history_path
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "w") as f:
        json.dump(history, f, indent=4)