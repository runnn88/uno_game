from random import Random

from domain.state.game_state import GameState


class Reshuffle:
    def __init__(self, rng: Random | None = None) -> None:
        self.rng = rng or Random()

    def ensure_draw_pile(self, state: GameState) -> None:
        if state.deck.draw_pile or len(state.deck.discard_pile) <= 1:
            return
        top = state.deck.discard_pile.pop()
        state.deck.draw_pile = state.deck.discard_pile
        state.deck.discard_pile = [top]
        state.deck.shuffle(self.rng)

