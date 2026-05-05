import socket

from uno_game.config.constants import DEFAULT_DISCOVERY_PORT
from uno_game.infrastructure.network.protocol import MessageType, NetworkMessage
from uno_game.infrastructure.network.serializer import receive_message, send_message


class DiscoveryClient:
    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_DISCOVERY_PORT) -> None:
        self.host = host
        self.port = port

    def create_room(self, game_port: int, public_host: str | None = None) -> str:
        response = self._request(NetworkMessage.of(MessageType.CREATE_ROOM, {"host": public_host, "port": game_port}))
        if response.type != MessageType.ROOM_CREATED:
            raise RuntimeError(response.payload.get("message", "Could not create room"))
        return str(response.payload["room_code"])

    def join_room(self, room_code: str) -> tuple[str, int]:
        response = self._request(NetworkMessage.of(MessageType.JOIN_ROOM, {"room_code": room_code.upper()}))
        if response.type != MessageType.ROOM_FOUND:
            raise RuntimeError(f"Room not found: {room_code}")
        return str(response.payload["host"]), int(response.payload["port"])

    def _request(self, message: NetworkMessage) -> NetworkMessage:
        with socket.create_connection((self.host, self.port), timeout=5) as sock:
            send_message(sock, message)
            response = receive_message(sock.makefile("rb"))
            if response is None:
                raise RuntimeError("Discovery server closed the connection")
            return response
