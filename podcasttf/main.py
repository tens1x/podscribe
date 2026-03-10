import sys
from pathlib import Path

import requests


DEFAULT_OUTPUT_DIR = Path('output')


def _prompt(message: str, default: str = '') -> str:
    """Prompt user for input with optional default."""
    if default:
        raw = input(f'  {message} [{default}]: ').strip()
        return raw or default
    return input(f'  {message}: ').strip()


def _confirm(message: str, default: bool = True) -> bool:
    """Ask yes/no question."""
    hint = 'Y/n' if default else 'y/N'
    raw = input(f'  {message} ({hint}): ').strip().lower()
    if not raw:
        return default
    return raw in ('y', 'yes')


def _step(number: int, total: int, title: str):
    """Print step header."""
    print()
    print(f'  [{number}/{total}] {title}')
    print(f'  {"-" * 40}')


def main():
    from podcasttf.setup_helper import check_and_setup
    check_and_setup()

    print()
    print('=' * 50)
    print('  Podcast Transcription Tool')
    print('=' * 50)

    # --- Gather user input ---
    print()
    print('  Paste the Xiaoyuzhou episode URL:')
    episode_url = _prompt('URL')
    if not episode_url:
        print('  No URL provided. Exiting.')
        sys.exit(1)

    print()
    resume_task_id = _prompt('Resume from task ID? (leave empty to start new)', '')

    print()
    save_audio = _confirm('Save audio file locally?', default=False)
    audio_dir = None
    if save_audio:
        audio_dir = _prompt('Audio save directory', str(DEFAULT_OUTPUT_DIR / 'audio'))

    print()
    print('  Output format:')
    print('    1) txt only')
    print('    2) srt only (with timestamps)')
    print('    3) both txt + srt')
    fmt_choice = _prompt('Choose [1/2/3]', '3')
    output_formats = {
        '1': ['txt'],
        '2': ['srt'],
        '3': ['txt', 'srt'],
    }.get(fmt_choice, ['txt', 'srt'])

    print()
    use_ai = _confirm('AI post-processing? (fix punctuation, add paragraphs)', default=True)

    print()
    output_dir = _prompt('Transcript save directory', str(DEFAULT_OUTPUT_DIR))

    # --- Confirm and execute ---
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    total_steps = 3 + (1 if save_audio else 0) + (1 if use_ai else 0)
    current_step = 0

    try:
        from podcasttf.podcast_downloader import extract_audio_url, download_audio
        from podcasttf.transcriber import transcribe_audio
        from podcasttf.srt_formatter import sentences_to_srt

        # Step: Extract
        current_step += 1
        _step(current_step, total_steps, 'Parsing episode page')
        audio_url, episode_title = extract_audio_url(episode_url)
        print(f'  Episode : {episode_title}')
        print(f'  Audio   : {audio_url}')

        # Step: Download audio (optional)
        if save_audio:
            current_step += 1
            _step(current_step, total_steps, 'Downloading audio')
            audio_save_path = Path(audio_dir)
            audio_save_path.mkdir(parents=True, exist_ok=True)
            audio_ext = audio_url.rsplit('.', 1)[-1].split('?')[0]
            audio_file = audio_save_path / f'{episode_title}.{audio_ext}'
            download_audio(audio_url, str(audio_file))
            print(f'  Saved to: {audio_file}')

        # Step: Transcribe
        current_step += 1
        _step(current_step, total_steps, 'Transcribing audio (DashScope Paraformer-v2)')
        if resume_task_id:
            from podcasttf.transcriber import resume_transcription
            result = resume_transcription(resume_task_id)
        else:
            result = transcribe_audio(audio_url)
        text = result['text']
        sentences = result['sentences']
        print(f'  Recognized {len(text)} characters, {len(sentences)} sentences')

        # Step: AI post-processing (optional)
        if use_ai:
            current_step += 1
            _step(current_step, total_steps, 'AI post-processing (Qwen)')
            from podcasttf.ai_postprocess import postprocess_text
            text = postprocess_text(text)

        # Step: Save outputs
        current_step += 1
        _step(current_step, total_steps, 'Saving results')
        saved_files = []

        if 'txt' in output_formats:
            txt_path = output_path / f'{episode_title}.txt'
            txt_path.write_text(text, encoding='utf-8')
            saved_files.append(txt_path)
            print(f'  TXT: {txt_path}')

        if 'srt' in output_formats:
            srt_path = output_path / f'{episode_title}.srt'
            srt_content = sentences_to_srt(sentences)
            srt_path.write_text(srt_content, encoding='utf-8')
            saved_files.append(srt_path)
            print(f'  SRT: {srt_path}')

        # --- Done ---
        print()
        print('=' * 50)
        print('  Done!')
        print(f'  Total characters: {len(text)}')
        for f in saved_files:
            print(f'  -> {f.resolve()}')
        print('=' * 50)

    except requests.exceptions.Timeout:
        print('\n  Error: Request timed out. Check your network.')
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f'\n  Error: HTTP {e.response.status_code}')
        sys.exit(1)
    except (ValueError, RuntimeError) as e:
        print(f'\n  Error: {e}')
        sys.exit(1)
    except KeyboardInterrupt:
        print('\n  Interrupted.')
        sys.exit(130)


if __name__ == '__main__':
    main()
