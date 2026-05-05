from dataclasses import dataclass

from config.enums import CardColor, CardRank


@dataclass(frozen=True)
class Card:
    id: str
    color: CardColor
    rank: CardRank

    @property
    def is_wild(self) -> bool:
        return self.color == CardColor.WILD

    @property
    def is_draw_card(self) -> bool:
        return self.rank in {CardRank.DRAW_TWO, CardRank.WILD_DRAW_FOUR}

