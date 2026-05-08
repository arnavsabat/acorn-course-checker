import time
import traceback
from typing import Optional

from playwright.sync_api import (
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeout,
    sync_playwright,
)

from . import discord_notify
from .login import ACORN_COURSES_URL, is_logged_in, login

# Text that definitively means the section has no open spots.
# Anything NOT matching these is treated as "may have space" to avoid missing opens.
_FULL_INDICATORS = frozenset(
    {
        "section full",
        "not waitlistable",
        "waitlist full",
        "no space available",
        "full - not waitlistable",
        "class is full",
    }
)

BROWSER_PROFILE_DIR = "acorn_browser_profile"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _wait_for_spa(page: Page, timeout: int = 15000) -> None:
    """Wait for Angular network activity to settle."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeout:
        pass
    time.sleep(1.5)


def _close_modal(page: Page) -> None:
    """Dismiss any open modal so the next navigation starts clean."""
    try:
        close_btn = page.locator(
            "[aria-label='Close'], button.close, .modal-close, button:has-text('Close')"
        ).first
        if close_btn.is_visible(timeout=1000):
            close_btn.click()
            return
    except Exception:
        pass
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


def _find_and_click_availability(page: Page, course_code: str, activity_code: str) -> bool:
    """
    Locate the Check Availability link for the target course/activity and click it.
    Returns True if a link was found and clicked.

    Strategy (in order):
      1. Confirm the course code is visible on the page.
      2. Use Playwright's :has-text filter to find a row/container that holds
         the exact activity code, then click the waitlistLink inside it.
      3. Fall back to the first visible waitlistLink on the page (safe when
         only one course is in the enrolment cart).
    """
    # --- Step 1: Confirm the course is present ---
    try:
        course_el = page.locator(f":text('{course_code}')").first
        course_el.wait_for(timeout=10000)
        course_el.scroll_into_view_if_needed()
    except PlaywrightTimeout:
        print(f"  Course {course_code} not found on page.")
        return False

    # --- Step 2: Find the specific activity row ---
    # ACORN renders activities in <tr> rows or Angular-flavoured divs.
    # We look for any row-like container whose text contains the activity code,
    # then grab the waitlistLink (or generic "Check Availability" link) inside it.
    row_candidates = page.locator(
        "tr, [class*='activityRow'], [class*='activity-row'], [class*='enrolment-row']"
    ).filter(has_text=activity_code)

    try:
        count = row_candidates.count()
    except Exception:
        count = 0

    if count > 0:
        row = row_candidates.first
        link = row.locator(
            "a.waitlistLink, a:has-text('Check Availability'), a:has-text('Waitlist')"
        ).first
        try:
            if link.is_visible(timeout=3000):
                link.scroll_into_view_if_needed()
                link.click()
                return True
        except Exception:
            pass

    # --- Step 3: Fallback — first visible waitlistLink on the page ---
    fallback = page.locator(
        "a.waitlistLink:visible, a:visible:has-text('Check Availability')"
    )
    try:
        if fallback.count() > 0:
            print(
                f"  Warning: could not pinpoint {activity_code} row; "
                "clicking first visible 'Check Availability' link."
            )
            first = fallback.first
            first.scroll_into_view_if_needed()
            first.click()
            return True
    except Exception:
        pass

    print("  No 'Check Availability' links found on page.")
    return False


def _read_popup_text(page: Page) -> Optional[str]:
    """
    Wait for an availability popup/modal to appear and return its inner text.
    Returns None if nothing is found within the timeout.
    """
    selectors = [
        "[role='dialog']:visible",
        ".modal-dialog:visible",
        ".modal:visible",
        "[class*='availability']:visible",
        "[class*='popup']:visible",
        "[class*='modal']:visible",
        "[class*='overlay']:visible",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            el.wait_for(timeout=6000)
            text = el.inner_text().strip()
            if text:
                return text
        except PlaywrightTimeout:
            continue
    return None


def _is_section_full(popup_text: str) -> bool:
    lower = popup_text.lower()
    return any(indicator in lower for indicator in _FULL_INDICATORS)


# ---------------------------------------------------------------------------
# Single check pass
# ---------------------------------------------------------------------------


def _check_once(page: Page, config: dict) -> str:
    """
    Navigate to the enrolment cart, check availability, and return a status string.

    Possible return values:
      'full'       — section is confirmed full
      'available'  — popup does not contain full-indicator text (may have space)
      'not_found'  — course/activity or popup not found (ambiguous)
      'logged_out' — session expired
      'error'      — navigation or unexpected failure
    """
    course_code = config["course_code"]
    activity_code = config["activity_code"]

    print("Navigating to Enrolment Cart...")
    try:
        page.goto(ACORN_COURSES_URL, wait_until="domcontentloaded", timeout=30000)
        _wait_for_spa(page)
    except Exception as exc:
        print(f"  Navigation error: {exc}")
        return "error"

    if not is_logged_in(page):
        return "logged_out"

    print(f"Finding {course_code} — {activity_code}...")
    clicked = _find_and_click_availability(page, course_code, activity_code)
    if not clicked:
        return "not_found"

    time.sleep(1)  # brief wait for Angular to open the popup
    print("Reading availability popup...")
    popup_text = _read_popup_text(page)

    if popup_text is None:
        print("  No popup found after clicking.")
        return "not_found"

    print(f"  Popup: {popup_text[:300].replace(chr(10), ' ')}")

    _close_modal(page)

    if _is_section_full(popup_text):
        print(f"  {course_code} {activity_code} is still full.")
        return "full"

    print(f"  {course_code} {activity_code} may have space!")
    return "available"


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run_checker(config: dict) -> None:
    course_code = config["course_code"]
    activity_code = config["activity_code"]
    interval_seconds = config["interval_minutes"] * 60
    webhook = config["discord_webhook"]

    # Tracks the last status we *notified Discord about* to avoid spam.
    last_notified: Optional[str] = None

    with sync_playwright() as pw:
        print("Launching Chromium (headed so you can intervene if needed)...")
        context: BrowserContext = pw.chromium.launch_persistent_context(
            user_data_dir=BROWSER_PROFILE_DIR,
            headless=False,
            args=[
                "--disable-session-crashed-bubble",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        page: Page = context.pages[0] if context.pages else context.new_page()

        discord_notify.send(
            webhook,
            f"ACORN checker started for **{course_code} {activity_code}**.\n"
            f"Checking every {config['interval_minutes']} minute(s).",
        )

        # ---- Initial login ----
        logged_in = login(page, config["utoreid"], config["password"])
        if not logged_in:
            discord_notify.send(
                webhook,
                f"⚠️ ACORN login needs manual action. "
                f"Please complete it in the browser window.\n"
                f"The checker will wait and retry automatically.",
            )
            print("Waiting up to 120 s for manual login...")
            for _ in range(24):
                time.sleep(5)
                if is_logged_in(page):
                    print("Logged in manually.")
                    break

        # ---- Check loop ----
        while True:
            try:
                status = _check_once(page, config)

                if status == "logged_out":
                    print("Session expired — attempting re-login...")
                    logged_in = login(page, config["utoreid"], config["password"])
                    if not logged_in and last_notified != "login_needed":
                        discord_notify.send(
                            webhook,
                            f"⚠️ ACORN session expired. Manual login may be needed.\n"
                            f"https://acorn.utoronto.ca/sws/#/courses/0",
                        )
                        last_notified = "login_needed"
                    time.sleep(30)
                    continue

                elif status == "available":
                    if last_notified != "available":
                        discord_notify.send(
                            webhook,
                            f"🚨 ACORN ALERT 🚨\n"
                            f"**{course_code} {activity_code}** may have space open.\n"
                            f"Check ACORN immediately!\n"
                            f"https://acorn.utoronto.ca/sws/#/courses/0",
                        )
                    last_notified = "available"

                elif status == "not_found":
                    if last_notified != "not_found":
                        discord_notify.send(
                            webhook,
                            f"⚠️ Could not find **{course_code} {activity_code}** "
                            f"in the enrolment cart or its availability popup.\n"
                            f"Verify the course is in your ACORN cart.",
                        )
                    last_notified = "not_found"

                elif status == "error":
                    if last_notified != "error":
                        discord_notify.send(
                            webhook,
                            f"⚠️ ACORN checker hit a navigation error. "
                            f"Retrying in {config['interval_minutes']} minute(s).",
                        )
                    last_notified = "error"

                else:  # 'full'
                    if last_notified == "available":
                        # Went back to full — inform once
                        discord_notify.send(
                            webhook,
                            f"ℹ️ {course_code} {activity_code} appears full again.",
                        )
                    last_notified = "full"

                print(
                    f"Next check in {config['interval_minutes']} minute(s). "
                    "Press Ctrl+C to stop.\n"
                )
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\nStopping...")
                discord_notify.send(
                    webhook,
                    f"ACORN checker stopped for {course_code} {activity_code}.",
                )
                break

            except Exception as exc:
                print(f"Unexpected error:\n{traceback.format_exc()}")
                if last_notified != "crash":
                    discord_notify.send(
                        webhook,
                        f"🚨 ACORN checker crashed!\n```\n{str(exc)[:400]}\n```",
                    )
                    last_notified = "crash"
                time.sleep(60)

        context.close()
