from pathlib import Path

import pygame


class SoundManager:
    def __init__(self, sounds_root: Path | None = None) -> None:
        package_root = Path(__file__).resolve().parents[2]
        self.sounds_root = sounds_root or package_root / "assets" / "sounds"
        self.enabled = False
        self.user_enabled = True
        self.volume = 0.7
        self._sounds: dict[str, pygame.mixer.Sound] = {}

    def configure(self, user_enabled: bool, volume: float) -> None:
        self.user_enabled = user_enabled
        self.volume = max(0.0, min(1.0, volume))
        for sound in self._sounds.values():
            try:
                sound.set_volume(self.volume)
            except pygame.error:
                self.enabled = False

    def initialize(self) -> None:
        if self.enabled or not self.user_enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False

    def play(self, name: str) -> None:
        try:
            if not self.user_enabled:
                return
            sound = self._load(name)
            if sound is not None:
                sound.set_volume(self.volume)
                sound.play()
        except pygame.error:
            self.enabled = False

    def _load(self, name: str) -> pygame.mixer.Sound | None:
        self.initialize()
        if not self.enabled:
            return None
        if name in self._sounds:
            return self._sounds[name]
        for ext in ("wav", "ogg", "mp3"):
            path = self.sounds_root / f"{name}.{ext}"
            if path.exists():
                try:
                    self._sounds[name] = pygame.mixer.Sound(str(path))
                    self._sounds[name].set_volume(self.volume)
                    return self._sounds[name]
                except pygame.error:
                    self.enabled = False
                    return None
        return None
