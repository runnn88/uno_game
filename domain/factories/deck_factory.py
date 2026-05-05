from random import Random

from uno_game.config.enums import CardColor, CardRank
from uno_game.domain.entities.card import Card
from uno_game.domain.entities.deck import Deck


COLOR_RANKS = [
    CardRank.ZERO,
    CardRank.ONE,
    CardRank.TWO,
    CardRank.THREE,
    CardRank.FOUR,
    CardRank.FIVE,
    CardRank.SIX,
    CardRank.SEVEN,
    CardRank.EIGHT,
    CardRank.NINE,
    CardRank.SKIP,
    CardRank.REVERSE,
    CardRank.DRAW_TWO,
]


def build_uno_deck(rng: Random | None = None) -> Deck:
    cards: list[Card] = []
    for color in (CardColor.RED, CardColor.YELLOW, CardColor.GREEN, CardColor.BLUE):
        for rank in COLOR_RANKS:
            copies = 1 if rank == CardRank.ZERO else 2
            for copy in range(copies):
                cards.append(Card(id=f"{color.value}_{rank.value}_{copy}", color=color, rank=rank))
    for copy in range(4):
        cards.append(Card(id=f"wild_{copy}", color=CardColor.WILD, rank=CardRank.WILD))
        cards.append(Card(id=f"wild_draw_four_{copy}", color=CardColor.WILD, rank=CardRank.WILD_DRAW_FOUR))
    deck = Deck(draw_pile=cards)
    deck.shuffle(rng or Random())
    return deck

