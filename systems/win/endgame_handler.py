from uno_game.config.enums import GamePhase
from uno_game.domain.state.game_state import GameState


class EndgameHandler:
    def end(self, state: GameState, winner_id: str) -> None:
        state.winner_id = winner_id
        state.phase = GamePhase.ENDED

