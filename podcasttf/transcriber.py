import time
import requests
from http import HTTPStatus
from dashscope.audio.asr import Transcription


def transcribe_audio(audio_url: str, language: str = 'zh') -> dict:
    """Transcribe audio and return full result with timestamps.

    Returns dict with keys:
        - text: full transcribed text
        - sentences: list of {begin_time, end_time, text} dicts (times in ms)
    """
    print('  Submitting transcription task...')
    task_response = Transcription.async_call(
        model='paraformer-v2',
        file_urls=[audio_url],
        language_hints=[language, 'en'],
    )

    if task_response.status_code != HTTPStatus.OK:
        raise RuntimeError(
            f'Transcription submission failed: '
            f'{task_response.code} - {task_response.message}'
        )

    task_id = task_response.output.task_id
    print(f'  Task ID: {task_id}')

    # Persist task_id so it can be resumed if interrupted
    from podcasttf.task_state import load_state, save_state
    state = load_state() or {}
    state['task_id'] = task_id
    save_state(state)

    return _wait_and_extract(task_id)


def resume_transcription(task_id: str) -> dict:
    """Resume a previous transcription task by its task ID.

    Returns dict with keys:
        - text: full transcribed text
        - sentences: list of {begin_time, end_time, text} dicts (times in ms)
    """
    print(f'  Resuming task: {task_id}')
    return _wait_and_extract(task_id)


def _wait_and_extract(task_id: str) -> dict:
    """Poll task status and extract result when done."""
    while True:
        time.sleep(5)
        result = Transcription.fetch(task=task_id)
        status = result.output.task_status
        print(f'\r  Status: {status}', end='', flush=True)

        if status == 'SUCCEEDED':
            print()
            return _extract_result(result)
        elif status == 'FAILED':
            print()
            raise RuntimeError(
                f'Transcription failed: {result.output}'
            )


def _extract_result(result) -> dict:
    """Extract text and sentence-level timestamps from transcription result."""
    results = result.output.get('results')
    if not results:
        raise RuntimeError('No transcription results returned')

    transcription_url = results[0].get('transcription_url')
    if not transcription_url:
        raise RuntimeError('No transcription URL in result')

    resp = requests.get(
        transcription_url, timeout=30,
        proxies={'http': None, 'https': None},
    )
    resp.raise_for_status()
    transcript_data = resp.json()

    full_text = ''
    all_sentences = []

    for transcript in transcript_data.get('transcripts', []):
        full_text += transcript.get('text', '')
        for sentence in transcript.get('sentences', []):
            all_sentences.append({
                'begin_time': sentence.get('begin_time', 0),
                'end_time': sentence.get('end_time', 0),
                'text': sentence.get('text', ''),
            })

    if not full_text:
        raise RuntimeError('Transcription result is empty')

    return {'text': full_text, 'sentences': all_sentences}
