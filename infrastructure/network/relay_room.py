import socket
from dataclasses import dataclass, field
from secrets import choice
from string import ascii_uppercase, digits

from config.constants import MAX_PLAYERS, ROOM_CODE_LENGTH
from config.enums import GamePhase
from domain.entities.player import Player
from domain.state.game_state import GameState
from systems.turn.turn_manager import TurnManager


@dataclass
class RelayRoom:
    code: str
    host_player_id: str
    state: GameState = field(default_factory=GameState.empty)
    clients: dict[socket.socket, str] = field(default_factory=dict)
    max_players: int = MAX_PLAYERS
    lobby_locked: bool = False


class RelayRoomDirectory:
    def __init__(self) -> None:
        self.rooms: dict[str, RelayRoom] = {}
        self.client_rooms: dict[socket.socket, str] = {}
        self.turns = TurnManager()

    def create_room(self, conn: socket.socket, name: str) -> RelayRoom:
        if conn in self.client_rooms:
            raise ValueError("Client is already in a room")
        code = self._new_code()
        room = RelayRoom(code=code, host_player_id="p1")
        room.state.phase = GamePhase.LOBBY
        room.state.players.append(Player("p1", self._unique_name(room, name, 1)))
        room.clients[conn] = "p1"
        self.rooms[code] = room
        self.client_rooms[conn] = code
        return room

    def join_room(self, conn: socket.socket, code: str, name: str) -> RelayRoom:
        room = self.rooms.get(code.upper().strip())
        if room is None:
            raise ValueError("Room not found")
        if room.state.phase not in {GamePhase.MENU, GamePhase.LOBBY}:
            raise ValueError("This game has already started")
        if room.lobby_locked:
            raise ValueError("The lobby is locked")
        if len([player for player in room.state.players if player.connected]) >= room.max_players:
            raise ValueError("room is full")
        player_id = f"p{len(room.state.players) + 1}"
        room.state.players.append(Player(player_id, self._unique_name(room, name, len(room.state.players) + 1)))
        room.clients[conn] = player_id
        self.client_rooms[conn] = room.code
        return room

    def disconnect(self, conn: socket.socket) -> RelayRoom | None:
        room_code = self.client_rooms.pop(conn, None)
        if room_code is None or room_code not in self.rooms:
            return None
        room = self.rooms[room_code]
        player_id = room.clients.pop(conn, None)
        if player_id is not None:
            if room.state.phase in {GamePhase.MENU, GamePhase.LOBBY}:
                self._remove_lobby_player(room, player_id)
            else:
                try:
                    room.state.player_by_id(player_id).connected = False
                except ValueError:
                    pass
            if room.state.phase == GamePhase.PLAYING:
                self._repair_turn_after_disconnect(room, player_id)
        if not room.clients:
            self.rooms.pop(room_code, None)
            return None
        return room

    def room_for(self, conn: socket.socket) -> RelayRoom:
        code = self.client_rooms.get(conn)
        if code is None or code not in self.rooms:
            raise ValueError("Client has not joined a room")
        return self.rooms[code]

    def _repair_turn_after_disconnect(self, room: RelayRoom, player_id: str) -> None:
        connected = [player for player in room.state.players if player.connected]
        if len(connected) == 1:
            room.state.winner_id = connected[0].id
            room.state.phase = GamePhase.ENDED
            return
        current = room.state.current_player
        if current is not None and current.id == player_id:
            room.state.turn.skip_next = False
            self.turns.advance(room.state)

    def _remove_lobby_player(self, room: RelayRoom, player_id: str) -> None:
        room.state.players = [player for player in room.state.players if player.id != player_id]
        if room.host_player_id == player_id and room.clients:
            room.host_player_id = next(iter(room.clients.values()))

    def _new_code(self) -> str:
        alphabet = ascii_uppercase + digits
        while True:
            code = "".join(choice(alphabet) for _ in range(ROOM_CODE_LENGTH))
            if code not in self.rooms:
                return code

    def _clean_name(self, name: str, index: int) -> str:
        cleaned = str(name).strip()[:18]
        if cleaned.strip().lower() in {"", "host", "player", "player 0"}:
            return f"Player {index}"
        return cleaned

    def _unique_name(self, room: RelayRoom, name: str, index: int) -> str:
        base = self._clean_name(name, index)
        existing = {player.name for player in room.state.players}
        if base not in existing:
            return base
        for suffix in range(2, MAX_PLAYERS + 2):
            candidate = f"{base[:14]} #{suffix}"
            if candidate not in existing:
                return candidate
        return f"Player {index}"
