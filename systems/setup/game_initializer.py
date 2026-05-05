from random import Random

from config.constants import MIN_PLAYERS, STARTING_HAND_SIZE
from config.enums import CardColor, CardRank, GamePhase
from domain.factories.deck_factory import build_uno_deck
from domain.state.game_state import GameState
from systems.draw.draw_manager import DrawManager


class GameInitializer:
    def __init__(self, rng: Random | None = None) -> None:
        self.rng = rng or Random()
        self.draws = DrawManager()

    def start(self, state: GameState) -> None:
        connected_players = [player for player in state.players if player.connected]
        if len(connected_players) < MIN_PLAYERS:
            raise ValueError("At least two players are required to start")
        state.deck = build_uno_deck(self.rng)
        for player in connected_players:
            player.hand.cards.clear()
            self.draws.draw_for_player(state, player.id, STARTING_HAND_SIZE)
        for player in state.players:
            if not player.connected:
                player.hand.cards.clear()
        state.deck.discard(self._opening_card(state))
        state.active_color = state.deck.top_discard.color if state.deck.top_discard else None
        state.turn.current_player_index = 0
        state.turn.pending_draw = 0
        state.turn.skip_next = False
        state.winner_id = None
        state.phase = GamePhase.PLAYING

    def _opening_card(self, state: GameState):
        skipped = []
        while state.deck.draw_pile:
            card = state.deck.draw()
            if card.color != CardColor.WILD and card.rank not in {CardRank.SKIP, CardRank.REVERSE, CardRank.DRAW_TWO}:
                for skipped_card in skipped:
                    state.deck.draw_pile.insert(0, skipped_card)
                return card
            skipped.append(card)
        if not skipped:
            raise ValueError("Deck is empty")
        return skipped.pop()
