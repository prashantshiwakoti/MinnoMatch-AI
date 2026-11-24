"""
MinnoMatch AI - Flask Application for Metropolia UAS
Multidisciplinary Innovation Project (MINNO) Synthesizer & Matcher
"""

import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, Response
from dotenv import load_dotenv, set_key
from ai_engine import AIEngine, CAMPUS_FACULTIES

ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(ENV_FILE)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'metropolia-ai-minno-secret-2026')

CHALLENGES_FILE = os.path.join(os.path.dirname(__file__), 'data', 'challenges.json')

# Initialize AI engine with environment keys if present
initial_provider = os.getenv('LLM_PROVIDER', 'gemini')
initial_key = os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY') or os.getenv('LLM_API_KEY')
ai_engine = AIEngine(api_key=initial_key, provider=initial_provider)

def load_challenges():
    if not os.path.exists(CHALLENGES_FILE):
        return []
    try:
        with open(CHALLENGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading challenges: {e}")
        return []

def save_challenges(challenges):
    os.makedirs(os.path.dirname(CHALLENGES_FILE), exist_ok=True)
    with open(CHALLENGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(challenges, f, indent=2, ensure_ascii=False)

def persist_env_variable(key_name, value):
    """Safely writes key to .env file and updates os.environ"""
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.write("# MinnoMatch AI Environment Configuration\n")
    if value:
        set_key(ENV_FILE, key_name, value)
        os.environ[key_name] = value
    else:
        # Clear variable from environment
        os.environ.pop(key_name, None)
        try:
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                lines = [line for line in f if not line.startswith(f"{key_name}=")]
            with open(ENV_FILE, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        except Exception:
            pass

@app.route('/')
def index():
    challenges = load_challenges()
    return render_template('index.html', challenges=challenges, faculties=CAMPUS_FACULTIES)

@app.route('/api/status', methods=['GET'])
def get_status():
    challenges = load_challenges()
    key_preview = ""
    if ai_engine.api_key and len(ai_engine.api_key) > 8:
        key_preview = f"{ai_engine.api_key[:4]}...{ai_engine.api_key[-4:]}"
    
    return jsonify({
        "status": "online",
        "app_name": "MinnoMatch AI",
        "institution": "Metropolia University of Applied Sciences",
        "provider": ai_engine.provider,
        "has_live_key": bool(ai_engine.api_key),
        "key_preview": key_preview,
        "env_persisted": os.path.exists(ENV_FILE),
        "total_challenges": len(challenges),
        "campuses": ["Karamalmi", "Myllypuro", "Arabia", "Myyrmäki"]
    })

@app.route('/api/challenges', methods=['GET', 'POST'])
def handle_challenges():
    challenges = load_challenges()
    if request.method == 'POST':
        data = request.get_json() or {}
        new_challenge = {
            "id": f"minno-{uuid.uuid4().hex[:6]}",
            "title": data.get("title", "Untitled MINNO Project"),
            "challenge_statement": data.get("challenge_statement", ""),
            "sdgs": data.get("sdgs", ["SDG 9: Industry, Innovation and Infrastructure"]),
            "campus_synergy": data.get("campus_synergy", []),
            "work_packages": data.get("work_packages", []),
            "academic_potential": data.get("academic_potential", ""),
            "milestones": data.get("milestones", [])
        }
        challenges.insert(0, new_challenge)
        save_challenges(challenges)
        return jsonify({"success": True, "challenge": new_challenge}), 201
    
    return jsonify({"success": True, "challenges": challenges})

@app.route('/api/synthesize', methods=['POST'])
def synthesize():
    data = request.get_json() or {}
    prompt = data.get("prompt", "")
    if not prompt.strip():
        return jsonify({"error": "Problem statement cannot be empty"}), 400
    
    result = ai_engine.synthesize_challenge(prompt)
    return jsonify({"success": True, "result": result})

@app.route('/api/match-student', methods=['POST'])
def match_student():
    data = request.get_json() or {}
    challenges = load_challenges()
    matches = ai_engine.match_student(data, challenges)
    return jsonify({"success": True, "matches": matches})

@app.route('/api/export-charter', methods=['POST'])
def export_charter():
    data = request.get_json() or {}
    charter_md = ai_engine.generate_project_charter(data)
    return jsonify({"success": True, "markdown": charter_md})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    global ai_engine
    data = request.get_json() or {}
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "gemini").lower()
    persist = data.get("persist", True)
    
    # Update environment variables and write to .env if requested
    if persist:
        persist_env_variable('LLM_PROVIDER', provider)
        if provider == "openai":
            persist_env_variable('OPENAI_API_KEY', api_key)
            persist_env_variable('GEMINI_API_KEY', "")
        elif provider == "gemini":
            persist_env_variable('GEMINI_API_KEY', api_key)
            persist_env_variable('OPENAI_API_KEY', "")
        else: # simulated / local
            persist_env_variable('GEMINI_API_KEY', "")
            persist_env_variable('OPENAI_API_KEY', "")
            api_key = None

    ai_engine = AIEngine(api_key=api_key, provider=provider)
    
    key_preview = ""
    if ai_engine.api_key and len(ai_engine.api_key) > 8:
        key_preview = f"{ai_engine.api_key[:4]}...{ai_engine.api_key[-4:]}"

    return jsonify({
        "success": True, 
        "provider": ai_engine.provider,
        "has_live_key": bool(ai_engine.api_key),
        "key_preview": key_preview,
        "saved_to_env": bool(persist)
    })

if __name__ == '__main__':
    print("🚀 MinnoMatch AI starting on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
