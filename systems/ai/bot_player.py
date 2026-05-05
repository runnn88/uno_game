from collections import Counter
from random import Random

from uno_game.application.commands.draw_card import DrawCardCommand
from uno_game.application.commands.pass_turn import PassTurnCommand
from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.application.handlers.draw_handler import DrawHandler
from uno_game.application.handlers.pass_turn_handler import PassTurnHandler
from uno_game.application.handlers.play_card_handler import PlayCardHandler
from uno_game.config.enums import CardColor, CardRank, PassDirection
from uno_game.domain.entities.card import Card
from uno_game.domain.entities.player import Player
from uno_game.domain.state.game_state import GameState
from uno_game.rules.validator.move_validator import MoveValidator


class BotPlayerController:
    def __init__(self, rng: Random | None = None) -> None:
        self.rng = rng or Random()
        self.validator = MoveValidator()
        self.play_handler = PlayCardHandler()
        self.draw_handler = DrawHandler()
        self.pass_handler = PassTurnHandler()

    def take_turn(self, state: GameState, player: Player) -> None:
        if state.current_player is None or state.current_player.id != player.id:
            return
        legal = self._legal_commands(state, player)
        if legal:
            self.play_handler.handle(state, self.rng.choice(legal))
            return
        if state.turn.drew_this_turn:
            self.pass_handler.handle(state, PassTurnCommand(player.id))
            return
        self.draw_handler.handle(state, DrawCardCommand(player.id))

    def _legal_commands(self, state: GameState, player: Player) -> list[PlayCardCommand]:
        commands: list[PlayCardCommand] = []
        for card in player.hand.cards:
            command = self._command_for_card(state, player, card)
            try:
                self.validator.validate(state, command)
            except ValueError:
                continue
            commands.append(command)
        return commands

    def _command_for_card(self, state: GameState, player: Player, card: Card) -> PlayCardCommand:
        chosen_color = self._best_color(player) if card.color == CardColor.WILD else None
        target_player_id = None
        if card.rank == CardRank.SEVEN:
            targets = [target for target in state.players if target.connected and target.id != player.id]
            target_player_id = self.rng.choice(targets).id if targets else None
        pass_direction = None
        if card.rank == CardRank.ZERO:
            pass_direction = self.rng.choice([PassDirection.CLOCKWISE, PassDirection.COUNTER_CLOCKWISE])
        return PlayCardCommand(player.id, card.id, chosen_color, target_player_id, pass_direction)

    def _best_color(self, player: Player) -> CardColor:
        colors = [card.color for card in player.hand.cards if card.color != CardColor.WILD]
        if not colors:
            return self.rng.choice([CardColor.RED, CardColor.YELLOW, CardColor.GREEN, CardColor.BLUE])
        return Counter(colors).most_common(1)[0][0]
