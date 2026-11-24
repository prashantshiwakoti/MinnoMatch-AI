"""
MinnoMatch AI - Comprehensive Quality & Security Test Suite
Hardened Pre-Production Release
"""

import unittest
import json
import threading
from unittest.mock import patch, MagicMock
from app import app, load_challenges, save_challenges
from ai_engine import AIEngine

class MinnoMatchSecurityTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.testing = True
        self.app = app.test_client()

    def test_index_page_and_security_headers(self):
        """Validates index rendering and presence of defensive security headers"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'MinnoMatch', response.data)
        self.assertIn(b'METROPOLIA UAS', response.data)

        # Verify defensive security headers (OWASP ASVS / VULN-2026-008)
        headers = response.headers
        self.assertEqual(headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')
        self.assertIn("default-src 'self'", headers.get('Content-Security-Policy', ''))

    def test_status_endpoint_no_key_leakage(self):
        """Ensures /api/status does not expose secret key substrings (VULN-2026-007)"""
        response = self.app.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'online')
        self.assertEqual(data['institution'], 'Metropolia University of Applied Sciences')
        self.assertIn('Karamalmi', data['campuses'])
        # Assert key_preview is eliminated
        self.assertNotIn('key_preview', data)

    def test_synthesize_endpoint_and_length_boundaries(self):
        """Tests standard decomposition and input length boundaries (VULN-2026-005)"""
        # 1. Valid input
        payload = {
            "prompt": "How can we use edge computer vision to detect falls among elderly residents in Myllypuro living labs?"
        }
        res_valid = self.app.post('/api/synthesize', json=payload)
        self.assertEqual(res_valid.status_code, 200)
        data = res_valid.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['result']['work_packages']), 4)

        # 2. Too short (< 10 chars)
        res_short = self.app.post('/api/synthesize', json={"prompt": "Short"})
        self.assertEqual(res_short.status_code, 400)
        self.assertIn("too brief", res_short.get_json()["error"])

        # 3. Too long (> 2000 chars)
        oversized = "A" * 2500
        res_long = self.app.post('/api/synthesize', json={"prompt": oversized})
        self.assertEqual(res_long.status_code, 400)
        self.assertIn("exceeds maximum length", res_long.get_json()["error"])

        # 4. Empty prompt
        res_empty = self.app.post('/api/synthesize', json={"prompt": "   "})
        self.assertEqual(res_empty.status_code, 400)

    def test_student_matching_and_type_resilience(self):
        """Ensures student matching handles non-string data types gracefully without crashing (VULN-2026-006)"""
        # 1. Standard valid string matching
        payload_valid = {
            "faculty": "Technology & ICT",
            "degree": "Information Technology",
            "skills": "Python, Machine Learning, Computer Vision",
            "interests": "Elderly fall prevention and healthcare"
        }
        res_valid = self.app.post('/api/match-student', json=payload_valid)
        self.assertEqual(res_valid.status_code, 200)
        matches = res_valid.get_json()['matches']
        self.assertGreater(len(matches), 0)
        self.assertGreater(matches[0]['compatibility_score'], 60)

        # 2. Malformed non-string types (integer skills, list interests)
        payload_types = {
            "faculty": 12345,
            "skills": 99999,
            "interests": ["healthcare", "robotics"]
        }
        res_types = self.app.post('/api/match-student', json=payload_types)
        # Should gracefully succeed with 200 instead of 500 crash
        self.assertEqual(res_types.status_code, 200)
        self.assertTrue(res_types.get_json()['success'])

    def test_stored_xss_sanitization_in_challenges(self):
        """Verifies HTML tags are stripped from challenge metadata (VULN-2026-001)"""
        xss_payload = {
            "title": "<script>alert('xss')</script>Smart Campus IoT",
            "challenge_statement": "Preventing falls <img src=x onerror=alert(1)> in Myllypuro."
        }
        res = self.app.post('/api/challenges', json=xss_payload)
        self.assertEqual(res.status_code, 201)
        created = res.get_json()['challenge']
        # Assert HTML tags were sanitized
        self.assertNotIn('<script>', created['title'])
        self.assertNotIn('<img', created['challenge_statement'])
        self.assertIn('Smart Campus IoT', created['title'])

        # Cleanup
        challenges = [c for c in load_challenges() if c['id'] != created['id']]
        save_challenges(challenges)

    def test_csrf_protection_when_forced(self):
        """Verifies CSRF rejection on missing or invalid token (VULN-2026-004)"""
        res = self.app.post('/api/challenges', json={"title": "CSRF Attack"}, headers={"X-Force-CSRF-Test": "true"})
        self.assertEqual(res.status_code, 403)
        self.assertIn("CSRF", res.get_json()["error"])

    def test_export_charter(self):
        """Validates 10-ECTS charter generation"""
        challenges = load_challenges()
        if challenges:
            sample = challenges[0]
            response = self.app.post('/api/export-charter', json=sample)
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertIn('# METROPOLIA UNIVERSITY OF APPLIED SCIENCES', data['markdown'])

    def test_settings_security_and_provider_validation(self):
        """Tests provider validation on /api/settings"""
        # Invalid provider
        bad_res = self.app.post('/api/settings', json={"provider": "untrusted_ai", "api_key": ""})
        self.assertEqual(bad_res.status_code, 400)
        self.assertIn("Invalid provider", bad_res.get_json()["error"])

        # Valid provider
        good_res = self.app.post('/api/settings', json={"provider": "simulated", "api_key": "", "persist": False})
        self.assertEqual(good_res.status_code, 200)
        self.assertEqual(good_res.get_json()["provider"], "simulated")

    def test_concurrent_atomic_challenge_persistence(self):
        """Validates that concurrent file writes do not corrupt storage (VULN-2026-009)"""
        errors = []
        created_ids = []

        def worker(idx):
            client = app.test_client()
            r = client.post('/api/challenges', json={
                "title": f"Concurrent Stress Test {idx}",
                "challenge_statement": "Testing atomic replacement"
            })
            if r.status_code == 201:
                created_ids.append(r.get_json()["challenge"]["id"])
            else:
                errors.append(r.status_code)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        self.assertEqual(len(errors), 0)
        # Verify JSON remains completely valid and uncorrupted
        loaded = load_challenges()
        self.assertIsInstance(loaded, list)

        # Cleanup
        clean = [c for c in loaded if c.get('id') not in created_ids]
        save_challenges(clean)

    @patch('requests.post')
    def test_mocked_live_gemini_call(self, mock_post):
        """Tests live LLM ingestion branch in ai_engine with mock response"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_payload = {
            "title": "Mocked AI Senior Care",
            "challenge_statement": "AI companion for Myllypuro elderly care",
            "sdgs": ["SDG 3: Good Health and Well-being"],
            "campus_synergy": ["Myllypuro: Clinical trial", "Karamalmi: Edge ML"],
            "work_packages": [{"faculty": "Technology & ICT", "campus": "Karamalmi", "role": "ML Engineer", "contribution": "Edge inference"}],
            "academic_potential": "Publication in Finnish Journal of eHealth",
            "milestones": ["Week 1: Scoping", "Week 12: Showcase"]
        }
        mock_response.json.return_value = {
            "candidates": [{
                "content": {"parts": [{"text": json.dumps(mock_payload)}]}
            }]
        }
        mock_post.return_value = mock_response

        engine = AIEngine(api_key="AIzaSyMockKeyForTesting12345", provider="gemini")
        result = engine.synthesize_challenge("How to assist elderly living in Helsinki?")
        self.assertEqual(result["title"], "Mocked AI Senior Care")
        self.assertEqual(len(result["work_packages"]), 1)

if __name__ == '__main__':
    unittest.main()
