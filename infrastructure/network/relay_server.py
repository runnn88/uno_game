import socket
import threading
from dataclasses import dataclass, field
from secrets import choice
from string import ascii_uppercase, digits

from application.commands.draw_card import DrawCardCommand
from application.commands.pass_turn import PassTurnCommand
from application.commands.play_card import PlayCardCommand
from application.commands.react_event import ReactEventCommand
from application.dto.game_state_dto import game_state_to_dto
from application.handlers.draw_handler import DrawHandler
from application.handlers.pass_turn_handler import PassTurnHandler
from application.handlers.play_card_handler import PlayCardHandler
from application.handlers.reaction_handler import ReactionHandler
from config.constants import DEFAULT_DISCOVERY_PORT, MAX_PLAYERS, ROOM_CODE_LENGTH
from config.enums import CardColor, GamePhase, PassDirection
from domain.entities.player import Player
from domain.state.game_state import GameState
from infrastructure.network.protocol import MessageType, NetworkMessage
from infrastructure.network.serializer import receive_message, send_message
from systems.setup.game_initializer import GameInitializer
from systems.turn.turn_manager import TurnManager


@dataclass
class RelayRoom:
    code: str
    host_player_id: str
    state: GameState = field(default_factory=GameState.empty)
    clients: dict[socket.socket, str] = field(default_factory=dict)
    max_players: int = MAX_PLAYERS
    lobby_locked: bool = False


class RelayServer:
    """Central room-code server. Players only connect to this relay, never to each other."""

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_DISCOVERY_PORT) -> None:
        self.host = host
        self.port = port
        self.rooms: dict[str, RelayRoom] = {}
        self.client_rooms: dict[socket.socket, str] = {}
        self._server_socket: socket.socket | None = None
        self._running = False
        self._lock = threading.RLock()
        self.initializer = GameInitializer()
        self.play_handler = PlayCardHandler()
        self.draw_handler = DrawHandler()
        self.pass_handler = PassTurnHandler()
        self.reaction_handler = ReactionHandler()
        self.turns = TurnManager()

    def start(self) -> None:
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self.port = self._server_socket.getsockname()[1]
        self._server_socket.listen()
        self._running = True
        threading.Thread(target=self._tick_loop, daemon=True).start()
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
        for room in list(self.rooms.values()):
            for conn in list(room.clients):
                conn.close()

    def _handle_client(self, conn: socket.socket) -> None:
        file_obj = conn.makefile("rb")
        try:
            while self._running:
                message = receive_message(file_obj)
                if message is None:
                    break
                self.process_message(conn, message)
        finally:
            self._disconnect(conn)

    def process_message(self, conn: socket.socket, message: NetworkMessage) -> None:
        with self._lock:
            try:
                if message.type == MessageType.CREATE_ROOM:
                    self._create_room(conn, str(message.payload.get("name", "Host")))
                elif message.type == MessageType.JOIN_ROOM:
                    self._join_room(conn, str(message.payload["room_code"]), str(message.payload.get("name", "Player")))
                else:
                    room = self._room_for(conn)
                    player_id = room.clients[conn]
                    self._process_room_message(room, conn, player_id, message)
            except Exception as exc:
                self._send_error(conn, str(exc))

    def _process_room_message(self, room: RelayRoom, conn: socket.socket, player_id: str, message: NetworkMessage) -> None:
        if message.type == MessageType.START_GAME:
            if player_id != room.host_player_id:
                raise ValueError("Only the host can start the game")
            self.initializer.start(room.state)
        elif message.type == MessageType.HOST_SETTINGS:
            if player_id != room.host_player_id:
                raise ValueError("Only the host can change settings")
            if "max_players" in message.payload:
                connected = len([player for player in room.state.players if player.connected])
                room.max_players = max(max(2, connected), min(MAX_PLAYERS, int(message.payload["max_players"])))
            if "lobby_locked" in message.payload:
                room.lobby_locked = bool(message.payload["lobby_locked"])
        elif message.type == MessageType.PLAY_CARD:
            chosen = message.payload.get("chosen_color")
            self.play_handler.handle(
                room.state,
                PlayCardCommand(
                    player_id,
                    message.payload["card_id"],
                    CardColor(chosen) if chosen else None,
                    message.payload.get("target_player_id"),
                    PassDirection(message.payload["pass_direction"]) if message.payload.get("pass_direction") else None,
                ),
            )
        elif message.type == MessageType.DRAW_CARD:
            self.draw_handler.handle(room.state, DrawCardCommand(player_id, message.payload.get("count", 1)))
        elif message.type == MessageType.PASS_TURN:
            self.pass_handler.handle(room.state, PassTurnCommand(player_id))
        elif message.type == MessageType.REACTION:
            self.reaction_handler.handle(room.state, ReactEventCommand(player_id))
        else:
            raise ValueError(f"Unsupported message type: {message.type.value}")
        self._broadcast_state(room)

    def _create_room(self, conn: socket.socket, name: str) -> None:
        if conn in self.client_rooms:
            raise ValueError("Client is already in a room")
        code = self._new_code()
        player_id = "p1"
        room = RelayRoom(code=code, host_player_id=player_id)
        room.state.phase = GamePhase.LOBBY
        room.state.players.append(Player(player_id, self._clean_name(name, 1)))
        room.clients[conn] = player_id
        self.rooms[code] = room
        self.client_rooms[conn] = code
        send_message(conn, NetworkMessage.of(MessageType.PLAYER_JOINED, {"player_id": player_id}))
        send_message(conn, NetworkMessage.of(MessageType.ROOM_CREATED, {"room_code": code}))
        self._broadcast_state(room)

    def _join_room(self, conn: socket.socket, code: str, name: str) -> None:
        code = code.upper().strip()
        room = self.rooms.get(code)
        if room is None:
            raise ValueError("Room not found")
        if room.state.phase not in {GamePhase.MENU, GamePhase.LOBBY}:
            raise ValueError("This game has already started")
        if room.lobby_locked:
            raise ValueError("The lobby is locked")
        if len([player for player in room.state.players if player.connected]) >= room.max_players:
            raise ValueError("The room is full")
        player_id = f"p{len(room.state.players) + 1}"
        room.state.players.append(Player(player_id, self._clean_name(name, len(room.state.players) + 1)))
        room.clients[conn] = player_id
        self.client_rooms[conn] = room.code
        send_message(conn, NetworkMessage.of(MessageType.PLAYER_JOINED, {"player_id": player_id}))
        self._broadcast_state(room)

    def _broadcast_state(self, room: RelayRoom) -> None:
        for conn, player_id in list(room.clients.items()):
            payload = game_state_to_dto(room.state, player_id).to_dict()
            payload["room_code"] = room.code
            payload["host_player_id"] = room.host_player_id
            payload["max_players"] = room.max_players
            payload["lobby_locked"] = room.lobby_locked
            try:
                send_message(conn, NetworkMessage.of(MessageType.GAME_STATE, payload))
            except OSError:
                self._disconnect(conn)

    def _tick_loop(self) -> None:
        while self._running:
            threading.Event().wait(0.1)
            with self._lock:
                for room in list(self.rooms.values()):
                    if self.reaction_handler.finish_if_ready(room.state):
                        self._broadcast_state(room)

    def _disconnect(self, conn: socket.socket) -> None:
        with self._lock:
            room_code = self.client_rooms.pop(conn, None)
            if room_code is not None and room_code in self.rooms:
                room = self.rooms[room_code]
                player_id = room.clients.pop(conn, None)
                if player_id is not None:
                    try:
                        room.state.player_by_id(player_id).connected = False
                    except ValueError:
                        pass
                    if room.state.phase == GamePhase.PLAYING:
                        self._repair_turn_after_disconnect(room, player_id)
                    self._broadcast_state(room)
                if not room.clients:
                    self.rooms.pop(room_code, None)
            try:
                conn.close()
            except OSError:
                pass

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

    def _room_for(self, conn: socket.socket) -> RelayRoom:
        code = self.client_rooms.get(conn)
        if code is None or code not in self.rooms:
            raise ValueError("Client has not joined a room")
        return self.rooms[code]

    def _new_code(self) -> str:
        alphabet = ascii_uppercase + digits
        while True:
            code = "".join(choice(alphabet) for _ in range(ROOM_CODE_LENGTH))
            if code not in self.rooms:
                return code

    def _clean_name(self, name: str, index: int) -> str:
        return str(name).strip()[:18] or f"Player {index}"

    def _send_error(self, conn: socket.socket, message: str) -> None:
        try:
            send_message(conn, NetworkMessage.of(MessageType.ERROR, {"message": message}))
        except OSError:
            self._disconnect(conn)
