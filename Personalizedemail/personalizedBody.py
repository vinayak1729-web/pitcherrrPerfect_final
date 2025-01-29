


def generate_email_body(username, question_id, answer, selected_team):
  return f"""
  <div style="font-family: Arial, sans-serif; line-height: 1.6;">
  <p>Hey {username},</p>
  <p>Here is your daily update from Pitcher Perfect!</p>

    <p>Today's Question : {question_id}</p>
    <p>Today's Answer : {answer}</p>

  <p>We hope you enjoy it. Keep rocking!</p>

  <p>Best,<br>
  The Pitcher Perfect Crew</p>
</div>
"""