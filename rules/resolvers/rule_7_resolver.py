from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.config.enums import CardRank
from uno_game.domain.entities.card import Card
from uno_game.domain.state.game_state import GameState
from uno_game.rules.resolvers.base_resolver import BaseResolver


class Rule7Resolver(BaseResolver):
    def can_resolve(self, card: Card) -> bool:
        return card.rank == CardRank.SEVEN

    def resolve(self, state: GameState, command: PlayCardCommand, card: Card) -> None:
        if command.target_player_id is None:
            raise ValueError("Seven requires a target player")
        self.play_to_discard(state, command)
        source = state.player_by_id(command.player_id)
        target = state.player_by_id(command.target_player_id)
        if source.id == target.id or not target.connected:
            raise ValueError("Seven target must be another connected player")
        source.hand, target.hand = target.hand, source.hand
