from uno_game.config.enums import Direction
from uno_game.domain.state.game_state import GameState


class DirectionManager:
    def reverse(self, state: GameState) -> None:
        state.turn.direction = (
            Direction.COUNTER_CLOCKWISE
            if state.turn.direction == Direction.CLOCKWISE
            else Direction.CLOCKWISE
        )

