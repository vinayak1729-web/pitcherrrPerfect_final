from flask import Flask, render_template, request, Response, jsonify
import requests
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
from num2words import num2words
import re
import statsapi
import pyttsx3
from google.cloud import translate_v2 as translate_client # Import Translation Client

load_dotenv()
app = Flask(__name__)

genai.configure(api_key=os.getenv("API_KEY"))

default_prompt = """You are a passionate baseball commentator bringing the game to life. Given the following details:
Teams playing: {teams}, Venue: {venue}, Date: {date}, Inning-by-inning breakdown: {inning_plays}, Play descriptions: {play_descriptions}, Final score: {final_score}.
Deliver an energetic, concise highlight reel focusing on game-changing moments, home runs with extra flair, clutch plays, final result drama. Use authentic baseball terminology and maintain high energy. Keep it under 3-4 key moments. End with the final score and what this means for both teams. Include Key play by play moments within the highlights of the game, home runs, cluth play, final result drama.
"""

generation_config = {
    "temperature": 0.7, # Lowered temperature for more consistent output
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    system_instruction=default_prompt + " "
)
import json
def stream_gemini_response(user_input, game_pk):
    try:
        chat_session = model.start_chat()
        response = chat_session.send_message(user_input, stream=True)
        
        has_yielded = False
        for chunk in response:
            has_yielded = True
            yield f"data: {chunk.text}\n\n"
        
        if not has_yielded:
            game_details = get_essential_game_info(game_pk)
            fallback = generate_fallback_commentary(game_details)
            # Send a single, formatted fallback response
            yield f"data: {'\\n'.join(fallback)}\n\n"
            
    except Exception as e:
        game_details = get_essential_game_info(game_pk)
        fallback = generate_fallback_commentary(game_details)
        # Send a single, formatted fallback response
        yield f"data: {'\\n'.join(fallback)}\n\n"

# --- MLB API Data Fetching ---
MLB_API_URL = 'https://statsapi.mlb.com/api/v1/schedule'
def fetch_game_data(game_pk):
    response = requests.get(f"{MLB_API_URL}?gamePk={game_pk}")
    game_info = response.json().get("dates", [])[0].get("games", [])[0]

    return {
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

# --- Essential Game Info ---
def get_essential_game_info(game_pk):
    game_data = fetch_game_data(game_pk)
    teams_and_score = {
        'matchup': f"{game_data['away_team']} vs {game_data['home_team']}",
        'final_score': f"{game_data['away_score']} - {game_data['home_score']}",
        'venue': game_data['venue'],
        'date': game_data['game_date']
    }

    game = statsapi.get('game', {'gamePk': game_pk})
    all_plays = game.get('liveData', {}).get('plays', {}).get('allPlays', [])
    inning_plays = []
    play_descriptions = [] # List to store play descriptions
    for play in all_plays:
        if play.get('about', {}).get('isComplete', False):
            inning_plays.append({
                'inning': f"{'Top' if play['about']['halfInning'] == 'top' else 'Bottom'} {play['about']['inning']}",
                'description': play['result'].get('description', ''),
                'score': f"{play['result'].get('awayScore', 0)}-{play['result'].get('homeScore', 0)}"
            })
            play_descriptions.append(play['result'].get('description', '')) # Add play description

    return {
        'game_info': teams_and_score,
        'plays': inning_plays,
        'play_descriptions': play_descriptions, # Include play descriptions in returned data
        'game_data': game_data
    }

# --- Fallback Commentary Generator ---
def generate_fallback_commentary(game_data):
    away_score, home_score = map(int, game_data['game_info']['final_score'].split(' - '))
    teams = game_data['game_info']['matchup'].split(' vs ')
    winning_team = teams[0] if away_score > home_score else teams[1]

    commentary = [
        f"⚾ WELCOME TO {game_data['game_info']['venue'].upper()}! ⚾",
        f"Today's matchup: {game_data['game_info']['matchup']} on {game_data['game_info']['date']}",
        "=" * 50
    ]

    current_inning = ""
    for play in game_data['plays']:
        if play['inning'] != current_inning:
            current_inning = play['inning']
            commentary.append(f"\n🎯 {current_inning.upper()}")

        commentary.append(f"• {play['description']}")
        commentary.append(f"Score Update: {play['score']}")

    commentary.extend([
        "\n🏆 FINAL WRAP",
        "=" * 50,
        f"{winning_team} takes this one!",
        f"Final Score: {game_data['game_info']['final_score']}",
        "\n📊 GAME HIGHLIGHTS",
        f"Venue: {game_data['game_info']['venue']}",
        f"Matchup: {game_data['game_info']['matchup']}",
        f"Date: {game_data['game_info']['date']}"
    ])

    return commentary

# --- Text Cleaning and Number Conversion ---
def convert_numbers_to_words(text):
    words = text.split()
    for i, word in enumerate(words):
        cleaned_word = word.replace('-', '').replace('.', '')
        if cleaned_word.isdigit():
            words[i] = num2words(int(cleaned_word))
        elif '-' in word and all(part.isdigit() for part in word.split('-')):
            nums = word.split('-')
            words[i] = f"{num2words(int(nums[0]))} to {num2words(int(nums[1]))}"
    return ' '.join(words)

import pyttsx3
from googletrans import Translator
import os

# Initialize translator and TTS engine
translator = Translator()
engine = pyttsx3.init()

def setup_voice_options():
    voices = engine.getProperty('voices')
    voice_options = {
        'male': [v for v in voices if 'male' in v.name.lower()][0],
        'female': [v for v in voices if 'female' in v.name.lower()][0]
    }
    return voice_options

def speak(text, language='en', gender='female', output_dir='static/audio'):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"speech_{hash(text)}_{language}_{gender}.wav"
    audio_path = os.path.join(output_dir, filename)
    
    try:
        # Translate if needed
        if language != 'en':
            translated = translator.translate(text, dest=language)
            text = translated.text
        
        # Set voice properties
        voices = setup_voice_options()
        engine.setProperty('voice', voices[gender].id)
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 1.0)
        
        # Save to file
        engine.save_to_file(text, audio_path)
        engine.runAndWait()
        
        return {'audio_url': f'/static/audio/{filename}', 'text': text}
    except Exception as e:
        print(f"TTS error: {e}")
        return {'error': str(e)}

@app.route('/speak', methods=['POST'])
def speak_route():
    text = request.form.get('text', '')
    language = request.form.get('language', 'en')
    gender = request.form.get('gender', 'female')
    
    result = speak(text, language, gender)
    return jsonify(result)

# --- Main Routes ---
@app.route('/')
def index():
    return render_template('c.html')

@app.route('/stream_ai_commentary/<game_pk>')
def stream_ai_commentary(game_pk):
    language = request.args.get('language', 'en')
    game_details = get_essential_game_info(game_pk)
    
    try:
        prompt_data = {
            'teams': game_details['game_info']['matchup'],
            'venue': game_details['game_info']['venue'],
            'date': game_details['game_info']['date'],
            'inning_plays': "\n".join(f"{p['inning']}: {p['description']} (Score: {p['score']})" for p in game_details['plays']),
            'play_descriptions': "\n".join(game_details['play_descriptions']),
            'final_score': game_details['game_info']['final_score']
        }
        
        user_input = default_prompt.format(**prompt_data)
        return Response(stream_gemini_response(user_input,game_pk), mimetype='text/event-stream')
        
    except Exception:
        # Direct fallback if prompt formatting fails
        commentary = generate_fallback_commentary(game_details)
        return Response(f"data: {' '.join(commentary)}\n\n", mimetype='text/event-stream')

@app.route('/get_ai_commentary/<game_pk>')
def get_ai_commentary(game_pk):
    game_details = get_essential_game_info(game_pk)
    commentary = generate_fallback_commentary(game_details)
    return jsonify({'commentary': commentary,
                    'game_info': game_details['game_info']})


@app.route('/game/<game_pk>')
def game_highlights(game_pk):
    game_details = fetch_game_data(game_pk)
    return render_template('c.html', game_data=game_details, game_pk=game_pk)


if __name__ == '__main__':
    app.run(debug=True)