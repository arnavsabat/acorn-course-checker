import time
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

ACORN_BASE = "https://acorn.utoronto.ca"
ACORN_COURSES_URL = f"{ACORN_BASE}/sws/#/courses/0"

# Selectors for the U of T SSO login form (adapts to both old and new SSO pages)
_USERNAME_SEL = (
    "input[name='username'], input[name='user'], "
    "input[id='username'], input[autocomplete='username'], "
    "input[type='email']"
)
_SUBMIT_SEL = (
    "input[type='submit'], button[type='submit'], "
    "button:has-text('Log In'), button:has-text('Sign In'), "
    "button:has-text('Login'), button:has-text('Continue')"
)


def is_logged_in(page: Page) -> bool:
    """Return True when the browser is on an authenticated ACORN SWS page."""
    url = page.url
    if "acorn.utoronto.ca/sws" not in url:
        return False
    # Guard against a "session expired" overlay that keeps the SWS URL
    try:
        for phrase in ("session has expired", "session expired", "signed out", "logged out"):
            if page.locator(f"text={phrase}").is_visible(timeout=500):
                return False
    except Exception:
        pass
    return True


def _handle_device_trust(page: Page) -> None:
    """Click a 'Yes, this is my device' style button if it appears."""
    for label in ("Yes, this is my device", "Trust this device", "Remember this device"):
        try:
            btn = page.get_by_role("button", name=label, exact=False)
            if btn.is_visible(timeout=2500):
                print(f"  Handling device trust prompt: '{label}'")
                btn.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                return
        except Exception:
            continue


def login(page: Page, utoreid: str, password: str) -> bool:
    """
    Navigate to ACORN and log in with the provided credentials.

    Returns True on success. If MFA or another manual step is required,
    waits up to 120 s for the user to complete it in the browser window
    and returns True only if login is detected afterward.
    """
    print("Navigating to ACORN...")
    try:
        page.goto(ACORN_COURSES_URL, wait_until="domcontentloaded", timeout=30000)
    except Exception as exc:
        print(f"  Navigation failed: {exc}")
        return False

    time.sleep(2)

    if is_logged_in(page):
        print("  Already logged in.")
        return True

    print(f"  On login page ({page.url[:80]}). Filling credentials...")
    try:
        username_el = page.wait_for_selector(_USERNAME_SEL, timeout=15000)
        username_el.fill(utoreid)

        pw_el = page.wait_for_selector("input[type='password']", timeout=5000)
        pw_el.fill(password)

        submit_el = page.query_selector(_SUBMIT_SEL)
        if submit_el:
            submit_el.click()
        else:
            pw_el.press("Enter")

        print("  Credentials submitted — waiting for redirect...")
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(2)

    except PlaywrightTimeout as exc:
        print(f"  Login form issue: {exc}")
        return False

    _handle_device_trust(page)
    time.sleep(2)

    if is_logged_in(page):
        print("  Login successful.")
        return True

    # Could be MFA / DUO / another step — give the user time to act manually
    print(
        f"  Login may need manual action (MFA/2FA?). Current URL: {page.url[:80]}\n"
        "  Please complete the login in the browser window (up to 120 s)..."
    )
    for _ in range(24):
        time.sleep(5)
        if is_logged_in(page):
            print("  Login completed (manual).")
            return True

    return False
