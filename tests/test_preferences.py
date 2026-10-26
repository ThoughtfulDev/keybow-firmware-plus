import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "editor"))
from keybow_editor import preferences


class PreferencesTests(unittest.TestCase):
    def test_persistence_and_invalid_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "editor/preferences.json"
            with patch.object(preferences, "path", return_value=target):
                self.assertEqual(preferences.read(), {"orientation": 0})
                for angle in (0, 90, 180, 270):
                    preferences.write({"orientation": angle})
                    self.assertEqual(preferences.read(), {"orientation": angle})
                for invalid in (45, "90", True, None):
                    with self.assertRaises(ValueError):
                        preferences.write({"orientation": invalid})
                    target.write_text(json.dumps({"orientation": invalid}))
                    self.assertEqual(preferences.read(), {"orientation": 0})
                target.write_text("broken json")
                self.assertEqual(preferences.read(), {"orientation": 0})
                target.write_text("[]")
                self.assertEqual(preferences.read(), {"orientation": 0})

    @unittest.skipUnless(shutil.which("node"), "Node unavailable")
    def test_display_coordinates_and_browser_storage(self):
        subprocess.run(["node", "tests/orientation-test.js"], cwd=ROOT, check=True)
