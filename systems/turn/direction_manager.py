from config.enums import Direction
from domain.state.game_state import GameState


class DirectionManager:
    def reverse(self, state: GameState) -> None:
        state.turn.direction = (
            Direction.COUNTER_CLOCKWISE
            if state.turn.direction == Direction.CLOCKWISE
            else Direction.CLOCKWISE
        )

