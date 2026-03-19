"""
Preply Lesson Insights Downloader
----------------------------------
Downloads the latest lesson's audio zip from Preply's AI Lesson Insights section
and extracts it directly into the lesson folder.

How it works:
  1. Kills any running Chrome instances
  2. Copies your Default Chrome profile to /tmp/chrome-session (original is never modified)
  3. Launches Chrome with --remote-debugging-port so Playwright can connect to it
     (This preserves your real login session and macOS Keychain cookies)
  4. Navigates to the Preply dashboard, finds the latest lesson in "Lesson Insights AI beta"
  5. Downloads the zip and extracts it directly into the lesson folder

Requirements:
    pip install playwright
    playwright install chrome

Usage:
    python3 preply_download.py "20260318-IsabellaM-5"
"""

import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from config import LESSONS_DIR

# --- Config ---
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_PROFILE_SRC = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default")
CHROME_SESSION_DIR = "/tmp/chrome-session"
REMOTE_DEBUG_PORT = 9222


def kill_chrome():
    print("Stopping any running Chrome instances...")
    subprocess.run(["pkill", "-9", "-f", "Google Chrome"], capture_output=True)
    time.sleep(2)


def copy_profile():
    """Copy the real Chrome profile to a temp dir — original is never touched."""
    print("Copying Chrome profile to temp location...")
    if os.path.exists(CHROME_SESSION_DIR):
        shutil.rmtree(CHROME_SESSION_DIR)
    os.makedirs(CHROME_SESSION_DIR)
    shutil.copytree(CHROME_PROFILE_SRC, os.path.join(CHROME_SESSION_DIR, "Default"))
    print(f"  Profile copied to {CHROME_SESSION_DIR}")


def launch_chrome():
    """Launch Chrome with remote debugging using the copied profile."""
    print("Launching Chrome with remote debugging...")
    proc = subprocess.Popen(
        [
            CHROME_BIN,
            f"--remote-debugging-port={REMOTE_DEBUG_PORT}",
            f"--user-data-dir={CHROME_SESSION_DIR}",
            "--profile-directory=Default",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(4)
    print(f"  Chrome launched (PID {proc.pid})")
    return proc


def run(playwright, dest_folder: Path):
    browser = playwright.chromium.connect_over_cdp(f"http://localhost:{REMOTE_DEBUG_PORT}")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()

    # Step 1: Go to dashboard
    print("Navigating to Preply dashboard...")
    page.goto("https://preply.com/en/home", timeout=30000)
    page.wait_for_load_state("domcontentloaded", timeout=15000)

    # Step 2: Find and click the latest lesson in Lesson Insights AI beta
    print("Finding latest lesson in Lesson Insights section...")
    page.wait_for_selector("a[href*='lesson-insights']", timeout=20000)

    # The first link matching the lesson-insights URL pattern is the most recent lesson
    first_lesson = page.locator("a[href*='lesson-insights']").first
    first_lesson.click()
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    time.sleep(2)
    print(f"  Lesson page: {page.url}")

    # Step 3: Download zip and extract directly into the lesson folder
    print("Downloading zip file...")
    with page.expect_download(timeout=30000) as dl_info:
        page.click("text=download")

    download = dl_info.value
    zip_path = dest_folder / "lesson_recordings.zip"
    download.save_as(str(zip_path))
    print(f"  Downloaded to: {zip_path}")

    print(f"  Extracting into {dest_folder} ...")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_folder)
    zip_path.unlink()
    print(f"  Extracted {len(list(dest_folder.glob('part_*.webm')))} parts.")

    browser.close()


def main():
    if len(sys.argv) != 2:
        print('Usage: python3 preply_download.py "YYYYMMDD-TutorName-N"')
        sys.exit(1)

    lesson = sys.argv[1]
    dest_folder = LESSONS_DIR / lesson

    if dest_folder.exists():
        print(f"Error: folder already exists: {dest_folder}", file=sys.stderr)
        sys.exit(1)

    dest_folder.mkdir(parents=True)
    print(f"Created: {dest_folder}")

    kill_chrome()
    copy_profile()
    chrome_proc = launch_chrome()

    try:
        with sync_playwright() as p:
            run(p, dest_folder)
        print(f"\nDone! Parts saved to: {dest_folder}")
    except Exception:
        # Clean up empty folder if download failed
        shutil.rmtree(dest_folder, ignore_errors=True)
        raise
    finally:
        chrome_proc.terminate()
        chrome_proc.wait()
        print("Chrome closed.")
        print("Cleaning up temp profile...")
        shutil.rmtree(CHROME_SESSION_DIR, ignore_errors=True)
        print("  Temp profile deleted.")


if __name__ == "__main__":
    main()
