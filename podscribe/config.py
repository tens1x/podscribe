import json
from pathlib import Path

CONFIG_DIR = Path.home() / '.podscribe'
CONFIG_FILE = CONFIG_DIR / 'config.json'


def load_config() -> dict | None:
    if not CONFIG_FILE.exists():
        return None

    try:
        return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None


def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    existing = {}
    if CONFIG_FILE.exists():
        try:
            existing = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            pass
    existing.update(config)
    CONFIG_FILE.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
