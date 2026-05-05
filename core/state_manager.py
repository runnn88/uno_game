from uno_game.domain.state.game_state import GameState


class StateManager:
    def __init__(self, state: GameState | None = None) -> None:
        self.state = state or GameState.empty()

    def replace(self, state: GameState) -> None:
        self.state = state

