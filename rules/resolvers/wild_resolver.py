from application.commands.play_card import PlayCardCommand
from config.enums import CardRank
from domain.entities.card import Card
from domain.state.game_state import GameState
from rules.resolvers.base_resolver import BaseResolver


class WildResolver(BaseResolver):
    def can_resolve(self, card: Card) -> bool:
        return card.rank == CardRank.WILD

    def resolve(self, state: GameState, command: PlayCardCommand, card: Card) -> None:
        if command.chosen_color is None:
            raise ValueError("Wild card requires a chosen color")
        self.play_to_discard(state, command)

