from .checker import run_checker
from .config import prompt_config


def main() -> None:
    print("=" * 50)
    print("  ACORN Course Space Checker")
    print("=" * 50)
    print()
    print("This tool monitors an ACORN enrolment cart and")
    print("sends a Discord notification if a section may")
    print("have space. It never auto-enrols you.")
    print()

    config = prompt_config()

    print()
    print(f"  Monitoring : {config['course_code']} {config['activity_code']}")
    print(f"  Interval   : {config['interval_minutes']} minute(s)")
    print(f"  Press Ctrl+C to stop at any time.")
    print()

    run_checker(config)
