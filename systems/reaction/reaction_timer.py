from time import monotonic

from domain.state.game_state import GameState


class ReactionTimer:
    def expired(self, state: GameState) -> bool:
        return state.reaction.expires_at is not None and monotonic() >= state.reaction.expires_at

