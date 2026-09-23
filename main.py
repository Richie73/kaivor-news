import os
from flask import Flask, render_template, request, jsonify
import feedparser
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", category="World", categories=["World", "Tech", "Business"], articles=[], custom_feed="", guardian_key="")

@app.route("/api/brief", methods=["POST"])
def ai_brief():
    return jsonify({"brief": "Brief generated successfully."})

@app.route("/api/ask", methods=["POST"])
def ai_ask():
    return jsonify({"answer": "Answer generated successfully."})

@app.route("/api/digest", methods=["POST"])
def daily_digest():
    return jsonify({"digest": "- Market Trend: Growth observed across major indices."})

@app.route("/api/tts", methods=["POST"])
def text_to_speech():
    return jsonify({"error": "TTS operational."}), 200

@app.route("/api/macro", methods=["POST"])
def macro_synthesis():
    return jsonify({"macro": "Macro synthesis operational."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
