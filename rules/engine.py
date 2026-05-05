from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.domain.state.game_state import GameState
from uno_game.rules.resolvers.draw_two_resolver import DrawTwoResolver
from uno_game.rules.resolvers.number_resolver import NumberResolver
from uno_game.rules.resolvers.reverse_resolver import ReverseResolver
from uno_game.rules.resolvers.rule_0_resolver import Rule0Resolver
from uno_game.rules.resolvers.rule_7_resolver import Rule7Resolver
from uno_game.rules.resolvers.rule_8_resolver import Rule8Resolver
from uno_game.rules.resolvers.skip_resolver import SkipResolver
from uno_game.rules.resolvers.wild_draw_four_resolver import WildDrawFourResolver
from uno_game.rules.resolvers.wild_resolver import WildResolver
from uno_game.rules.validator.move_validator import MoveValidator


class RuleEngine:
    def __init__(self) -> None:
        self.move_validator = MoveValidator()
        self.resolvers = [
            Rule0Resolver(),
            Rule7Resolver(),
            Rule8Resolver(),
            SkipResolver(),
            ReverseResolver(),
            DrawTwoResolver(),
            WildDrawFourResolver(),
            WildResolver(),
            NumberResolver(),
        ]

    def validate_play(self, state: GameState, command: PlayCardCommand) -> None:
        self.move_validator.validate(state, command)

    def resolve_play(self, state: GameState, command: PlayCardCommand) -> None:
        card = state.player_by_id(command.player_id).hand.find(command.card_id)
        if card is None:
            raise ValueError(f"Card not in hand: {command.card_id}")
        for resolver in self.resolvers:
            if resolver.can_resolve(card):
                resolver.resolve(state, command, card)
                return
        raise ValueError(f"No resolver for card: {card}")

