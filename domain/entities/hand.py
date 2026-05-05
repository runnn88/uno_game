from dataclasses import dataclass, field

from uno_game.domain.entities.card import Card


@dataclass
class Hand:
    cards: list[Card] = field(default_factory=list)

    def add(self, card: Card) -> None:
        self.cards.append(card)

    def remove(self, card_id: str) -> Card:
        for index, card in enumerate(self.cards):
            if card.id == card_id:
                return self.cards.pop(index)
        raise ValueError(f"Card not in hand: {card_id}")

    def find(self, card_id: str) -> Card | None:
        return next((card for card in self.cards if card.id == card_id), None)

