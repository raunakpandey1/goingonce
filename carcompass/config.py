"""Runtime settings, read from the environment (and .env when present)."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MODEL = os.getenv("CARCOMPASS_MODEL", "claude-opus-5-5")
DATA_DIR = Path(__file__).resolve().parent / "data"
RUNTIME_DIR = DATA_DIR / "runtime"


def has_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def demo_safe_default() -> bool:
    """Demo-safe mode replays saved AI results instead of calling the API."""
    return os.getenv("CARCOMPASS_DEMO_SAFE", "0") == "1" or not has_api_key()
