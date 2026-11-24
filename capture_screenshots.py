"""
Automated Screenshot Generator for MinnoMatch AI using Playwright
"""

import os
import sys
import time
import subprocess
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), 'screenshots')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def main():
    print("Starting Flask test server...")
    proc = subprocess.Popen([sys.executable, 'app.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2) # wait for server to start

    try:
        with sync_playwright() as p:
            print("Launching headless browser...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()

            url = "http://127.0.0.1:5000"
            page.goto(url, wait_until="networkidle")
            time.sleep(1)

            # 1. Capture Main / Synthesizer Tab before and after prompt
            print("1. Capturing Synthesizer Tab...")
            page.fill("#challengePrompt", "How can we use edge computer vision and empathetic audio to assist dementia patients in Helsinki home care?")
            page.click("#synthesizeBtn")
            page.wait_for_selector("#synthesizeResult .synth-title", timeout=8000)
            time.sleep(1)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_ai_synthesizer.png"), full_page=True)

            # 2. Capture Project Charter Modal
            print("2. Capturing 10-ECTS Project Charter...")
            page.click("#viewCharterBtn")
            page.wait_for_selector("#charterModal:not(.hidden)", timeout=4000)
            time.sleep(1)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_project_charter_modal.png"))
            page.evaluate('closeModal("charterModal")')
            time.sleep(1)

            # 3. Capture Student Matcher Tab
            print("3. Capturing Student Matcher Tab...")
            page.click("button[data-tab='matcherTab']")
            page.fill("#studentDegree", "Software Engineering")
            page.fill("#studentSkills", "Python, Computer Vision, Edge IoT, FastAPI")
            page.fill("#studentInterests", "Elderly healthcare, sensor networks, assistive robotics")
            page.click("#matchBtn")
            page.wait_for_selector(".match-card", timeout=5000)
            time.sleep(1)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_student_matcher.png"), full_page=True)

            # 4. Capture Active Projects Catalog
            print("4. Capturing MINNO Catalog Tab...")
            page.click("button[data-tab='catalogTab']")
            time.sleep(1)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_projects_catalog.png"), full_page=True)

            browser.close()
            print("All screenshots successfully captured!")

    finally:
        print("Terminating Flask server...")
        proc.terminate()
        proc.wait()

if __name__ == '__main__':
    main()
