"""
MinnoMatch AI - Unit & Integration Test Suite
"""

import unittest
import json
from app import app, load_challenges

class MinnoMatchTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_index_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'MinnoMatch', response.data)
        self.assertIn(b'METROPOLIA UAS', response.data)

    def test_status_endpoint(self):
        response = self.app.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'online')
        self.assertEqual(data['institution'], 'Metropolia University of Applied Sciences')
        self.assertIn('Karamalmi', data['campuses'])

    def test_synthesize_endpoint(self):
        payload = {
            "prompt": "How can we use edge computer vision to detect falls among elderly residents in Myllypuro living labs?"
        }
        response = self.app.post('/api/synthesize', json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        result = data['result']
        self.assertIn('title', result)
        self.assertIn('work_packages', result)
        self.assertEqual(len(result['work_packages']), 4)
        faculties = [wp['faculty'] for wp in result['work_packages']]
        self.assertIn('Technology & ICT', faculties)
        self.assertIn('Health Care & Social Services', faculties)
        self.assertIn('Culture & Design', faculties)
        self.assertIn('Business & Management', faculties)

    def test_student_matching(self):
        payload = {
            "faculty": "Technology & ICT",
            "degree": "Information Technology",
            "skills": "Python, Machine Learning, Computer Vision",
            "interests": "Elderly fall prevention and healthcare"
        }
        response = self.app.post('/api/match-student', json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        matches = data['matches']
        self.assertGreater(len(matches), 0)
        top_match = matches[0]
        self.assertGreater(top_match['compatibility_score'], 60)
        self.assertIn('recommended_role', top_match)

    def test_export_charter(self):
        challenges = load_challenges()
        if challenges:
            sample = challenges[0]
            response = self.app.post('/api/export-charter', json=sample)
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertIn('# METROPOLIA UNIVERSITY OF APPLIED SCIENCES', data['markdown'])
            self.assertIn('MINNO', data['markdown'])

if __name__ == '__main__':
    unittest.main()
