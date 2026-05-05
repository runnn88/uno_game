from dataclasses import dataclass

from uno_game.config.enums import Direction


@dataclass
class TurnState:
    current_player_index: int = 0
    direction: Direction = Direction.CLOCKWISE
    pending_draw: int = 0
    pending_draw_value: int = 0
    skip_next: bool = False
    drew_this_turn: bool = False
    drawn_card_id: str | None = None
