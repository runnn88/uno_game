from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.core.event_bus import EventBus
from uno_game.domain.state.game_state import GameState
from uno_game.rules.engine import RuleEngine
from uno_game.systems.turn.turn_manager import TurnManager
from uno_game.systems.win.endgame_handler import EndgameHandler


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
        if state.player_by_id(command.player_id).has_won:
            self.endgame.end(state, command.player_id)
            self.events.emit("GAME_ENDED", {"winner_id": command.player_id})
            return
        self.turns.advance(state)
