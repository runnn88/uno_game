from __future__ import annotations

import argparse

from config.constants import DEFAULT_DISCOVERY_PORT
from infrastructure.network.relay_server import RelayServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the UNO authoritative relay server.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address. Use 0.0.0.0 for a public/server relay.")
    parser.add_argument("--port", type=int, default=DEFAULT_DISCOVERY_PORT, help="TCP port for relay clients.")
    args = parser.parse_args()

    server = RelayServer(host=args.host, port=args.port)
    print(f"UNO relay server listening on {args.host}:{args.port}")
    server.start()


if __name__ == "__main__":
    main()
