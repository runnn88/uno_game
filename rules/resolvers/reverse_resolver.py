from application.commands.play_card import PlayCardCommand
from config.enums import CardRank, Direction
from domain.entities.card import Card
from domain.state.game_state import GameState
from rules.resolvers.base_resolver import BaseResolver


class ReverseResolver(BaseResolver):
    def can_resolve(self, card: Card) -> bool:
        return card.rank == CardRank.REVERSE

    def resolve(self, state: GameState, command: PlayCardCommand, card: Card) -> None:
        self.play_to_discard(state, command)
        state.turn.direction = (
            Direction.COUNTER_CLOCKWISE
            if state.turn.direction == Direction.CLOCKWISE
            else Direction.CLOCKWISE
        )

