"""Playwright tests for the Awesome ASR Flask website.

Starts the Flask dev server, navigates to each page, takes screenshots,
and verifies key content is present.
"""

import subprocess
import time

import pytest
from playwright.sync_api import Page, expect

SCREENSHOTS_DIR = "tests/screenshots"


@pytest.fixture(scope="session", autouse=True)
def flask_server():
    """Start the Flask dev server for the test session."""
    proc = subprocess.Popen(
        ["python", "-m", "web.app"],
        cwd="/home/user/awesome-asr",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for the server to start
    time.sleep(3)
    yield proc
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def base_url():
    return "http://127.0.0.1:5000"


def test_dashboard(page: Page, base_url: str):
    """Test the main dashboard page."""
    page.goto(base_url)

    # Verify key elements
    expect(page.locator("nav .nav-brand")).to_have_text("Awesome ASR")
    expect(page.locator("h1")).to_have_text("ASR Research Dashboard")

    # Verify today's highlights card is present
    expect(page.locator("text=Today's Highlights")).to_be_visible()
    expect(page.locator("text=3 papers")).to_be_visible()
    expect(page.locator("text=2 models")).to_be_visible()

    # Verify key ideas are shown
    expect(page.locator("text=Streaming ASR")).to_be_visible()

    # Screenshot
    page.screenshot(path=f"{SCREENSHOTS_DIR}/01-dashboard.png", full_page=True)


def test_daily_list(page: Page, base_url: str):
    """Test the daily updates archive page."""
    page.goto(f"{base_url}/daily")

    expect(page.locator("h1")).to_have_text("Daily Updates Archive")

    # Verify both dates appear in the table
    expect(page.locator("text=2026-02-17")).to_be_visible()
    expect(page.locator("text=2026-02-16")).to_be_visible()

    page.screenshot(path=f"{SCREENSHOTS_DIR}/02-daily-list.png", full_page=True)


def test_daily_detail(page: Page, base_url: str):
    """Test a single daily report page."""
    page.goto(f"{base_url}/daily/2026-02-17")

    expect(page.locator("h1").first).to_contain_text("2026-02-17")

    # Verify paper content is rendered
    expect(page.locator("text=StreamConformer")).to_be_visible()
    expect(page.locator("text=WhisperMed")).to_be_visible()
    expect(page.locator("text=AfriSpeech-15").first).to_be_visible()

    page.screenshot(path=f"{SCREENSHOTS_DIR}/03-daily-detail.png", full_page=True)


def test_podcasts_page(page: Page, base_url: str):
    """Test the podcasts page."""
    page.goto(f"{base_url}/podcasts")

    expect(page.locator("h1")).to_have_text("ASR Weekly Podcast")
    expect(page.locator("text=Auto-generated podcast")).to_be_visible()

    page.screenshot(path=f"{SCREENSHOTS_DIR}/04-podcasts.png", full_page=True)


def test_mindmaps_page(page: Page, base_url: str):
    """Test the mindmaps page."""
    page.goto(f"{base_url}/mindmaps")

    expect(page.locator("h1")).to_have_text("Interactive ASR Mindmaps")

    page.screenshot(path=f"{SCREENSHOTS_DIR}/05-mindmaps.png", full_page=True)


def test_navigation(page: Page, base_url: str):
    """Test that navigation links work correctly."""
    page.goto(base_url)

    # Click "Daily Updates" nav link
    page.click("nav >> text=Daily Updates")
    expect(page).to_have_url(f"{base_url}/daily")

    # Click "Podcasts" nav link
    page.click("nav >> text=Podcasts")
    expect(page).to_have_url(f"{base_url}/podcasts")

    # Click "Mindmaps" nav link
    page.click("nav >> text=Mindmaps")
    expect(page).to_have_url(f"{base_url}/mindmaps")

    # Click logo to go home
    page.click("nav >> text=Awesome ASR")
    expect(page).to_have_url(f"{base_url}/")


def test_404_page(page: Page, base_url: str):
    """Test that a nonexistent daily report returns 404."""
    response = page.goto(f"{base_url}/daily/9999-99-99")
    assert response.status == 404
