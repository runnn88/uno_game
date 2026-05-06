from __future__ import annotations

import argparse

from config.constants import DEFAULT_DISCOVERY_PORT
from infrastructure.network.client import GameClient
from infrastructure.network.protocol import MessageType


def main() -> None:
    parser = argparse.ArgumentParser(description="Connect to a UNO relay server from the terminal.")
    parser.add_argument("--host", default="127.0.0.1", help="Relay host.")
    parser.add_argument("--port", type=int, default=DEFAULT_DISCOVERY_PORT, help="Relay port.")
    parser.add_argument("--name", default="Player", help="Player display name.")
    parser.add_argument("--create", action="store_true", help="Create a relay room.")
    parser.add_argument("--room-code", help="Join an existing relay room.")
    args = parser.parse_args()

    client = GameClient(_print_message)
    client.connect_to_server(args.host, args.port)
    if args.create:
        client.create_room(args.name)
    elif args.room_code:
        client.join_room(args.room_code, args.name)
    else:
        raise SystemExit("Use --create to host or --room-code CODE to join.")

    print("Commands: start | draw | pass | uno | react | play <card_id> [color] [target] [pass_direction] | quit")
    while True:
        raw = input("> ").strip()
        if raw in {"quit", "exit"}:
            client.disconnect()
            return
        parts = raw.split()
        if not parts:
            continue
        _handle_command(client, parts)


def _handle_command(client: GameClient, parts: list[str]) -> None:
    command = parts[0].lower()
    if command == "start":
        client.start_game()
    elif command == "draw":
        client.draw_card()
    elif command == "pass":
        client.pass_turn()
    elif command == "uno":
        client.call_uno()
    elif command == "react":
        client.react()
    elif command == "play" and len(parts) >= 2:
        client.play_card(
            parts[1],
            parts[2] if len(parts) > 2 else None,
            parts[3] if len(parts) > 3 else None,
            parts[4] if len(parts) > 4 else None,
        )
    else:
        print("Unknown command")


def _print_message(message) -> None:
    if message.type == MessageType.GAME_STATE:
        state = message.payload
        players = ", ".join(f"{player.get('name')}:{player.get('card_count')}" for player in state.get("players", []))
        print(f"state phase={state.get('phase')} turn={state.get('current_player_id')} players=[{players}]")
    elif message.type == MessageType.ERROR:
        print(f"error: {message.payload.get('message')}")
    else:
        print(f"{message.type.value}: {message.payload}")


if __name__ == "__main__":
    main()
