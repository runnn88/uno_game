from time import monotonic

from application.commands.play_card import PlayCardCommand
from config.constants import REACTION_TIMEOUT_SECONDS
from config.enums import CardRank, GamePhase
from domain.entities.card import Card
from domain.state.game_state import GameState
from rules.resolvers.base_resolver import BaseResolver


class Rule8Resolver(BaseResolver):
    def can_resolve(self, card: Card) -> bool:
        return card.rank == CardRank.EIGHT

    def resolve(self, state: GameState, command: PlayCardCommand, card: Card) -> None:
        self.play_to_discard(state, command)
        state.phase = GamePhase.REACTION
        state.reaction.active = True
        state.reaction.source_player_id = command.player_id
        state.reaction.responders.clear()
        state.reaction.expires_at = monotonic() + REACTION_TIMEOUT_SECONDS

