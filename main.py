import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>Kaivor News is Online!</h1><p>Flask server is running successfully.</p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
