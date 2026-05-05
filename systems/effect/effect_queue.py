from typing import Any

from domain.state.game_state import GameState


class EffectQueue:
    def push(self, state: GameState, effect: dict[str, Any]) -> None:
        state.effects.queue.append(effect)

    def pop(self, state: GameState) -> dict[str, Any] | None:
        if not state.effects.queue:
            return None
        return state.effects.queue.pop(0)

