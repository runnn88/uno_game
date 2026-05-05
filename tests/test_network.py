import threading
import time
import unittest

from uno_game.infrastructure.network.client import GameClient
from uno_game.infrastructure.network.host_server import HostServer


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


if __name__ == "__main__":
    unittest.main()

