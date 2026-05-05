from domain.state.game_state import GameState


class TurnOrder:
    def next_index(self, state: GameState, steps: int = 1) -> int:
        if not state.players:
            return 0
        connected = [index for index, player in enumerate(state.players) if player.connected]
        if not connected:
            return state.turn.current_player_index
        index = state.turn.current_player_index
        remaining = steps
        while remaining > 0:
            index = (index + int(state.turn.direction)) % len(state.players)
            if state.players[index].connected:
                remaining -= 1
        return index
