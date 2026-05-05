# UNO Game Package

This folder contains the actual game implementation. The project is organized for a host-authoritative online UNO game where clients send player intents and the host validates rules, updates game state, and broadcasts synchronized state.

## Run The Pygame Game

From this `uno_game/` folder:

```bash
python main.py
```

The pygame app includes local hotseat, bot games, relay-hosted room codes, and room-code join.
Use the Settings page from the main menu to toggle sound, adjust volume, enable/disable placeholder background art, show/hide missing-card labels, and switch fullscreen.

Install dependency if needed:

```bash
pip install -r requirements.txt
```

Run verification:

```bash
python run_tests.py
```

## CLI Network Tools

Private relay room-code play:

```bash
python main.py relay --host 0.0.0.0 --port 5051
```

Run the relay on a neutral/server machine. Hosts and players connect to the relay and use only a room code; players do not connect directly to the host machine, so the host IP is not shared peer-to-peer.

## Architecture

- `config/`: constants, settings, enums
- `core/`: app shell, event bus, state manager, game loop
- `domain/`: pure game entities, value objects, state, and deck factory
- `rules/`: host-side move validation and card effect resolvers
- `systems/`: gameplay systems such as turn order, draw, reaction, setup, and win handling
- `application/`: command objects, handlers, and DTOs for local or networked play
- `infrastructure/`: local controller, relay client/server, serialization, replay logging
- `presentation/`: pygame-only scenes, UI components, input, and rendering
- `assets/`: images, fonts, and sounds
- `utils/`: small shared helpers

## Online Model

The host is the single source of truth. Clients never mutate game state directly.

Client flow:

1. Connect to the relay server and create or join a room code.
2. Send commands such as `PLAY_CARD`, `DRAW_CARD`, or `REACTION`.
3. Receive `GAME_STATE` messages and render the latest state.

Relay/host flow:

1. The relay accepts clients and assigns room/player IDs.
2. The first player in a room is the host and may start the game or lock the lobby.
3. The relay validates every incoming command with the same host-authoritative rule engine.
4. The relay applies rules and broadcasts per-player state.

## Card Assets

Card rendering uses `presentation/rendering/card_asset_manager.py`.

It looks for images in:

- `assets/images/cards/`
- `assets/images/`

If an image is missing, `CardRenderer` uses `assets/images/placeholder.jfif` and overlays readable card text where needed.

See `assets/README.md` for every supported and optional asset filename.

## Presentation Scenes

The pygame app delegates lifecycle work to scene classes:

- `presentation/scenes/menu_scene.py`: main mode selection
- `presentation/scenes/lobby_scene.py`: relay room creation and room-code join forms
- `presentation/scenes/settings_scene.py`: sound, volume, display, and visual helper settings
- `presentation/scenes/game_scene.py`: active table, hand, draw/play/react controls
- `presentation/scenes/end_scene.py`: endgame overlay flow

## Playable-Ready Coverage

- Host-authoritative validation for card plays, draw penalties, reactions, and turn order.
- Online host ownership: only the host can start the game.
- Late joins and full rooms are rejected by the host.
- Disconnected players are skipped; the last connected player wins.
- Local hotseat supports 2, 3, or 4 players.
- Illegal cards are dimmed in the hand before the player clicks them.
- Optional sounds load from `assets/sounds`; missing sounds are safe no-ops.
- User settings are saved to `config/user_settings.json`.
