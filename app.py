from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cointoss_secret_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Game storage
games = {}

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ─── REST endpoints (kept for backward compat) ───────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_game')
def create_game():
    code = generate_code()
    games[code] = {
        "players": {},          # sid -> {name, index}
        "scores": [0, 0],
        "whose_turn": 0,        # 0 = player1, 1 = player2
        "rounds": 0,
        "max_score": 2,
        "game_over": False,
        "host_sid": None,
    }
    return jsonify({"code": code})

# ─── Socket events ────────────────────────────────────────────────────────────

@socketio.on('join_game')
def handle_join(data):
    code = data.get('code', '').strip().upper()
    name = data.get('name', 'Player').strip() or 'Player'

    if code not in games:
        emit('error', {'msg': 'Game not found. Check the code and try again.'})
        return

    game = games[code]

    if game['game_over']:
        emit('error', {'msg': 'This game has already ended.'})
        return

    # Reconnect if same sid somehow already in (rare)
    sid = request.sid

    # Allow at most 2 players
    if len(game['players']) >= 2 and sid not in game['players']:
        emit('error', {'msg': 'Game is full (2 players max).'})
        return

    join_room(code)

    if sid not in game['players']:
        idx = len(game['players'])   # 0 or 1
        game['players'][sid] = {'name': name, 'index': idx}
        if idx == 0:
            game['host_sid'] = sid
    
    player_info = game['players'][sid]

    emit('joined', {
        'code': code,
        'your_index': player_info['index'],
        'your_name': player_info['name'],
        'player_count': len(game['players']),
    })

    # Broadcast updated lobby to all in room
    _broadcast_state(code)

    # If 2 players are now in, start the game
    if len(game['players']) == 2:
        names = _get_names(game)
        socketio.emit('game_start', {
            'names': names,
            'whose_turn': game['whose_turn'],
        }, room=code)


@socketio.on('toss')
def handle_toss(data):
    code = data.get('code', '').strip().upper()
    sid = request.sid

    if code not in games:
        emit('error', {'msg': 'Game not found.'})
        return

    game = games[code]

    if game['game_over']:
        emit('error', {'msg': 'Game is already over.'})
        return

    if len(game['players']) < 2:
        emit('error', {'msg': 'Waiting for opponent to join.'})
        return

    player = game['players'].get(sid)
    if player is None:
        emit('error', {'msg': 'You are not in this game.'})
        return

    if player['index'] != game['whose_turn']:
        emit('error', {'msg': "It's not your turn!"})
        return

    # Do the toss
    result = random.choice(['Heads', 'Tails'])
    winner_index = 0 if result == 'Heads' else 1
    game['scores'][winner_index] += 1
    game['rounds'] += 1

    # Check win
    winner_name = None
    if game['scores'][winner_index] >= game['max_score']:
        game['game_over'] = True
        winner_name = _get_names(game)[winner_index]

    # Alternate turn
    game['whose_turn'] = 1 - game['whose_turn']

    names = _get_names(game)
    payload = {
        'result': result,
        'winner_index': winner_index,
        'round_winner_name': names[winner_index],
        'scores': game['scores'],
        'whose_turn': game['whose_turn'],
        'turn_name': names[game['whose_turn']],
        'game_over': game['game_over'],
        'winner_name': winner_name,
        'names': names,
    }
    socketio.emit('toss_result', payload, room=code)


@socketio.on('reset_game')
def handle_reset(data):
    code = data.get('code', '').strip().upper()

    if code not in games:
        emit('error', {'msg': 'Game not found.'})
        return

    game = games[code]
    game['scores'] = [0, 0]
    game['whose_turn'] = 0
    game['rounds'] = 0
    game['game_over'] = False

    names = _get_names(game)
    socketio.emit('game_reset', {
        'names': names,
        'scores': [0, 0],
        'whose_turn': 0,
        'turn_name': names[0],
    }, room=code)


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    for code, game in list(games.items()):
        if sid in game['players']:
            left_name = game['players'][sid]['name']
            del game['players'][sid]
            socketio.emit('player_left', {'name': left_name}, room=code)
            # Clean up empty games
            if len(game['players']) == 0:
                del games[code]
            break


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_names(game):
    names = ['Player 1', 'Player 2']
    for p in game['players'].values():
        names[p['index']] = p['name']
    return names

def _broadcast_state(code):
    game = games[code]
    names = _get_names(game)
    socketio.emit('lobby_update', {
        'player_count': len(game['players']),
        'names': names,
        'scores': game['scores'],
        'whose_turn': game['whose_turn'],
    }, room=code)


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=False)
