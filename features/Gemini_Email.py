import json
import os
import random
import google.generativeai as genai
from dotenv import load_dotenv

def generate_email_subject(question_type, answer, team=None):
    subjects = {
        "fan_duration": f"🏆 {team} Fan for {answer} Years - Your Baseball Journey Continues!",
        "favorite_teams": f"⚾ {answer} Game Alert: Your Team is Ready to Shine!",
        "favorite_players": f"🌟 {answer}'s Latest Highlights Just for You!",
        "selected_team": f"⚾ Your {answer} Nation Weekly Roundup",
        "favorite_match": f"🔥 From {answer} to Today's Excitement",
    }
    return subjects.get(question_type, "⚾ Your Weekly MLB Insider Update")

# Enhanced Gemini prompt template
GEMINI_PROMPT_TEMPLATE = """
Create an engaging baseball fan email body with these specifics:
- Question Type: {question_type}
- Fan's Answer: {answer}
- Team: {team}
- Notification Frequency: {notification}

Key requirements:
- Maintain an enthusiastic, personal tone
- Include relevant statistics or upcoming events
- Add a clear call-to-action
- Keep it concise and engaging
- Focus on building fan community
- Include relevant game schedules or player stats if applicable
"""

# Load environment variables and configure Gemini
load_dotenv()
genai.configure(api_key=os.getenv("API_KEY"))

generation_config = {
    "temperature": 1.5,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config
)


def generate_email_prompts(question_type, answer, team=None):
    prompts = {
        "fan_duration": {
            "subject": f"Welcome {team} Fan of {answer} Years!",
            "body": f"As a dedicated fan who has followed MLB for {answer} years, we're excited to have you in our community."
        },
        "favorite_teams": {
            "subject": f"Your Team {answer} Has an Upcoming Match!",
            "body": f"Get ready to cheer for {answer}! We've got some exciting updates about your favorite team."
        },
        "favorite_players": {
            "subject": f"Latest Updates About {answer}",
            "body": f"Stay updated with the latest news and performance stats about {answer}."
        },
        "selected_team": {
            "subject": f"Welcome to {answer} Nation!",
            "body": f"Thanks for selecting {answer} as your team. Here's what's happening with your team this week."
        },
        "favorite_match": {
            "subject": f"Relive the Magic of {answer}",
            "body": f"Remember the excitement of {answer}? We've got similar thrilling matches coming up!"
        }
    }
    
    return prompts.get(question_type, {
        "subject": "MLB Updates Just for You!",
        "body": "Here are your personalized MLB updates for the week."
    })

# Load the main user database
with open("/PitcherPerfectmain/database/users.json", "r") as user_file:
    users = json.load(user_file)

for user in users:
    username = user["username"]
    details_path = f"/PitcherPerfectmain/database/details/{username}.json"

    if os.path.exists(details_path):
        with open(details_path, "r") as details_file:
            user_details = json.load(details_file)

        # Get all questions except notifications
        eligible_questions = [q for q in user_details["questions"] if q["id"] != "notifications"]
        
        # Select one random question
        random_question = random.choice(eligible_questions)
        question_id = random_question["id"]
        
        # Get the answer based on question type
        if question_id in ["favorite_teams", "favorite_players"]:
            random_ans = random.choice(random_question["answer"])
            answer = random.choice(answer)
        else:
            answer = random_question["answer"]

        # Get notification frequency
        notification_answer = next(q["answer"] for q in user_details["questions"] if q["id"] == "notifications")

        # Get selected team for email context
        selected_team = next((q["answer"] for q in user_details["questions"] if q["id"] == "selected_team"), None)

        # Generate email prompts
        email_prompts = generate_email_prompts(question_id, answer, selected_team)

        # Print results
        print(f"User: {username}")
        print(f"Question Type: {question_id}")
        print(f"Answer: {answer}")
        print(f"Notification Frequency: {notification_answer}")
        print(f"Email Subject: {email_prompts['subject']}")
        print(f"Email Body: {email_prompts['body']}\n")
    else:
        print(f"Details file for user '{username}' does not exist.\n")



# Inside your user processing loop:
subject = generate_email_subject(question_id, answer, selected_team)
gemini_prompt = GEMINI_PROMPT_TEMPLATE.format(
    question_type=question_id,
    answer=answer,
    team=selected_team,
    notification=notification_answer
)
email_body = model.generate_content(gemini_prompt).text

print(f"Subject: {subject}")
print(f"Body: {email_body}\n")
