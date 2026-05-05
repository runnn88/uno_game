from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


SETTINGS_PATH = Path(__file__).resolve().parent / "user_settings.json"


@dataclass
class UserSettings:
    sound_enabled: bool = True
    volume: float = 0.7
    show_background_art: bool = True
    show_missing_card_labels: bool = True
    fullscreen: bool = False

    def clamp(self) -> None:
        self.volume = max(0.0, min(1.0, self.volume))


def load_user_settings(path: Path = SETTINGS_PATH) -> UserSettings:
    if not path.exists():
        return UserSettings()
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        settings = UserSettings(**{key: value for key, value in data.items() if key in UserSettings.__dataclass_fields__})
        settings.clamp()
        return settings
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return UserSettings()


def save_user_settings(settings: UserSettings, path: Path = SETTINGS_PATH) -> None:
    settings.clamp()
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
