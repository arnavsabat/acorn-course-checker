# ACORN Course Space Checker

A Python tool that monitors a University of Toronto ACORN enrolment cart and sends a **Discord notification** when a course section may have space available.

> **This tool never auto-enrols you.** It only reads availability information and pings you on Discord so you can log in and enrol manually.

---

## How it works

1. Opens ACORN in a Chromium browser window using [Playwright](https://playwright.dev/).
2. Logs in with your UTORid and password.
3. Navigates to your **Enrolment Cart** and clicks **Check Availability** for the section you're watching.
4. Reads the availability popup.
5. If the popup does **not** contain phrases like "Section Full" or "Not Waitlistable", sends a Discord alert.
6. Repeats every N minutes.

---

## Requirements

- **macOS / Linux** (Windows WSL also works)
- **Python 3.8+**
- A [Discord webhook URL](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) for the channel where you want alerts

---

## Quick start

```bash
git clone <repo-url>
cd acorn-course-checker
./install.sh
python3 run.py
```

`run.py` automatically uses the `.venv` interpreter, so you do not need to manually activate the virtual environment.

### What `install.sh` does

- Creates a `.venv` virtual environment
- Installs `playwright` and `requests`
- Downloads Playwright's Chromium browser

---

## First run

```
==============================
  ACORN Course Space Checker
==============================

Enter UTORid: yourutorid
Enter password:              ← hidden while typing
Enter Discord webhook URL: https://discord.com/api/webhooks/...
Enter course code (e.g. CSC236H1): CSC236H1
Enter activity code (e.g. LEC 5101): LEC 5101
Enter check interval in minutes [15]:
```

Non-sensitive settings (UTORid, course code, webhook URL, interval) are saved to `config.json` so subsequent runs only ask for your **password**.

> `config.json` is excluded from git via `.gitignore` — never commit it.

---

## Example Discord notifications

**Checker started:**
```
ACORN checker started for CSC236H1 LEC 5101.
Checking every 15 minute(s).
```

**Space may be open:**
```
🚨 ACORN ALERT 🚨
CSC236H1 LEC 5101 may have space open.
Check ACORN immediately!
https://acorn.utoronto.ca/sws/#/courses/0
```

**Session expired:**
```
⚠️ ACORN session expired. Manual login may be needed.
https://acorn.utoronto.ca/sws/#/courses/0
```

---

## Security notes

- Your **password is never saved** to disk. It is entered via `getpass` each run and held only in memory.
- The browser profile folder (`acorn_browser_profile/`) stores session cookies so ACORN stays logged in between checks. This folder is gitignored — do not share or commit it.
- The tool does not attempt to bypass MFA. If MFA is required, it notifies you via Discord and waits up to 120 s for you to complete it in the browser window.

---

## Project structure

```
acorn-course-checker/
├── run.py                     # Entry point (auto-selects .venv interpreter)
├── install.sh                 # One-time setup script
├── requirements.txt
├── acorn_checker/
│   ├── cli.py                 # Prompts and top-level entry
│   ├── config.py              # Settings prompt + config.json persistence
│   ├── login.py               # ACORN login / session detection
│   ├── checker.py             # Availability check loop
│   └── discord_notify.py      # Discord webhook sender
├── .gitignore
├── LICENSE
└── README.md
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Course not found on page" | Make sure the course is in your ACORN Enrolment Cart |
| "No popup found after clicking" | ACORN's DOM may have changed; open an issue with a screenshot |
| Discord notifications not arriving | Test your webhook URL with `curl -X POST <url> -d '{"content":"test"}'` |
| Browser shows "Restore pages?" | Already handled by Playwright launch flags; dismiss it manually if it persists |
| MFA required every run | Use the persistent browser profile — after the first manual MFA, ACORN should remember the device |

---

## Disclaimer

This tool is for **personal, non-commercial use** to monitor publicly visible course availability on ACORN. It does not exploit any API, bypass authentication, or interact with ACORN beyond what a logged-in student would do manually in a browser.
