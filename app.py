"""
MinnoMatch AI - Flask Application for Metropolia UAS
Multidisciplinary Innovation Project (MINNO) Synthesizer & Matcher
Hardened Pre-Production Release
"""

import os
import json
import uuid
import re
import secrets
import logging
import tempfile
import threading
import time
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, session, Response
from dotenv import load_dotenv, set_key
from ai_engine import AIEngine, CAMPUS_FACULTIES

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("MinnoMatch")

ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(ENV_FILE)

app = Flask(__name__)
# Cryptographically secure session secret key (no static fallback)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or secrets.token_hex(32)
# Enforce 2MB maximum content length to prevent payload flooding DoS
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

CHALLENGES_FILE = os.path.join(os.path.dirname(__file__), 'data', 'challenges.json')

# Initialize AI engine with environment keys if present
initial_provider = os.getenv('LLM_PROVIDER', 'gemini')
initial_key = os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY') or os.getenv('LLM_API_KEY')
ai_engine = AIEngine(api_key=initial_key, provider=initial_provider)

# In-memory synchronization lock for file persistence
file_lock = threading.Lock()

# In-memory rate limiting tracker (IP:endpoint -> list of timestamps)
rate_limit_lock = threading.Lock()
request_records = defaultdict(list)

def is_rate_limited(ip: str, endpoint: str, max_requests: int = 20, window_seconds: int = 60) -> bool:
    """Sliding-window IP rate limiter"""
    now = time.time()
    key = f"{ip}:{endpoint}"
    with rate_limit_lock:
        request_records[key] = [t for t in request_records[key] if now - t < window_seconds]
        if len(request_records[key]) >= max_requests:
            return True
        request_records[key].append(now)
        return False

def sanitize_text(val, max_len=1000) -> str:
    """Strips HTML tags and clamps length to prevent stored XSS and buffer abuse"""
    if not val or not isinstance(val, str):
        return ""
    clean = re.sub(r'<[^>]*>', '', val)
    return clean.strip()[:max_len]

def load_challenges():
    if not os.path.exists(CHALLENGES_FILE):
        return []
    try:
        with file_lock:
            with open(CHALLENGES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading challenges: {e}")
        return []

def save_challenges(challenges):
    """Atomic write with file lock to prevent race conditions and partial file corruption"""
    os.makedirs(os.path.dirname(CHALLENGES_FILE), exist_ok=True)
    dir_name = os.path.dirname(CHALLENGES_FILE)
    with file_lock:
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
            json.dump(challenges, tf, indent=2, ensure_ascii=False)
            temp_name = tf.name
        os.replace(temp_name, CHALLENGES_FILE)

def persist_env_variable(key_name, value):
    """Safely updates .env with logging"""
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.write("# MinnoMatch AI Environment Configuration\n")
    if value:
        set_key(ENV_FILE, key_name, value)
        os.environ[key_name] = value
    else:
        os.environ.pop(key_name, None)
        try:
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                lines = [line for line in f if not line.startswith(f"{key_name}=")]
            with open(ENV_FILE, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        except Exception as e:
            logger.warning(f"Could not remove {key_name} from .env: {e}")

@app.before_request
def csrf_protection():
    """CSRF protection for state-changing requests"""
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return
    # Allow test client when testing without forced CSRF verification
    if (app.config.get('TESTING') or app.testing) and not request.headers.get('X-Force-CSRF-Test'):
        return
    # Allow admin token authentication bypass
    admin_token = os.getenv('ADMIN_SECRET_TOKEN')
    auth_header = request.headers.get('Authorization', '')
    if admin_token and auth_header == f"Bearer {admin_token}":
        return

    csrf_header = request.headers.get('X-CSRF-Token')
    session_token = session.get('csrf_token')
    if not csrf_header or not session_token or not secrets.compare_digest(csrf_header, session_token):
        return jsonify({"error": "Invalid or missing CSRF token", "success": False}), 403

@app.after_request
def apply_security_headers(response):
    """Injects defensive HTTP security headers (OWASP ASVS compliance)"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "font-src 'self' https://fonts.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "script-src 'self'; "
        "img-src 'self' data:;"
    )
    return response

@app.route('/')
def index():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(24)
    challenges = load_challenges()
    return render_template(
        'index.html', 
        challenges=challenges, 
        faculties=CAMPUS_FACULTIES,
        csrf_token=session['csrf_token']
    )

@app.route('/api/status', methods=['GET'])
def get_status():
    challenges = load_challenges()
    return jsonify({
        "status": "online",
        "app_name": "MinnoMatch AI",
        "institution": "Metropolia University of Applied Sciences",
        "provider": ai_engine.provider,
        "has_live_key": bool(ai_engine.api_key),
        "env_persisted": os.path.exists(ENV_FILE),
        "total_challenges": len(challenges),
        "campuses": ["Karamalmi", "Myllypuro", "Arabia", "Myyrmäki"]
    })

@app.route('/api/challenges', methods=['GET', 'POST'])
def handle_challenges():
    challenges = load_challenges()
    if request.method == 'POST':
        client_ip = request.remote_addr or '127.0.0.1'
        if is_rate_limited(client_ip, 'challenges_post', max_requests=15, window_seconds=60):
            return jsonify({"error": "Rate limit exceeded. Please wait a minute.", "success": False}), 429

        data = request.get_json(silent=True) or {}
        raw_title = data.get("title", "Untitled MINNO Project")
        raw_statement = data.get("challenge_statement", "")

        # Sanitize text fields to eliminate Stored XSS
        title = sanitize_text(raw_title, max_len=150)
        statement = sanitize_text(raw_statement, max_len=2000)

        if not title:
            return jsonify({"error": "Challenge title cannot be empty", "success": False}), 400

        new_challenge = {
            "id": f"minno-{uuid.uuid4().hex[:6]}",
            "title": title,
            "challenge_statement": statement,
            "sdgs": data.get("sdgs", ["SDG 9: Industry, Innovation and Infrastructure"]),
            "campus_synergy": [sanitize_text(s, 100) for s in data.get("campus_synergy", [])],
            "work_packages": data.get("work_packages", []),
            "academic_potential": sanitize_text(data.get("academic_potential", ""), 500),
            "milestones": [sanitize_text(m, 200) for m in data.get("milestones", [])]
        }
        challenges.insert(0, new_challenge)
        save_challenges(challenges)
        return jsonify({"success": True, "challenge": new_challenge}), 201
    
    return jsonify({"success": True, "challenges": challenges})

@app.route('/api/synthesize', methods=['POST'])
def synthesize():
    client_ip = request.remote_addr or '127.0.0.1'
    if is_rate_limited(client_ip, 'synthesize', max_requests=12, window_seconds=60):
        return jsonify({"error": "Rate limit exceeded. Please wait a minute.", "success": False}), 429

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body", "success": False}), 400

    raw_prompt = data.get("prompt", "")
    if not isinstance(raw_prompt, str) or not raw_prompt.strip():
        return jsonify({"error": "Problem statement cannot be empty", "success": False}), 400

    prompt = raw_prompt.strip()
    if len(prompt) < 10:
        return jsonify({"error": "Problem statement too brief (minimum 10 characters required)", "success": False}), 400
    if len(prompt) > 2000:
        return jsonify({"error": "Problem statement exceeds maximum length of 2,000 characters", "success": False}), 400
    
    result = ai_engine.synthesize_challenge(prompt)
    return jsonify({"success": True, "result": result})

@app.route('/api/match-student', methods=['POST'])
def match_student():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body", "success": False}), 400

    challenges = load_challenges()
    matches = ai_engine.match_student(data, challenges)
    return jsonify({"success": True, "matches": matches})

@app.route('/api/export-charter', methods=['POST'])
def export_charter():
    data = request.get_json(silent=True) or {}
    charter_md = ai_engine.generate_project_charter(data)
    return jsonify({"success": True, "markdown": charter_md})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    client_ip = request.remote_addr or '127.0.0.1'
    if is_rate_limited(client_ip, 'settings', max_requests=6, window_seconds=60):
        return jsonify({"error": "Rate limit exceeded. Please wait before updating settings.", "success": False}), 429

    admin_token = os.getenv('ADMIN_SECRET_TOKEN')
    auth_header = request.headers.get('Authorization', '')
    if admin_token and auth_header != f"Bearer {admin_token}":
        return jsonify({"error": "Administrative authorization token required", "success": False}), 401

    data = request.get_json(silent=True) or {}
    provider = data.get("provider", "gemini").lower()
    if provider not in ('gemini', 'openai', 'simulated'):
        return jsonify({"error": "Invalid provider. Allowed: gemini, openai, simulated", "success": False}), 400

    api_key = data.get("api_key", "").strip() if isinstance(data.get("api_key"), str) else ""
    persist = bool(data.get("persist", True))

    # Disable direct disk modification in production
    if os.getenv('FLASK_ENV') == 'production' and persist:
        persist = False
        logger.info("Persist to .env suppressed in production environment")

    global ai_engine
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

    ai_engine = AIEngine(api_key=api_key or None, provider=provider)
    
    return jsonify({
        "success": True, 
        "provider": ai_engine.provider,
        "has_live_key": bool(ai_engine.api_key),
        "saved_to_env": bool(persist)
    })

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 MinnoMatch AI starting on http://127.0.0.1:{port} (Debug: {debug_mode})")
    app.run(host='127.0.0.1', port=port, debug=debug_mode)
