from uno_game.application.commands.draw_card import DrawCardCommand
from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.application.commands.react_event import ReactEventCommand
from uno_game.application.handlers.draw_handler import DrawHandler
from uno_game.application.handlers.play_card_handler import PlayCardHandler
from uno_game.application.handlers.reaction_handler import ReactionHandler
from uno_game.domain.state.game_state import GameState


class LocalController:
    def __init__(self) -> None:
        self.play_cards = PlayCardHandler()
        self.draw_cards = DrawHandler()
        self.reactions = ReactionHandler()

    def play_card(self, state: GameState, command: PlayCardCommand) -> None:
        self.play_cards.handle(state, command)

    def draw_card(self, state: GameState, command: DrawCardCommand) -> None:
        self.draw_cards.handle(state, command)

    def react(self, state: GameState, command: ReactEventCommand) -> None:
        self.reactions.handle(state, command)

