from uno_game.config.enums import CardColor, CardRank
from uno_game.domain.entities.card import Card
from uno_game.domain.state.game_state import GameState


ACTION_FINAL_RANKS = {
    CardRank.SKIP,
    CardRank.REVERSE,
    CardRank.DRAW_TWO,
    CardRank.WILD,
    CardRank.WILD_DRAW_FOUR,
}

PENALTY_VALUES = {
    CardRank.DRAW_TWO: 2,
    CardRank.WILD_DRAW_FOUR: 4,
}


def card_matches_state(state: GameState, card: Card) -> bool:
    top = state.deck.top_discard
    if top is None:
        return True
    if card.color == CardColor.WILD:
        return True
    if card.color == (state.active_color or top.color):
        return True
    return card.rank == top.rank


def penalty_value(card: Card) -> int:
    return PENALTY_VALUES.get(card.rank, 0)


def is_action_final_card(card: Card) -> bool:
    return card.rank in ACTION_FINAL_RANKS
