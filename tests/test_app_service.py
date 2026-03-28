import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from podscribe.app_service import build_request, normalize_config, process_episode


class NormalizeConfigTests(unittest.TestCase):
    def test_adds_defaults_for_missing_fields(self):
        normalized = normalize_config({'save_audio': True, 'audio_dir': None, 'output_formats': ['txt', 'bad']})

        self.assertEqual(normalized['output_formats'], ['txt'])
        self.assertTrue(normalized['save_audio'])
        self.assertTrue(normalized['audio_dir'].endswith('/PodScribe/audio'))
        self.assertTrue(normalized['use_ai'])


class ProcessEpisodeTests(unittest.TestCase):
    def test_process_episode_writes_outputs_and_emits_progress(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / 'output'
            request = build_request(
                'https://www.xiaoyuzhoufm.com/episode/test-id',
                {
                    'output_formats': ['txt', 'srt'],
                    'output_dir': str(output_dir),
                    'save_audio': False,
                    'use_ai': True,
                },
            )
            messages = []

            with patch('podscribe.app_service.extract_audio_url', return_value=('https://audio.example/test.m4a', 'Demo Episode')), \
                    patch('podscribe.app_service.transcribe_audio', return_value={
                        'text': '原始文本',
                        'sentences': [{'begin_time': 0, 'end_time': 1000, 'text': '原始文本'}],
                    }), \
                    patch('podscribe.app_service.postprocess_text', return_value='整理后的文本'), \
                    patch('podscribe.app_service.save_state'), \
                    patch('podscribe.app_service.clear_state'), \
                    patch('podscribe.app_service.add_record') as add_record:
                result = process_episode(
                    request,
                    progress_callback=lambda event: messages.append(event.message),
                )

            self.assertEqual(result.episode_title, 'Demo Episode')
            self.assertEqual(result.text, '整理后的文本')
            self.assertEqual(len(result.output_files), 2)
            self.assertTrue((output_dir / 'Demo Episode.txt').exists())
            self.assertTrue((output_dir / 'Demo Episode.srt').exists())
            self.assertTrue(any('Parsing episode page' in message for message in messages))
            self.assertTrue(any('AI post-processing complete' in message for message in messages))
            add_record.assert_called_once()


if __name__ == '__main__':
    unittest.main()
