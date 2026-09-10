import os
import requests
from flask import jsonify, request

# Set your DeepSeek API key (or configure it securely in your Render Environment Variables)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-a4c7cb47c96e46a58c4787116202d031")

@app.route('/brief', methods=['POST'])
def brief_article():
    data = request.get_json()
    article_title = data.get('title', '')
    article_link = data.get('link', '')

    if not article_title:
        return jsonify({"summary": "No article title provided."})

    try:
        # Call DeepSeek PAYG API using its OpenAI-compatible endpoint
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a sharp, concise news summarizer. Provide a 3-sentence summary of the news topic."},
                {"role": "user", "content": f"Summarize this news headline/topic concisely: {article_title}"}
            ],
            "stream": False
        }
        response = requests.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers, timeout=5.0)
        
        if response.status_code == 200:
            result = response.json()
            summary = result['choices'][0]['message']['content']
            return jsonify({"summary": summary})
    except Exception as e:
        print(f"DeepSeek API error: {e}")

    return jsonify({"summary": "Could not generate summary at this time."})
    
