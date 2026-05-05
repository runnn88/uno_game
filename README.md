# UNO Game Package

This folder contains the actual game implementation. The project is organized for a host-authoritative online UNO game where clients send player intents and the host validates rules, updates game state, and broadcasts synchronized state.

## Run The Pygame Game

From this `uno_game/` folder:

```bash
python main.py
```

The pygame app includes local hotseat, host online, host room code, direct join, and room-code join.
Use the Settings page from the main menu to toggle sound, adjust volume, enable/disable placeholder background art, show/hide missing-card labels, and switch fullscreen.

Install dependency if needed:

```bash
pip install -r requirements.txt
```

Run verification:

```bash
python run_tests.py
```

Or, from the parent `Assignment4/` folder:

```bash
python -m uno_game.main
```

## CLI Network Tools

Start a local host without the pygame UI:

```bash
python main.py host --host 127.0.0.1 --port 5050
```

Connect clients:

```bash
python main.py client --host 127.0.0.1 --port 5050 --name Alice
python main.py client --host 127.0.0.1 --port 5050 --name Bob
```

Room-code discovery:

```bash
python main.py discovery --host 127.0.0.1 --port 5051
python main.py host --host 127.0.0.1 --port 5050 --discovery-host 127.0.0.1
python main.py client --room-code ABC12 --discovery-host 127.0.0.1 --name Alice
```

## Architecture

- `config/`: constants, settings, enums
- `core/`: app shell, event bus, state manager, game loop
- `domain/`: pure game entities, value objects, state, and deck factory
- `rules/`: host-side move validation and card effect resolvers
- `systems/`: gameplay systems such as turn order, draw, reaction, setup, and win handling
- `application/`: command objects, handlers, and DTOs for local or networked play
- `infrastructure/`: local controller, TCP host/client, discovery, serialization, replay logging
- `presentation/`: pygame-only scenes, UI components, input, and rendering
- `assets/`: images, fonts, and sounds
- `utils/`: small shared helpers

## Online Model

The host is the single source of truth. Clients never mutate game state directly.

Client flow:

1. Connect to host directly or resolve a room code through discovery.
2. Send commands such as `PLAY_CARD`, `DRAW_CARD`, or `REACTION`.
3. Receive `GAME_STATE` messages and render the latest state.

Host flow:

1. Accept clients and assign player IDs.
2. Start the game, shuffle, and deal hands.
3. Validate every incoming command.
4. Apply rules and broadcast per-player state.

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
- `presentation/scenes/lobby_scene.py`: direct and room-code join forms
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
