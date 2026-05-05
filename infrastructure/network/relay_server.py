import socket
import threading

from application.dto.game_state_dto import game_state_to_dto
from config.constants import DEFAULT_DISCOVERY_PORT
from infrastructure.network.protocol import MessageType, NetworkMessage
from infrastructure.network.relay_commands import RelayCommandProcessor
from infrastructure.network.relay_room import RelayRoom, RelayRoomDirectory
from infrastructure.network.serializer import receive_message, send_message


class RelayServer:
    """Central room-code server. Players only connect to this relay, never to each other."""

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_DISCOVERY_PORT) -> None:
        self.host = host
        self.port = port
        self.directory = RelayRoomDirectory()
        self.commands = RelayCommandProcessor()
        self._server_socket: socket.socket | None = None
        self._running = False
        self._lock = threading.RLock()

    @property
    def rooms(self) -> dict[str, RelayRoom]:
        return self.directory.rooms

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
        for room in list(self.directory.rooms.values()):
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
                    room = self.directory.create_room(conn, str(message.payload.get("name", "Host")))
                    self._send_joined(conn, room)
                    send_message(conn, NetworkMessage.of(MessageType.ROOM_CREATED, {"room_code": room.code}))
                    self._broadcast_state(room)
                elif message.type == MessageType.JOIN_ROOM:
                    room = self.directory.join_room(conn, str(message.payload["room_code"]), str(message.payload.get("name", "Player")))
                    self._send_joined(conn, room)
                    self._broadcast_state(room)
                elif message.type == MessageType.SHUTDOWN_RELAY:
                    self._shutdown_from(conn)
                else:
                    room = self.directory.room_for(conn)
                    player_id = room.clients[conn]
                    self.commands.process(room, player_id, message)
                    self._broadcast_state(room)
            except Exception as exc:
                self._send_error(conn, str(exc))

    def _shutdown_from(self, conn: socket.socket) -> None:
        send_message(conn, NetworkMessage.of(MessageType.RELAY_STOPPING, {"message": "Relay is stopping"}))
        threading.Thread(target=self.stop, daemon=True).start()

    def _send_joined(self, conn: socket.socket, room: RelayRoom) -> None:
        send_message(conn, NetworkMessage.of(MessageType.PLAYER_JOINED, {"player_id": room.clients[conn]}))

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
                for room in list(self.directory.rooms.values()):
                    if self.commands.finish_reactions(room):
                        self._broadcast_state(room)

    def _disconnect(self, conn: socket.socket) -> None:
        with self._lock:
            room = self.directory.disconnect(conn)
            if room is not None:
                self._broadcast_state(room)
            try:
                conn.close()
            except OSError:
                pass

    def _send_error(self, conn: socket.socket, message: str) -> None:
        try:
            send_message(conn, NetworkMessage.of(MessageType.ERROR, {"message": message}))
        except OSError:
            self._disconnect(conn)
