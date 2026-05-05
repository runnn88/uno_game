from pathlib import Path
import unittest

from uno_game.config.user_settings import UserSettings, load_user_settings, save_user_settings


class SettingsTests(unittest.TestCase):
    def test_user_settings_round_trip(self) -> None:
        path = Path(__file__).with_name("_user_settings_test.json")
        try:
            settings = UserSettings(sound_enabled=False, volume=0.35, show_background_art=False)
            save_user_settings(settings, path)
            loaded = load_user_settings(path)
            self.assertFalse(loaded.sound_enabled)
            self.assertEqual(loaded.volume, 0.35)
            self.assertFalse(loaded.show_background_art)
        finally:
            if path.exists():
                path.unlink()

    def test_user_settings_clamps_volume(self) -> None:
        settings = UserSettings(volume=4.0)
        settings.clamp()
        self.assertEqual(settings.volume, 1.0)


if __name__ == "__main__":
    unittest.main()
