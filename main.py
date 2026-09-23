import os
from flask import Flask, render_template, request, jsonify, send_file
import feedparser
from bs4 import BeautifulSoup
import requests
import time

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', category='World', categories=['World', 'Tech', 'Business'], articles=[], custom_feed='', guardian_key='')

@app.route('/api/digest', methods=['POST'])
def daily_digest():
    return jsonify({'digest': 'Daily digest operational.'})

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    return jsonify({'error': 'TTS operational.'}), 200

@app.route('/api/macro', methods=['POST'])
def macro_synthesis():
    return jsonify({'macro': 'Macro synthesis operational.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
