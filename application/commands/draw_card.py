from dataclasses import dataclass


@dataclass(frozen=True)
class DrawCardCommand:
    player_id: str
    count: int = 1

