from uno_game.application.commands.draw_card import DrawCardCommand
from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.config.enums import CardColor, CardRank, PassDirection
from uno_game.core.event_bus import EventBus
from uno_game.domain.entities.player import Player
from uno_game.domain.state.game_state import GameState
from uno_game.rules.validator.card_playability import card_matches_state
from uno_game.rules.validator.move_validator import MoveValidator
from uno_game.systems.draw.draw_manager import DrawManager
from uno_game.systems.turn.turn_manager import TurnManager


class DrawHandler:
    def __init__(self, events: EventBus | None = None) -> None:
        self.draws = DrawManager()
        self.turns = TurnManager()
        self.validator = MoveValidator()
        self.events = events or EventBus()

    def handle(self, state: GameState, command: DrawCardCommand) -> None:
        if state.current_player is None or state.current_player.id != command.player_id:
            raise ValueError("It is not this player's turn")
        if state.reaction.active:
            raise ValueError("Resolve the reaction before drawing")
        if state.turn.drew_this_turn:
            raise ValueError("You already drew; play the drawn card or pass")

        if state.turn.pending_draw > 0:
            count = state.turn.pending_draw
            state.turn.pending_draw = 0
            state.turn.pending_draw_value = 0
            state.turn.drew_this_turn = False
            state.turn.drawn_card_id = None
            drawn = self.draws.draw_for_player(state, command.player_id, count)
            self.events.emit("CARDS_DRAWN", {"player_id": command.player_id, "count": len(drawn)})
            self.turns.advance(state)
            return

        player = state.player_by_id(command.player_id)
        if self._has_legal_play(state, player):
            raise ValueError("You have a legal card to play")

        drawn = self.draws.draw_for_player(state, command.player_id, 1)
        state.turn.drew_this_turn = True
        state.turn.drawn_card_id = drawn[0].id if drawn else None
        self.events.emit("CARDS_DRAWN", {"player_id": command.player_id, "count": len(drawn)})
        if not drawn or not card_matches_state(state, drawn[0]):
            state.turn.drew_this_turn = False
            state.turn.drawn_card_id = None
            self.turns.advance(state)

    def _has_legal_play(self, state: GameState, player: Player) -> bool:
        for card in player.hand.cards:
            target_player_id = None
            if card.rank == CardRank.SEVEN:
                target = next((candidate for candidate in state.players if candidate.connected and candidate.id != player.id), None)
                target_player_id = target.id if target else None
            pass_direction = PassDirection.CLOCKWISE if card.rank == CardRank.ZERO else None
            chosen_color = CardColor.RED if card.color == CardColor.WILD else None
            try:
                self.validator.validate(state, PlayCardCommand(player.id, card.id, chosen_color, target_player_id, pass_direction))
            except ValueError:
                continue
            return True
        return False
