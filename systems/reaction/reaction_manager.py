from config.enums import GamePhase
from domain.state.game_state import GameState
from systems.reaction.reaction_result import ReactionResult
from systems.reaction.reaction_timer import ReactionTimer


class ReactionManager:
    def __init__(self) -> None:
        self.timer = ReactionTimer()

    def record(self, state: GameState, player_id: str) -> None:
        if state.reaction.active and player_id not in state.reaction.responders and state.player_by_id(player_id).connected:
            state.reaction.responders.append(player_id)

    def finish_if_ready(self, state: GameState) -> ReactionResult | None:
        expected = {player.id for player in state.players if player.connected}
        responders = set(state.reaction.responders)
        if not state.reaction.active:
            return None
        if responders >= expected or self.timer.expired(state):
            losers = self._missing_or_last_responder(state, expected)
            state.reaction.active = False
            state.phase = GamePhase.PLAYING
            return ReactionResult(tuple(losers), tuple(state.reaction.responders))
        return None

    def _missing_or_last_responder(self, state: GameState, expected: set[str]) -> list[str]:
        missing = [player.id for player in state.players if player.id in expected and player.id not in state.reaction.responders]
        if missing:
            return missing
        return [state.reaction.responders[-1]] if state.reaction.responders else []
