#!/usr/bin/env python3
"""
Entry point for the ACORN course space checker.

If a .venv directory exists alongside this file and the current interpreter
is not already inside it, this script re-execs itself using the venv's
Python so that dependencies installed by install.sh are always available.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_VENV_PYTHON = os.path.join(_ROOT, ".venv", "bin", "python3")

if os.path.exists(_VENV_PYTHON) and not os.environ.get("_ACORN_VENV"):
    os.environ["_ACORN_VENV"] = "1"
    os.execv(_VENV_PYTHON, [_VENV_PYTHON] + sys.argv)

from acorn_checker.cli import main  # noqa: E402 — import after potential re-exec

if __name__ == "__main__":
    main()
