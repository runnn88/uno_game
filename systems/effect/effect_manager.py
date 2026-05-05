from domain.state.game_state import GameState
from systems.effect.effect_queue import EffectQueue


class EffectManager:
    def __init__(self) -> None:
        self.queue = EffectQueue()

    def apply_pending(self, state: GameState) -> None:
        while self.queue.pop(state) is not None:
            pass

