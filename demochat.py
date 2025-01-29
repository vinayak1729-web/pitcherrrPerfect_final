from flask import Flask, render_template, request
import statsapi

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    boxscore = None
    if request.method == 'POST':
        game_pk = request.form.get('game_pk')
        if game_pk:
            try:
                boxscore = statsapi.boxscore(game_pk)
                print(boxscore)
            except Exception as e:
                boxscore = f"An error occurred: {e}"
                
    return render_template('boxscore.html', boxscore=boxscore)

if __name__ == '__main__':
    app.run(debug=True)
