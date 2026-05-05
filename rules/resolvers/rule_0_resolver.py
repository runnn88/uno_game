from application.commands.play_card import PlayCardCommand
from config.enums import CardRank, PassDirection
from domain.entities.card import Card
from domain.state.game_state import GameState
from rules.resolvers.base_resolver import BaseResolver


class Rule0Resolver(BaseResolver):
    def can_resolve(self, card: Card) -> bool:
        return card.rank == CardRank.ZERO

    def resolve(self, state: GameState, command: PlayCardCommand, card: Card) -> None:
        if command.pass_direction is None:
            raise ValueError("Zero requires a hand passing direction")
        self.play_to_discard(state, command)
        hands = [player.hand for player in state.players]
        if len(hands) > 1:
            rotated = hands[-1:] + hands[:-1] if command.pass_direction == PassDirection.CLOCKWISE else hands[1:] + hands[:1]
            for player, hand in zip(state.players, rotated):
                player.hand = hand
