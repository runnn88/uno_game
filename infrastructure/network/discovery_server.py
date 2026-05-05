import secrets
import socket
import string
import threading
from collections.abc import Callable

from uno_game.config.constants import DEFAULT_DISCOVERY_PORT, ROOM_CODE_LENGTH
from uno_game.infrastructure.network.protocol import MessageType, NetworkMessage
from uno_game.infrastructure.network.serializer import receive_message, send_message


class DiscoveryServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = DEFAULT_DISCOVERY_PORT,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.on_log = on_log or (lambda message: None)
        self.rooms: dict[str, tuple[str, int]] = {}
        self._server_socket: socket.socket | None = None
        self._running = False

    def start(self) -> None:
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self.port = self._server_socket.getsockname()[1]
        self._server_socket.listen()
        self._running = True
        self.on_log(f"Discovery server listening on {self.host}:{self.port}")
        while self._running:
            try:
                conn, addr = self._server_socket.accept()
            except OSError:
                if self._running:
                    raise
                break
            threading.Thread(target=self._handle_client, args=(conn, addr[0]), daemon=True).start()

    def stop(self) -> None:
        self._running = False
        if self._server_socket is not None:
            self._server_socket.close()

    def _handle_client(self, conn: socket.socket, peer_ip: str) -> None:
        file_obj = conn.makefile("rb")
        try:
            message = receive_message(file_obj)
            if message is not None:
                self._process(conn, peer_ip, message)
        finally:
            conn.close()

    def _process(self, conn: socket.socket, peer_ip: str, message: NetworkMessage) -> None:
        if message.type == MessageType.CREATE_ROOM:
            host = message.payload.get("host") or peer_ip
            port = int(message.payload["port"])
            code = self._new_code()
            self.rooms[code] = (host, port)
            send_message(conn, NetworkMessage.of(MessageType.ROOM_CREATED, {"room_code": code}))
        elif message.type == MessageType.JOIN_ROOM:
            code = str(message.payload["room_code"]).upper()
            endpoint = self.rooms.get(code)
            if endpoint is None:
                send_message(conn, NetworkMessage.of(MessageType.ROOM_NOT_FOUND, {"room_code": code}))
                return
            host, port = endpoint
            send_message(conn, NetworkMessage.of(MessageType.ROOM_FOUND, {"room_code": code, "host": host, "port": port}))
        else:
            send_message(conn, NetworkMessage.of(MessageType.ERROR, {"message": "Unsupported discovery message"}))

    def _new_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(ROOM_CODE_LENGTH))
            if code not in self.rooms:
                return code
