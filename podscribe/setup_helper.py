import os

from rich.console import Console
from rich.panel import Panel
from InquirerPy import inquirer

from podscribe.config import CONFIG_FILE, load_config, save_config

console = Console()

REQUIRED_KEY = 'DASHSCOPE_API_KEY'
APPLY_URL = 'https://dashscope.console.aliyun.com/apiKey'


def check_and_setup() -> str:
    api_key = os.getenv(REQUIRED_KEY)
    if api_key and api_key != 'your_api_key_here':
        return api_key

    config = load_config() or {}
    config_key = config.get('dashscope_api_key')
    if isinstance(config_key, str) and config_key.strip() and config_key != 'your_api_key_here':
        os.environ[REQUIRED_KEY] = config_key
        return config_key

    # --- Interactive setup ---
    console.print()
    console.print(Panel(
        "[bold cyan]First-time Setup[/]\n[dim]Configure your DashScope API Key to get started.[/]",
        border_style="cyan",
        padding=(0, 2),
        width=50,
    ))

    console.print("  [cyan][1/3][/] API key not found in environment or config.")
    console.print(f"        Config file: [dim]{CONFIG_FILE}[/]")

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

    save_config({
        **config,
        'dashscope_api_key': api_key,
    })

    console.print()
    console.print(f"  [bold green]✓[/] Setup complete! Key saved to [dim]{CONFIG_FILE}[/]")
    console.print()

    os.environ[REQUIRED_KEY] = api_key
    return api_key
