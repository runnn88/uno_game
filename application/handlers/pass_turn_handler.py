from application.commands.pass_turn import PassTurnCommand
from core.event_bus import EventBus
from domain.state.game_state import GameState
from systems.turn.turn_manager import TurnManager


class PassTurnHandler:
    def __init__(self, events: EventBus | None = None) -> None:
        self.turns = TurnManager()
        self.events = events or EventBus()

    def handle(self, state: GameState, command: PassTurnCommand) -> None:
        if state.current_player is None or state.current_player.id != command.player_id:
            raise ValueError("It is not this player's turn")
        if state.reaction.active:
            raise ValueError("Resolve the reaction before passing")
        if not state.turn.drew_this_turn:
            raise ValueError("You can only pass after drawing a playable card")
        state.turn.drew_this_turn = False
        state.turn.drawn_card_id = None
        self.events.emit("TURN_PASSED", {"player_id": command.player_id})
        self.turns.advance(state)
