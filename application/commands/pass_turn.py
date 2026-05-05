from dataclasses import dataclass


@dataclass(frozen=True)
class PassTurnCommand:
    player_id: str
