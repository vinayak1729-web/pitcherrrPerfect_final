# email_automation/main.py
from dataHandler import generate_user_email_data, load_users ,load_email_notification_history
from send_Personalized_email import send_personalized_email
from emailLogic import check_due_email_notification, update_email_history

if __name__ == "__main__":
    user_email_data = generate_user_email_data()
    email_history = load_email_notification_history()
    users = load_users()

    for username, user_data in user_email_data.items():
        if user_data:
            if check_due_email_notification(username, user_data, email_history):
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
                    if send_personalized_email(recipient_email, username, question_id, answer, selected_team):
                      update_email_history(username, question_id, email_history)


                else:
                    print(f"Could not find email address for user {username}")

            else:
                print(f"Email notification not due for {username} yet")
        else:
            print(f"No data available for user: {username}")