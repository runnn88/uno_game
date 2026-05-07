import pygame

from presentation.theme import ACCENT, ACCENT_2, BAD, GOOD, MUTED, PANEL, PANEL_2, TEXT
from presentation.ui.components.settings_row import SettingsRow

def draw_outlined_text(
    surface: pygame.Surface, 
    text: str, 
    font: pygame.font.Font, 
    text_color: tuple[int, int, int], 
    outline_color: tuple[int, int, int], 
    x: int, 
    y: int, 
    thickness: int = 2, 
    angle: float = 0
) -> None:
    """Draw text has outlier and rotate."""
    base_text = font.render(text, True, outline_color)
    inner_text = font.render(text, True, text_color)
    
    if angle != 0:
        base_text = pygame.transform.rotate(base_text, angle)
        inner_text = pygame.transform.rotate(inner_text, angle)
        
    step = max(1, thickness // 2)
    
    for dx in range(-thickness, thickness + 1, step):
        for dy in range(-thickness, thickness + 1, step):
            if dx == 0 and dy == 0:
                continue
            surface.blit(base_text, (x + dx, y + dy))
            
    surface.blit(inner_text, (x, y))
    
def draw_main_menu(app) -> None:
    assert app.screen is not None
    
    bg_img = app.card_renderer.assets.load_background("menu_background") if app.card_renderer else None
    if bg_img:
        bg_img = pygame.transform.smoothscale(bg_img, app.screen.get_size())
        app.screen.blit(bg_img, (0, 0))
    else:
        app.screen.fill((255, 255, 255))
    
    if app.card_renderer:
        from domain.entities.card import Card
        from config.enums import CardColor, CardRank
        cards_to_draw = [
            Card("c1", CardColor.RED, CardRank.FIVE),
            Card("c2", CardColor.BLUE, CardRank.SKIP),
            Card("c3", CardColor.YELLOW, CardRank.REVERSE),
            Card("c4", CardColor.GREEN, CardRank.DRAW_TWO),
            Card("c5", CardColor.WILD, CardRank.WILD)
        ]
        
        fan_positions = [
            (500, 85, 35), (539, 66, 24), (582, 63, 8), 
            (622, 66, -9), (632, 72, -30)
        ]
        for i, (x, y, angle) in enumerate(fan_positions):
            if i < len(cards_to_draw):
                card_img = app.card_renderer.assets.load(cards_to_draw[i])
            else:
                card_img = app.card_renderer.assets.load_card_back()
                
            if card_img:
                card_img = pygame.transform.smoothscale(card_img, (97, 139))
                rotated = pygame.transform.rotate(card_img, angle)
                app.screen.blit(rotated, (x, y))

    # The white oval base
    ellipse_width, ellipse_height = 410, 142
    ellipse_surf = pygame.Surface((ellipse_width, ellipse_height), pygame.SRCALPHA)
    pygame.draw.ellipse(ellipse_surf, (255, 255, 255), (0, 0, ellipse_width, ellipse_height))
    rotation_angle = 10.75
    rotated_ellipse = pygame.transform.rotate(ellipse_surf, rotation_angle)
    
    original_center = (442 + ellipse_width // 2, 150 + ellipse_height // 2)
    ellipse_rect = rotated_ellipse.get_rect(center=original_center)
    
    app.screen.blit(rotated_ellipse, ellipse_rect.topleft)

    title_font = app.fonts.get(160)
    draw_outlined_text(
        surface=app.screen,
        text="UNO",
        font=title_font,
        text_color=(237, 92, 115),
        outline_color=(0, 0, 0),
        x=471,
        y=102,
        thickness=14, 
        angle=9.63
    )

    # Buttons
    btn_font = app.fonts.get(28)
    app.buttons.clear()
    buttons_data = [
        ("Play", 552, 360, "choose_mode", (253, 238, 103), (253, 247, 195)),
        ("Instruction", 552, 456, "instructions", (253, 133, 130), (255, 200, 199)),
        ("Settings", 552, 552, "settings", (253, 238, 103), (253, 247, 195))
    ]
    
    mouse = pygame.mouse.get_pos()
    for label, x, y, action, bg_color, border_color in buttons_data:
        rect = pygame.Rect(x, y, 176, 62)
        app._add_button(x, y, 176, 62, label, action) 
        
        is_hover = rect.collidepoint(mouse)
        draw_rect = rect.inflate(4, 4) if is_hover else rect
        
        pygame.draw.rect(app.screen, border_color, draw_rect.inflate(12, 12), border_radius=20)
        pygame.draw.rect(app.screen, bg_color, draw_rect, border_radius=20)
        
        text_w, text_h = btn_font.size(label)
        text_x = draw_rect.centerx - text_w // 2
        text_y = draw_rect.centery - text_h // 2
        
        draw_outlined_text(
            surface=app.screen,
            text=label,
            font=btn_font,
            text_color=(255, 255, 255),  
            outline_color=(0, 0, 0),  
            x=text_x,
            y=text_y,
            thickness=2
        )
        
        
def draw_play_menu(app) -> None:
    assert app.screen is not None
    app.buttons.clear()
    app.input_boxes.clear()
    app._draw_title("UNO Online")

    hero = pygame.Rect(76, 124, 430, 500)
    menu = pygame.Rect(548, 124, 656, 500)
    app._draw_panel(hero, (251, 248, 236))
    app._draw_panel(menu, PANEL)

    app._draw_text("Fast local play", 116, 170, TEXT, size="big")
    app._draw_text("or code-based online rooms", 118, 218, MUTED)
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
    app._draw_text("or code-based online rooms", 118, 218, MUTED)
    app._draw_chip("Hotseat", 118, 274, ACCENT_2)
    app._draw_chip("Bots", 230, 274, GOOD)
    app._draw_chip("Room Code", 315, 274, ACCENT)
    app._draw_menu_cards()
    app._draw_text("Match color or rank, stack draw cards, and use special 0/7/8 rules.", 118, 560, MUTED, size="small")

    app._draw_text("Choose Mode", 602, 168, TEXT, size="big")
    app._draw_text("Local games start immediately. Online games use room codes.", 604, 214, MUTED)
    x = 604
    y = 258
    app._add_button(x, y, 126, 48, "2P Local", "local", 2)
    app._add_button(x + 138, y, 126, 48, "3P Local", "local", 3)
    app._add_button(x + 276, y, 126, 48, "4P Local", "local", 4)
    app._add_button(x, y + 64, 195, 48, "1P + Bot", "local", (2, 1))
    app._add_button(x + 207, y + 64, 195, 48, "1P + 3 Bots", "local", (4, 3))
    app._add_button(x, y + 146, 402, 50, "Host Online Room", "host_room")
    app._add_button(x, y + 208, 402, 50, "Join Room Code", "join_room")
    app._add_button(x, y + 286, 195, 48, "Instructions", "instructions")
    app._add_button(x + 207, y + 286, 195, 48, "Settings", "settings")
    app._draw_text("Online play uses room codes. Connection details stay out of the game UI.", 640, 676, MUTED, center=True, size="small")
    if app.notice:
        app._draw_text(app.notice, 640, 696, BAD, center=True)
    if not app.notice_overlay:
        app._draw_buttons()
    app._draw_notice_overlay()


def draw_instructions(app) -> None:
    assert app.screen is not None
    app.buttons.clear()
    app.input_boxes.clear()
    
    title_font = app.fonts.get(70)
    draw_outlined_text(
        surface=app.screen,
        text="Instruction",
        font=title_font,
        text_color=(255, 228, 21),  
        outline_color=(0, 0, 0),     
        x=450,                     
        y=52,
        thickness=5                  
    )
    
    app._add_button(28, 22, 92, 34, "Back", "menu")

    app._draw_panel(pygame.Rect(73, 150, 554, 532), PANEL)
    app._draw_panel(pygame.Rect(652, 150, 554, 532), PANEL_2)

    app._draw_chip("Flow", 93, 170, ACCENT_2)
    app._draw_text("How To Play", 254, 170, TEXT, size="big")
    rules = [
        "Match the discard pile by color or rank. Wild cards can be played on any color.",
        "Click a playable card in your hand. Dimmed cards are not legal for the current turn.",
        "If you cannot play, click Draw. After drawing, play the drawn card if it is legal or click Pass.",
        "Press U to call UNO when you have one card, or to catch another player who forgot.",
        "When a draw penalty is active, you must stack a +2 or +4 with equal or higher value, otherwise draw the penalty.",
        "First player with no cards wins. Action cards cannot be played as your final card.",
    ]
    app._draw_wrapped_lines(rules, 93, 274, 460, 26, TEXT, size="small")

    app._draw_chip("Cards", 698, 170, ACCENT)
    app._draw_text("Card Meanings", 842, 170, TEXT, size="big")
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
    app._draw_text("Online rooms use room codes. Connection details stay out of the game UI.", 640, 248, MUTED, center=True, size="small")
    font, small, _big = app._fonts()
    for box in app.input_boxes:
        box.draw(app.screen, font, small)
    connect_label = "Connecting..." if app.connecting else ("Create" if app.mode == "host_room" else "Connect")
    app._add_button(420, 486, 210, 46, connect_label, "connect", enabled=not app.connecting)
    app._add_button(650, 486, 210, 46, "Back", "menu")
    app._draw_buttons()
    if app.notice:
        app._draw_text(app.notice, 640, 560, BAD, center=True)
