from dataclasses import dataclass, field

from uno_game.domain.entities.hand import Hand


@dataclass
class Player:
    id: str
    name: str
    hand: Hand = field(default_factory=Hand)
    connected: bool = True
    is_bot: bool = False

    @property
    def has_won(self) -> bool:
        return len(self.hand.cards) == 0
