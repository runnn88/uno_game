from dataclasses import dataclass

from config.enums import CardColor


@dataclass(frozen=True)
class ChooseColorCommand:
    player_id: str
    color: CardColor

