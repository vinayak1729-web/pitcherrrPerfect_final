import json
import os
import random

def generate_user_email_data():
    """
    Generates email data for each user based on their profile questions.

    Returns:
        dict: A dictionary containing email data, keyed by username.
              Each user has a dictionary with 'question_id', 'answer',
              'notification_frequency', and 'selected_team'.
    """
    user_email_data = {}

    # Load the main user database
    with open("database/users.json", "r") as user_file:
        users = json.load(user_file)

    for user in users:
        username = user["username"]
        details_path = f"database/details/{username}.json"

        if os.path.exists(details_path):
            with open(details_path, "r") as details_file:
                user_details = json.load(details_file)

            # Get all questions except notifications
            eligible_questions = [q for q in user_details["questions"] if q["id"] != "notifications"]
            
            if not eligible_questions:
                print(f"No eligible questions found for user '{username}'. Skipping.")
                continue
                
            # Select one random question
            random_question = random.choice(eligible_questions)
            question_id = random_question["id"]
            
            # Get the answer based on question type
            if question_id in ["favorite_teams", "favorite_players"]:
                random_ans = random.choice(random_question["answer"])
                answer = random.choice(random_ans)
            else:
                answer = random_question["answer"]

            # Get notification frequency
            notification_answer = next(q["answer"] for q in user_details["questions"] if q["id"] == "notifications")

            # Get selected team for email context
            selected_team = next((q["answer"] for q in user_details["questions"] if q["id"] == "selected_team"), None)
            
            # Store user data for email generation
            user_email_data[username] = {
                "question_id": question_id,
                "answer": answer,
                "notification_frequency": notification_answer,
                "selected_team": selected_team,
            }
        
        else:
           print(f"Details file for user '{username}' does not exist.\n")
           user_email_data[username] = None # Indicate no data found

    return user_email_data

if __name__ == "__main__":
    user_email_data = generate_user_email_data()
    
    for username, data in user_email_data.items():
        if data:
            print(f"User: {username}")
            print(f"Question Type: {data['question_id']}")
            print(f"Answer: {data['answer']}")
            print(f"Notification Frequency: {data['notification_frequency']}")
            print(f"Selected Team: {data['selected_team']}")
            print("-" * 30)
        else:
            print(f"No data available for user: {username}")
            print("-" * 30)