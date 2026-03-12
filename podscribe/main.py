import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from podscribe.config import load_config, save_config
from podscribe.history import add_record, load_history

console = Console()
DEFAULT_OUTPUT_DIR = Path('output')
VERSION = '0.1.0'
DEFAULT_CONFIG = {
    'output_formats': ['txt', 'srt'],
    'output_dir': str(DEFAULT_OUTPUT_DIR),
    'save_audio': False,
    'audio_dir': None,
    'use_ai': True,
}


def _normalize_config(config: dict | None) -> dict:
    merged = DEFAULT_CONFIG.copy()
    if config:
        merged.update(config)

    output_formats = merged.get('output_formats') or DEFAULT_CONFIG['output_formats']
    merged['output_formats'] = [fmt for fmt in output_formats if fmt in {'txt', 'srt'}] or DEFAULT_CONFIG['output_formats']
    merged['output_dir'] = str(merged.get('output_dir') or DEFAULT_CONFIG['output_dir'])
    merged['save_audio'] = bool(merged.get('save_audio', DEFAULT_CONFIG['save_audio']))
    merged['audio_dir'] = merged.get('audio_dir') or None
    merged['use_ai'] = bool(merged.get('use_ai', DEFAULT_CONFIG['use_ai']))
    if merged['save_audio'] and not merged['audio_dir']:
        merged['audio_dir'] = str(DEFAULT_OUTPUT_DIR / 'audio')
    return merged


def _format_output_path(path_value: str | None) -> str:
    if not path_value:
        return '-'

    path = Path(path_value)
    text = str(path)
    if path.is_absolute() or text.startswith('./') or text.startswith('../'):
        return text
    if text == '.':
        return './'
    return f'./{text}'


def _format_config(config: dict | None) -> dict:
    normalized = _normalize_config(config)
    return {
        'formats': ' + '.join(normalized['output_formats']),
        'output': _format_output_path(normalized['output_dir']),
        'ai': 'on' if normalized['use_ai'] else 'off',
        'save_audio': 'on' if normalized['save_audio'] else 'off',
        'audio_dir': _format_output_path(normalized['audio_dir']),
    }


def _merge_prompt_config(current_config: dict | None, state: dict | None = None) -> dict:
    merged = _normalize_config(current_config)
    for key in ('output_formats', 'output_dir', 'save_audio', 'audio_dir', 'use_ai'):
        if state and key in state:
            merged[key] = state[key]
    return _normalize_config(merged)


def _append_summary_item(summary: Text, label: str, value: str, value_style: str = 'green'):
    if summary.plain:
        summary.append(' | ', style='dim')
    summary.append(f'{label}: ', style='dim')
    summary.append(value, style=value_style)


def _format_prompt_summary(state: dict) -> Text | None:
    summary = Text()

    if 'output_formats' in state:
        _append_summary_item(summary, 'Format', ' + '.join(state['output_formats']))
    if 'save_audio' in state:
        _append_summary_item(summary, 'Audio', 'on' if state['save_audio'] else 'off')
    if state.get('save_audio') and state.get('audio_dir'):
        _append_summary_item(summary, 'Audio dir', _format_output_path(state['audio_dir']), value_style='dim')
    if 'use_ai' in state:
        _append_summary_item(summary, 'AI', 'on' if state['use_ai'] else 'off')
    if 'output_dir' in state:
        _append_summary_item(summary, 'Output', _format_output_path(state['output_dir']), value_style='dim')

    return summary if summary.plain else None


def _format_config_summary(config: dict | None) -> Text | None:
    if not config:
        return None

    normalized = _normalize_config(config)
    return _format_prompt_summary({
        'output_formats': normalized['output_formats'],
        'save_audio': normalized['save_audio'],
        'audio_dir': normalized['audio_dir'],
        'use_ai': normalized['use_ai'],
        'output_dir': normalized['output_dir'],
    })


def _render_prompt_page(
    config: dict | None,
    step_label: str,
    prompt_title: str,
    summary: Text | None = None,
    clear_console: bool = True,
):
    if clear_console:
        console.clear()
    _banner(config)

    if summary and summary.plain:
        summary_line = Text('  ')
        summary_line.append('Chosen: ', style='cyan')
        summary_line.append_text(summary)
        console.print(summary_line)
        console.print()

    step_line = Text('  ')
    step_line.append(step_label, style='bold cyan')
    step_line.append(f' {prompt_title}', style='cyan')
    console.print(step_line)
    console.print()


def _banner(config: dict | None):
    current = _format_config(config)

    title = Text()
    title.append('🎙  PodScribe', style='bold cyan')
    title.append(f'  v{VERSION}', style='dim')

    content = Text()
    content.append_text(title)
    content.append('\n')
    content.append('Podcast → Text, powered by AI', style='dim white')
    content.append('\n\n')
    content.append(f"Format: {current['formats']}")
    content.append('\n')
    content.append(f"Output: {current['output']}")
    content.append('\n')
    content.append(f"AI post: {current['ai']}")

    panel = Panel(
        content,
        border_style='cyan',
        padding=(0, 2),
        width=42,
    )
    console.print()
    console.print(panel)


def _state_to_config(state: dict) -> dict:
    return _normalize_config({
        'output_formats': state.get('output_formats'),
        'output_dir': state.get('output_dir'),
        'save_audio': state.get('save_audio'),
        'audio_dir': state.get('audio_dir'),
        'use_ai': state.get('use_ai'),
    })


def _parse_episode_urls(raw_urls: str) -> list[str]:
    return [url.strip() for url in raw_urls.split(',') if url.strip()]


def _prompt_episode_urls(
    current_config: dict | None = None,
    prompt_title: str = 'Enter episode URLs',
    clear_console: bool = True,
) -> list[str]:
    from InquirerPy import inquirer

    _render_prompt_page(
        current_config,
        '[1/1]',
        prompt_title,
        _format_config_summary(current_config),
        clear_console=clear_console,
    )
    raw_urls = inquirer.text(
        message='Paste Xiaoyuzhou episode URL(s), separated by commas:',
        qmark='🔗',
        validate=lambda value: len(_parse_episode_urls(value)) > 0,
        invalid_message='Enter at least one URL.',
    ).execute()
    urls = _parse_episode_urls(raw_urls)
    console.print()
    console.print(f'  [green]Found {len(urls)} episode(s) to process[/]')
    return urls


def _prompt_config(current_config: dict | None = None) -> dict:
    from InquirerPy import inquirer

    config = _normalize_config(current_config)
    state: dict = {}

    _render_prompt_page(
        _merge_prompt_config(config, state),
        '[1/5]',
        'Audio settings',
        _format_prompt_summary(state),
    )
    save_audio = inquirer.confirm(
        message='Save audio file locally?',
        default=config['save_audio'],
        qmark='💾',
    ).execute()
    state['save_audio'] = save_audio

    audio_dir = None
    if save_audio:
        _render_prompt_page(
            _merge_prompt_config(config, state),
            '[2/5]',
            'Audio directory',
            _format_prompt_summary(state),
        )
        audio_dir = inquirer.text(
            message='Audio save directory:',
            default=config['audio_dir'] or str(DEFAULT_OUTPUT_DIR / 'audio'),
            qmark='📂',
        ).execute().strip()
        state['audio_dir'] = audio_dir

    _render_prompt_page(
        _merge_prompt_config(config, state),
        '[3/5]',
        'Output formats',
        _format_prompt_summary(state),
    )
    output_formats = inquirer.checkbox(
        message='Select output formats:',
        choices=[
            {'name': 'txt  — plain text', 'value': 'txt', 'enabled': 'txt' in config['output_formats']},
            {'name': 'srt  — subtitles with timestamps', 'value': 'srt', 'enabled': 'srt' in config['output_formats']},
        ],
        qmark='📄',
        pointer='›',
        enabled_symbol='●',
        disabled_symbol='○',
        validate=lambda value: len(value) > 0,
        invalid_message='Select at least one format.',
    ).execute()
    state['output_formats'] = output_formats

    _render_prompt_page(
        _merge_prompt_config(config, state),
        '[4/5]',
        'AI post-processing',
        _format_prompt_summary(state),
    )
    use_ai = inquirer.confirm(
        message='AI post-processing? (fix punctuation, add paragraphs)',
        default=config['use_ai'],
        qmark='🤖',
    ).execute()
    state['use_ai'] = use_ai

    _render_prompt_page(
        _merge_prompt_config(config, state),
        '[5/5]',
        'Transcript directory',
        _format_prompt_summary(state),
    )
    output_dir = inquirer.text(
        message='Transcript save directory:',
        default=config['output_dir'],
        qmark='📂',
    ).execute().strip()
    state['output_dir'] = output_dir

    return {
        'output_formats': output_formats,
        'output_dir': output_dir,
        'save_audio': save_audio,
        'audio_dir': audio_dir,
        'use_ai': use_ai,
    }


def _check_resume():
    from InquirerPy import inquirer
    from podscribe.task_state import load_state

    state = load_state()
    if not state:
        return None

    console.print()
    console.print('  [bold yellow]Unfinished task detected:[/]')
    console.print(f"    Episode : {state.get('episode_title', 'unknown')}")
    console.print(f"    URL     : {state.get('episode_url', 'unknown')}")
    step = state.get('completed_step', '?')
    console.print(f'    Progress: stopped after step [{step}]')
    if state.get('task_id'):
        console.print(f"    Task ID : {state['task_id']}")
    console.print()

    choice = inquirer.select(
        message='What would you like to do?',
        choices=[
            {'name': 'Resume this task', 'value': 'resume'},
            {'name': 'Start a new task', 'value': 'new'},
            {'name': 'Quit', 'value': 'quit'},
        ],
        default='resume',
        pointer='›',
        qmark='?',
    ).execute()

    if choice == 'resume':
        return state
    if choice == 'quit':
        sys.exit(0)
    return None


def _show_history(config: dict | None):
    _banner(config)

    records = sorted(
        load_history(),
        key=lambda record: record.get('timestamp', ''),
        reverse=True,
    )[:20]

    console.print()
    if not records:
        console.print('  [dim]No history yet.[/]')
        return

    table = Table(show_header=True, header_style='bold cyan')
    table.add_column('Time', style='dim')
    table.add_column('Title')
    table.add_column('Status')
    table.add_column('Output')

    for record in records:
        status = record.get('status', 'failed')
        status_text = '[green]success[/]' if status == 'success' else '[red]failed[/]'
        output_files = record.get('output_files') or []
        output_text = '\n'.join(output_files) if output_files else '-'
        table.add_row(
            record.get('timestamp', '-'),
            record.get('title') or record.get('url', '-'),
            status_text,
            output_text,
        )

    console.print(table)


def _edit_config(current_config: dict | None):
    console.clear()
    _banner(current_config)

    current = _format_config(current_config)
    console.print()
    console.print('  [bold cyan]Config mode[/]')
    console.print(f"    Format    : [green]{current['formats']}[/]")
    console.print(f"    Output    : [dim]{current['output']}[/]")
    console.print(f"    Save audio: [green]{current['save_audio']}[/]")
    if _normalize_config(current_config)['save_audio']:
        console.print(f"    Audio dir : [dim]{current['audio_dir']}[/]")
    console.print(f"    AI post   : [green]{current['ai']}[/]")

    config = _prompt_config(current_config)
    save_config(config)

    console.print()
    console.print(Panel(
        'Configuration saved.',
        border_style='green',
        title='[bold green]Config[/]',
        padding=(0, 2),
        width=42,
    ))


def _build_state(episode_url: str, config: dict) -> dict:
    return {
        'episode_url': episode_url,
        'save_audio': config['save_audio'],
        'audio_dir': config['audio_dir'],
        'output_formats': config['output_formats'],
        'use_ai': config['use_ai'],
        'output_dir': config['output_dir'],
        'completed_step': 0,
    }


def _record_failure(episode_url: str, state: dict, error: str):
    add_record(
        url=episode_url,
        title=state.get('episode_title') or episode_url,
        status='failed',
        output_files=[],
        error=error,
    )


def _process_episode(
    episode_url: str,
    config: dict,
    index: int,
    total: int,
    resumed_state: dict | None = None,
) -> bool:
    import requests

    from podscribe.podcast_downloader import download_audio, extract_audio_url
    from podscribe.srt_formatter import sentences_to_srt
    from podscribe.task_state import clear_state, save_state
    from podscribe.transcriber import resume_transcription, transcribe_audio

    config = _normalize_config(config)
    state = resumed_state.copy() if resumed_state else _build_state(episode_url, config)
    completed_step = state.get('completed_step', 0)
    output_path = Path(config['output_dir'])
    output_path.mkdir(parents=True, exist_ok=True)

    total_steps = 3 + (1 if config['save_audio'] else 0) + (1 if config['use_ai'] else 0)
    current_step = 0

    console.print()
    console.print(f'  [bold cyan][{index}/{total}][/] [cyan]Processing episode {index}...[/]')

    try:
        current_step += 1
        if completed_step < current_step:
            with console.status(f'[bold cyan][{current_step}/{total_steps}][/] [cyan]Parsing episode page...[/]', spinner='dots'):
                audio_url, episode_title = extract_audio_url(episode_url)
            state['audio_url'] = audio_url
            state['episode_title'] = episode_title
            state['completed_step'] = current_step
            save_state(state)
        else:
            audio_url = state['audio_url']
            episode_title = state['episode_title']
        console.print(f'  [green]✓[/] Episode : [bold green]{episode_title}[/]')
        console.print(f'  [green]✓[/] Audio   : [dim]{audio_url}[/]')

        if config['save_audio']:
            current_step += 1
            if completed_step < current_step:
                console.print()
                console.print(f'  [bold cyan][{current_step}/{total_steps}][/] [cyan]Downloading audio...[/]')
                audio_save_path = Path(config['audio_dir'])
                audio_save_path.mkdir(parents=True, exist_ok=True)
                audio_ext = audio_url.rsplit('.', 1)[-1].split('?')[0]
                audio_file = audio_save_path / f'{episode_title}.{audio_ext}'
                download_audio(audio_url, str(audio_file))
                console.print(f'  [green]✓[/] Saved to: [dim]{audio_file}[/]')
                state['completed_step'] = current_step
                save_state(state)

        current_step += 1
        with console.status(f'[bold cyan][{current_step}/{total_steps}][/] [cyan]Transcribing audio (DashScope Paraformer-v2)...[/]', spinner='dots'):
            task_id = state.get('task_id')
            if task_id:
                result = resume_transcription(task_id)
            else:
                result = transcribe_audio(audio_url)
        text = result['text']
        sentences = result['sentences']
        state['completed_step'] = current_step
        save_state(state)
        console.print(f'  [green]✓[/] Recognized {len(text)} characters, {len(sentences)} sentences')

        if config['use_ai']:
            current_step += 1
            with console.status(f'[bold cyan][{current_step}/{total_steps}][/] [cyan]AI post-processing (Qwen)...[/]', spinner='dots'):
                from podscribe.ai_postprocess import postprocess_text

                text = postprocess_text(text)
            state['completed_step'] = current_step
            save_state(state)
            console.print('  [green]✓[/] Post-processing complete')

        current_step += 1
        saved_files = []

        if 'txt' in config['output_formats']:
            txt_path = output_path / f'{episode_title}.txt'
            txt_path.write_text(text, encoding='utf-8')
            saved_files.append(str(txt_path.resolve()))

        if 'srt' in config['output_formats']:
            srt_path = output_path / f'{episode_title}.srt'
            srt_content = sentences_to_srt(sentences)
            srt_path.write_text(srt_content, encoding='utf-8')
            saved_files.append(str(srt_path.resolve()))

        clear_state()
        add_record(
            url=episode_url,
            title=episode_title,
            status='success',
            output_files=saved_files,
        )

        console.print()
        done_text = Text()
        done_text.append('Done! ', style='bold green')
        done_text.append(f'{len(text)} characters transcribed', style='dim')
        results = Text()
        for idx, file_path in enumerate(saved_files):
            if idx:
                results.append('\n')
            results.append(f'  → {file_path}', style='dim')
        console.print(Panel(
            Text.assemble(done_text, '\n\n', results),
            border_style='green',
            title='[bold green]Complete[/]',
            padding=(0, 2),
            width=60,
        ))
        return True
    except requests.exceptions.Timeout:
        _record_failure(episode_url, state, 'Request timed out. Check your network.')
        console.print('\n  [bold red]Error:[/] Request timed out. Check your network.')
        return False
    except requests.exceptions.HTTPError as error:
        status_code = error.response.status_code if error.response else 'unknown'
        message = f'HTTP {status_code}'
        _record_failure(episode_url, state, message)
        console.print(f'\n  [bold red]Error:[/] {message}')
        return False
    except (ValueError, RuntimeError) as error:
        _record_failure(episode_url, state, str(error))
        console.print(f'\n  [bold red]Error:[/] {error}')
        return False
    except KeyboardInterrupt:
        _record_failure(episode_url, state, 'Interrupted by user.')
        console.print('\n  [dim]Interrupted.[/]')
        sys.exit(130)


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else None
    current_config = load_config()

    if command == 'config':
        _edit_config(current_config)
        return

    if command == 'history':
        _show_history(current_config)
        return

    _banner(current_config)

    from podscribe.setup_helper import check_and_setup

    check_and_setup()

    resumed = _check_resume()
    if resumed:
        config = _state_to_config(resumed)
    else:
        config = _normalize_config(current_config) if current_config else None

    first_iteration = True
    next_resumed_state = resumed

    while True:
        if next_resumed_state:
            episode_urls = [next_resumed_state['episode_url']]
        else:
            if not first_iteration:
                console.clear()
            try:
                episode_urls = _prompt_episode_urls(
                    config or current_config,
                    prompt_title='Paste new URL(s) to continue, or press Ctrl+C to exit' if not first_iteration else 'Enter episode URLs',
                    clear_console=first_iteration,
                )
            except KeyboardInterrupt:
                console.print('\n  [dim]Goodbye.[/]')
                return
            if config is None:
                config = _prompt_config()
                save_config(config)

        results: list[bool] = []
        for index, episode_url in enumerate(episode_urls, start=1):
            resumed_state = next_resumed_state if next_resumed_state and index == 1 else None
            results.append(_process_episode(
                episode_url=episode_url,
                config=config,
                index=index,
                total=len(episode_urls),
                resumed_state=resumed_state,
            ))

        succeeded = sum(1 for result in results if result)
        failed = len(results) - succeeded

        console.print()
        summary_text = Text()
        summary_text.append('Batch complete: ', style='cyan')
        summary_text.append(f'{succeeded} succeeded', style='green')
        summary_text.append(', ', style='cyan')
        summary_text.append(f'{failed} failed', style='red' if failed else 'cyan')
        console.print(Panel(
            summary_text,
            border_style='cyan',
            title='[bold cyan]Batch Summary[/]',
            padding=(0, 2),
            width=60,
        ))

        time.sleep(0.8)
        first_iteration = False
        next_resumed_state = None


if __name__ == '__main__':
    main()
