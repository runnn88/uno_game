from uno_game.domain.entities.player import Player


class WinValidator:
    def is_winner(self, player: Player) -> bool:
        return player.has_won

