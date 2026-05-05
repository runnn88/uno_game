from dataclasses import dataclass, field
from random import Random

from uno_game.domain.entities.card import Card


@dataclass
class Deck:
    draw_pile: list[Card] = field(default_factory=list)
    discard_pile: list[Card] = field(default_factory=list)

    def shuffle(self, rng: Random) -> None:
        rng.shuffle(self.draw_pile)

    def draw(self) -> Card:
        if not self.draw_pile:
            raise IndexError("Draw pile is empty")
        return self.draw_pile.pop()

    def discard(self, card: Card) -> None:
        self.discard_pile.append(card)

    @property
    def top_discard(self) -> Card | None:
        return self.discard_pile[-1] if self.discard_pile else None

