"""Persist task progress so interrupted runs can be resumed."""
import json
from pathlib import Path

STATE_DIR = Path('.podcasttf')
STATE_FILE = STATE_DIR / 'last_task.json'


def save_state(state: dict):
    """Save current task state to disk."""
    STATE_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def load_state() -> dict | None:
    """Load last task state, or None if no state exists."""
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None


def clear_state():
    """Remove state file after successful completion."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
