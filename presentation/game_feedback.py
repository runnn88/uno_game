from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


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

    # smoother/slower animation
    duration: float = 0.42


class FeedbackHost(Protocol):
    mode: str
    session: Any
    card_motions: list[CardMotion]
    toasts: list[Toast]
    _last_game_state: dict[str, Any] | None


class GameFeedback:
    def __init__(self, host: FeedbackHost) -> None:
        self.host = host

    # =========================================================
    # MAIN OBSERVER
    # =========================================================
    def observe(self) -> None:

        if self.host.mode != "game" or self.host.session is None:
            self.host._last_game_state = None
            return

        state = self.host.session.snapshot()

        if state is None:
            return

        previous = self.host._last_game_state

        # -----------------------------------------------------
        # FIRST FRAME
        # -----------------------------------------------------
        if previous is None:

            if state.get("phase") == "playing":
                self._animate_initial_deal(state)

            self.host._last_game_state = state
            return

        # -----------------------------------------------------
        # NORMAL UPDATE
        # -----------------------------------------------------
        self._animate_phase_changes(previous, state)
        self._animate_top_card_change(previous, state)
        self._animate_count_changes(previous, state)

        self.host._last_game_state = state

    # =========================================================
    # INITIAL DEAL
    # =========================================================
    def _animate_initial_deal(
        self,
        state: dict[str, Any],
    ) -> None:

        for player in state.get("players", []):

            self.animate_cards(
                self._deck_anchor(),
                self._player_anchor(
                    state,
                    player.get("id"),
                ),
                min(
                    7,
                    int(player.get("card_count", 0)),
                ),
                face_down=True,
            )

    # =========================================================
    # PHASE CHANGES
    # =========================================================
    def _animate_phase_changes(
        self,
        previous: dict[str, Any],
        state: dict[str, Any],
    ) -> None:

        if (
            previous.get("phase")
            in {"menu", "lobby", "ended"}
            and state.get("phase") == "playing"
        ):
            self._animate_initial_deal(state)

    # =========================================================
    # PLAY CARD ANIMATION
    # =========================================================
    def _animate_top_card_change(
        self,
        previous: dict[str, Any],
        state: dict[str, Any],
    ) -> None:

        old_top = previous.get("top_card") or {}
        new_top = state.get("top_card") or {}

        if (
            not new_top
            or old_top.get("id") == new_top.get("id")
        ):
            return

        actor_id = previous.get("current_player_id")

        self.host.card_motions.append(
            CardMotion(
                start=self._player_anchor(
                    previous,
                    actor_id,
                ),
                end=self._discard_anchor(),
                card=new_top,
                duration=0.36,
            )
        )

    # =========================================================
    # DRAW CARD ANIMATION
    # =========================================================
    def _animate_count_changes(
        self,
        previous: dict[str, Any],
        state: dict[str, Any],
    ) -> None:

        if (
            previous.get("phase")
            in {"menu", "lobby", "ended"}
            and state.get("phase") == "playing"
        ):
            return

        previous_players = self._players_by_id(previous)

        for player in state.get("players", []):

            player_id = player.get("id")

            if player_id not in previous_players:
                continue

            delta = (
                int(player.get("card_count", 0))
                - int(
                    previous_players[player_id].get(
                        "card_count",
                        0,
                    )
                )
            )

            if delta <= 0:
                continue

            self.animate_cards(
                self._deck_anchor(),
                self._player_anchor(
                    state,
                    player_id,
                ),
                min(4, delta),
                face_down=True,
            )

    # =========================================================
    # TOASTS
    # =========================================================
    def push_toast(
        self,
        title: str,
        body: str,
        tone: tuple[int, int, int],
        duration: float = 4.2,
    ) -> None:

        if (
            self.host.toasts
            and self.host.toasts[-1].title == title
            and self.host.toasts[-1].body == body
        ):
            return

        self.host.toasts.append(
            Toast(
                title,
                body,
                tone,
                duration=duration,
            )
        )

        self.host.toasts = self.host.toasts[-4:]

    # =========================================================
    # GENERIC CARD ANIMATION
    # =========================================================
    def animate_cards(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        count: int,
        face_down: bool,
    ) -> None:

        for index in range(count):

            offset = index * 9

            self.host.card_motions.append(
                CardMotion(
                    (
                        start[0] + offset,
                        start[1] - offset,
                    ),
                    (
                        end[0] + offset,
                        end[1] - offset,
                    ),
                    face_down=face_down,

                    # smoother stagger
                    duration=0.42 + index * 0.055,
                )
            )

    # =========================================================
    # HELPERS
    # =========================================================
    def _players_by_id(
        self,
        state: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:

        return {
            str(player.get("id")): player
            for player in state.get("players", [])
        }

    # =========================================================
    # CENTER DECK POSITION
    # =========================================================
    def _deck_anchor(self) -> tuple[int, int]:

        # moved downward
        return (510, 255)

    # =========================================================
    # DISCARD PILE POSITION
    # =========================================================
    def _discard_anchor(self) -> tuple[int, int]:

        # moved downward
        return (650, 255)

    # =========================================================
    # PLAYER DESTINATION POSITIONS
    # =========================================================
    def _player_anchor(
        self,
        state: dict[str, Any],
        player_id: str | None,
    ) -> tuple[int, int]:

        # -----------------------------------------------------
        # LOCAL PLAYER
        # -----------------------------------------------------
        if player_id == self._viewer_id():

            # lower landing position
            return (610, 640)

        # -----------------------------------------------------
        # OPPONENTS
        # -----------------------------------------------------
        opponent_anchors = [
            (110, 250),   # left
            (640, 130),   # top
            (1010, 250),  # right
        ]

        opponent_index = 0

        for player in state.get("players", []):

            if player.get("id") == self._viewer_id():
                continue

            if player.get("id") == player_id:

                return opponent_anchors[
                    min(
                        opponent_index,
                        len(opponent_anchors) - 1,
                    )
                ]

            opponent_index += 1

        # fallback
        return (110, 250)

    # =========================================================
    # LOCAL PLAYER ID
    # =========================================================
    def _viewer_id(self) -> str | None:

        return (
            self.host.session.player_id
            if self.host.session
            else None
        )