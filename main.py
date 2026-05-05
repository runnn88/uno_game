from pathlib import Path
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.constants import DEFAULT_DISCOVERY_PORT
from infrastructure.network.client import GameClient
from infrastructure.network.protocol import MessageType
from infrastructure.network.relay_server import RelayServer
from presentation.pygame_app import PygameUnoApp


def main() -> None:
    args = sys.argv[1:]
    if not args:
        PygameUnoApp().run()
        return
    mode = args[0]
    options = _parse_options(args[1:])
    if mode == "relay":
        _run_relay(options)
    elif mode == "client":
        _run_client(options)
    else:
        raise SystemExit(f"Unknown mode: {mode}")


def _run_relay(options: dict[str, str]) -> None:
    server = RelayServer(host=options.get("host", "0.0.0.0"), port=int(options.get("port", DEFAULT_DISCOVERY_PORT)))
    print(f"Relay server listening on {server.host}:{server.port}")
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

    relay_host = options.get("relay-host", options.get("host", "127.0.0.1"))
    relay_port = int(options.get("relay-port", options.get("port", DEFAULT_DISCOVERY_PORT)))
    client = GameClient(on_message)
    client.connect_to_server(relay_host, relay_port)
    if "create" in options:
        client.create_room(options.get("name", "Host"))
    elif "room-code" in options:
        client.join_room(options["room-code"], options.get("name", "Player"))
    else:
        raise SystemExit("Use --create yes to host or --room-code CODE to join through the relay")
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
