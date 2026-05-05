from uno_game.config.enums import CardRank
from uno_game.domain.entities.card import Card
from uno_game.domain.state.game_state import GameState
from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.rules.resolvers.base_resolver import BaseResolver


class NumberResolver(BaseResolver):
    def can_resolve(self, card: Card) -> bool:
        return card.rank in {
            CardRank.ONE, CardRank.TWO, CardRank.THREE, CardRank.FOUR, CardRank.FIVE,
            CardRank.SIX, CardRank.NINE,
        }

    def resolve(self, state: GameState, command: PlayCardCommand, card: Card) -> None:
        self.play_to_discard(state, command)

