from domain.state.game_state import GameState
from rules.validator.win_validator import WinValidator


class WinChecker:
    def __init__(self) -> None:
        self.validator = WinValidator()

    def winner_id(self, state: GameState) -> str | None:
        for player in state.players:
            if self.validator.is_winner(player):
                return player.id
        return None

