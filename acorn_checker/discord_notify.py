import requests


def send(webhook_url: str, message: str) -> bool:
    """Send a Discord webhook message. Returns True on success."""
    try:
        resp = requests.post(
            webhook_url,
            json={"content": message},
            timeout=10,
        )
        if resp.status_code in (200, 204):
            return True
        print(f"[discord] Unexpected status {resp.status_code}: {resp.text[:200]}")
        return False
    except requests.RequestException as exc:
        print(f"[discord] Failed to send notification: {exc}")
        return False
