from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from presentation.theme import ACCENT, ACCENT_2, BAD, GOOD, MUTED, color_tuple, readable_card


@dataclass
class Toast:
    title: str
    body: str
    tone: tuple[int, int, int]
    age: float = 0.0
    duration: float = 4.2


@dataclass
class CardMotion:
    start: tuple[int, int]
    end: tuple[int, int]
    card: dict[str, str] | None = None
    face_down: bool = False
    age: float = 0.0
    duration: float = 0.34


class FeedbackHost(Protocol):
    mode: str
    session: Any
    card_motions: list[CardMotion]
    toasts: list[Toast]
    _last_game_state: dict[str, Any] | None


class GameFeedback:
    def __init__(self, host: FeedbackHost) -> None:
        self.host = host

    def observe(self) -> None:
        if self.host.mode != "game" or self.host.session is None:
            self.host._last_game_state = None
            return
        state = self.host.session.snapshot()
        if state is None:
            return
        previous = self.host._last_game_state
        if previous is None:
            if state.get("phase") == "playing":
                self._notify_initial_deal(state)
            self.host._last_game_state = state
            return
        self._notify_phase_changes(previous, state)
        self._notify_top_card_change(previous, state)
        self._notify_count_changes(previous, state)
        self._notify_reaction_changes(previous, state)
        self._notify_turn_change(previous, state)
        self.host._last_game_state = state

    def _notify_initial_deal(self, state: dict[str, Any]) -> None:
        hand_count = self._card_count(state, self._viewer_id())
        self.push_toast("Cards are dealt!", f"You have {hand_count} cards. Scan for a match and get ready.", ACCENT_2)
        for player in state.get("players", []):
            self.animate_cards(self._deck_anchor(), self._player_anchor(state, player.get("id")), min(4, int(player.get("card_count", 0))), face_down=True)

    def _notify_phase_changes(self, previous: dict[str, Any], state: dict[str, Any]) -> None:
        if previous.get("phase") != "playing" and state.get("phase") == "playing":
            self._notify_initial_deal(state)
        if previous.get("phase") != "ended" and state.get("phase") == "ended":
            winner_id = state.get("winner_id")
            title = "You win!" if winner_id == self._viewer_id() else f"{self._name_for(state, winner_id)} wins!"
            body = "The table bows to your final card." if winner_id == self._viewer_id() else "Game over. Time for a rematch."
            self.push_toast(title, body, GOOD)

    def _notify_top_card_change(self, previous: dict[str, Any], state: dict[str, Any]) -> None:
        old_top = previous.get("top_card") or {}
        new_top = state.get("top_card") or {}
        if not new_top or old_top.get("id") == new_top.get("id"):
            return
        actor_id = previous.get("current_player_id")
        actor = self._name_for(state, actor_id)
        card_label = readable_card(new_top)
        title = f"You played {card_label}!" if actor_id == self._viewer_id() else f"{actor} played {card_label}!"
        self.push_toast(title, self._effect_hint(new_top, state, actor_id), self._card_tone(new_top))
        self.host.card_motions.append(CardMotion(self._player_anchor(previous, actor_id), self._discard_anchor(), new_top))

    def _notify_count_changes(self, previous: dict[str, Any], state: dict[str, Any]) -> None:
        if previous.get("phase") != "playing" and state.get("phase") == "playing":
            return
        previous_players = self._players_by_id(previous)
        for player in state.get("players", []):
            player_id = player.get("id")
            if player_id not in previous_players:
                continue
            delta = int(player.get("card_count", 0)) - int(previous_players[player_id].get("card_count", 0))
            if delta <= 0:
                continue
            actor = self._name_for(state, player_id)
            title = f"You drew {delta} card{'s' if delta != 1 else ''}!" if player_id == self._viewer_id() else f"{actor} drew {delta} card{'s' if delta != 1 else ''}!"
            body = self._draw_body(previous, state, player_id)
            self.push_toast(title, body, BAD if delta >= 2 else ACCENT)
            self.animate_cards(self._deck_anchor(), self._player_anchor(state, player_id), min(4, delta), face_down=True)

    def _notify_reaction_changes(self, previous: dict[str, Any], state: dict[str, Any]) -> None:
        old_reaction = previous.get("reaction", {})
        new_reaction = state.get("reaction", {})
        if not old_reaction.get("active") and new_reaction.get("active"):
            source = self._name_for(state, new_reaction.get("source_player_id"))
            self.push_toast("Reaction round!", f"{source} played an 8. Smash React now. Last or missing response draws 2.", BAD)
            return
        old_responders = set(old_reaction.get("responders", ()))
        new_responders = set(new_reaction.get("responders", ()))
        for responder_id in sorted(new_responders - old_responders):
            if responder_id == self._viewer_id():
                self.push_toast("You reacted!", "Nice tap. Now hope someone else blinked.", GOOD, duration=2.4)
            else:
                self.push_toast(f"{self._name_for(state, responder_id)} reacted!", "They are safe for now. Watch the last responder.", ACCENT_2, duration=2.4)
        if old_reaction.get("active") and not new_reaction.get("active"):
            punished = self._players_with_card_gain(previous, state, minimum=2)
            if punished:
                names = ", ".join(self._name_for(state, player_id) for player_id in punished)
                self.push_toast("Reaction settled!", f"{names} got clipped. Last or missing response draws 2.", BAD)

    def _notify_turn_change(self, previous: dict[str, Any], state: dict[str, Any]) -> None:
        old_turn = previous.get("current_player_id")
        new_turn = state.get("current_player_id")
        if old_turn == new_turn or state.get("phase") != "playing":
            return
        if new_turn == self._viewer_id():
            body = f"Stack a draw card or take the +{state.get('pending_draw')} penalty." if state.get("pending_draw", 0) else "Match color, match rank, or draw if stuck."
            self.push_toast("Your turn!", body, GOOD)
        else:
            self.push_toast(f"{self._name_for(state, new_turn)} is up", "Watch their play. The next surprise may be aimed at you.", MUTED, duration=2.7)

    def push_toast(self, title: str, body: str, tone: tuple[int, int, int], duration: float = 4.2) -> None:
        if self.host.toasts and self.host.toasts[-1].title == title and self.host.toasts[-1].body == body:
            return
        self.host.toasts.append(Toast(title, body, tone, duration=duration))
        self.host.toasts = self.host.toasts[-4:]

    def animate_cards(self, start: tuple[int, int], end: tuple[int, int], count: int, face_down: bool) -> None:
        for index in range(count):
            offset = index * 7
            self.host.card_motions.append(
                CardMotion((start[0] + offset, start[1] - offset), (end[0] + offset, end[1] - offset), face_down=face_down, duration=0.28 + index * 0.035)
            )

    def _draw_body(self, previous: dict[str, Any], state: dict[str, Any], player_id: str | None) -> str:
        if state.get("pending_draw", 0) == 0 and previous.get("pending_draw", 0) > 0:
            return "Penalty collected. Their turn is toast, but the table moves on."
        if state.get("reaction", {}).get("active"):
            return "Reaction punishment landed. Stay sharp when an 8 appears."
        if player_id == self._viewer_id() and state.get("drew_this_turn"):
            return "If that new card glows, play it now. Otherwise pass."
        return "They could not play and had to add to their hand."

    def _effect_hint(self, card: dict[str, str], state: dict[str, Any], actor_id: str | None) -> str:
        rank = card.get("rank")
        lead = "You will" if actor_id == self._viewer_id() else "They will"
        if rank == "0":
            return f"{lead} pass everyone around the table. Hands are moving."
        if rank == "7":
            return f"{lead} swap hands with a target. Someone's hand just became someone else's problem."
        if rank == "8":
            return "Everybody must react now. Last click, or no click, draws 2."
        if rank == "skip":
            return "The next player gets skipped. Blink and the turn is gone."
        if rank == "reverse":
            return "Direction flips. The turn order just changed lanes."
        if rank == "draw_two":
            return f"Penalty grows to +{state.get('pending_draw', 2)}. Stack or suffer."
        if rank == "wild_draw_four":
            return f"Color becomes {state.get('active_color')}. Penalty grows to +{state.get('pending_draw', 4)}."
        if rank == "wild":
            return f"Color becomes {state.get('active_color')}. Plan your next match."
        return "Clean play. The turn moves on."

    def _players_by_id(self, state: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {str(player.get("id")): player for player in state.get("players", [])}

    def _players_with_card_gain(self, previous: dict[str, Any], state: dict[str, Any], minimum: int = 1) -> list[str]:
        old = self._players_by_id(previous)
        gained: list[str] = []
        for player in state.get("players", []):
            player_id = str(player.get("id"))
            delta = int(player.get("card_count", 0)) - int(old.get(player_id, {}).get("card_count", 0))
            if delta >= minimum:
                gained.append(player_id)
        return gained

    def _viewer_id(self) -> str | None:
        return self.host.session.player_id if self.host.session else None

    def _card_count(self, state: dict[str, Any], player_id: str | None) -> int:
        return int(self._players_by_id(state).get(str(player_id), {}).get("card_count", 0))

    def _name_for(self, state: dict[str, Any], player_id: str | None) -> str:
        if player_id == self._viewer_id():
            return "You"
        for player in state.get("players", []):
            if player.get("id") == player_id:
                return str(player.get("name"))
        return "None"

    def _deck_anchor(self) -> tuple[int, int]:
        return (450, 197)

    def _discard_anchor(self) -> tuple[int, int]:
        return (584, 197)

    def _player_anchor(self, state: dict[str, Any], player_id: str | None) -> tuple[int, int]:
        if player_id == self._viewer_id():
            return (610, 584)
        for index, player in enumerate(state.get("players", [])):
            if player.get("id") == player_id:
                return (132, 154 + index * 38)
        return (132, 154)

    def _card_tone(self, card: dict[str, str]) -> tuple[int, int, int]:
        return color_tuple(card.get("color", "wild")) if card.get("color") != "wild" else ACCENT_2
