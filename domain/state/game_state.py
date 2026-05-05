from dataclasses import dataclass, field

from config.enums import CardColor, GamePhase
from domain.entities.deck import Deck
from domain.entities.player import Player
from domain.state.effect_state import EffectState
from domain.state.reaction_state import ReactionState
from domain.state.turn_state import TurnState


@dataclass
class GameState:
    players: list[Player] = field(default_factory=list)
    deck: Deck = field(default_factory=Deck)
    turn: TurnState = field(default_factory=TurnState)
    effects: EffectState = field(default_factory=EffectState)
    reaction: ReactionState = field(default_factory=ReactionState)
    phase: GamePhase = GamePhase.MENU
    active_color: CardColor | None = None
    winner_id: str | None = None

    @classmethod
    def empty(cls) -> "GameState":
        return cls()

    @property
    def current_player(self) -> Player | None:
        if not self.players:
            return None
        return self.players[self.turn.current_player_index]

    def player_by_id(self, player_id: str) -> Player:
        for player in self.players:
            if player.id == player_id:
                return player
        raise ValueError(f"Unknown player: {player_id}")

