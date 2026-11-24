# Automated Test Coverage & Gap Analysis Report

**Application:** MinnoMatch AI  
**Test Runner:** Python `unittest` + `coverage.py`  
**Assessment Date:** November 24, 2026  
**Total Test Execution Time:** 0.028s  
**Current Overall Code Coverage:** **75%**  

---

## 1. Code Coverage Summary

The test suite was analyzed using `coverage.py` measuring statement execution across all active source files:

```
Name           Stmts   Miss  Cover   Missing Lines
-------------------------------------------------------------------------------
ai_engine.py      99     28    72%   47, 51-56, 63-115, 132-133, 135, 137
app.py           107     42    61%   28, 32-34, 37-39, 43-58, 86-103, 110, 138-148, 165-166
test_app.py       74      1    99%   106
-------------------------------------------------------------------------------
TOTAL            280     71    75%
```

---

## 2. Inventory of Current Test Suite (`test_app.py`)

| Test Method | Target Endpoint / Function | Test Classification | Assertion Summary |
| :--- | :--- | :--- | :--- |
| `test_index_page` | `GET /` | Integration / HTML | Verifies HTTP 200, checks brand keywords in response |
| `test_status_endpoint` | `GET /api/status` | API Integration | Verifies HTTP 200, checks JSON structure and campuses list |
| `test_synthesize_endpoint` | `POST /api/synthesize` | Domain & API | Verifies 4 faculty work packages generated from prompt |
| `test_student_matching` | `POST /api/match-student` | Domain & API | Verifies compatibility score calculation (>60%) |
| `test_export_charter` | `POST /api/export-charter` | Formatting & API | Verifies standard 10-ECTS Markdown format generation |
| `test_settings_persistence`| `POST /api/settings` | State Mutation | Verifies provider switching and preview generation |

---

## 3. Coverage Gap Analysis

### 3.1 Uncovered Areas in `ai_engine.py` (28 Missing Statements - 72% Coverage)
1. **Live LLM Execution Branches (`lines 63–115`):**
   - The entire `_call_live_llm()` method is unexercised during tests because tests run offline without mock HTTP responses.
   - Both the OpenAI `/chat/completions` pathway and the Google Gemini `/models/gemini-1.5-flash:generateContent` pathway lack unit tests.
2. **LLM Error Handling & Fallback (`lines 51–56`):**
   - The `try/except` block catching external network errors or invalid API keys is untested.
3. **Keyword Domain Classification Branches (`lines 132–137`):**
   - The specific heuristic triggers for environmental sustainability (`is_eco`), creative media (`is_media`), and education (`is_edu`) lack isolated test cases.

### 3.2 Uncovered Areas in `app.py` (42 Missing Statements - 61% Coverage)
1. **File I/O Exception Handling (`lines 28, 32–34`):**
   - Corrupted or unreadable JSON file handling in `load_challenges()` and `save_challenges()` is untested.
2. **Physical `.env` Persistence Helper (`lines 43–58`):**
   - Tests execute with `persist=False` to prevent modifying local configuration, leaving line removal and file rewriting untested.
3. **Challenge Creation Endpoint (`lines 86–103`):**
   - `POST /api/challenges` is not tested in the automated suite (only tested in our audit verification script).
4. **Validation Failures & Bad Requests (`line 110`):**
   - Submitting an empty prompt to `/api/synthesize` is not tested.

---

## 4. Recommended New Automated Tests

To achieve **>90% production-ready test coverage**, the following 6 test cases should be added to `test_app.py`:

### Test 1: Validation & Error Handling on `/api/synthesize`
```python
def test_synthesize_validation_errors(self):
    # Empty prompt
    res = self.app.post('/api/synthesize', json={"prompt": ""})
    self.assertEqual(res.status_code, 400)
    self.assertIn("cannot be empty", res.get_json()["error"])

    # Overly long prompt (boundary test)
    oversized = "A" * 5000
    res_long = self.app.post('/api/synthesize', json={"prompt": oversized})
    # After remediation, this should return 400
```

### Test 2: Type Coercion on `/api/match-student`
```python
def test_match_student_non_string_types(self):
    # Non-string integer skills should not crash with 500
    res = self.app.post('/api/match-student', json={
        "faculty": "Technology & ICT",
        "skills": 99999,
        "interests": None
    })
    self.assertIn(res.status_code, [200, 400])
```

### Test 3: Mocked Live Gemini LLM Execution
```python
from unittest.mock import patch, MagicMock

@patch('requests.post')
def test_live_gemini_call(self, mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [{
            "content": {"parts": [{"text": json.dumps({"title": "Mocked Project", "work_packages": []})}]}
        }]
    }
    mock_post.return_value = mock_response

    engine = AIEngine(api_key="AIzaSyMockKey", provider="gemini")
    result = engine.synthesize_challenge("Test prompt")
    self.assertEqual(result["title"], "Mocked Project")
```

### Test 4: Stored Challenge Persistence & Retrieval
```python
def test_challenge_creation_and_retrieval(self):
    payload = {
        "title": "Automated Test Project",
        "challenge_statement": "Validating end-to-end challenge persistence"
    }
    create_res = self.app.post('/api/challenges', json=payload)
    self.assertEqual(create_res.status_code, 201)
    new_id = create_res.get_json()["challenge"]["id"]

    list_res = self.app.get('/api/challenges')
    ids = [c["id"] for c in list_res.get_json()["challenges"]]
    self.assertIn(new_id, ids)
```

### Test 5: Concurrency Safety for Flat-File Writes
```python
import threading

def test_concurrent_challenge_writes(self):
    def post_worker(idx):
        client = app.test_client()
        client.post('/api/challenges', json={"title": f"Thread {idx}"})

    threads = [threading.Thread(target=post_worker, args=(i,)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    # Verify JSON file remains valid and readable
    challenges = load_challenges()
    self.assertIsInstance(challenges, list)
```

---

## 5. Test Infrastructure Recommendations

1. **Continuous Integration (CI):** Integrate `pytest` and `flake8` into a GitHub Actions workflow (`.github/workflows/ci.yml`) triggering on every pull request.
2. **Security Regression Tests:** Automate Bandit static checks and `pip-audit` as mandatory non-blocking quality gates in the pipeline.
3. **Frontend E2E Testing:** Expand [capture_screenshots.py](file:///d:/Flask/capture_screenshots.py) into an end-to-end Playwright assertion suite verifying that DOM inputs and button states correctly synchronize without runtime JavaScript console errors.
