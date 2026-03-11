def ms_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT time format: HH:MM:SS,mmm"""
    hours = ms // 3_600_000
    ms %= 3_600_000
    minutes = ms // 60_000
    ms %= 60_000
    seconds = ms // 1_000
    millis = ms % 1_000
    return f'{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}'


def sentences_to_srt(sentences: list) -> str:
    """Convert sentence list (with begin_time/end_time in ms) to SRT string."""
    blocks = []
    for i, s in enumerate(sentences, 1):
        start = ms_to_srt_time(s['begin_time'])
        end = ms_to_srt_time(s['end_time'])
        blocks.append(f'{i}\n{start} --> {end}\n{s["text"]}')
    return '\n\n'.join(blocks) + '\n'
