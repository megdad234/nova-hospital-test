from pathlib import Path
import unittest

class ShortcutTests(unittest.TestCase):
    def test_lan_shortcut(self):
        source = (Path(__file__).parent / 'windows' / 'configure-lan-client.ps1').read_text()
        self.assertIn('CreateShortcut', source)
        self.assertIn('--host', source)
        self.assertIn('--port', source)

if __name__ == '__main__':
    unittest.main()
