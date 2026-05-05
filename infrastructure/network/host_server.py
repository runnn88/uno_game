import socket
import threading
import time
from collections.abc import Callable

from uno_game.application.commands.draw_card import DrawCardCommand
from uno_game.application.commands.pass_turn import PassTurnCommand
from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.application.commands.react_event import ReactEventCommand
from uno_game.application.dto.game_state_dto import game_state_to_dto
from uno_game.application.handlers.draw_handler import DrawHandler
from uno_game.application.handlers.pass_turn_handler import PassTurnHandler
from uno_game.application.handlers.play_card_handler import PlayCardHandler
from uno_game.application.handlers.reaction_handler import ReactionHandler
from uno_game.config.constants import DEFAULT_GAME_PORT, MAX_PLAYERS
from uno_game.config.enums import CardColor, GamePhase, PassDirection
from uno_game.core.event_bus import EventBus
from uno_game.domain.entities.player import Player
from uno_game.domain.state.game_state import GameState
from uno_game.infrastructure.network.protocol import MessageType, NetworkMessage
from uno_game.infrastructure.network.serializer import receive_message, send_message
from uno_game.systems.setup.game_initializer import GameInitializer
from uno_game.systems.turn.turn_manager import TurnManager


class HostServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = DEFAULT_GAME_PORT,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.on_log = on_log or (lambda message: None)
        self.state = GameState.empty()
        self.events = EventBus()
        self.play_handler = PlayCardHandler(self.events)
        self.draw_handler = DrawHandler(self.events)
        self.pass_turn_handler = PassTurnHandler(self.events)
        self.reaction_handler = ReactionHandler(self.events)
        self.initializer = GameInitializer()
        self.turns = TurnManager()
        self.clients: dict[socket.socket, str] = {}
        self.host_player_id: str | None = None
        self._server_socket: socket.socket | None = None
        self._running = False
        self._lock = threading.RLock()

    def start(self) -> None:
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self.port = self._server_socket.getsockname()[1]
        self._server_socket.listen()
        self._running = True
        threading.Thread(target=self._tick_loop, daemon=True).start()
        self.on_log(f"Host server listening on {self.host}:{self.port}")
        while self._running:
            try:
                conn, _addr = self._server_socket.accept()
            except OSError:
                if self._running:
                    raise
                break
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def stop(self) -> None:
        self._running = False
        if self._server_socket is not None:
            self._server_socket.close()
        for conn in list(self.clients):
            conn.close()

    def _handle_client(self, conn: socket.socket) -> None:
        file_obj = conn.makefile("rb")
        try:
            while self._running:
                message = receive_message(file_obj)
                if message is None:
                    break
                self.process_message(conn, message)
        except OSError as exc:
            self._send_error(conn, str(exc))
        finally:
            self._disconnect(conn)

    def process_message(self, conn: socket.socket, message: NetworkMessage) -> None:
        with self._lock:
            try:
                if message.type == MessageType.JOIN_ROOM:
                    self._join(conn, message.payload.get("name", "Player"))
                elif message.type == MessageType.START_GAME:
                    if self._player_id(conn) != self.host_player_id:
                        raise ValueError("Only the host can start the game")
                    self.initializer.start(self.state)
                    self.broadcast_state()
                elif message.type == MessageType.PLAY_CARD:
                    player_id = self._player_id(conn)
                    chosen = message.payload.get("chosen_color")
                    command = PlayCardCommand(
                        player_id=player_id,
                        card_id=message.payload["card_id"],
                        chosen_color=CardColor(chosen) if chosen else None,
                        target_player_id=message.payload.get("target_player_id"),
                        pass_direction=PassDirection(message.payload["pass_direction"]) if message.payload.get("pass_direction") else None,
                    )
                    self.play_handler.handle(self.state, command)
                    self.broadcast_state()
                elif message.type == MessageType.DRAW_CARD:
                    player_id = self._player_id(conn)
                    self.draw_handler.handle(self.state, DrawCardCommand(player_id, message.payload.get("count", 1)))
                    self.broadcast_state()
                elif message.type == MessageType.PASS_TURN:
                    player_id = self._player_id(conn)
                    self.pass_turn_handler.handle(self.state, PassTurnCommand(player_id))
                    self.broadcast_state()
                elif message.type == MessageType.REACTION:
                    player_id = self._player_id(conn)
                    self.reaction_handler.handle(self.state, ReactEventCommand(player_id))
                    self.broadcast_state()
                else:
                    self._send_error(conn, f"Unsupported message type: {message.type.value}")
            except Exception as exc:
                self._send_error(conn, str(exc))

    def broadcast(self, message: NetworkMessage) -> None:
        for conn in list(self.clients):
            try:
                send_message(conn, message)
            except OSError:
                self._disconnect(conn)

    def broadcast_state(self) -> None:
        for conn, player_id in list(self.clients.items()):
            payload = game_state_to_dto(self.state, player_id).to_dict()
            try:
                send_message(conn, NetworkMessage.of(MessageType.GAME_STATE, payload))
            except OSError:
                self._disconnect(conn)

    def _tick_loop(self) -> None:
        while self._running:
            time.sleep(0.1)
            with self._lock:
                if self.reaction_handler.finish_if_ready(self.state):
                    self.broadcast_state()

    def _join(self, conn: socket.socket, name: str) -> None:
        if conn in self.clients:
            return
        if self.state.phase not in {GamePhase.MENU, GamePhase.LOBBY}:
            self._send_error(conn, "This game has already started")
            return
        if len([player for player in self.state.players if player.connected]) >= MAX_PLAYERS:
            self._send_error(conn, "The room is full")
            return
        player_id = f"p{len(self.state.players) + 1}"
        clean_name = str(name).strip()[:18] or f"Player {len(self.state.players) + 1}"
        self.clients[conn] = player_id
        if self.host_player_id is None:
            self.host_player_id = player_id
            self.state.phase = GamePhase.LOBBY
        self.state.players.append(Player(player_id, clean_name))
        send_message(conn, NetworkMessage.of(MessageType.PLAYER_JOINED, {"player_id": player_id}))
        self.broadcast_state()

    def _disconnect(self, conn: socket.socket) -> None:
        with self._lock:
            player_id = self.clients.pop(conn, None)
            if player_id is not None:
                try:
                    self.state.player_by_id(player_id).connected = False
                except ValueError:
                    pass
                if self.state.phase == GamePhase.PLAYING:
                    self._repair_turn_after_disconnect(player_id)
                self.broadcast_state()
            try:
                conn.close()
            except OSError:
                pass

    def _repair_turn_after_disconnect(self, player_id: str) -> None:
        connected = [player for player in self.state.players if player.connected]
        if len(connected) == 1:
            self.state.winner_id = connected[0].id
            self.state.phase = GamePhase.ENDED
            return
        current = self.state.current_player
        if current is not None and current.id == player_id:
            self.state.turn.skip_next = False
            self.turns.advance(self.state)

    def _player_id(self, conn: socket.socket) -> str:
        if conn not in self.clients:
            raise ValueError("Client has not joined the room")
        return self.clients[conn]

    def _send_error(self, conn: socket.socket, message: str) -> None:
        try:
            send_message(conn, NetworkMessage.of(MessageType.ERROR, {"message": message}))
        except OSError:
            self._disconnect(conn)
