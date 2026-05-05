from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.config.enums import CardRank
from uno_game.domain.entities.card import Card
from uno_game.domain.state.game_state import GameState
from uno_game.rules.resolvers.base_resolver import BaseResolver


class DrawTwoResolver(BaseResolver):
    def can_resolve(self, card: Card) -> bool:
        return card.rank == CardRank.DRAW_TWO

    def resolve(self, state: GameState, command: PlayCardCommand, card: Card) -> None:
        self.play_to_discard(state, command)
        state.turn.pending_draw += 2
        state.turn.pending_draw_value = 2
