from dataclasses import dataclass
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    CREATE_ROOM = "CREATE_ROOM"
    ROOM_CREATED = "ROOM_CREATED"
    JOIN_ROOM = "JOIN_ROOM"
    PLAYER_JOINED = "PLAYER_JOINED"
    START_GAME = "START_GAME"
    HOST_SETTINGS = "HOST_SETTINGS"
    PLAY_CARD = "PLAY_CARD"
    DRAW_CARD = "DRAW_CARD"
    PASS_TURN = "PASS_TURN"
    CHOOSE_COLOR = "CHOOSE_COLOR"
    CHOOSE_TARGET = "CHOOSE_TARGET"
    REACTION = "REACTION"
    REACTION_START = "REACTION_START"
    GAME_STATE = "GAME_STATE"
    ERROR = "ERROR"
    DISCONNECT = "DISCONNECT"


@dataclass(frozen=True)
class NetworkMessage:
    type: MessageType
    payload: dict[str, Any]

    @classmethod
    def of(cls, message_type: MessageType | str, payload: dict[str, Any] | None = None) -> "NetworkMessage":
        return cls(MessageType(message_type), payload or {})
