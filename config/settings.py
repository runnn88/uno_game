from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    width: int = 1280
    height: int = 720
    fps: int = 60
    title: str = "UNO Host"
    seed: int | None = None


DEFAULT_SETTINGS = Settings()

