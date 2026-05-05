from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.config.enums import CardRank
from uno_game.domain.entities.card import Card
from uno_game.domain.state.game_state import GameState
from uno_game.rules.resolvers.base_resolver import BaseResolver


class SkipResolver(BaseResolver):
    def can_resolve(self, card: Card) -> bool:
        return card.rank == CardRank.SKIP

    def resolve(self, state: GameState, command: PlayCardCommand, card: Card) -> None:
        self.play_to_discard(state, command)
        state.turn.skip_next = True

