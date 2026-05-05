from application.commands.play_card import PlayCardCommand
from core.event_bus import EventBus
from domain.state.game_state import GameState
from rules.engine import RuleEngine
from systems.turn.turn_manager import TurnManager
from systems.win.endgame_handler import EndgameHandler


class PlayCardHandler:
    def __init__(self, events: EventBus | None = None) -> None:
        self.engine = RuleEngine()
        self.turns = TurnManager()
        self.endgame = EndgameHandler()
        self.events = events or EventBus()

    def handle(self, state: GameState, command: PlayCardCommand) -> None:
        self.engine.validate_play(state, command)
        self.engine.resolve_play(state, command)
        state.turn.drew_this_turn = False
        state.turn.drawn_card_id = None
        self.events.emit("CARD_PLAYED", {"player_id": command.player_id, "card_id": command.card_id})
        if state.player_by_id(command.player_id).has_won and not state.reaction.active:
            self.endgame.end(state, command.player_id)
            self.events.emit("GAME_ENDED", {"winner_id": command.player_id})
            return
        self.turns.advance(state)
