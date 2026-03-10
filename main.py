import argparse
import sys
from pathlib import Path

import requests


def main():
    from setup_helper import check_and_setup
    check_and_setup()

    parser = argparse.ArgumentParser(
        description='Transcribe Xiaoyuzhou podcast episodes to text'
    )
    parser.add_argument('url', help='Xiaoyuzhou episode URL')
    parser.add_argument(
        '-o', '--output-dir', default='output',
        help='Output directory for transcripts (default: output)'
    )
    parser.add_argument(
        '-l', '--language', default='zh',
        help='Primary language hint (default: zh)'
    )
    parser.add_argument(
        '--save-audio', action='store_true',
        help='Also save the downloaded audio file'
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from podcast_downloader import extract_audio_url, download_audio
        from transcriber import transcribe_audio

        # Step 1: Extract audio URL
        print(f'Fetching episode info from: {args.url}')
        audio_url, episode_title = extract_audio_url(args.url)
        print(f'Episode: {episode_title}')
        print(f'Audio URL: {audio_url}')

        # Step 2: Optionally download audio
        if args.save_audio:
            audio_ext = audio_url.rsplit('.', 1)[-1].split('?')[0]
            audio_path = output_dir / f'{episode_title}.{audio_ext}'
            print(f'Downloading audio to: {audio_path}')
            download_audio(audio_url, str(audio_path))
            print('Audio saved.')

        # Step 3: Transcribe
        print('Starting transcription...')
        transcript_text = transcribe_audio(audio_url, language=args.language)

        # Step 4: Save transcript
        txt_path = output_dir / f'{episode_title}.txt'
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(transcript_text)

        print(f'Transcript saved to: {txt_path}')
        print(f'Total characters: {len(transcript_text)}')

    except requests.exceptions.Timeout:
        print('Error: Request timed out. Check your network connection.')
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f'Error: HTTP {e.response.status_code}')
        sys.exit(1)
    except (ValueError, RuntimeError) as e:
        print(f'Error: {e}')
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nInterrupted by user.')
        sys.exit(130)


if __name__ == '__main__':
    main()
