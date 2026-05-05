from uno_game.application.commands.react_event import ReactEventCommand
from uno_game.config.constants import REACTION_PENALTY_CARDS
from uno_game.core.event_bus import EventBus
from uno_game.domain.state.game_state import GameState
from uno_game.systems.draw.draw_manager import DrawManager
from uno_game.systems.reaction.reaction_manager import ReactionManager
from uno_game.systems.win.endgame_handler import EndgameHandler
from uno_game.systems.win.win_checker import WinChecker


class ReactionHandler:
    def __init__(self, events: EventBus | None = None) -> None:
        self.reactions = ReactionManager()
        self.draws = DrawManager()
        self.endgame = EndgameHandler()
        self.wins = WinChecker()
        self.events = events or EventBus()

    def handle(self, state: GameState, command: ReactEventCommand) -> None:
        self.reactions.record(state, command.player_id)
        self.finish_if_ready(state)

    def finish_if_ready(self, state: GameState) -> bool:
        result = self.reactions.finish_if_ready(state)
        if result is not None:
            for loser_player_id in result.loser_player_ids:
                self.draws.draw_for_player(state, loser_player_id, REACTION_PENALTY_CARDS)
            self.events.emit(
                "REACTION_FINISHED",
                {"loser_player_ids": result.loser_player_ids, "penalty": REACTION_PENALTY_CARDS},
            )
            winner_id = self.wins.winner_id(state)
            if winner_id is not None:
                self.endgame.end(state, winner_id)
                self.events.emit("GAME_ENDED", {"winner_id": winner_id})
            return True
        return False
