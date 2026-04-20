from flask import Flask, render_template, jsonify
import random

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/toss')
def toss():
    result = random.choice(['Heads', 'Tails'])
    return jsonify({'result': result})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
