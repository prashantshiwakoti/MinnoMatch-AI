# Security & Quality Remediation Roadmap

**Application:** MinnoMatch AI  
**Prepared For:** Metropolia UAS Strategy & Development Services  
**Assessment Date:** November 24, 2026  
**Implementation Priority:** P0 (Immediate) -> P1 (High) -> P2 (Medium) -> P3 (Architectural)  

---

## 1. Remediation Schedule & Priorities

```
+--------------------------------------------------------------------------+
|  P0: IMMEDIATE (Within 48 Hours)                                         |
|   - Eliminate Stored & DOM XSS in Catalog Rendering (VULN-2026-001)      |
|   - Disable Debug Mode in Production Entrypoint (VULN-2026-003)          |
|   - Secure /api/settings from Unauthenticated Mutation (VULN-2026-002)   |
|   - Remove Static Default SECRET_KEY Fallback (VULN-2026-010)            |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|  P1: HIGH PRIORITY (Within 1 Week)                                       |
|   - Implement CSRF Token Validation on POST Endpoints (VULN-2026-004)    |
|   - Apply Input Length Limits & Rate Limiting (VULN-2026-005)            |
|   - Patch Type Exception Crash in ai_engine.py (VULN-2026-006)           |
|   - Suppress Partial API Key Disclosure in /api/status (VULN-2026-007)   |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|  P2: MEDIUM PRIORITY (Within 2–3 Weeks)                                  |
|   - Inject Defensive HTTP Security Headers via Middleware (VULN-2026-008)|
|   - Implement Atomic File Writes & File Locking on Storage (VULN-2026-009)|
|   - Expand Test Coverage from 75% to >90% (TEST_COVERAGE_REPORT)         |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|  P3: ARCHITECTURAL HARDENING (Long Term)                                 |
|   - Migrate Storage from Flat JSON to SQLite / PostgreSQL + SQLAlchemy   |
|   - Implement Role-Based Access Control (RBAC: Student vs Staff)         |
|   - Add XML Delimiter Containment for Prompt Injection (VULN-2026-012)   |
+--------------------------------------------------------------------------+
```

---

## 2. Detailed Technical Fixes & Code Patches

### Fix P0.1: Remediate Stored & DOM XSS (VULN-2026-001)

#### 1. In `static/app.js`: Add HTML Escaping Helper
```javascript
// Add at top of static/app.js
function escapeHTML(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
```

#### 2. In `static/app.js`: Update Catalog Template Literal
```javascript
// Replace lines 245-288 in static/app.js
catalog.innerHTML = data.challenges.map(c => `
  <div class="challenge-card" data-campuses="${escapeHTML((c.campus_synergy || []).join(' '))}">
    <div class="challenge-top">
      <span class="challenge-id">${escapeHTML(c.id)}</span>
      <div class="sdg-tags">
        ${(c.sdgs || []).map(sdg => `<span class="sdg-badge">${escapeHTML(sdg.split(':')[0])}</span>`).join('')}
      </div>
    </div>
    <h3 class="challenge-title">${escapeHTML(c.title)}</h3>
    <p class="challenge-desc">${escapeHTML(c.challenge_statement)}</p>

    <div class="work-packages-preview">
      <h4>Multidisciplinary Campus Allocation:</h4>
      <div class="wp-tags">
        ${(c.work_packages || []).map(wp => `
          <div class="wp-tag">
            <strong>${escapeHTML(wp.campus.split(' ')[0])}:</strong> ${escapeHTML(wp.role)}
          </div>
        `).join('')}
      </div>
    </div>

    <div class="academic-note">
      <strong>🔬 Academic Scope:</strong> ${escapeHTML(c.academic_potential)}
    </div>

    <div class="challenge-card-footer">
      <button class="btn btn-outline btn-sm charter-btn" data-id="${escapeHTML(c.id)}">📄 View 10-ECTS Charter</button>
    </div>
  </div>
`).join('');

// Attach safe event listener using ID lookup instead of inline onclick:
catalog.querySelectorAll('.charter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const targetId = btn.dataset.id;
    const challenge = data.challenges.find(item => item.id === targetId);
    if (challenge) viewProjectCharter(challenge);
  });
});
```

---

### Fix P0.2: Disable Debug Mode in Production (VULN-2026-003)

In `app.py` line 166:
```python
# Before:
# app.run(host='127.0.0.1', port=5000, debug=True)

# After:
if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 MinnoMatch AI starting on http://127.0.0.1:{port} (Debug: {debug_mode})")
    app.run(host='127.0.0.1', port=port, debug=debug_mode)
```

---

### Fix P0.3: Restrict `/api/settings` and Eliminate Unauthenticated `.env` Mutation (VULN-2026-002)

In `app.py`:
```python
ADMIN_SECRET_TOKEN = os.getenv('ADMIN_SECRET_TOKEN')

@app.route('/api/settings', methods=['POST'])
def update_settings():
    # Require an authorization header if ADMIN_SECRET_TOKEN is set
    auth_header = request.headers.get('Authorization', '')
    if ADMIN_SECRET_TOKEN and auth_header != f"Bearer {ADMIN_SECRET_TOKEN}":
        return jsonify({"error": "Unauthorized. Administrative authorization required.", "success": False}), 401

    data = request.get_json() or {}
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "gemini").lower()
    
    # Do not allow arbitrary web clients to write directly to .env in production
    if os.getenv('FLASK_ENV') == 'production':
        return jsonify({"error": "Dynamic .env mutation disabled in production environment.", "success": False}), 403

    # Update in-memory engine safely
    global ai_engine
    ai_engine = AIEngine(api_key=api_key or None, provider=provider)
    return jsonify({
        "success": True,
        "provider": ai_engine.provider,
        "has_live_key": bool(ai_engine.api_key)
    })
```

---

### Fix P1.1: Patch Type Exception Crash in `ai_engine.py` (VULN-2026-006)

In `ai_engine.py` lines 211–214:
```python
# Before:
# student_skills = [s.strip().lower() for s in student_profile.get("skills", "").split(",") if s.strip()]

# After:
raw_skills = student_profile.get("skills", "")
if isinstance(raw_skills, list):
    student_skills = [str(s).strip().lower() for s in raw_skills if str(s).strip()]
elif isinstance(raw_skills, str):
    student_skills = [s.strip().lower() for s in raw_skills.split(",") if s.strip()]
else:
    student_skills = []

raw_interests = student_profile.get("interests", "")
student_interests = str(raw_interests).lower() if raw_interests is not None else ""
```

---

### Fix P1.2: Suppress Partial API Key Disclosure in `/api/status` (VULN-2026-007)

In `app.py` lines 74–84:
```python
@app.route('/api/status', methods=['GET'])
def get_status():
    challenges = load_challenges()
    return jsonify({
        "status": "online",
        "app_name": "MinnoMatch AI",
        "institution": "Metropolia University of Applied Sciences",
        "provider": ai_engine.provider,
        "has_live_key": bool(ai_engine.api_key),
        # Remove key_preview to eliminate credential reconnaissance
        "total_challenges": len(challenges),
        "campuses": ["Karamalmi", "Myllypuro", "Arabia", "Myyrmäki"]
    })
```

---

### Fix P1.3: Apply Input Boundaries on `/api/synthesize` (VULN-2026-005)

In `app.py` lines 107–116:
```python
MAX_PROMPT_LENGTH = 2000

@app.route('/api/synthesize', methods=['POST'])
def synthesize():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body", "success": False}), 400

    prompt = data.get("prompt", "")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "Problem statement cannot be empty", "success": False}), 400

    cleaned_prompt = prompt.strip()
    if len(cleaned_prompt) > MAX_PROMPT_LENGTH:
        return jsonify({
            "error": f"Problem statement exceeds maximum length of {MAX_PROMPT_LENGTH} characters",
            "success": False
        }), 400

    result = ai_engine.synthesize_challenge(cleaned_prompt)
    return jsonify({"success": True, "result": result})
```

---

### Fix P2.1: Implement Defensive HTTP Security Headers (VULN-2026-008)

In `app.py`:
```python
@app.after_request
def apply_security_headers(response):
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
```

---

### Fix P2.2: Concurrency-Safe Atomic JSON Persistence (VULN-2026-009)

In `app.py`:
```python
import tempfile

def save_challenges(challenges):
    os.makedirs(os.path.dirname(CHALLENGES_FILE), exist_ok=True)
    # Write to a temporary file in the same directory, then atomic rename
    dir_name = os.path.dirname(CHALLENGES_FILE)
    with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
        json.dump(challenges, tf, indent=2, ensure_ascii=False)
        temp_name = tf.name
    
    os.replace(temp_name, CHALLENGES_FILE)
```

---

## 3. Post-Remediation Verification Protocol

Once the P0 and P1 patches are applied:
1. **Re-run Bandit Scan:** Verify zero High-severity findings (`bandit -r . -f screen`).
2. **Execute Full Test Suite with Coverage:** Verify that coverage exceeds 85% (`coverage run -m unittest test_app.py; coverage report`).
3. **Execute PoC Regression Tests:** Confirm that script injection in `/api/challenges` renders as plain text without execution.
4. **Deploy with Production WSGI Server:** Run via Gunicorn or Waitress instead of Werkzeug development server:
   `waitress-serve --listen=127.0.0.1:5000 app:app`
