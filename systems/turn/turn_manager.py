from domain.state.game_state import GameState
from systems.turn.turn_order import TurnOrder


class TurnManager:
    def __init__(self) -> None:
        self.order = TurnOrder()

    def advance(self, state: GameState) -> None:
        steps = 2 if state.turn.skip_next else 1
        state.turn.current_player_index = self.order.next_index(state, steps)
        state.turn.skip_next = False

