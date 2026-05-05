import threading
import time
import unittest

from infrastructure.network.client import GameClient
from infrastructure.network.host_server import HostServer
from infrastructure.network.relay_server import RelayServer


class NetworkTests(unittest.TestCase):
    def test_only_host_can_start_game(self) -> None:
        server = HostServer(host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        while server.port == 0:
            time.sleep(0.01)

        errors: list[str] = []
        host = GameClient()
        guest = GameClient(lambda message: errors.append(str(message.payload.get("message", ""))) if message.type.value == "ERROR" else None)
        try:
            host.connect("127.0.0.1", server.port, "Host")
            guest.connect("127.0.0.1", server.port, "Guest")
            time.sleep(0.2)
            guest.start_game()
            time.sleep(0.2)
            self.assertTrue(any("Only the host" in error for error in errors))
        finally:
            host.disconnect()
            guest.disconnect()
            server.stop()

    def test_host_lobby_lock_rejects_new_players(self) -> None:
        server = HostServer(host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        while server.port == 0:
            time.sleep(0.01)

        errors: list[str] = []
        host = GameClient()
        guest = GameClient(lambda message: errors.append(str(message.payload.get("message", ""))) if message.type.value == "ERROR" else None)
        try:
            host.connect("127.0.0.1", server.port, "Host")
            time.sleep(0.1)
            server.configure_lobby(lobby_locked=True)
            guest.connect("127.0.0.1", server.port, "Guest")
            time.sleep(0.2)
            self.assertTrue(any("locked" in error for error in errors))
        finally:
            host.disconnect()
            guest.disconnect()
            server.stop()

    def test_relay_room_code_join_uses_relay_server(self) -> None:
        relay = RelayServer(host="127.0.0.1", port=0)
        thread = threading.Thread(target=relay.start, daemon=True)
        thread.start()
        while relay.port == 0:
            time.sleep(0.01)

        room_codes: list[str] = []
        host_states: list[dict] = []
        guest_states: list[dict] = []
        host = GameClient(lambda message: room_codes.append(str(message.payload["room_code"])) if message.type.value == "ROOM_CREATED" else host_states.append(message.payload) if message.type.value == "GAME_STATE" else None)
        guest = GameClient(lambda message: guest_states.append(message.payload) if message.type.value == "GAME_STATE" else None)
        try:
            host.connect_to_server("127.0.0.1", relay.port)
            host.create_room("Host")
            time.sleep(0.2)
            self.assertTrue(room_codes)
            guest.connect_to_server("127.0.0.1", relay.port)
            guest.join_room(room_codes[-1], "Guest")
            time.sleep(0.2)
            self.assertEqual(guest_states[-1].get("room_code"), room_codes[-1])
            host.start_game()
            time.sleep(0.2)
            self.assertEqual(host_states[-1].get("phase"), "playing")
            self.assertEqual(guest_states[-1].get("phase"), "playing")
        finally:
            host.disconnect()
            guest.disconnect()
            relay.stop()


if __name__ == "__main__":
    unittest.main()
