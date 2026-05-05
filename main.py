from pathlib import Path
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uno_game.config.constants import DEFAULT_DISCOVERY_PORT, DEFAULT_GAME_PORT
from uno_game.infrastructure.network.client import GameClient
from uno_game.infrastructure.network.discovery_client import DiscoveryClient
from uno_game.infrastructure.network.discovery_server import DiscoveryServer
from uno_game.infrastructure.network.host_server import HostServer
from uno_game.infrastructure.network.protocol import MessageType
from uno_game.presentation.pygame_app import PygameUnoApp


def main() -> None:
    args = sys.argv[1:]
    if not args:
        PygameUnoApp().run()
        return
    mode = args[0]
    options = _parse_options(args[1:])
    if mode == "discovery":
        _run_discovery(options)
    elif mode == "host":
        _run_host(options)
    elif mode == "client":
        _run_client(options)
    else:
        raise SystemExit(f"Unknown mode: {mode}")


def _run_discovery(options: dict[str, str]) -> None:
    server = DiscoveryServer(
        host=options.get("host", "0.0.0.0"),
        port=int(options.get("port", DEFAULT_DISCOVERY_PORT)),
        on_log=print,
    )
    server.start()


def _run_host(options: dict[str, str]) -> None:
    port = int(options.get("port", DEFAULT_GAME_PORT))
    server = HostServer(host=options.get("host", "0.0.0.0"), port=port, on_log=print)
    discovery_host = options.get("discovery-host")
    if discovery_host:
        code = DiscoveryClient(discovery_host, int(options.get("discovery-port", DEFAULT_DISCOVERY_PORT))).create_room(
            game_port=port,
            public_host=options.get("public-host"),
        )
        print(f"Room code: {code}")
    server.start()


def _run_client(options: dict[str, str]) -> None:
    def on_message(message) -> None:
        if message.type == MessageType.GAME_STATE:
            state = message.payload
            current = state.get("current_player_id")
            phase = state.get("phase")
            hand = next((player.get("hand", []) for player in state.get("players", []) if player.get("id") == client.player_id), [])
            print(f"state phase={phase} current={current} hand={[card['id'] for card in hand]}")
        elif message.type == MessageType.ERROR:
            print(f"error: {message.payload.get('message')}")
        else:
            print(f"{message.type.value}: {message.payload}")

    if "room-code" in options:
        host, port = DiscoveryClient(
            options.get("discovery-host", "127.0.0.1"),
            int(options.get("discovery-port", DEFAULT_DISCOVERY_PORT)),
        ).join_room(options["room-code"])
    else:
        host = options.get("host", "127.0.0.1")
        port = int(options.get("port", DEFAULT_GAME_PORT))

    client = GameClient(on_message)
    client.connect(host, port, options.get("name", "Player"))
    print("Commands: start | draw [count] | pass | play <card_id> [color] [target_player_id] [pass_direction] | react | quit")
    while True:
        raw = input("> ").strip()
        if raw in {"quit", "exit"}:
            client.disconnect()
            return
        parts = raw.split()
        if not parts:
            continue
        if parts[0] == "start":
            client.start_game()
        elif parts[0] == "draw":
            client.draw_card(int(parts[1]) if len(parts) > 1 else 1)
        elif parts[0] == "pass":
            client.pass_turn()
        elif parts[0] == "react":
            client.react()
        elif parts[0] == "play" and len(parts) >= 2:
            client.play_card(
                parts[1],
                parts[2] if len(parts) > 2 else None,
                parts[3] if len(parts) > 3 else None,
                parts[4] if len(parts) > 4 else None,
            )
        else:
            print("Unknown command")


def _parse_options(args: list[str]) -> dict[str, str]:
    options: dict[str, str] = {}
    index = 0
    while index < len(args):
        key = args[index]
        if not key.startswith("--") or index + 1 >= len(args):
            raise SystemExit(f"Expected --key value near: {key}")
        options[key[2:]] = args[index + 1]
        index += 2
    return options


if __name__ == "__main__":
    main()
