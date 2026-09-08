#!/usr/bin/env python3
"""
Kaivor FP010 Automation & Bridge Validation Tool
Tests local OpenAI-compatible API server endpoints, model listing, 
and parameter handling for Open WebUI integration.
"""

import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(name, url, method="GET", data=None):
    print(f"[*] Testing {name} ({method} {url})...", end=" ")
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.status
            response_body = response.read().decode("utf-8")
            if status == 200:
                print("PASS (200 OK)")
                return json.loads(response_body) if response_body else {}
            else:
                print(f"FAIL (Status: {status})")
                return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def main():
    print("========================================================")
    print("KAIVOR FP010 BRIDGE VALIDATION SUITE")
    print("========================================================")
    
    # 1. Test Root / Health Endpoint
    health = test_endpoint("Health / Root", f"{BASE_URL}/")
    if health is None:
        print("\n[!] Error: Kaivor API server is not running or unreachable on port 8000.")
        print("Start it with: python -m core.api.openai_server")
        sys.exit(1)

    # 2. Test Model Listing (/v1/models)
    models = test_endpoint("OpenAI Models Endpoint", f"{BASE_URL}/v1/models")
    if models and "data" in models:
        model_ids = [m.get("id") for m in models["data"]]
        print(f"    Discovered models: {model_ids}")
        if "kaivor" not in model_ids:
            print("[!] Warning: 'kaivor' model ID not found in model list.")
    else:
        print("[!] Fail: Invalid model list structure.")

    # 3. Test Chat Completions (/v1/chat/completions) with Parameters
    payload = {
        "model": "kaivor",
        "messages": [
            {"role": "system", "content": "You are a precise technical assistant."},
            {"role": "user", "content": "System check: report status."}
        ],
        "temperature": 0.2
    }
    chat_res = test_endpoint("Chat Completions Bridge", f"{BASE_URL}/v1/chat/completions", method="POST", data=payload)
    if chat_res and "choices" in chat_res:
        content = chat_res["choices"][0]["message"]["content"]
        provider = chat_res.get("kaivor", {}).get("provider", "Unknown")
        print(f"    Provider routed: {provider}")
        print(f"    Assistant response snippet: {content[:80]}...")
        print("\n[SUCCESS] FP010 Bridge Validation Passed.")
    else:
        print("\n[FAIL] Chat completion failed to return expected OpenAI schema.")
        sys.exit(1)

if __name__ == "__main__":
    main()
