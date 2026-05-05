from domain.entities.card import Card
from domain.state.game_state import GameState
from systems.draw.reshuffle import Reshuffle


class DrawManager:
    def __init__(self) -> None:
        self.reshuffle = Reshuffle()

    def draw_for_player(self, state: GameState, player_id: str, count: int = 1) -> list[Card]:
        drawn: list[Card] = []
        player = state.player_by_id(player_id)
        for _ in range(count):
            self.reshuffle.ensure_draw_pile(state)
            if not state.deck.draw_pile:
                break
            card = state.deck.draw()
            player.hand.add(card)
            drawn.append(card)
        return drawn
