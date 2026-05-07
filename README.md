# UNO Game Package

This folder contains the playable UNO implementation. The game is built around a fixed, server-authoritative relay: players only run the game, host or join from the UI, and share room codes. Players should not need to know any IP address, port, tunnel URL, or server URL.

## Commands

Run the game:

```bash
python main.py
```

Run the fixed relay server:

```bash
python main.py relay --host 0.0.0.0 --port 5051
```

Stop a relay server running on this machine:

```bash
python main.py stop-relay --host 127.0.0.1 --port 5051
```

## Player Flow

Start the game with the game command above.

To host an online room, choose **Host Online Room** in the game. The relay creates the room and returns a room code. Use the copy button and send that room code to the other players.

To join an online room, choose **Join Room Code** in the game and paste the room code. The game connects to the configured fixed relay server automatically.

Local hotseat, bot games, online hosting, online joining, settings, and instructions are all handled inside the pygame UI.

## Game Rules

- Match the discard pile by color or rank. Wild cards can be played on any color.
- Click a playable card to choose it, then press the right-side Play button or press `P`.
- If playing the chosen card would leave you with one card, the Play button becomes UNO and the game calls UNO after the card is played.
- If you cannot play, draw a card. If the drawn card is legal, you may play it; otherwise pass.
- Press `U` to call UNO for yourself when you have one card, or to catch another player with one unprotected card.
- Draw penalties can be stacked with `+2` or `Wild +4`, but the new card must have equal or higher penalty value. If you cannot stack, draw the full pending penalty.
- `0`: choose clockwise or counter-clockwise, then everyone passes hands in that direction.
- `7`: choose another player and swap hands with them. A final `7` is legal, but if you swap your empty hand away, the player who receives zero cards wins.
- `8`: starts a reaction round. Players press React; the last responder, or anyone who misses the timer, draws the reaction penalty.
- `Skip`: the next player loses their turn.
- `Reverse`: changes turn direction with three or more connected players. With exactly two connected players, it acts like Skip.
- `+2`: adds two cards to the pending draw penalty.
- `Wild`: choose the active color.
- `Wild +4`: choose the active color and add four cards to the pending draw penalty.
- Number cards can finish the game. Final action cards are blocked except for the custom final-`7` swap rule above.

## Fixed Relay Configuration

The relay endpoint is configured by `UNO_RELAY_URL` in `.env`. This is deployment configuration, not player input.

For local testing, `.env.example` points at `tcp://127.0.0.1:5051`. For real online play, change the value once to your stable relay server, such as an Azure VM DNS name or static public IP. Everyone who runs the game should use the same configured relay endpoint.

The UI intentionally shows only room codes. The operating system, network stack, and relay server handle the actual connection details.

## Online Model

The relay server is the source of truth. Clients never mutate official game state directly.

Client flow:

- Connect to the configured relay server.
- Create or join a room code.
- Send commands such as `PLAY_CARD`, `DRAW_CARD`, `START_GAME`, `PASS_TURN`, and `REACTION`.
- Receive full authoritative game-state snapshots and render them.

Server flow:

- Accept clients and assign connection/player IDs.
- Create rooms and validate room-code joins.
- Treat the first player as the room owner for lobby permissions.
- Validate every gameplay command with the rule engine.
- Apply card effects, turn changes, reactions, stacking, swaps, and win checks.
- Broadcast per-player state snapshots after changes.

## Architecture

- `config/`: constants, environment loading, settings, enums
- `core/`: app shell, event bus, state manager, game loop
- `domain/`: pure game entities, value objects, state, and deck factory
- `rules/`: server-side move validation and card effect resolvers
- `systems/`: gameplay systems such as turn order, draw, reaction, setup, and win handling
- `application/`: command objects, handlers, and DTOs for local or networked play
- `infrastructure/network/`: fixed relay server, game client, protocol, and serialization
- `infrastructure/persistence/`: replay logging support
- `presentation/`: pygame-only scenes, UI components, input, rendering, animations, and feedback
- `assets/`: images, fonts, and sounds
- `utils/`: small shared helpers

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
- `presentation/scenes/instructions_scene.py`: how-to-play and card meaning guide
- `presentation/scenes/lobby_scene.py`: room-code host/join forms
- `presentation/scenes/settings_scene.py`: sound, volume, display, and visual helper settings
- `presentation/scenes/game_scene.py`: active table, hand, draw/play/react controls
- `presentation/scenes/end_scene.py`: endgame overlay flow

## Playable-Ready Coverage

- Server-authoritative validation for card plays, draw penalties, reactions, and turn order.
- Online room ownership: only the room owner can start the game.
- Late joins and full rooms are rejected by the server.
- Disconnected players are skipped; the last connected player wins.
- Local hotseat supports 2, 3, or 4 players.
- Bot modes are available from the main menu.
- Illegal cards are dimmed in the hand before the player clicks them.
- Smooth UI feedback, fast transitions, and animated card movement.
- Optional sounds load from `assets/sounds`; missing sounds are safe no-ops.
- User settings are saved to `config/user_settings.json`.
