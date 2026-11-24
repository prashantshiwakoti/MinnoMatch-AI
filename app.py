"""
MinnoMatch AI - Flask Application for Metropolia UAS
Multidisciplinary Innovation Project (MINNO) Synthesizer & Matcher
"""

import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, Response
from ai_engine import AIEngine, CAMPUS_FACULTIES

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'metropolia-ai-minno-secret-2026')

CHALLENGES_FILE = os.path.join(os.path.dirname(__file__), 'data', 'challenges.json')

# Initialize AI engine
ai_engine = AIEngine()

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

@app.route('/')
def index():
    challenges = load_challenges()
    return render_template('index.html', challenges=challenges, faculties=CAMPUS_FACULTIES)

@app.route('/api/status', methods=['GET'])
def get_status():
    challenges = load_challenges()
    return jsonify({
        "status": "online",
        "app_name": "MinnoMatch AI",
        "institution": "Metropolia University of Applied Sciences",
        "provider": ai_engine.provider,
        "has_live_key": bool(ai_engine.api_key),
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
    provider = data.get("provider", "gemini")
    
    ai_engine = AIEngine(api_key=api_key, provider=provider)
    return jsonify({
        "success": True, 
        "provider": ai_engine.provider,
        "has_live_key": bool(ai_engine.api_key)
    })

if __name__ == '__main__':
    print("🚀 MinnoMatch AI starting on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
