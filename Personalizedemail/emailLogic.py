# email_automation/email_logic.py
from datetime import datetime, timedelta
from dataHandler import load_email_notification_history,save_email_notification_history
def check_due_email_notification(username, user_data, email_history):
    """Checks if a user is due for an email notification based on their history and frequency."""
    if not user_data:
      return False
    notification_frequency = user_data["notification_frequency"].lower()
    if username not in email_history:
       return True
    last_notification_str = email_history[username].get("last_sent_date")
    if not last_notification_str:
      return True

    if notification_frequency == "never":
        return False

    last_notification = datetime.fromisoformat(last_notification_str)
    now = datetime.now()

    if notification_frequency == "daily":
        return now - last_notification >= timedelta(days=1)
    elif notification_frequency == "weekly":
        return now - last_notification >= timedelta(weeks=1)
    elif notification_frequency == "monthly":
        return now - last_notification >= timedelta(days=30) #Approximate
    return False

def update_email_history(username, question_id, email_history):
      if username not in email_history:
           email_history[username] = {
               "notification_history":[],
               "last_sent_date" : datetime.now().isoformat(),
           }
      else :
        email_history[username]["last_sent_date"] = datetime.now().isoformat()
      email_history[username]["notification_history"].append({
          "question_id": question_id,
          "timestamp": datetime.now().isoformat(),
      })
      save_email_notification_history(email_history)