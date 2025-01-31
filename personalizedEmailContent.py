# personalizedEmailContent.py
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
import re
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

genai.configure(api_key=os.getenv("API_KEY"))

emailPrompt = """
You are an email generator specializing in creating personalized, engaging emails related to user submissions. You will receive a username, a question ID, an answer provided by the user, and a selected team. The selected team will be a team in Major League Baseball. You should use your knowledge of baseball and MLB teams to make the email more personalized and engaging. The email body should be based on a randomly selected template from the string provided below, and should acknowledge the user's answer and the team they've selected with some baseball-related flair.

Here are the variables:

*   `username`: (String) The name of the user.
*   `question_id`: (String) The ID of the question they answered.
*   `answer`: (String) The user's answer to the question.
*   `selected_team`: (String) The MLB team the user selected (e.g., "New York Yankees", "Los Angeles Dodgers", "Boston Red Sox").
"""
# Create the model
generation_config ={
"temperature": 1,
"top_p": 0.95,
"top_k": 64,
"max_output_tokens": 8192,
"response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
model_name="gemini-2.0-flash-exp",
generation_config=generation_config,
system_instruction=emailPrompt + " " 
)
def gemini_chat(user_input):
    try:
      chat_session = model.start_chat()
      response = chat_session.send_message(user_input)
      return response.text
    except Exception as e:
        print(f"Error during chat: {e}")
        return "An error occurred. Please try again."

def extract_subject_and_body(email_text):
  """Extracts the subject line and email body from a generated email, expects explicit subject line in generated email before full body html.
   Return none if no email and subject match available"""
  
  subject_match = re.search(r"Subject: (.*)(?=\n)", email_text,re.IGNORECASE)
  if subject_match:
    subject = subject_match.group(1).strip()

    # Find start of email after Subject line
    body_start_match = re.search(r"<html.*?>", email_text, re.IGNORECASE)
    if body_start_match:
      body_start_index = body_start_match.start()

      body = email_text[body_start_index:].strip() # body after <html> found
      return subject, body

  return None, None

def personalizedEmail(username,question_id,answer,team):
   email=gemini_chat(f"""
       Generate a personalized HTML email for {username} (a baseball fan). Here are their details:
     * Question ID: {question_id}
     * Answer: {answer}
     * Favorite Team: {team}.

     The email MUST have this output format ( with all fields )  :

     1.  Subject: Subject line should reflect content , mention baseball or MLB (or specific to answer or favourite player or team), use creative language . 
     2. HTML:  `<html><body >` ... content here using only valid and relevant tags. should not have errors when opening in browser . all content enclosed inside these tags
       The  body needs include  following  points in generated content  with values. all should  print as string content after processing:
         a. Address the user: Include personalized greetings to the user: {username} showing excitement related to player , or favorite team mentioned before
         b. Acknowledge  User answer ( and/ or fav player) to their  {question_id}: {answer}. (Include details, related stories about current impact on baseball game). Ensure not literal values , should correctly print  'Shohei Ohtani' and NOT '{answer}'. 
         c. Make a general enthusiastic and supporting baseball call : Support and recognize excitement related  favorite team: {team}, Include details like great recent performance.
     - Sign the email as:  <p>By PitcherPerfect From Suryaprabha</p>  
    - The Output should include subject, fully formed correct body in `html`, with  the full content from `a`,`b` and `c`.

    -Do not return raw parameter variable with their parameter keys. e.g, it should not print  literal value such as  'username' '{username}'  etc inside Email Body .

    Response : Provide email output string content only in this format without preambles :

    Subject: The Subject here
    <html><body > ......full body here </body></html>

       
   
  """)
   subject, body = extract_subject_and_body(email)
   return subject, body


print(personalizedEmail("vinu","fav_player","Shohei Ohtani","Dodgers"))