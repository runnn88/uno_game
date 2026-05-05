from abc import ABC, abstractmethod

from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.domain.entities.card import Card
from uno_game.domain.state.game_state import GameState


class BaseResolver(ABC):
    @abstractmethod
    def can_resolve(self, card: Card) -> bool:
        raise NotImplementedError

    @abstractmethod
    def resolve(self, state: GameState, command: PlayCardCommand, card: Card) -> None:
        raise NotImplementedError

    def play_to_discard(self, state: GameState, command: PlayCardCommand) -> None:
        player = state.player_by_id(command.player_id)
        card = player.hand.remove(command.card_id)
        state.deck.discard(card)
        state.active_color = command.chosen_color or card.color

