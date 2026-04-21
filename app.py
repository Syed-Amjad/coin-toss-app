from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, join_room
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cointoss_arena_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

games = {}

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

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

# ─── REST ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_game')
def create_game():
    code = generate_code()
    games[code] = {
        'players':          {},
        'scores':           [0, 0],
        'whose_turn':       0,
        'rounds':           0,
        'max_score':        2,
        'game_over':        False,
        'host_sid':         None,
        'toss_in_progress': False,
    }
    return jsonify({'code': code})

# ─── Socket events ────────────────────────────────────────────────────────────

@socketio.on('join_game')
def handle_join(data):
    code = data.get('code', '').strip().upper()
    name = (data.get('name', '') or '').strip() or 'Player'
    sid  = request.sid

    if code not in games:
        emit('error', {'msg': 'Game not found. Check the code and try again.'})
        return

    game = games[code]

    if game['game_over']:
        emit('error', {'msg': 'This game has already ended.'})
        return

    if len(game['players']) >= 2 and sid not in game['players']:
        emit('error', {'msg': 'Game is full — only 2 players allowed.'})
        return

    join_room(code)

    if sid not in game['players']:
        idx = len(game['players'])
        game['players'][sid] = {'name': name, 'index': idx}
        if idx == 0:
            game['host_sid'] = sid

    info = game['players'][sid]
    emit('joined', {
        'code':         code,
        'your_index':   info['index'],
        'your_name':    info['name'],
        'player_count': len(game['players']),
    })

    _broadcast_state(code)

    if len(game['players']) == 2:
        names = _get_names(game)
        # Randomly decide who goes first — unbiased
        first = random.randint(0, 1)
        game['whose_turn'] = first
        socketio.emit('game_start', {
            'names':      names,
            'whose_turn': first,
        }, room=code)


@socketio.on('toss')
def handle_toss(data):
    code = data.get('code', '').strip().upper()
    sid  = request.sid

    if code not in games:
        emit('error', {'msg': 'Game not found.'})
        return

    game = games[code]

    if game['game_over']:
        emit('error', {'msg': 'Game over. Reset to play again.'})
        return

    if len(game['players']) < 2:
        emit('error', {'msg': 'Still waiting for opponent.'})
        return

    if game['toss_in_progress']:
        return  # silently ignore duplicate toss

    player = game['players'].get(sid)
    if not player:
        emit('error', {'msg': 'You are not in this game.'})
        return

    if player['index'] != game['whose_turn']:
        emit('error', {'msg': "Wait — it's your opponent's turn!"})
        return

    game['toss_in_progress'] = True

    # ── FAIR TOSS LOGIC ───────────────────────────────────────────────────────
    # coin_face is purely cosmetic display (Heads/Tails text on the coin).
    # round_winner is a completely independent fair 50/50 random choice.
    # This eliminates the old bug where Heads always meant Player 1 wins.
    coin_face    = random.choice(['Heads', 'Tails'])
    winner_index = random.randint(0, 1)
    # ─────────────────────────────────────────────────────────────────────────

    game['scores'][winner_index] += 1
    game['rounds'] += 1
    game['toss_in_progress'] = False

    match_winner_name = None
    if game['scores'][winner_index] >= game['max_score']:
        game['game_over'] = True
        match_winner_name = _get_names(game)[winner_index]

    # Winner of round tosses next (fair, engaging)
    game['whose_turn'] = winner_index

    names = _get_names(game)
    socketio.emit('toss_result', {
        'coin_face':         coin_face,
        'winner_index':      winner_index,
        'round_winner_name': names[winner_index],
        'scores':            game['scores'],
        'whose_turn':        game['whose_turn'],
        'turn_name':         names[game['whose_turn']],
        'game_over':         game['game_over'],
        'winner_name':       match_winner_name,
        'names':             names,
    }, room=code)


@socketio.on('reset_game')
def handle_reset(data):
    code = data.get('code', '').strip().upper()
    if code not in games:
        emit('error', {'msg': 'Game not found.'})
        return

    game = games[code]
    game['scores']           = [0, 0]
    game['rounds']           = 0
    game['game_over']        = False
    game['toss_in_progress'] = False

    first = random.randint(0, 1)
    game['whose_turn'] = first

    names = _get_names(game)
    socketio.emit('game_reset', {
        'names':      names,
        'scores':     [0, 0],
        'whose_turn': first,
        'turn_name':  names[first],
    }, room=code)


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    for code, game in list(games.items()):
        if sid in game['players']:
            left_name = game['players'][sid]['name']
            del game['players'][sid]
            game['toss_in_progress'] = False
            socketio.emit('player_left', {'name': left_name}, room=code)
            if not game['players']:
                del games[code]
            break


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=False)

