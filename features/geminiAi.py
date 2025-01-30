import google.generativeai as genai
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

genai.configure(api_key=os.getenv("API_KEY"))

defaultprompt = """Write a friendly and engaging email for baseball fans.
Generate a captivating subject line and body content centered around baseball. 
The theme can focus on any notable player, an exciting match, team highlights,
upcoming games, or iconic moments in baseball history. The tone should be enthusiastic 
and conversational, making the reader feel part of the action. Avoid using specific genders or names, 
and make the content universally appealing. Ensure the email is concise, with a strong call to action for
fans to stay engaged (e.g., watch a game, buy merchandise, or join a fan community).
"""
# Create the model
generation_config ={
"temperature": 2,
"top_p": 0.95,
"top_k": 64,
"max_output_tokens": 8192,
"response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
model_name="gemini-1.5-pro",
generation_config=generation_config,
system_instruction=defaultprompt + " " 
)

def gemini_chat(user_input):
  try:
    chat_session = model.start_chat()
    response = chat_session.send_message(user_input)

    # Simulate streaming by printing output with a small delay
    for chunk in response.text.split(" "):
      print(chunk, end=" ", flush=True)
      time.sleep(0.1)  # Adjust delay as needed

  except Exception as e:
    print(f"Error during chat: {e}")
    return "An error occurred. Please try again."
