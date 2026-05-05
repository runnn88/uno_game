from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.config.enums import CardRank
from uno_game.domain.entities.card import Card
from uno_game.domain.state.game_state import GameState
from uno_game.rules.resolvers.wild_resolver import WildResolver


class WildDrawFourResolver(WildResolver):
    def can_resolve(self, card: Card) -> bool:
        return card.rank == CardRank.WILD_DRAW_FOUR

    def resolve(self, state: GameState, command: PlayCardCommand, card: Card) -> None:
        super().resolve(state, command, card)
        state.turn.pending_draw += 4
        state.turn.pending_draw_value = 4
