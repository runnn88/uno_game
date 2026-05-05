from __future__ import annotations

import threading
from time import monotonic
from typing import Any

from application.commands.draw_card import DrawCardCommand
from application.commands.play_card import PlayCardCommand
from application.commands.react_event import ReactEventCommand
from application.dto.game_state_dto import game_state_to_dto
from application.handlers.draw_handler import DrawHandler
from application.handlers.play_card_handler import PlayCardHandler
from application.handlers.reaction_handler import ReactionHandler
from config.enums import CardColor, PassDirection
from domain.entities.player import Player
from domain.state.game_state import GameState
from infrastructure.network.client import GameClient
from infrastructure.network.protocol import MessageType, NetworkMessage
from systems.ai.bot_player import BotPlayerController
from systems.setup.game_initializer import GameInitializer


class LocalGameSession:
    def __init__(self, player_count: int = 2, bot_count: int = 0) -> None:
        human_count = max(1, player_count - bot_count)
        players = [Player(f"p{i + 1}", f"Player {i + 1}") for i in range(human_count)]
        for index in range(bot_count):
            bot_id = len(players) + 1
            players.append(Player(f"p{bot_id}", f"Bot {index + 1}", is_bot=True))
        self.state = GameState(players=players)
        self.initializer = GameInitializer()
        self.play_handler = PlayCardHandler()
        self.draw_handler = DrawHandler()
        self.reaction_handler = ReactionHandler()
        self.bot_controller = BotPlayerController()
        self._bot_action_at = 0.0
        self.error: str | None = None
        self.info = "Local hotseat"
        self.start_game()

    @property
    def player_id(self) -> str | None:
        return self.state.current_player.id if self.state.current_player else None

    @property
    def can_start_game(self) -> bool:
        return True

    def snapshot(self) -> dict[str, Any] | None:
        return game_state_to_dto(self.state, self.player_id).to_dict()

    def start_game(self) -> None:
        self._run(lambda: self.initializer.start(self.state))

    def play_card(
        self,
        card_id: str,
        chosen_color: str | None = None,
        target_player_id: str | None = None,
        pass_direction: str | None = None,
    ) -> None:
        player_id = self.player_id
        if player_id is None:
            return
        color = CardColor(chosen_color) if chosen_color else None
        direction = PassDirection(pass_direction) if pass_direction else None
        self._run(lambda: self.play_handler.handle(self.state, PlayCardCommand(player_id, card_id, color, target_player_id, direction)))

    def draw_card(self) -> None:
        player_id = self.player_id
        if player_id is not None:
            self._run(lambda: self.draw_handler.handle(self.state, DrawCardCommand(player_id)))

    def pass_turn(self) -> None:
        player_id = self.player_id
        if player_id is None:
            return
        from application.commands.pass_turn import PassTurnCommand
        from application.handlers.pass_turn_handler import PassTurnHandler

        self._run(lambda: PassTurnHandler().handle(self.state, PassTurnCommand(player_id)))

    def react(self, player_id: str | None = None) -> None:
        target = player_id or self.player_id
        if target is not None:
            self._run(lambda: self.reaction_handler.handle(self.state, ReactEventCommand(target)))

    def update(self) -> None:
        if self.state.reaction.active:
            for player in self.state.players:
                if player.is_bot and player.id not in self.state.reaction.responders:
                    self.react(player.id)
        if self.state.reaction.active and self.reaction_handler.finish_if_ready(self.state):
            self.error = None
            self._bot_action_at = monotonic() + 0.5
        current = self.state.current_player
        if current is not None and current.is_bot and not self.state.reaction.active and self.state.winner_id is None:
            now = monotonic()
            if self._bot_action_at == 0.0:
                self._bot_action_at = now + 0.6
            elif now >= self._bot_action_at:
                self._run(lambda: self.bot_controller.take_turn(self.state, current))
                self._bot_action_at = monotonic() + 0.6
        elif current is not None and not current.is_bot:
            self._bot_action_at = 0.0

    def close(self) -> None:
        pass

    def _run(self, fn) -> None:
        try:
            fn()
            self.error = None
        except Exception as exc:
            self.error = str(exc)


class OnlineGameSession:
    def __init__(
        self,
        host: str,
        port: int,
        name: str,
        is_host: bool = False,
        room_code: str | None = None,
    ) -> None:
        self.is_host = is_host
        self.room_code = room_code
        self.client = GameClient(self._on_message)
        self._lock = threading.RLock()
        self._ready = threading.Event()
        self._state: dict[str, Any] | None = None
        self.error: str | None = None
        self.info = "Connected through relay"
        self.client.connect_to_server(host, port, timeout=2.5)
        try:
            if is_host:
                self.client.create_room(name)
            else:
                if room_code is None:
                    raise ValueError("Room code is required")
                self.client.join_room(room_code, name)
            self._wait_until_ready(is_host)
        except Exception:
            self.client.disconnect()
            raise

    @property
    def player_id(self) -> str | None:
        return self.client.player_id

    @property
    def can_start_game(self) -> bool:
        return self.is_host

    def snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            return dict(self._state) if self._state else None

    def start_game(self) -> None:
        self._run_network("start the game", self.client.start_game)

    def play_card(
        self,
        card_id: str,
        chosen_color: str | None = None,
        target_player_id: str | None = None,
        pass_direction: str | None = None,
    ) -> None:
        self._run_network("play that card", lambda: self.client.play_card(card_id, chosen_color, target_player_id, pass_direction))

    def draw_card(self) -> None:
        self._run_network("draw a card", self.client.draw_card)

    def pass_turn(self) -> None:
        self._run_network("pass the turn", self.client.pass_turn)

    def react(self, player_id: str | None = None) -> None:
        self._run_network("send your reaction", self.client.react)

    def host_settings(self, max_players: int | None = None, lobby_locked: bool | None = None) -> None:
        self._run_network("update host settings", lambda: self.client.host_settings(max_players=max_players, lobby_locked=lobby_locked))

    def update(self) -> None:
        pass

    def close(self) -> None:
        self.client.disconnect()

    def _on_message(self, message: NetworkMessage) -> None:
        with self._lock:
            if message.type == MessageType.GAME_STATE:
                self._state = dict(message.payload)
            elif message.type == MessageType.ERROR:
                self.error = str(message.payload.get("message", "Network error"))
                self._ready.set()
            elif message.type == MessageType.PLAYER_JOINED:
                self.error = None
                if not self.is_host:
                    self._ready.set()
            elif message.type == MessageType.ROOM_CREATED:
                self.room_code = str(message.payload.get("room_code", ""))
                self.error = None
                self._ready.set()

    def _run_network(self, action: str, fn) -> None:
        try:
            fn()
        except Exception as exc:
            self.error = f"Could not {action}: {exc}"

    def _wait_until_ready(self, is_host: bool) -> None:
        if not self._ready.wait(3.0):
            raise TimeoutError("The relay accepted the socket but did not confirm the room.")
        if self.error:
            raise ValueError(self.error)
        if is_host and not self.room_code:
            raise ValueError("Relay did not return a room code.")
        if not self.client.player_id:
            raise ValueError("Relay did not assign a player slot.")
