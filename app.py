from flask import Flask, render_template, jsonify, request
import random
import string

app = Flask(__name__)

# In-memory game storage (simple, not persistent)
games = {}


def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/create_game')
def create_game():
    code = generate_code()
    games[code] = {
        "players": [],
        "scores": [0, 0]
    }
    return jsonify({"code": code})


@app.route('/join_game')
def join_game():
    code = request.args.get('code')

    if code not in games:
        return jsonify({"error": "Invalid code"}), 400

    if len(games[code]["players"]) >= 2:
        return jsonify({"error": "Game full"}), 400

    games[code]["players"].append("Player")

    return jsonify({"message": "Joined", "players": len(games[code]["players"])})


@app.route('/toss')
def toss():
    code = request.args.get('code')

    if code not in games:
        return jsonify({"error": "Invalid game"}), 400

    result = random.choice(['Heads', 'Tails'])

    if result == "Heads":
        games[code]["scores"][0] += 1
    else:
        games[code]["scores"][1] += 1

    return jsonify({
        "result": result,
        "scores": games[code]["scores"]
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
