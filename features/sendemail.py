import os
from email.message import EmailMessage
import ssl
import smtplib
from dotenv import load_dotenv
load_dotenv()
email_sender = 'vinayak.test.001@gmail.com'

def send_email_function(receiver_email, subject, body):
    
    email_password = os.environ.get("EMAIL_PASSWORD")
    if not email_password:
        raise ValueError("EMAIL_PASSWORD environment variable not set or incorrect.")

    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = receiver_email
    em['Subject'] = subject
    em.set_content(body)

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(email_sender, email_password)
            smtp.sendmail(email_sender, receiver_email, em.as_string())
            print(f"Email sent successfully to {receiver_email}!")
    except smtplib.SMTPAuthenticationError as e:
        print("Authentication error:", e)
    except Exception as e:
        print("An error occurred:", e)

# import json
# import os
# import random

# def generate_email_prompts(question_type, answer, team=None):
#     prompts = {
#         "fan_duration": {
#             "subject": f"Welcome {team} Fan of {answer} Years!",
#             "body": f"As a dedicated fan who has followed MLB for {answer} years, we're excited to have you in our community."
#         },
#         "favorite_teams": {
#             "subject": f"Your Team {answer} Has an Upcoming Match!",
#             "body": f"Get ready to cheer for {answer}! We've got some exciting updates about your favorite team."
#         },
#         "favorite_players": {
#             "subject": f"Latest Updates About {answer}",
#             "body": f"Stay updated with the latest news and performance stats about {answer}."
#         },
#         "selected_team": {
#             "subject": f"Welcome to {answer} Nation!",
#             "body": f"Thanks for selecting {answer} as your team. Here's what's happening with your team this week."
#         },
#         "favorite_match": {
#             "subject": f"Relive the Magic of {answer}",
#             "body": f"Remember the excitement of {answer}? We've got similar thrilling matches coming up!"
#         }
#     }
    
#     return prompts.get(question_type, {
#         "subject": "MLB Updates Just for You!",
#         "body": "Here are your personalized MLB updates for the week."
#     })

# # Load the main user database
# with open("database/users.json", "r") as user_file:
#     users = json.load(user_file)

# for user in users:
#     username = user["username"]
#     details_path = f"database/details/{username}.json"

#     if os.path.exists(details_path):
#         with open(details_path, "r") as details_file:
#             user_details = json.load(details_file)

#         # Get all questions except notifications
#         eligible_questions = [q for q in user_details["questions"] if q["id"] != "notifications"]
        
#         # Select one random question
#         random_question = random.choice(eligible_questions)
#         question_id = random_question["id"]
        
#         # Get the answer based on question type
#         if question_id in ["favorite_teams", "favorite_players"]:
#             random_ans = random.choice(random_question["answer"])
#             answer = random.choice(answer)
#         else:
#             answer = random_question["answer"]

#         # Get notification frequency
#         notification_answer = next(q["answer"] for q in user_details["questions"] if q["id"] == "notifications")

#         # Get selected team for email context
#         selected_team = next((q["answer"] for q in user_details["questions"] if q["id"] == "selected_team"), None)

#         # Generate email prompts
#         email_prompts = generate_email_prompts(question_id, answer, selected_team)

#         # Print results
#         print(f"User: {username}")
#         print(f"Question Type: {question_id}")
#         print(f"Answer: {answer}")
#         print(f"Notification Frequency: {notification_answer}")
#         print(f"Email Subject: {email_prompts['subject']}")
#         print(f"Email Body: {email_prompts['body']}\n")
#     else:
#         print(f"Details file for user '{username}' does not exist.\n")
