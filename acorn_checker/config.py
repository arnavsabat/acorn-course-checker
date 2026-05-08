import getpass
import json
from pathlib import Path

CONFIG_FILE = Path("config.json")


def _load_saved() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(data: dict) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def prompt_config() -> dict:
    """
    Prompt for all required settings. Non-sensitive values are persisted to
    config.json so repeat runs can reuse them. The password is never saved.
    """
    saved = _load_saved()

    def ask(key: str, prompt: str, default: str = "") -> str:
        current = saved.get(key, default)
        hint = f" [{current}]" if current else ""
        value = input(f"{prompt}{hint}: ").strip()
        return value if value else current

    utoreid = ask("utoreid", "Enter UTORid")
    password = getpass.getpass("Enter password: ")
    discord_webhook = ask("discord_webhook", "Enter Discord webhook URL")
    course_code = ask("course_code", "Enter course code (e.g. CSC236H1)").upper()
    activity_code = ask("activity_code", "Enter activity code (e.g. LEC 5101)").upper()

    interval_raw = ask("interval_minutes", "Enter check interval in minutes", default="15")
    try:
        interval_minutes = max(1, int(interval_raw))
    except ValueError:
        print("Invalid interval, defaulting to 15 minutes.")
        interval_minutes = 15

    _save({
        "utoreid": utoreid,
        "discord_webhook": discord_webhook,
        "course_code": course_code,
        "activity_code": activity_code,
        "interval_minutes": interval_minutes,
    })

    return {
        "utoreid": utoreid,
        "password": password,
        "discord_webhook": discord_webhook,
        "course_code": course_code,
        "activity_code": activity_code,
        "interval_minutes": interval_minutes,
    }
