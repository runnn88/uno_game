import json
import socket

from uno_game.infrastructure.network.protocol import MessageType, NetworkMessage


class Serializer:
    def encode(self, message: NetworkMessage) -> bytes:
        data = {"type": message.type.value, "payload": message.payload}
        return (json.dumps(data, separators=(",", ":")) + "\n").encode("utf-8")

    def decode(self, raw: bytes | str) -> NetworkMessage:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return NetworkMessage(type=MessageType(data["type"]), payload=data.get("payload", {}))


def send_message(sock: socket.socket, message: NetworkMessage, serializer: Serializer | None = None) -> None:
    sock.sendall((serializer or Serializer()).encode(message))


def receive_message(file_obj: object, serializer: Serializer | None = None) -> NetworkMessage | None:
    line = file_obj.readline()
    if not line:
        return None
    return (serializer or Serializer()).decode(line)
