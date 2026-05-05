from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.domain.entities.card import Card
from uno_game.domain.state.game_state import GameState
from uno_game.rules.resolvers.base_resolver import BaseResolver
from uno_game.rules.validator.stack_validator import StackValidator


class StackResolver(BaseResolver):
    def __init__(self) -> None:
        self.validator = StackValidator()

    def can_resolve(self, card: Card) -> bool:
        return card.is_draw_card

    def resolve(self, state: GameState, command: PlayCardCommand, card: Card) -> None:
        if not self.validator.can_stack(state, card):
            raise ValueError("This draw card cannot be stacked now")
        self.play_to_discard(state, command)
        state.turn.pending_draw += 2 if card.rank.value == "draw_two" else 4

