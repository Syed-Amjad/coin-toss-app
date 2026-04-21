from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, join_room
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cointoss_arena_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

games = {}  # code -> game dict


def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _get_names(game):
    names = ['Player 1', 'Player 2']
    for p in game['players'].values():
        names[p['index']] = p['name']
    return names


def _full_state(code):
    """Broadcast full game state to all players in room."""
    game = games[code]
    names = _get_names(game)
    socketio.emit('state_sync', {
        'player_count': len(game['players']),
        'names':        names,
        'scores':       game['scores'],
        'whose_turn':   game['whose_turn'],
        'game_over':    game['game_over'],
        'rounds':       game['rounds'],
    }, room=code)


# ─── REST ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/create_game')
def create_game():
    code = generate_code()
    games[code] = {
        'players':          {},   # sid -> {name, index}
        'scores':           [0, 0],
        'whose_turn':       0,    # index (0 or 1) of current player
        'rounds':           0,
        'max_score':        2,
        'game_over':        False,
        'host_sid':         None,
        'toss_locked':      False, # prevent duplicate tosses
    }
    return jsonify({'code': code})


# ─── Socket events ────────────────────────────────────────────────────────────

@socketio.on('join_game')
def handle_join(data):
    code = (data.get('code') or '').strip().upper()
    name = (data.get('name') or '').strip() or 'Player'
    sid  = request.sid

    if code not in games:
        emit('error', {'msg': 'Game not found. Check the code and try again.'})
        return

    game = games[code]

    if game['game_over']:
        emit('error', {'msg': 'This game has already ended. Ask the host to reset.'})
        return

    # Reject 3rd+ player (unless it's a reconnecting known sid)
    if len(game['players']) >= 2 and sid not in game['players']:
        emit('error', {'msg': 'Game is full — only 2 players allowed.'})
        return

    join_room(code)

    # Register new player
    if sid not in game['players']:
        idx = len(game['players'])   # 0 for first, 1 for second
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

    _full_state(code)

    # Start game when both players are present
    if len(game['players']) == 2:
        # Randomly and fairly decide who goes first
        first = random.randint(0, 1)
        game['whose_turn'] = first
        names = _get_names(game)
        socketio.emit('game_start', {
            'names':      names,
            'whose_turn': first,
            'scores':     game['scores'],
        }, room=code)


@socketio.on('toss')
def handle_toss(data):
    code = (data.get('code') or '').strip().upper()
    sid  = request.sid

    if code not in games:
        emit('error', {'msg': 'Game not found.'})
        return

    game = games[code]

    if game['game_over']:
        emit('error', {'msg': 'Game over! Reset to play again.'})
        return

    if len(game['players']) < 2:
        emit('error', {'msg': 'Still waiting for your opponent to join.'})
        return

    # Silently ignore double-tap
    if game['toss_locked']:
        return

    player = game['players'].get(sid)
    if not player:
        emit('error', {'msg': 'You are not part of this game.'})
        return

    if player['index'] != game['whose_turn']:
        emit('error', {'msg': "Not your turn — wait for your opponent!"})
        return

    # ── LOCK & TOSS ───────────────────────────────────────────────────────────
    game['toss_locked'] = True

    # Coin face is COSMETIC only — purely for display.
    # The round winner is a separate independent fair 50/50 pick.
    # This removes the old bug where Heads always = Player 1 wins.
    coin_face    = random.choice(['Heads', 'Tails'])
    winner_index = random.randint(0, 1)   # true 50/50, unrelated to coin face

    game['scores'][winner_index] += 1
    game['rounds'] += 1
    game['toss_locked'] = False

    # Check if match is won
    match_winner_name = None
    if game['scores'][winner_index] >= game['max_score']:
        game['game_over'] = True
        match_winner_name = _get_names(game)[winner_index]

    # Winner of round gets next turn (mirrors real coin-toss game UX)
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
        'rounds':            game['rounds'],
    }, room=code)


@socketio.on('reset_game')
def handle_reset(data):
    code = (data.get('code') or '').strip().upper()

    if code not in games:
        emit('error', {'msg': 'Game not found.'})
        return

    game = games[code]
    game['scores']     = [0, 0]
    game['rounds']     = 0
    game['game_over']  = False
    game['toss_locked'] = False

    # Random first turn on every reset — keeps it fair and exciting
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
            game['toss_locked'] = False
            socketio.emit('player_left', {'name': left_name}, room=code)
            # Purge empty games to free memory
            if not game['players']:
                del games[code]
            break


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=False)
