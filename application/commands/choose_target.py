from dataclasses import dataclass


@dataclass(frozen=True)
class ChooseTargetCommand:
    player_id: str
    target_player_id: str

