import os
import time
import requests
from typing import Callable

API_URL_SUBMIT = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
API_URL_QUERY_BASE = "https://dashscope.aliyuncs.com/api/v1/tasks/"


def _get_headers() -> dict:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY not set")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }


def transcribe_audio(
    audio_url: str,
    language: str = 'zh',
    status_callback: Callable[[str], None] | None = None,
) -> dict:
    """Transcribe audio and return full result with timestamps.

    Returns dict with keys:
        - text: full transcribed text
        - sentences: list of {begin_time, end_time, text} dicts (times in ms)
    """
    headers = _get_headers()

    payload = {
        "model": "qwen3-asr-flash-filetrans",
        "input": {
            "file_url": audio_url,
        },
        "parameters": {
            "language": language,
            "enable_itn": False,
            "enable_words": True,
        },
    }

    resp = requests.post(API_URL_SUBMIT, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    task_id = data["output"]["task_id"]

    # Persist task_id so it can be resumed if interrupted
    from podscribe.task_state import load_state, save_state
    state = load_state() or {}
    state['task_id'] = task_id
    save_state(state)

    return _wait_and_extract(task_id, status_callback=status_callback)


def resume_transcription(
    task_id: str,
    status_callback: Callable[[str], None] | None = None,
) -> dict:
    """Resume a previous transcription task by its task ID."""
    return _wait_and_extract(task_id, status_callback=status_callback)


def _wait_and_extract(
    task_id: str,
    status_callback: Callable[[str], None] | None = None,
) -> dict:
    """Poll task status and extract result when done."""
    headers = _get_headers()

    while True:
        time.sleep(5)
        query_resp = requests.get(
            API_URL_QUERY_BASE + task_id, headers=headers, timeout=30
        )
        query_resp.raise_for_status()
        result = query_resp.json()
        status = result["output"]["task_status"]

        if status_callback:
            status_callback(status)

        if status == 'SUCCEEDED':
            return _extract_result(result)
        if status == 'FAILED':
            raise RuntimeError(f'Transcription failed: {result["output"]}')


def _extract_result(result: dict) -> dict:
    """Extract text and sentence-level timestamps from transcription result."""
    output = result.get("output", {})

    results = output.get("results")
    if not results:
        single_result = output.get("result")
        if single_result:
            results = [single_result]

    if not results:
        raise RuntimeError(
            f'No transcription results returned. Output keys: {list(output.keys())}'
        )

    transcription_url = results[0].get("transcription_url")
    if not transcription_url:
        raise RuntimeError('No transcription URL in result')

    resp = requests.get(transcription_url, timeout=30)
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
