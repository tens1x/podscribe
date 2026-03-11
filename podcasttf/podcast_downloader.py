import re
import json
import requests


def sanitize_filename(title: str) -> str:
    title = re.sub(r'[\\/:*?"<>|]', '', title)
    title = title.strip('. ')
    return title or 'untitled'


def extract_audio_url(episode_url: str) -> tuple:
    if 'xiaoyuzhoufm.com/episode/' not in episode_url:
        raise ValueError(f'Invalid Xiaoyuzhou episode URL: {episode_url}')

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }

    response = requests.get(episode_url, headers=headers, timeout=30)
    response.raise_for_status()
    html = response.text

    audio_url = None
    title = 'untitled'

    # Strategy 1: parse __NEXT_DATA__ JSON
    next_data_match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    if next_data_match:
        try:
            data = json.loads(next_data_match.group(1))
            props = data.get('props', {}).get('pageProps', {})
            episode = props.get('episode', props.get('episodeDetailData', {}))
            if isinstance(episode, dict):
                enclosure = episode.get('enclosure', {})
                if isinstance(enclosure, dict):
                    audio_url = enclosure.get('url')
                title = episode.get('title', title)
        except (json.JSONDecodeError, KeyError):
            pass

    # Strategy 2: regex fallback for CDN audio URL
    if not audio_url:
        pattern = r'https://media\.xyzcdn\.net/[^"\'\\s]+\.(?:m4a|mp3|mp4a)'
        match = re.search(pattern, html)
        if match:
            audio_url = match.group(0)

    # Extract title from <title> tag as fallback
    if title == 'untitled':
        title_match = re.search(r'<title>(.*?)</title>', html)
        if title_match:
            raw_title = title_match.group(1)
            raw_title = raw_title.replace(' - 小宇宙', '').strip()
            if raw_title:
                title = raw_title

    if not audio_url:
        raise RuntimeError(
            'Could not extract audio URL from the episode page. '
            'The page structure may have changed, or the episode may require login.'
        )

    return audio_url, sanitize_filename(title)


def download_audio(audio_url: str, save_path: str) -> str:
    response = requests.get(audio_url, stream=True, timeout=60)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))

    with open(save_path, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size:
                percent = (downloaded / total_size) * 100
                print(f'\rDownloading: {percent:.1f}% ({downloaded // 1024 // 1024}MB)', end='', flush=True)
    print()
    return save_path
