import socket
import threading
from collections.abc import Callable

from uno_game.infrastructure.network.protocol import MessageType, NetworkMessage
from uno_game.infrastructure.network.serializer import receive_message, send_message


class GameClient:
    def __init__(self, on_message: Callable[[NetworkMessage], None] | None = None) -> None:
        self.on_message = on_message or (lambda message: None)
        self.socket: socket.socket | None = None
        self.player_id: str | None = None
        self.state: dict[str, object] | None = None
        self._running = False

    def connect(self, host: str, port: int, name: str) -> None:
        self.socket = socket.create_connection((host, port))
        self._running = True
        threading.Thread(target=self.receive_loop, daemon=True).start()
        self.send(NetworkMessage.of(MessageType.JOIN_ROOM, {"name": name}))

    def disconnect(self) -> None:
        self._running = False
        if self.socket is not None:
            self.socket.close()

    def send(self, message: NetworkMessage) -> None:
        if self.socket is None:
            raise RuntimeError("Client is not connected")
        send_message(self.socket, message)

    def start_game(self) -> None:
        self.send(NetworkMessage.of(MessageType.START_GAME))

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

    def react(self) -> None:
        self.send(NetworkMessage.of(MessageType.REACTION))

    def receive_loop(self) -> None:
        if self.socket is None:
            return
        file_obj = self.socket.makefile("rb")
        while self._running:
            try:
                message = receive_message(file_obj)
            except OSError:
                break
            if message is None:
                break
            self.handle(message)

    def handle(self, message: NetworkMessage) -> None:
        if message.type == MessageType.PLAYER_JOINED:
            self.player_id = message.payload.get("player_id")
        elif message.type == MessageType.GAME_STATE:
            self.state = message.payload
        self.on_message(message)


Client = GameClient
