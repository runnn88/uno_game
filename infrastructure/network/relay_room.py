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
        player_name = self._join_name(room, name, len(room.state.players) + 1)
        room.state.players.append(Player(player_id, player_name))
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
            player_name = self._player_name(room, player_id)
            if room.state.phase in {GamePhase.MENU, GamePhase.LOBBY}:
                self._remove_lobby_player(room, player_id)
            else:
                self._remove_active_player(room, player_id)
            self._set_room_notice(room, f"{player_name} left the room.")
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

    def _remove_active_player(self, room: RelayRoom, player_id: str) -> None:
        players = room.state.players
        leaving_index = next((index for index, player in enumerate(players) if player.id == player_id), None)
        if leaving_index is None:
            return
        was_current = leaving_index == room.state.turn.current_player_index
        room.state.players = [player for player in players if player.id != player_id]
        room.state.reaction.responders = [responder for responder in room.state.reaction.responders if responder != player_id]
        room.state.uno_protected_player_ids.discard(player_id)
        remaining = room.state.players
        if not remaining:
            return
        if len(remaining) == 1 and room.state.phase == GamePhase.PLAYING:
            room.state.winner_id = remaining[0].id
            room.state.phase = GamePhase.ENDED
            room.state.turn.current_player_index = 0
            return
        if leaving_index < room.state.turn.current_player_index:
            room.state.turn.current_player_index -= 1
        elif was_current and room.state.turn.current_player_index >= len(remaining):
            room.state.turn.current_player_index = 0
        elif room.state.turn.current_player_index >= len(remaining):
            room.state.turn.current_player_index = len(remaining) - 1
        if room.host_player_id == player_id and room.clients:
            room.host_player_id = next(iter(room.clients.values()))

    def _player_name(self, room: RelayRoom, player_id: str) -> str:
        try:
            return room.state.player_by_id(player_id).name
        except ValueError:
            return "A player"

    def _set_room_notice(self, room: RelayRoom, message: str) -> None:
        room.state.room_notice = message
        room.state.room_notice_sequence += 1

    def _new_code(self) -> str:
        alphabet = ascii_uppercase + digits
        while True:
            code = "".join(choice(alphabet) for _ in range(ROOM_CODE_LENGTH))
            if code not in self.rooms:
                return code

    def _clean_name(self, name: str, index: int) -> str:
        cleaned = str(name).strip()[:18]
        if self._is_generic_name(cleaned):
            return f"Player {index}"
        return cleaned

    def _join_name(self, room: RelayRoom, name: str, index: int) -> str:
        cleaned = self._clean_name(name, index)
        if self._is_generic_name(str(name).strip()[:18]):
            return self._unique_name(room, name, index)
        existing = {player.name.strip().lower() for player in room.state.players if player.connected}
        if cleaned.strip().lower() in existing:
            raise ValueError("Name already taken")
        return cleaned

    def _is_generic_name(self, name: str) -> bool:
        return name.strip().lower() in {"", "host", "player", "player 0"}

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
