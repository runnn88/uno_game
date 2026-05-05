from dataclasses import dataclass

from config.enums import CardColor, PassDirection


@dataclass(frozen=True)
class PlayCardCommand:
    player_id: str
    card_id: str
    chosen_color: CardColor | None = None
    target_player_id: str | None = None
    pass_direction: PassDirection | None = None
