import sys
from pathlib import Path

import requests
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from InquirerPy import inquirer
from InquirerPy.separator import Separator

console = Console()
DEFAULT_OUTPUT_DIR = Path('output')
VERSION = '0.1.0'


def _banner():
    title = Text()
    title.append("🎙  PodScribe", style="bold cyan")
    title.append(f"  v{VERSION}", style="dim")
    subtitle = Text("Podcast → Text, powered by AI", style="dim white")

    content = Text.assemble(title, "\n", subtitle)
    panel = Panel(
        content,
        border_style="cyan",
        padding=(0, 2),
        width=42,
    )
    console.print()
    console.print(panel)


def _check_resume():
    from podscribe.task_state import load_state
    state = load_state()
    if not state:
        return None

    console.print()
    console.print("  [bold yellow]Unfinished task detected:[/]")
    console.print(f"    Episode : {state.get('episode_title', 'unknown')}")
    console.print(f"    URL     : {state.get('episode_url', 'unknown')}")
    step = state.get('completed_step', '?')
    console.print(f"    Progress: stopped after step [{step}]")
    if state.get('task_id'):
        console.print(f"    Task ID : {state['task_id']}")
    console.print()

    choice = inquirer.select(
        message="What would you like to do?",
        choices=[
            {"name": "Resume this task", "value": "resume"},
            {"name": "Start a new task", "value": "new"},
            {"name": "Quit", "value": "quit"},
        ],
        default="resume",
        pointer="›",
        qmark="?",
    ).execute()

    if choice == "resume":
        return state
    elif choice == "quit":
        sys.exit(0)
    return None


def main():
    from podscribe.setup_helper import check_and_setup
    check_and_setup()

    _banner()

    # --- Check for unfinished task ---
    resumed = _check_resume()

    if resumed:
        episode_url = resumed['episode_url']
        save_audio = resumed.get('save_audio', False)
        audio_dir = resumed.get('audio_dir')
        output_formats = resumed.get('output_formats', ['txt', 'srt'])
        use_ai = resumed.get('use_ai', True)
        output_dir = resumed.get('output_dir', str(DEFAULT_OUTPUT_DIR))
        completed_step = resumed.get('completed_step', 0)
    else:
        completed_step = 0

        # --- Gather user input ---
        console.print()
        episode_url = inquirer.text(
            message="Paste the Xiaoyuzhou episode URL:",
            qmark="🔗",
            validate=lambda x: len(x.strip()) > 0,
            invalid_message="URL cannot be empty.",
        ).execute().strip()

        save_audio = inquirer.confirm(
            message="Save audio file locally?",
            default=False,
            qmark="💾",
        ).execute()

        audio_dir = None
        if save_audio:
            audio_dir = inquirer.text(
                message="Audio save directory:",
                default=str(DEFAULT_OUTPUT_DIR / 'audio'),
                qmark="📂",
            ).execute().strip()

        output_formats = inquirer.checkbox(
            message="Select output formats:",
            choices=[
                {"name": "txt  — plain text", "value": "txt", "enabled": True},
                {"name": "srt  — subtitles with timestamps", "value": "srt", "enabled": True},
            ],
            qmark="📄",
            pointer="›",
            enabled_symbol="●",
            disabled_symbol="○",
            validate=lambda x: len(x) > 0,
            invalid_message="Select at least one format.",
        ).execute()

        use_ai = inquirer.confirm(
            message="AI post-processing? (fix punctuation, add paragraphs)",
            default=True,
            qmark="🤖",
        ).execute()

        output_dir = inquirer.text(
            message="Transcript save directory:",
            default=str(DEFAULT_OUTPUT_DIR),
            qmark="📂",
        ).execute().strip()

    # --- Confirm and execute ---
    from podscribe.task_state import save_state, clear_state

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    total_steps = 3 + (1 if save_audio else 0) + (1 if use_ai else 0)
    current_step = 0

    state = {
        'episode_url': episode_url,
        'save_audio': save_audio,
        'audio_dir': audio_dir,
        'output_formats': output_formats,
        'use_ai': use_ai,
        'output_dir': output_dir,
        'completed_step': 0,
    }

    if resumed:
        state.update({
            'episode_title': resumed.get('episode_title'),
            'audio_url': resumed.get('audio_url'),
            'task_id': resumed.get('task_id'),
        })

    try:
        from podscribe.podcast_downloader import extract_audio_url, download_audio
        from podscribe.transcriber import transcribe_audio, resume_transcription
        from podscribe.srt_formatter import sentences_to_srt

        # Step: Extract
        current_step += 1
        if completed_step < current_step:
            with console.status(f"[cyan][{current_step}/{total_steps}] Parsing episode page...", spinner="dots"):
                audio_url, episode_title = extract_audio_url(episode_url)
            state['audio_url'] = audio_url
            state['episode_title'] = episode_title
            state['completed_step'] = current_step
            save_state(state)
        else:
            audio_url = state['audio_url']
            episode_title = state['episode_title']
        console.print(f"  [green]✓[/] Episode : [bold]{episode_title}[/]")
        console.print(f"  [green]✓[/] Audio   : [dim]{audio_url}[/]")

        # Step: Download audio (optional)
        if save_audio:
            current_step += 1
            if completed_step < current_step:
                console.print()
                console.print(f"  [cyan][{current_step}/{total_steps}] Downloading audio...[/]")
                audio_save_path = Path(audio_dir)
                audio_save_path.mkdir(parents=True, exist_ok=True)
                audio_ext = audio_url.rsplit('.', 1)[-1].split('?')[0]
                audio_file = audio_save_path / f'{episode_title}.{audio_ext}'
                download_audio(audio_url, str(audio_file))
                console.print(f"  [green]✓[/] Saved to: {audio_file}")
                state['completed_step'] = current_step
                save_state(state)

        # Step: Transcribe
        current_step += 1
        if completed_step < current_step:
            with console.status(f"[cyan][{current_step}/{total_steps}] Transcribing audio (DashScope Paraformer-v2)...", spinner="dots"):
                task_id = state.get('task_id')
                if task_id:
                    result = resume_transcription(task_id)
                else:
                    result = transcribe_audio(audio_url)
        else:
            result = transcribe_audio(audio_url)
        text = result['text']
        sentences = result['sentences']
        state['completed_step'] = current_step
        save_state(state)
        console.print(f"  [green]✓[/] Recognized {len(text)} characters, {len(sentences)} sentences")

        # Step: AI post-processing (optional)
        if use_ai:
            current_step += 1
            with console.status(f"[cyan][{current_step}/{total_steps}] AI post-processing (Qwen)...", spinner="dots"):
                from podscribe.ai_postprocess import postprocess_text
                text = postprocess_text(text)
            state['completed_step'] = current_step
            save_state(state)
            console.print(f"  [green]✓[/] Post-processing complete")

        # Step: Save outputs
        current_step += 1
        saved_files = []

        if 'txt' in output_formats:
            txt_path = output_path / f'{episode_title}.txt'
            txt_path.write_text(text, encoding='utf-8')
            saved_files.append(txt_path)

        if 'srt' in output_formats:
            srt_path = output_path / f'{episode_title}.srt'
            srt_content = sentences_to_srt(sentences)
            srt_path.write_text(srt_content, encoding='utf-8')
            saved_files.append(srt_path)

        clear_state()

        # --- Done ---
        console.print()
        done_text = Text()
        done_text.append("Done! ", style="bold green")
        done_text.append(f"{len(text)} characters transcribed", style="dim")
        results = "\n".join(f"  → {f.resolve()}" for f in saved_files)
        console.print(Panel(
            f"{done_text}\n\n{results}",
            border_style="green",
            title="[bold green]Complete[/]",
            padding=(0, 2),
            width=60,
        ))

    except requests.exceptions.Timeout:
        console.print("\n  [bold red]Error:[/] Request timed out. Check your network.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"\n  [bold red]Error:[/] HTTP {e.response.status_code}")
        sys.exit(1)
    except (ValueError, RuntimeError) as e:
        console.print(f"\n  [bold red]Error:[/] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n  [dim]Interrupted.[/]")
        sys.exit(130)


if __name__ == '__main__':
    main()
