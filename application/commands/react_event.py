from dataclasses import dataclass


@dataclass(frozen=True)
class ReactEventCommand:
    player_id: str

