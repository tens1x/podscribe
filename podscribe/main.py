import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from podscribe.app_service import (
    DEFAULT_CONFIG,
    DEFAULT_OUTPUT_DIR,
    PodscribeError,
    build_request,
    normalize_config as service_normalize_config,
    process_episode,
)
from podscribe.config import load_config, save_config
from podscribe.history import load_history

console = Console()
VERSION = '0.1.0'


def _normalize_config(config: dict | None) -> dict:
    return service_normalize_config(config)


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


def _format_config_summary(config: dict | None) -> Text | None:
    if not config:
        return None

    normalized = _normalize_config(config)
    summary = Text()
    summary.append('Format: ', style='dim')
    summary.append(' + '.join(normalized['output_formats']), style='green')
    summary.append(' | ', style='dim')
    summary.append('Audio: ', style='dim')
    summary.append('on' if normalized['save_audio'] else 'off', style='green')
    if normalized['save_audio'] and normalized['audio_dir']:
        summary.append(' | ', style='dim')
        summary.append('Audio dir: ', style='dim')
        summary.append(_format_output_path(normalized['audio_dir']), style='dim')
    summary.append(' | ', style='dim')
    summary.append('AI: ', style='dim')
    summary.append('on' if normalized['use_ai'] else 'off', style='green')
    summary.append(' | ', style='dim')
    summary.append('Output: ', style='dim')
    summary.append(_format_output_path(normalized['output_dir']), style='dim')
    return summary


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


def _format_menu_path(path_value: str | None) -> str:
    if not path_value:
        return '-'

    home = Path.home()
    path = Path(path_value).expanduser()
    try:
        relative = path.relative_to(home)
        return '~' if str(relative) == '.' else f'~/{relative}'
    except ValueError:
        return _format_output_path(path_value)


def _format_edit_config_value(config: dict, key: str) -> str:
    if key == 'output_formats':
        return ' + '.join(config['output_formats'])
    if key == 'save_audio':
        return 'on' if config['save_audio'] else 'off'
    if key == 'audio_dir':
        return _format_menu_path(config['audio_dir'] or str(DEFAULT_OUTPUT_DIR / 'audio'))
    if key == 'use_ai':
        return 'on' if config['use_ai'] else 'off'
    if key == 'output_dir':
        return _format_menu_path(config['output_dir'])
    raise KeyError(key)


def _edit_config_menu(config: dict) -> dict:
    from InquirerPy import inquirer
    from InquirerPy.separator import Separator

    original_config = config
    working_config = _normalize_config(config)
    label_width = 18

    try:
        while True:
            console.clear()
            _banner(working_config)
            console.print()
            console.print('  [bold cyan]Edit config[/]')
            console.print()

            choice = inquirer.select(
                message='Select an option to change:',
                choices=[
                    {
                        'name': f"{'Output formats':<{label_width}} [{_format_edit_config_value(working_config, 'output_formats')}]",
                        'value': 'output_formats',
                    },
                    {
                        'name': f"{'Save audio':<{label_width}} [{_format_edit_config_value(working_config, 'save_audio')}]",
                        'value': 'save_audio',
                    },
                    {
                        'name': f"{'Audio directory':<{label_width}} [{_format_edit_config_value(working_config, 'audio_dir')}]",
                        'value': 'audio_dir',
                    },
                    {
                        'name': f"{'AI post-process':<{label_width}} [{_format_edit_config_value(working_config, 'use_ai')}]",
                        'value': 'use_ai',
                    },
                    {
                        'name': f"{'Output directory':<{label_width}} [{_format_edit_config_value(working_config, 'output_dir')}]",
                        'value': 'output_dir',
                    },
                    Separator('────────────────'),
                    {'name': 'Save & back', 'value': 'save'},
                    {'name': 'Discard & back', 'value': 'discard'},
                ],
                pointer='›',
                qmark='?',
            ).execute()

            if choice == 'save':
                return working_config
            if choice == 'discard':
                return original_config

            if choice == 'output_formats':
                selected_formats = inquirer.checkbox(
                    message='Select output formats:',
                    choices=[
                        {'name': 'txt  — plain text', 'value': 'txt', 'enabled': 'txt' in working_config['output_formats']},
                        {'name': 'srt  — subtitles with timestamps', 'value': 'srt', 'enabled': 'srt' in working_config['output_formats']},
                    ],
                    qmark='📄',
                    pointer='›',
                    enabled_symbol='●',
                    disabled_symbol='○',
                    validate=lambda value: len(value) > 0,
                    invalid_message='Select at least one format.',
                ).execute()
                working_config['output_formats'] = selected_formats
                continue

            if choice == 'save_audio':
                working_config['save_audio'] = inquirer.confirm(
                    message='Save audio file locally?',
                    default=working_config['save_audio'],
                    qmark='💾',
                ).execute()
                continue

            if choice == 'audio_dir':
                if not working_config['save_audio']:
                    console.print()
                    console.print('  [dim]Enable "Save audio" first to edit the audio directory.[/]')
                    console.print()
                    _pause()
                    continue
                working_config['audio_dir'] = inquirer.text(
                    message='Audio save directory:',
                    default=working_config['audio_dir'] or str(DEFAULT_OUTPUT_DIR / 'audio'),
                    qmark='📂',
                ).execute().strip()
                continue

            if choice == 'use_ai':
                working_config['use_ai'] = inquirer.confirm(
                    message='AI post-processing? (fix punctuation, add paragraphs)',
                    default=working_config['use_ai'],
                    qmark='🤖',
                ).execute()
                continue

            if choice == 'output_dir':
                working_config['output_dir'] = inquirer.text(
                    message='Transcript save directory:',
                    default=working_config['output_dir'],
                    qmark='📂',
                ).execute().strip()
    except KeyboardInterrupt:
        return original_config


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


def _show_history(config: dict | None, show_banner: bool = True):
    if show_banner:
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


def _edit_config(
    current_config: dict | None,
    *,
    show_banner: bool = True,
    clear_console: bool = True,
):
    if clear_console:
        console.clear()
    if show_banner:
        _banner(current_config)

    original_config = _normalize_config(current_config)
    updated_config = _edit_config_menu(original_config)
    if updated_config is original_config:
        return

    save_config(updated_config)

    console.print()
    console.print(Panel(
        'Configuration saved.',
        border_style='green',
        title='[bold green]Config[/]',
        padding=(0, 2),
        width=42,
    ))


def _main_menu(config: dict | None) -> str:
    from InquirerPy import inquirer

    return inquirer.select(
        message='What would you like to do?',
        choices=[
            {'name': 'Start transcription', 'value': 'start'},
            {'name': 'Edit config', 'value': 'edit_config'},
            {'name': 'View history', 'value': 'view_history'},
            {'name': 'Quit', 'value': 'quit'},
        ],
        pointer='›',
        qmark='?',
    ).execute()


def _pause():
    input('  Press Enter to continue...')


def _process_episode(
    episode_url: str,
    config: dict,
    index: int,
    total: int,
    resumed_state: dict | None = None,
) -> bool:
    try:
        request = build_request(
            episode_url,
            config,
            resumed_state=resumed_state,
            index=index,
            total=total,
        )
        last_message = None

        def on_progress(event):
            nonlocal last_message
            if event.message == last_message:
                return
            last_message = event.message
            console.print(f'  [cyan]{event.message}[/]')

        result = process_episode(request, progress_callback=on_progress)

        console.print()
        done_text = Text()
        done_text.append('Done! ', style='bold green')
        done_text.append(f'{len(result.text)} characters transcribed', style='dim')
        results = Text()
        for idx, file_path in enumerate(result.output_files):
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
    except PodscribeError as error:
        console.print(f'\n  [bold red]Error:[/] {error}')
        return False
    except KeyboardInterrupt:
        console.print('\n  [dim]Interrupted.[/]')
        raise


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else None
    raw_config = load_config()
    current_config = _normalize_config(raw_config)

    if command == 'config':
        _edit_config(current_config)
        return

    if command == 'history':
        _show_history(current_config)
        return

    if command == 'gui':
        from podscribe.gui import main as gui_main

        gui_main()
        return

    from podscribe.setup_helper import check_and_setup

    _banner(current_config)
    check_and_setup()

    try:
        resumed = _check_resume()
    except KeyboardInterrupt:
        console.print('\n  [dim]Goodbye.[/]')
        return

    config = _state_to_config(resumed) if resumed else current_config

    if resumed:
        try:
            results = [
                _process_episode(
                    episode_url=resumed['episode_url'],
                    config=config,
                    index=1,
                    total=1,
                    resumed_state=resumed,
                )
            ]
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
            console.print()
            _pause()
        except KeyboardInterrupt:
            console.print('\n  [dim]Cancelled.[/]')
        config = _normalize_config(load_config())

    if raw_config is None and not resumed:
        default_config = _normalize_config(DEFAULT_CONFIG)
        configured_config = _edit_config_menu(default_config)
        if configured_config is not default_config:
            save_config(configured_config)
            config = _normalize_config(load_config())
        else:
            config = default_config

    while True:
        console.clear()
        _banner(config)
        try:
            choice = _main_menu(config)
        except KeyboardInterrupt:
            console.print('\n  [dim]Goodbye.[/]')
            return

        if choice == 'start':
            try:
                episode_urls = _prompt_episode_urls(
                    config,
                    prompt_title='Enter episode URLs',
                    clear_console=True,
                )
                results: list[bool] = []
                for index, episode_url in enumerate(episode_urls, start=1):
                    results.append(_process_episode(
                        episode_url=episode_url,
                        config=config,
                        index=index,
                        total=len(episode_urls),
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
                console.print()
                _pause()
            except KeyboardInterrupt:
                console.print('\n  [dim]Cancelled.[/]')
            continue

        if choice == 'edit_config':
            try:
                console.clear()
                _banner(config)
                _edit_config(config, show_banner=False, clear_console=False)
            except KeyboardInterrupt:
                pass
            config = _normalize_config(load_config())
            continue

        if choice == 'view_history':
            try:
                console.clear()
                _banner(config)
                _show_history(config, show_banner=False)
                console.print()
                _pause()
            except KeyboardInterrupt:
                pass
            continue

        console.print('\n  [dim]Goodbye.[/]')
        return


if __name__ == '__main__':
    main()
