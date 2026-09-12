import os
import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

@app.route('/brief', methods=['POST'])
def brief():
    data = request.get_json()
    article_title = data.get('title', '')
    if not article_title:
        return jsonify({"summary": "No article title provided."})
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://kaivor-news.onrender.com", # Optional, helps OpenRouter rank your app
        "X-Title": "Kaivor News"
    }
    
    payload = {
        "model": "deepseek/deepseek-chat", # Or any model available on OpenRouter (e.g., openai/gpt-4o-mini)
        "messages": [
            {"role": "system", "content": "You are a sharp, concise news summarizer. Provide a 1-sentence summary of this news headline/topic concisely."},
            {"role": "user", "content": f"Summarize this news headline/topic concisely: {article_title}"}
        ],
        "stream": False
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            result = response.json()
            summary = result["choices"][0]["message"]["content"]
            return jsonify({"summary": summary})
    except Exception as e:
        print(f"OpenRouter API error: {e}")
        
    return jsonify({"summary": "Could not generate summary at this time."})
    
