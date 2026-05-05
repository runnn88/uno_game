from dataclasses import dataclass

from uno_game.domain.entities.card import Card
from uno_game.domain.state.game_state import GameState


@dataclass(frozen=True)
class PlayerViewDTO:
    id: str
    name: str
    card_count: int
    connected: bool
    is_bot: bool
    hand: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class GameStateDTO:
    players: tuple[PlayerViewDTO, ...]
    current_player_id: str | None
    top_card: dict[str, str] | None
    active_color: str | None
    direction: str
    pending_draw: int
    pending_draw_value: int
    reaction: dict[str, object]
    drew_this_turn: bool
    drawn_card_id: str | None
    phase: str
    winner_id: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "players": [player.__dict__ for player in self.players],
            "current_player_id": self.current_player_id,
            "top_card": self.top_card,
            "active_color": self.active_color,
            "direction": self.direction,
            "pending_draw": self.pending_draw,
            "pending_draw_value": self.pending_draw_value,
            "reaction": self.reaction,
            "drew_this_turn": self.drew_this_turn,
            "drawn_card_id": self.drawn_card_id,
            "phase": self.phase,
            "winner_id": self.winner_id,
        }


def card_to_dict(card: Card) -> dict[str, str]:
    return {"id": card.id, "color": card.color.value, "rank": card.rank.value}


def game_state_to_dto(state: GameState, viewer_player_id: str | None = None) -> GameStateDTO:
    current = state.current_player
    players: list[PlayerViewDTO] = []
    for player in state.players:
        visible_hand = tuple(card_to_dict(card) for card in player.hand.cards) if player.id == viewer_player_id else ()
        players.append(PlayerViewDTO(player.id, player.name, len(player.hand.cards), player.connected, player.is_bot, visible_hand))
    return GameStateDTO(
        players=tuple(players),
        current_player_id=current.id if current else None,
        top_card=card_to_dict(state.deck.top_discard) if state.deck.top_discard else None,
        active_color=state.active_color.value if state.active_color else None,
        direction=state.turn.direction.name,
        pending_draw=state.turn.pending_draw,
        pending_draw_value=state.turn.pending_draw_value,
        reaction={
            "active": state.reaction.active,
            "source_player_id": state.reaction.source_player_id,
            "responders": tuple(state.reaction.responders),
            "expires_at": state.reaction.expires_at,
        },
        drew_this_turn=state.turn.drew_this_turn,
        drawn_card_id=state.turn.drawn_card_id,
        phase=state.phase.value,
        winner_id=state.winner_id,
    )
