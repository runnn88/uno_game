from application.commands.draw_card import DrawCardCommand
from application.commands.play_card import PlayCardCommand
from application.commands.react_event import ReactEventCommand
from application.handlers.draw_handler import DrawHandler
from application.handlers.play_card_handler import PlayCardHandler
from application.handlers.reaction_handler import ReactionHandler
from domain.state.game_state import GameState


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

