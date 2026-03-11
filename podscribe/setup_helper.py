import os
import shutil
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from InquirerPy import inquirer

console = Console()

ENV_FILE = Path('.env')
ENV_EXAMPLE = Path('.env.example')
REQUIRED_KEY = 'DASHSCOPE_API_KEY'
APPLY_URL = 'https://dashscope.console.aliyun.com/apiKey'


def check_and_setup() -> str:
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv(REQUIRED_KEY)
    if api_key and api_key != 'your_api_key_here':
        return api_key

    # --- Interactive setup ---
    console.print()
    console.print(Panel(
        "[bold cyan]First-time Setup[/]\n[dim]Configure your DashScope API Key to get started.[/]",
        border_style="cyan",
        padding=(0, 2),
        width=50,
    ))

    if not ENV_FILE.exists():
        console.print("  [cyan][1/3][/] .env file not found, creating...")
        if ENV_EXAMPLE.exists():
            shutil.copy(ENV_EXAMPLE, ENV_FILE)
        else:
            ENV_FILE.write_text(f'{REQUIRED_KEY}=your_api_key_here\n')
        console.print(f"        Created: [dim]{ENV_FILE.resolve()}[/]")
    else:
        console.print("  [cyan][1/3][/] .env file found, but API key is not configured.")

    console.print()
    console.print(f"  [cyan][2/3][/] You need a DashScope API Key.")
    console.print(f"        Get one here: [link={APPLY_URL}][underline]{APPLY_URL}[/][/]")
    console.print()

    api_key = inquirer.secret(
        message="[3/3] Paste your API Key here:",
        qmark="🔑",
        validate=lambda x: len(x.strip()) > 0,
        invalid_message="API Key cannot be empty.",
    ).execute().strip()

    _update_env_file(api_key)

    console.print()
    console.print("  [bold green]✓[/] Setup complete! Key saved to .env")
    console.print()

    os.environ[REQUIRED_KEY] = api_key
    return api_key


def _update_env_file(api_key: str):
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
    with open(ENV_FILE, 'a') as f:
        f.write(f'{REQUIRED_KEY}={api_key}\n')
