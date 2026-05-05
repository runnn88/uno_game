from config.enums import CardRank
from domain.entities.card import Card
from domain.state.game_state import GameState


class StackValidator:
    def can_stack(self, state: GameState, card: Card) -> bool:
        return state.turn.pending_draw > 0 and card.rank in {CardRank.DRAW_TWO, CardRank.WILD_DRAW_FOUR}

