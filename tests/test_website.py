"""Playwright tests for the Awesome ASR Flask website.

Starts the Flask dev server, navigates to each page, takes screenshots,
and verifies key content is present.
"""

import re
import subprocess
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = str(PROJECT_ROOT / "tests" / "screenshots")


@pytest.fixture(scope="session", autouse=True)
def flask_server():
    """Start the Flask dev server for the test session."""
    proc = subprocess.Popen(
        ["python", "-m", "web.app"],
        cwd=str(PROJECT_ROOT),
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
    expect(page.locator("text=6 papers")).to_be_visible()
    expect(page.locator("text=3 models")).to_be_visible()

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
    expect(page.locator("text=Voxtral Realtime").first).to_be_visible()
    expect(page.locator("text=Decoder-only Conformer").first).to_be_visible()

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


def test_leaderboard_page(page: Page, base_url: str):
    """Test the leaderboard page displays top 10 models."""
    page.goto(f"{base_url}/leaderboard")

    # Verify page title and heading
    expect(page.locator("h1")).to_have_text("Open ASR Leaderboard")

    # Verify description text
    expect(page.locator("text=Top 10 models by average Word Error Rate")).to_be_visible()

    # Verify last updated is shown
    expect(page.locator("text=Last updated")).to_be_visible()

    # Verify the leaderboard table exists with correct headers
    table = page.locator("table.leaderboard-table")
    expect(table).to_be_visible()
    expect(table.locator("th", has_text="Rank")).to_be_visible()
    expect(table.locator("th", has_text="Model")).to_be_visible()
    expect(table.locator("th", has_text="Avg WER")).to_be_visible()
    expect(table.locator("th", has_text="RTFx")).to_be_visible()

    # Verify per-dataset columns
    for col in ["LS Clean", "LS Other", "CV", "VP", "TED", "GS", "SPGI", "E22", "AMI"]:
        expect(table.locator("th", has_text=col)).to_be_visible()

    # Verify top models are present
    expect(page.locator("text=nvidia/canary-1b")).to_be_visible()
    expect(page.locator("text=nvidia/parakeet-tdt-1.1b")).to_be_visible()

    # Verify there are exactly 10 data rows
    rows = table.locator("tbody tr")
    expect(rows).to_have_count(10)

    # Verify medal styling for top 3 (gold, silver, bronze)
    first_row = rows.nth(0)
    expect(first_row).to_have_class(re.compile(r"rank-gold"))
    second_row = rows.nth(1)
    expect(second_row).to_have_class(re.compile(r"rank-silver"))
    third_row = rows.nth(2)
    expect(third_row).to_have_class(re.compile(r"rank-bronze"))

    # Verify WER values are present
    expect(page.locator("text=6.67%")).to_be_visible()

    # Verify about section
    expect(page.locator("text=About the Benchmarks")).to_be_visible()
    expect(page.locator("text=ESB (End-to-end Speech Benchmark)")).to_be_visible()

    # Verify HuggingFace links
    hf_link = page.locator("a[href='https://huggingface.co/nvidia/canary-1b']")
    expect(hf_link).to_be_visible()

    # Screenshot
    page.screenshot(path=f"{SCREENSHOTS_DIR}/06-leaderboard.png", full_page=True)


def test_navigation(page: Page, base_url: str):
    """Test that navigation links work correctly."""
    page.goto(base_url)

    # Click "Daily Updates" nav link
    page.click("nav >> text=Daily Updates")
    expect(page).to_have_url(f"{base_url}/daily")

    # Click "Leaderboard" nav link
    page.click("nav >> text=Leaderboard")
    expect(page).to_have_url(f"{base_url}/leaderboard")

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
