import threading
import time
import unittest
import socket

import main
from infrastructure.network.client import GameClient
from infrastructure.network.relay_server import RelayServer


class NetworkTests(unittest.TestCase):
    def test_only_host_can_start_game(self) -> None:
        server = RelayServer(host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        while server.port == 0:
            time.sleep(0.01)

        errors: list[str] = []
        room_codes: list[str] = []
        host = GameClient(lambda message: room_codes.append(str(message.payload["room_code"])) if message.type.value == "ROOM_CREATED" else None)
        guest = GameClient(lambda message: errors.append(str(message.payload.get("message", ""))) if message.type.value == "ERROR" else None)
        try:
            host.connect_to_server("127.0.0.1", server.port)
            host.create_room("Host")
            time.sleep(0.2)
            guest.connect_to_server("127.0.0.1", server.port)
            guest.join_room(room_codes[-1], "Guest")
            time.sleep(0.2)
            guest.start_game()
            time.sleep(0.2)
            self.assertTrue(any("Only the host" in error for error in errors))
        finally:
            host.disconnect()
            guest.disconnect()
            server.stop()

    def test_host_lobby_lock_rejects_new_players(self) -> None:
        server = RelayServer(host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        while server.port == 0:
            time.sleep(0.01)

        errors: list[str] = []
        room_codes: list[str] = []
        host = GameClient()
        host.on_message = lambda message: room_codes.append(str(message.payload["room_code"])) if message.type.value == "ROOM_CREATED" else None
        guest = GameClient(lambda message: errors.append(str(message.payload.get("message", ""))) if message.type.value == "ERROR" else None)
        try:
            host.connect_to_server("127.0.0.1", server.port)
            host.create_room("Host")
            time.sleep(0.2)
            host.host_settings(lobby_locked=True)
            time.sleep(0.2)
            guest.connect_to_server("127.0.0.1", server.port)
            guest.join_room(room_codes[-1], "Guest")
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

    def test_stop_relay_command_stops_listener(self) -> None:
        relay = RelayServer(host="127.0.0.1", port=0)
        thread = threading.Thread(target=relay.start, daemon=True)
        thread.start()
        while relay.port == 0:
            time.sleep(0.01)

        main._stop_relay({"host": "127.0.0.1", "port": str(relay.port)})
        time.sleep(0.2)
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", relay.port), timeout=0.2)

    def test_relay_numbers_default_names_by_join_order(self) -> None:
        relay = RelayServer(host="127.0.0.1", port=0)
        thread = threading.Thread(target=relay.start, daemon=True)
        thread.start()
        while relay.port == 0:
            time.sleep(0.01)

        room_codes: list[str] = []
        guest_states: list[dict] = []
        host = GameClient(lambda message: room_codes.append(str(message.payload["room_code"])) if message.type.value == "ROOM_CREATED" else None)
        guest = GameClient(lambda message: guest_states.append(message.payload) if message.type.value == "GAME_STATE" else None)
        try:
            host.connect_to_server("127.0.0.1", relay.port)
            host.create_room("Host")
            time.sleep(0.2)
            guest.connect_to_server("127.0.0.1", relay.port)
            guest.join_room(room_codes[-1], "Player")
            time.sleep(0.2)

            names = [player["name"] for player in guest_states[-1]["players"]]
            self.assertEqual(names, ["Player 1", "Player 2"])
        finally:
            host.disconnect()
            guest.disconnect()
            relay.stop()

    def test_relay_preserves_custom_player_names(self) -> None:
        relay = RelayServer(host="127.0.0.1", port=0)
        thread = threading.Thread(target=relay.start, daemon=True)
        thread.start()
        while relay.port == 0:
            time.sleep(0.01)

        room_codes: list[str] = []
        guest_states: list[dict] = []
        host = GameClient(lambda message: room_codes.append(str(message.payload["room_code"])) if message.type.value == "ROOM_CREATED" else None)
        guest = GameClient(lambda message: guest_states.append(message.payload) if message.type.value == "GAME_STATE" else None)
        try:
            host.connect_to_server("127.0.0.1", relay.port)
            host.create_room("Alice")
            time.sleep(0.2)
            guest.connect_to_server("127.0.0.1", relay.port)
            guest.join_room(room_codes[-1], "Bob")
            time.sleep(0.2)

            names = [player["name"] for player in guest_states[-1]["players"]]
            self.assertEqual(names, ["Alice", "Bob"])
        finally:
            host.disconnect()
            guest.disconnect()
            relay.stop()

    def test_relay_reports_room_is_full(self) -> None:
        relay = RelayServer(host="127.0.0.1", port=0)
        thread = threading.Thread(target=relay.start, daemon=True)
        thread.start()
        while relay.port == 0:
            time.sleep(0.01)

        room_codes: list[str] = []
        errors: list[str] = []
        host = GameClient(lambda message: room_codes.append(str(message.payload["room_code"])) if message.type.value == "ROOM_CREATED" else None)
        guest = GameClient()
        extra = GameClient(lambda message: errors.append(str(message.payload.get("message", ""))) if message.type.value == "ERROR" else None)
        try:
            host.connect_to_server("127.0.0.1", relay.port)
            host.create_room("Host")
            time.sleep(0.2)
            host.host_settings(max_players=2)
            guest.connect_to_server("127.0.0.1", relay.port)
            guest.join_room(room_codes[-1], "Player")
            time.sleep(0.2)
            extra.connect_to_server("127.0.0.1", relay.port)
            extra.join_room(room_codes[-1], "Player")
            time.sleep(0.2)

            self.assertIn("room is full", errors)
        finally:
            host.disconnect()
            guest.disconnect()
            extra.disconnect()
            relay.stop()

    def test_relay_removes_lobby_player_and_reuses_default_slot(self) -> None:
        relay = RelayServer(host="127.0.0.1", port=0)
        thread = threading.Thread(target=relay.start, daemon=True)
        thread.start()
        while relay.port == 0:
            time.sleep(0.01)

        room_codes: list[str] = []
        host_states: list[dict] = []
        host = GameClient(
            lambda message: room_codes.append(str(message.payload["room_code"]))
            if message.type.value == "ROOM_CREATED"
            else host_states.append(message.payload)
            if message.type.value == "GAME_STATE"
            else None
        )
        first_guest = GameClient()
        second_guest = GameClient()
        try:
            host.connect_to_server("127.0.0.1", relay.port)
            host.create_room("Host")
            time.sleep(0.2)
            first_guest.connect_to_server("127.0.0.1", relay.port)
            first_guest.join_room(room_codes[-1], "Player")
            time.sleep(0.2)
            first_guest.disconnect()
            time.sleep(0.2)
            second_guest.connect_to_server("127.0.0.1", relay.port)
            second_guest.join_room(room_codes[-1], "Player")
            time.sleep(0.2)

            names = [player["name"] for player in host_states[-1]["players"]]
            self.assertEqual(names, ["Player 1", "Player 2"])
        finally:
            host.disconnect()
            first_guest.disconnect()
            second_guest.disconnect()
            relay.stop()


if __name__ == "__main__":
    unittest.main()
