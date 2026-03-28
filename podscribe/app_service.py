from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import requests

from podscribe.ai_postprocess import postprocess_text
from podscribe.history import add_record
from podscribe.podcast_downloader import download_audio, extract_audio_url
from podscribe.srt_formatter import sentences_to_srt
from podscribe.task_state import clear_state, save_state
from podscribe.transcriber import resume_transcription, transcribe_audio

DEFAULT_OUTPUT_DIR = Path.home() / 'PodScribe'
DEFAULT_CONFIG = {
    'output_formats': ['txt', 'srt'],
    'output_dir': str(DEFAULT_OUTPUT_DIR),
    'save_audio': False,
    'audio_dir': None,
    'use_ai': True,
}


class PodscribeError(RuntimeError):
    """User-facing transcription error."""


@dataclass(slots=True)
class ProgressEvent:
    step: int
    total_steps: int
    stage: str
    message: str


@dataclass(slots=True)
class TranscriptionRequest:
    episode_url: str
    output_formats: list[str]
    output_dir: str
    save_audio: bool = False
    audio_dir: str | None = None
    use_ai: bool = True
    resumed_state: dict[str, Any] | None = None
    index: int = 1
    total: int = 1


@dataclass(slots=True)
class TranscriptionResult:
    episode_title: str
    text: str
    sentences: list[dict[str, Any]]
    output_files: list[str]
    audio_file: str | None = None


ProgressCallback = Callable[[ProgressEvent], None]


def normalize_config(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = DEFAULT_CONFIG.copy()
    if config:
        merged.update(config)

    output_formats = merged.get('output_formats') or DEFAULT_CONFIG['output_formats']
    merged['output_formats'] = [
        fmt for fmt in output_formats if fmt in {'txt', 'srt'}
    ] or DEFAULT_CONFIG['output_formats']
    merged['output_dir'] = str(merged.get('output_dir') or DEFAULT_CONFIG['output_dir'])
    merged['save_audio'] = bool(merged.get('save_audio', DEFAULT_CONFIG['save_audio']))
    merged['audio_dir'] = merged.get('audio_dir') or None
    merged['use_ai'] = bool(merged.get('use_ai', DEFAULT_CONFIG['use_ai']))
    if merged['save_audio'] and not merged['audio_dir']:
        merged['audio_dir'] = str(DEFAULT_OUTPUT_DIR / 'audio')
    return merged


def build_request(
    episode_url: str,
    config: dict[str, Any],
    *,
    resumed_state: dict[str, Any] | None = None,
    index: int = 1,
    total: int = 1,
) -> TranscriptionRequest:
    normalized = normalize_config(config)
    return TranscriptionRequest(
        episode_url=episode_url,
        output_formats=list(normalized['output_formats']),
        output_dir=normalized['output_dir'],
        save_audio=normalized['save_audio'],
        audio_dir=normalized['audio_dir'],
        use_ai=normalized['use_ai'],
        resumed_state=resumed_state,
        index=index,
        total=total,
    )


def process_episode(
    request: TranscriptionRequest,
    progress_callback: ProgressCallback | None = None,
) -> TranscriptionResult:
    config = normalize_config({
        'output_formats': request.output_formats,
        'output_dir': request.output_dir,
        'save_audio': request.save_audio,
        'audio_dir': request.audio_dir,
        'use_ai': request.use_ai,
    })
    state = request.resumed_state.copy() if request.resumed_state else _build_state(request.episode_url, config)
    completed_step = state.get('completed_step', 0)
    output_path = Path(config['output_dir'])
    output_path.mkdir(parents=True, exist_ok=True)

    total_steps = 3 + (1 if config['save_audio'] else 0) + (1 if config['use_ai'] else 0)
    current_step = 0
    audio_file_path: str | None = None

    def emit(stage: str, message: str, step: int = current_step):
        if progress_callback is None:
            return
        progress_callback(ProgressEvent(
            step=step,
            total_steps=total_steps,
            stage=stage,
            message=message,
        ))

    try:
        current_step += 1
        emit('parse', f'[{request.index}/{request.total}] Parsing episode page...')
        if completed_step < current_step:
            audio_url, episode_title = extract_audio_url(request.episode_url)
            state['audio_url'] = audio_url
            state['episode_title'] = episode_title
            state['completed_step'] = current_step
            save_state(state)
        else:
            audio_url = state['audio_url']
            episode_title = state['episode_title']
        emit('parse', f'[{request.index}/{request.total}] Episode: {episode_title}', step=current_step)

        if config['save_audio']:
            current_step += 1
            emit('download', f'[{request.index}/{request.total}] Downloading audio...')
            if completed_step < current_step:
                audio_save_path = Path(config['audio_dir'])
                audio_save_path.mkdir(parents=True, exist_ok=True)
                audio_ext = audio_url.rsplit('.', 1)[-1].split('?')[0]
                audio_file = audio_save_path / f'{episode_title}.{audio_ext}'
                download_audio(audio_url, str(audio_file))
                audio_file_path = str(audio_file.resolve())
                state['audio_file'] = audio_file_path
                state['completed_step'] = current_step
                save_state(state)
            else:
                audio_file_path = state.get('audio_file')
            emit('download', f'[{request.index}/{request.total}] Audio saved')

        current_step += 1
        emit('transcribe', f'[{request.index}/{request.total}] Submitting transcription...')
        last_status: str | None = None

        def on_status(status: str):
            nonlocal last_status
            if status == last_status:
                return
            last_status = status
            emit('transcribe', f'[{request.index}/{request.total}] Transcription status: {status}')

        with_status = on_status if progress_callback else None
        task_id = state.get('task_id')
        if task_id:
            result = resume_transcription(task_id, status_callback=with_status)
        else:
            result = transcribe_audio(audio_url, status_callback=with_status)
        text = result['text']
        sentences = result['sentences']
        state['completed_step'] = current_step
        save_state(state)
        emit('transcribe', f'[{request.index}/{request.total}] Transcribed {len(text)} characters')

        if config['use_ai']:
            current_step += 1
            emit('postprocess', f'[{request.index}/{request.total}] AI post-processing...')
            text = postprocess_text(text)
            state['completed_step'] = current_step
            save_state(state)
            emit('postprocess', f'[{request.index}/{request.total}] AI post-processing complete')

        current_step += 1
        emit('save', f'[{request.index}/{request.total}] Saving output files...')
        saved_files: list[str] = []

        if 'txt' in config['output_formats']:
            txt_path = output_path / f'{episode_title}.txt'
            txt_path.write_text(text, encoding='utf-8')
            saved_files.append(str(txt_path.resolve()))

        if 'srt' in config['output_formats']:
            srt_path = output_path / f'{episode_title}.srt'
            srt_path.write_text(sentences_to_srt(sentences), encoding='utf-8')
            saved_files.append(str(srt_path.resolve()))

        clear_state()
        add_record(
            url=request.episode_url,
            title=episode_title,
            status='success',
            output_files=saved_files,
        )
        emit('complete', f'[{request.index}/{request.total}] Finished {episode_title}')
        return TranscriptionResult(
            episode_title=episode_title,
            text=text,
            sentences=sentences,
            output_files=saved_files,
            audio_file=audio_file_path,
        )
    except KeyboardInterrupt:
        _record_failure(request.episode_url, state, 'Interrupted by user.')
        raise
    except requests.exceptions.Timeout as error:
        message = 'Request timed out. Check your network.'
        _record_failure(request.episode_url, state, message)
        raise PodscribeError(message) from error
    except requests.exceptions.HTTPError as error:
        status_code = error.response.status_code if error.response else 'unknown'
        message = f'HTTP {status_code}'
        _record_failure(request.episode_url, state, message)
        raise PodscribeError(message) from error
    except (ValueError, RuntimeError) as error:
        message = str(error)
        _record_failure(request.episode_url, state, message)
        raise PodscribeError(message) from error


def _build_state(episode_url: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        'episode_url': episode_url,
        'save_audio': config['save_audio'],
        'audio_dir': config['audio_dir'],
        'output_formats': config['output_formats'],
        'use_ai': config['use_ai'],
        'output_dir': config['output_dir'],
        'completed_step': 0,
    }


def _record_failure(episode_url: str, state: dict[str, Any], error: str):
    add_record(
        url=episode_url,
        title=state.get('episode_title') or episode_url,
        status='failed',
        output_files=[],
        error=error,
    )
