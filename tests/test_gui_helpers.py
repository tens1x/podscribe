import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from podscribe.gui import reveal_directory, split_episode_urls


class GuiHelperTests(unittest.TestCase):
    def test_split_episode_urls_strips_empty_items(self):
        urls = split_episode_urls(' https://a , ,https://b  ,  ')

        self.assertEqual(urls, ['https://a', 'https://b'])

    def test_reveal_directory_uses_open_on_macos(self):
        with patch('podscribe.gui.sys.platform', 'darwin'), \
                patch('podscribe.gui.subprocess.run') as run:
            reveal_directory(Path('/tmp/demo'))

        run.assert_called_once_with(['open', str(Path('/tmp/demo').resolve())], check=False)

    def test_reveal_directory_uses_startfile_on_windows(self):
        with patch('podscribe.gui.sys.platform', 'win32'), \
                patch.object(sys.modules['podscribe.gui'].os, 'startfile', create=True) as startfile:
            reveal_directory(Path('/tmp/demo'))

        startfile.assert_called_once_with(str(Path('/tmp/demo').resolve()))


if __name__ == '__main__':
    unittest.main()
