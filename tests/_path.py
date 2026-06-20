"""Shared test helper: put scripts/ on sys.path and locate fixtures."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def fixture(name):
    return os.path.join(FIXTURES, name)
