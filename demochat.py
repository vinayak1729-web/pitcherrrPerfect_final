from flask import Flask, render_template, jsonify
import json

app = Flask(__name__)

def load_user_team_data():
    with open('database/user_teams/user_team_data.json', 'r') as file:
        return json.load(file)

@app.route('/')
def index():
    user_data = load_user_team_data()
    players = user_data['shinde9271']['M']['selected_players']
    return render_template('my_team.html', players=players)

if __name__ == '__main__':
    app.run(debug=True)
