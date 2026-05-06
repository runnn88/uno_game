import pygame

from presentation.theme import ACCENT, ACCENT_2, BAD, GOOD, MUTED, PANEL, PANEL_2, TEXT
from presentation.ui.components.settings_row import SettingsRow


# def draw_menu(app) -> None:
#     assert app.screen is not None
#     app.buttons.clear()
#     app.input_boxes.clear()
#     app._draw_title("UNO Online")

#     hero = pygame.Rect(76, 124, 430, 500)
#     menu = pygame.Rect(548, 124, 656, 500)
#     app._draw_panel(hero, (251, 248, 236))
#     app._draw_panel(menu, PANEL)

#     app._draw_text("Fast local play", 116, 170, TEXT, size="big")
#     app._draw_text("or relay-hosted rooms", 118, 218, MUTED)
#     app._draw_chip("Hotseat", 118, 274, ACCENT_2)
#     app._draw_chip("Bots", 230, 274, GOOD)
#     app._draw_chip("Room Code", 315, 274, ACCENT)
#     app._draw_menu_cards()
#     app._draw_text("Match color or rank, stack draw cards, and use special 0/7/8 rules.", 118, 560, MUTED, size="small")

#     app._draw_text("Choose Mode", 602, 168, TEXT, size="big")
#     app._draw_text("Local games start immediately. Relay games need the relay server running.", 604, 214, MUTED)
#     x = 604
#     y = 258
#     app._add_button(x, y, 126, 48, "2P Local", "local", 2)
#     app._add_button(x + 138, y, 126, 48, "3P Local", "local", 3)
#     app._add_button(x + 276, y, 126, 48, "4P Local", "local", 4)
#     app._add_button(x, y + 64, 195, 48, "1P + Bot", "local", (2, 1))
#     app._add_button(x + 207, y + 64, 195, 48, "1P + 3 Bots", "local", (4, 3))
#     app._add_button(x, y + 146, 402, 50, "Host Relay Room", "host_room")
#     app._add_button(x, y + 208, 402, 50, "Join Relay Code", "join_room")
#     app._add_button(x, y + 286, 195, 48, "Instructions", "instructions")
#     app._add_button(x + 207, y + 286, 195, 48, "Settings", "settings")
#     app._draw_text("Online play uses a relay room code. Players never connect directly to the host.", 640, 676, MUTED, center=True, size="small")
#     if app.notice:
#         app._draw_text(app.notice, 640, 696, BAD, center=True)
#     if not app.notice_overlay:
#         app._draw_buttons()
#     app._draw_notice_overlay()
def draw_menu(app) -> None:
    assert app.screen is not None
    app.buttons.clear()
    app.input_boxes.clear()
    app._draw_title("UNO Online")

    hero = pygame.Rect(76, 124, 430, 500)
    menu = pygame.Rect(548, 124, 656, 500)
    app._draw_panel(hero, (251, 248, 236))
    app._draw_panel(menu, PANEL)

    app._draw_text("Fast local play", 116, 170, TEXT, size="big")
    app._draw_text("or relay-hosted rooms", 118, 218, MUTED)
    app._draw_chip("Hotseat", 118, 274, ACCENT_2)
    app._draw_chip("Bots", 230, 274, GOOD)
    app._draw_chip("Room Code", 315, 274, ACCENT)
    app._draw_menu_cards()
    app._draw_text("Match color or rank, stack draw cards, and use special 0/7/8 rules.", 118, 560, MUTED, size="small")

    app._draw_text("Main Menu", 602, 168, TEXT, size="big")
    app._draw_text("Choose what you want to do next.", 604, 214, MUTED)
    x = 604
    y = 258
    app._add_button(x, y, 402, 50, "Play", "choose_mode")
    app._add_button(x, y + 64, 402, 50, "Settings", "settings")
    app._add_button(x, y + 128, 402, 50, "Instructions", "instructions")

    if app.notice:
        app._draw_text(app.notice, 640, 676, BAD, center=True)
    if not app.notice_overlay:
        app._draw_buttons()
    app._draw_notice_overlay()


def draw_choose_mode(app) -> None:
    assert app.screen is not None
    app.buttons.clear()
    app.input_boxes.clear()
    app._draw_title("UNO Online")

    hero = pygame.Rect(76, 124, 430, 500)
    menu = pygame.Rect(548, 124, 656, 500)
    app._draw_panel(hero, (251, 248, 236))
    app._draw_panel(menu, PANEL)

    app._draw_text("Fast local play", 116, 170, TEXT, size="big")
    app._draw_text("or relay-hosted rooms", 118, 218, MUTED)
    app._draw_chip("Hotseat", 118, 274, ACCENT_2)
    app._draw_chip("Bots", 230, 274, GOOD)
    app._draw_chip("Room Code", 315, 274, ACCENT)
    app._draw_menu_cards()
    app._draw_text("Match color or rank, stack draw cards, and use special 0/7/8 rules.", 118, 560, MUTED, size="small")

    app._draw_text("Choose Mode", 602, 168, TEXT, size="big")
    app._draw_text("Local games start immediately. Relay games need the relay server running.", 604, 214, MUTED)
    x = 604
    y = 258
    app._add_button(x, y, 126, 48, "2P Local", "local", 2)
    app._add_button(x + 138, y, 126, 48, "3P Local", "local", 3)
    app._add_button(x + 276, y, 126, 48, "4P Local", "local", 4)
    app._add_button(x, y + 64, 195, 48, "1P + Bot", "local", (2, 1))
    app._add_button(x + 207, y + 64, 195, 48, "1P + 3 Bots", "local", (4, 3))
    app._add_button(x, y + 146, 402, 50, "Host Relay Room", "host_room")
    app._add_button(x, y + 208, 402, 50, "Join Relay Code", "join_room")
    app._add_button(x, y + 286, 195, 48, "Instructions", "instructions")
    app._add_button(x + 207, y + 286, 195, 48, "Settings", "settings")
    app._draw_text("Online play uses a relay room code. Players never connect directly to the host.", 640, 676, MUTED, center=True, size="small")
    if app.notice:
        app._draw_text(app.notice, 640, 696, BAD, center=True)
    if not app.notice_overlay:
        app._draw_buttons()
    app._draw_notice_overlay()


def draw_instructions(app) -> None:
    assert app.screen is not None
    app.buttons.clear()
    app.input_boxes.clear()
    app._draw_title("Instructions")
    app._add_button(28, 22, 92, 34, "Back", "menu")

    app._draw_panel(pygame.Rect(76, 216, 546, 408), PANEL)
    app._draw_panel(pygame.Rect(658, 216, 546, 408), PANEL_2)

    app._draw_chip("Flow", 116, 248, ACCENT_2)
    app._draw_text("How To Play", 116, 288, TEXT, size="big")
    rules = [
        "Match the discard pile by color or rank. Wild cards can be played on any color.",
        "Click a playable card in your hand. Dimmed cards are not legal for the current turn.",
        "If you cannot play, click Draw. After drawing, play the drawn card if it is legal or click Pass.",
        "When a draw penalty is active, you must stack a +2 or +4 with equal or higher value, otherwise draw the penalty.",
        "First player with no cards wins. Action cards cannot be played as your final card.",
    ]
    app._draw_wrapped_lines(rules, 116, 340, 460, 26, TEXT, size="small")

    app._draw_chip("Cards", 698, 248, ACCENT)
    app._draw_text("Card Meanings", 698, 288, TEXT, size="big")
    cards = [
        "0: choose clockwise or counter-clockwise, then all players pass hands in that direction.",
        "7: choose another player and swap hands with them.",
        "8: starts a reaction round. Players hit React; the last or missing responder is punished.",
        "Skip: the next player loses their turn.",
        "Reverse: changes the turn direction.",
        "+2: adds two cards to the pending draw penalty.",
        "Wild: choose the active color.",
        "Wild +4: choose the active color and adds four cards to the pending draw penalty.",
    ]
    app._draw_wrapped_lines(cards, 698, 340, 464, 24, TEXT, size="small")
    app._draw_buttons()


def draw_settings(app) -> None:
    assert app.screen is not None
    app.buttons.clear()
    app.input_boxes.clear()
    app._draw_background("menu_background")
    app._draw_title("Settings")

    # Main settings panel drawn as semi-transparent surface (30% black)
    settings_panel = pygame.Rect(320, 200, 640, 400)
    panel_surf = pygame.Surface((settings_panel.width, settings_panel.height), pygame.SRCALPHA)
    panel_surf.fill((0, 0, 0, 76))  # 30% opaque black
    app.screen.blit(panel_surf, settings_panel.topleft)
    
    pygame.draw.rect(app.screen, (50, 50, 50), settings_panel, width=2, border_radius=8)

    rows = [
        ("Volume", "volume", f"{int(app.user_settings.volume * 100)}%"),
        ("Fullscreen", "fullscreen", "On" if app.user_settings.fullscreen else "Off"),
    ]

    y = 260
    font, small, _big = app._fonts()

    # Draw semi-transparent overlay for each settings row
    for label, key, value in rows:
        row_rect = pygame.Rect(360, y - 10, 560, 60)
        overlay = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 0))  # 30% opaque black
        app.screen.blit(overlay, row_rect.topleft)

        SettingsRow(row_rect, label, value).draw(app.screen, font, small)

        if key == "volume":
            app._add_button(740, y, 42, 38, "-", "volume_down")
            app._add_button(794, y, 42, 38, "+", "volume_up")
        else:
            app._add_button(740, y, 112, 38, "Toggle", f"toggle_{key}")
        y += 80

    app._add_button(380, 520, 180, 48, "Save", "save_settings")
    app._add_button(720, 520, 180, 48, "Back", "menu")
    # app._draw_text("Settings are saved to config/user_settings.json.", 640, 600, MUTED, center=True)

    if app.notice:
        app._draw_text(app.notice, 640, 640, GOOD, center=True)

    app._draw_buttons()


def draw_join(app, input_box_cls) -> None:
    assert app.screen is not None
    app.buttons.clear()
    if not app.input_boxes:
        if app.mode == "host_room":
            app.input_boxes = [
                input_box_cls(pygame.Rect(420, 322, 440, 46), "Name", "Player 1"),
            ]
        else:
            app.input_boxes = [
                input_box_cls(pygame.Rect(420, 276, 440, 46), "Name", "Player"),
                input_box_cls(pygame.Rect(420, 374, 440, 46), "Room Code", ""),
            ]
    app._draw_title("Host Game" if app.mode == "host_room" else "Join Game")
    app._draw_panel(pygame.Rect(360, 210, 560, 330), PANEL)
    app._draw_text("Online rooms use only relay room codes. IP addresses stay out of the game UI.", 640, 248, MUTED, center=True, size="small")
    font, small, _big = app._fonts()
    for box in app.input_boxes:
        box.draw(app.screen, font, small)
    connect_label = "Connecting..." if app.connecting else ("Create" if app.mode == "host_room" else "Connect")
    app._add_button(420, 486, 210, 46, connect_label, "connect", enabled=not app.connecting)
    app._add_button(650, 486, 210, 46, "Back", "menu")
    app._draw_buttons()
    if app.notice:
        app._draw_text(app.notice, 640, 560, BAD, center=True)
