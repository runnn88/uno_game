import socket
import threading
from collections.abc import Callable

from infrastructure.network.protocol import MessageType, NetworkMessage
from infrastructure.network.serializer import receive_message, send_message


class GameClient:
    def __init__(self, on_message: Callable[[NetworkMessage], None] | None = None) -> None:
        self.on_message = on_message or (lambda message: None)
        self.socket: socket.socket | None = None
        self.player_id: str | None = None
        self.state: dict[str, object] | None = None
        self._running = False
        self._intentional_disconnect = False

    def connect_to_server(self, host: str, port: int, timeout: float = 2.5) -> None:
        self.socket = socket.create_connection((host, port), timeout=timeout)
        self.socket.settimeout(None)
        self._running = True
        self._intentional_disconnect = False
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def create_room(self, name: str) -> None:
        self.send(NetworkMessage.of(MessageType.CREATE_ROOM, {"name": name}))

    def join_room(self, room_code: str, name: str) -> None:
        self.send(NetworkMessage.of(MessageType.JOIN_ROOM, {"room_code": room_code, "name": name}))

    def disconnect(self) -> None:
        self._intentional_disconnect = True
        self._running = False
        if self.socket is not None:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.socket.close()

    def send(self, message: NetworkMessage) -> None:
        if self.socket is None:
            raise RuntimeError("Client is not connected")
        try:
            send_message(self.socket, message)
        except OSError as exc:
            self._running = False
            raise RuntimeError("Lost connection to the relay server") from exc

    def start_game(self) -> None:
        self.send(NetworkMessage.of(MessageType.START_GAME))

    def host_settings(self, max_players: int | None = None, lobby_locked: bool | None = None) -> None:
        payload: dict[str, object] = {}
        if max_players is not None:
            payload["max_players"] = max_players
        if lobby_locked is not None:
            payload["lobby_locked"] = lobby_locked
        self.send(NetworkMessage.of(MessageType.HOST_SETTINGS, payload))

    def play_card(
        self,
        card_id: str,
        chosen_color: str | None = None,
        target_player_id: str | None = None,
        pass_direction: str | None = None,
    ) -> None:
        self.send(NetworkMessage.of(MessageType.PLAY_CARD, {
            "card_id": card_id,
            "chosen_color": chosen_color,
            "target_player_id": target_player_id,
            "pass_direction": pass_direction,
        }))

    def draw_card(self, count: int = 1) -> None:
        self.send(NetworkMessage.of(MessageType.DRAW_CARD, {"count": count}))

    def pass_turn(self) -> None:
        self.send(NetworkMessage.of(MessageType.PASS_TURN))

    def call_uno(self) -> None:
        self.send(NetworkMessage.of(MessageType.CALL_UNO))

    def react(self) -> None:
        self.send(NetworkMessage.of(MessageType.REACTION))

    def receive_loop(self) -> None:
        if self.socket is None:
            return
        file_obj = self.socket.makefile("rb")
        lost_message = "Lost connection to the relay server"
        while self._running:
            try:
                message = receive_message(file_obj)
            except OSError as exc:
                lost_message = str(exc) or lost_message
                break
            if message is None:
                break
            self.handle(message)
        was_running = self._running
        self._running = False
        if was_running and not self._intentional_disconnect:
            self.handle(NetworkMessage.of(MessageType.ERROR, {"message": lost_message}))

    def handle(self, message: NetworkMessage) -> None:
        if message.type == MessageType.PLAYER_JOINED:
            self.player_id = message.payload.get("player_id")
        elif message.type == MessageType.GAME_STATE:
            self.state = message.payload
        self.on_message(message)


Client = GameClient
