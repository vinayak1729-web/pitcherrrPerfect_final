# from flask import Flask, render_template
# import statsapi

# def fetch_first_highlight(game_pk):
#     highlights = []
#     raw_highlights = statsapi.game_highlights(game_pk)
#     lines = raw_highlights.split('\n')
#     current_title, current_description = None, None
    
#     for line in lines:
#         if not line.strip():
#             continue
#         if line.startswith('https://') and line.endswith('.mp4'):
#             if current_title and current_description:
#                 highlights.append({
#                     'title': current_title,
#                     'description': current_description,
#                     'video_url': line.strip()
#                 })
#             break  # Only need the first highlight
#         elif '(' in line and ')' in line and any(x in line for x in ['00:', '01:', '02:']):
#             current_title = line.strip()
#         elif current_title and not current_description:
#             current_description = line.strip()
    
#     return highlights[0] if highlights else None

# def get_game_info(team_id):
#     game_pk = statsapi.last_game(team_id)
#     game_data = statsapi.get('game', {'gamePk': game_pk})
#     teams = game_data.get('gameData', {}).get('teams', {})
#     home_team = teams.get('home', {}).get('name', 'Unknown')
#     away_team = teams.get('away', {}).get('name', 'Unknown')
#     first_highlight = fetch_first_highlight(game_pk)
    
#     return home_team, away_team, first_highlight

# app = Flask(__name__)

# @app.route('/')
# def index():
#     team_id = 119  # Example team ID (change as needed)
#     home_team, away_team, highlight = get_game_info(147)
#     return render_template('latestvh.html', home_team=home_team, away_team=away_team, highlight=highlight)

# if __name__ == '__main__':
#     app.run(debug=True)


import json
import ast

def get_team_id(username):
    # Read username data from json file
    with open(f'database/details/{username}.json', 'r') as f:
        user_data = json.load(f)
    
    # Ensure it's a list before iterating
    if not isinstance(user_data, list):
        return None

    # Find the team selection data
    team_data = None
    for item in user_data:
        if isinstance(item, dict) and item.get('id') == 'selected_team':
            team_data = item
            break

    if team_data:
        try:
            # Extract team name from the answer string
            team_name = ast.literal_eval(team_data['answer'])[0]
            
            # Read team mapping from team.json
            with open('database/team.json', 'r') as f:
                team_mapping = json.load(f)
            
            # Search for team ID in all divisions
            for league in team_mapping.values():
                for division in league.values():
                    for team in division:
                        if team['name'] == team_name:
                            return team['id']
                            
        except (SyntaxError, ValueError):
            print("Error: Invalid format for 'answer' field.")
            return None

    return None

team_id = get_team_id("vinayak1729")
print(team_id)  # Will print 119 for Los Angeles Dodgers
