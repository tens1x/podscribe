import os
import shutil
from pathlib import Path

ENV_FILE = Path('.env')
ENV_EXAMPLE = Path('.env.example')
REQUIRED_KEY = 'DASHSCOPE_API_KEY'
APPLY_URL = 'https://dashscope.console.aliyun.com/apiKey'


def check_and_setup() -> str:
    """Check for API key; guide user through setup if missing. Returns the key."""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv(REQUIRED_KEY)
    if api_key and api_key != 'your_api_key_here':
        return api_key

    # --- Interactive setup ---
    print()
    print('=' * 50)
    print('  First-time Setup')
    print('=' * 50)
    print()

    if not ENV_FILE.exists():
        print(f'[1/3] .env file not found, creating from .env.example...')
        if ENV_EXAMPLE.exists():
            shutil.copy(ENV_EXAMPLE, ENV_FILE)
        else:
            ENV_FILE.write_text(f'{REQUIRED_KEY}=your_api_key_here\n')
        print(f'      Created: {ENV_FILE.resolve()}')
    else:
        print(f'[1/3] .env file found, but API key is not configured.')

    print()
    print(f'[2/3] You need a DashScope API Key.')
    print(f'      Get one here: {APPLY_URL}')
    print()

    api_key = input('[3/3] Paste your API Key here: ').strip()

    if not api_key:
        print('\nNo key provided. Exiting.')
        raise SystemExit(1)

    # Write to .env
    _update_env_file(api_key)

    print()
    print('Setup complete! Key saved to .env')
    print('=' * 50)
    print()

    os.environ[REQUIRED_KEY] = api_key
    return api_key


def _update_env_file(api_key: str):
    """Write or update the API key in .env file."""
    if ENV_FILE.exists():
        content = ENV_FILE.read_text()
        if f'{REQUIRED_KEY}=' in content:
            lines = content.splitlines()
            lines = [
                f'{REQUIRED_KEY}={api_key}' if line.startswith(f'{REQUIRED_KEY}=') else line
                for line in lines
            ]
            ENV_FILE.write_text('\n'.join(lines) + '\n')
            return
    # Append or create
    with open(ENV_FILE, 'a') as f:
        f.write(f'{REQUIRED_KEY}={api_key}\n')
