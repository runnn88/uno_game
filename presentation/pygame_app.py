from __future__ import annotations

import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pygame

from config.enums import CardColor, CardRank
from config.settings import DEFAULT_SETTINGS
from config.user_settings import UserSettings, load_user_settings, save_user_settings
from domain.entities.card import Card
from presentation.audio.sound_manager import SoundManager
from presentation.game_feedback import CardMotion, GameFeedback, Toast
from presentation.game_sessions import LocalGameSession, OnlineGameSession
from presentation.rendering.gameplay_effects import draw_card_motions, draw_toasts
from presentation.rendering.card_renderer import CardRenderer
from presentation.screen_drawers import draw_instructions, draw_join, draw_menu, draw_settings
from presentation.scenes.end_scene import EndScene
from presentation.scenes.game_scene import GameScene
from presentation.scenes.instructions_scene import InstructionsScene
from presentation.scenes.lobby_scene import LobbyScene
from presentation.scenes.menu_scene import MenuScene
from presentation.scenes.settings_scene import SettingsScene
from presentation.theme import (
    ACCENT,
    ACCENT_2,
    BAD,
    BORDER,
    CARD_H,
    CARD_W,
    GOOD,
    MUTED,
    PANEL,
    SHADOW,
    TABLE_GREEN,
    TEXT,
    color_tuple,
)


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: str
    payload: Any = None
    enabled: bool = True


class InputBox:
    def __init__(self, rect: pygame.Rect, label: str, value: str = "") -> None:
        self.rect = rect
        self.label = label
        self.value = value
        self.active = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif event.key in {pygame.K_RETURN, pygame.K_TAB}:
                self.active = False
            elif event.unicode and len(self.value) < 32:
                self.value += event.unicode
            return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small: pygame.font.Font) -> None:
        border = ACCENT if self.active else (176, 197, 199)
        shadow = pygame.Surface((self.rect.width + 8, self.rect.height + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow, SHADOW, shadow.get_rect().move(4, 4), border_radius=8)
        surface.blit(shadow, (self.rect.x - 4, self.rect.y - 4))
        pygame.draw.rect(surface, (249, 253, 251), self.rect, border_radius=8)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=8)
        surface.blit(small.render(self.label.upper(), True, MUTED), (self.rect.x, self.rect.y - 23))
        clipped = self.value[-24:]
        surface.blit(font.render(clipped, True, TEXT), (self.rect.x + 12, self.rect.y + 10))


class PygameUnoApp:
    def __init__(self) -> None:
        self.settings = DEFAULT_SETTINGS
        self.screen: pygame.Surface | None = None
        self.clock: pygame.time.Clock | None = None
        self.running = False
        self.mode = "menu"
        self.user_settings: UserSettings = load_user_settings()
        self.session: LocalGameSession | OnlineGameSession | None = None
        self.card_renderer: CardRenderer | None = None
        self.sounds = SoundManager()
        self.buttons: list[Button] = []
        self.input_boxes: list[InputBox] = []
        self.hand_targets: list[tuple[pygame.Rect, dict[str, str]]] = []
        self.pending_card: dict[str, str] | None = None
        self.pending_color: str | None = None
        self.pending_pass_direction: str | None = None
        self.host_settings_open = False
        self.transition_alpha = 255
        self.click_feedback: list[tuple[tuple[int, int], float]] = []
        self.card_motions: list[CardMotion] = []
        self.toasts: list[Toast] = []
        self._last_game_state: dict[str, Any] | None = None
        self.feedback = GameFeedback(self)
        self.notice = ""
        self.notice_overlay: str | None = None
        self.assets_root = Path(__file__).resolve().parents[2] / "assets"
        self.scenes = {
            "menu": MenuScene(self),
            "host_room": LobbyScene(self, "host_room"),
            "join_room": LobbyScene(self, "join_room"),
            "game": GameScene(self),
            "end": EndScene(self),
            "settings": SettingsScene(self),
            "instructions": InstructionsScene(self),
        }

    def run(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((self.settings.width, self.settings.height))
        pygame.display.set_caption("UNO Online")
        self.clock = pygame.time.Clock()
        self.card_renderer = CardRenderer()
        self._apply_user_settings()
        self.sounds.initialize()
        self._set_mode("menu")
        self.running = True
        while self.running:
            dt = self.clock.tick(self.settings.fps) / 1000
            self._handle_events()
            self._update(dt)
            self._draw()
        self._close_session()
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.mode in {"game", "host_room", "join_room", "settings", "instructions"}:
                    self._go_menu()
                else:
                    self.running = False
                continue

            self._current_scene().handle_event(event)

    def _update(self, dt: float) -> None:
        self.transition_alpha = max(0, self.transition_alpha - int(950 * dt))
        self.click_feedback = [(pos, age + dt) for pos, age in self.click_feedback if age + dt < 0.24]
        self.card_motions = [motion for motion in self.card_motions if motion.age + dt < motion.duration]
        for motion in self.card_motions:
            motion.age += dt
        self.toasts = [toast for toast in self.toasts if toast.age + dt < toast.duration]
        for toast in self.toasts:
            toast.age += dt
        self._current_scene().update(dt)
        self.feedback.observe()
        self._handle_session_error()

    def _draw(self) -> None:
        assert self.screen is not None
        self.screen.fill(TABLE_GREEN)
        self._current_scene().draw(self.screen)
        draw_card_motions(self)
        draw_toasts(self)
        self._draw_transition()
        self._draw_click_feedback()
        pygame.display.flip()

    def _current_scene(self):
        if self.mode == "game":
            state = self.session.snapshot() if self.session else None
            if state and state.get("phase") == "ended":
                return self.scenes["end"]
        return self.scenes.get(self.mode, self.scenes["menu"])

    def _draw_menu(self) -> None:
        draw_menu(self)

    def _draw_instructions(self) -> None:
        draw_instructions(self)

    def _draw_settings(self) -> None:
        draw_settings(self)

    def _draw_join(self) -> None:
        draw_join(self, InputBox)

    def _draw_game(self) -> None:
        assert self.screen is not None
        assert self.card_renderer is not None
        self.buttons.clear()
        self.input_boxes.clear()
        self.hand_targets.clear()
        state = self.session.snapshot() if self.session else None
        self._draw_game_frame(state)
        if state is None:
            self._draw_text("Waiting for state...", 640, 360, TEXT, center=True)
            return

        players = state.get("players", [])
        phase = state.get("phase")
        current = state.get("current_player_id")
        me = self.session.player_id if self.session else None
        current_name = self._player_name(players, current)
        top_card = state.get("top_card")
        self._draw_players(players, current, me)
        self._draw_center_pile(top_card, state.get("active_color"), state.get("pending_draw", 0))
        self._draw_text(f"Turn: {current_name}", 640, 34, TEXT, center=True)
        self._draw_text(f"Direction: {state.get('direction')}  Phase: {phase}", 640, 62, MUTED, center=True)
        if isinstance(self.session, OnlineGameSession) and self.session.room_code:
            self._draw_chip(f"Room {self.session.room_code}", 1042, 30, ACCENT, width=180)

        my_player = next((player for player in players if player.get("id") == me), None)
        hand = list(my_player.get("hand", [])) if my_player else []
        self._draw_hand(hand, state, can_play=phase == "playing" and current == me)

        if phase in {"menu", "lobby"} or not top_card:
            can_start = bool(self.session and self.session.can_start_game)
            self._add_button(1070, 612, 150, 44, "Start", "start", enabled=can_start)
        elif phase == "reaction":
            self._draw_reaction_controls(state)
        elif phase == "playing":
            if state.get("drew_this_turn") and current == me:
                self._add_button(1070, 612, 150, 44, "Pass", "pass_turn", enabled=True)
            else:
                draw_label = "Draw Penalty" if state.get("pending_draw", 0) else "Draw"
                self._add_button(1070, 612, 150, 44, draw_label, "draw", enabled=current == me)

        if phase == "ended":
            winner = self._player_name(players, state.get("winner_id"))
            self._draw_overlay(f"{winner} wins")
            self._add_button(530, 410, 220, 46, "Back To Menu", "menu")

        self._draw_prompt(state)
        if self.session and self.session.can_start_game and phase in {"menu", "lobby", "playing"}:
            self._add_button(1055, 122, 154, 36, "Host Settings", "host_settings")
        if self.host_settings_open:
            self._draw_host_settings(state)
        self._add_button(28, 22, 92, 34, "Menu", "menu")
        self._draw_buttons()
        error = self.session.error if self.session else None
        if error:
            self._draw_text(error, 640, 690, BAD, center=True)

    def _draw_game_frame(self, state: dict[str, Any] | None) -> None:
        assert self.screen is not None
        pygame.draw.rect(self.screen, (222, 241, 232), pygame.Rect(0, 0, 1280, 92))
        pygame.draw.line(self.screen, BORDER, (0, 92), (1280, 92), 2)
        self._draw_panel(pygame.Rect(22, 104, 245, 470), PANEL)
        self._draw_panel(pygame.Rect(1014, 104, 244, 470), PANEL)
        pygame.draw.rect(self.screen, (229, 244, 237), pygame.Rect(0, 584, 1280, 136))
        pygame.draw.line(self.screen, BORDER, (0, 584), (1280, 584), 2)
        pygame.draw.ellipse(self.screen, (179, 220, 202), pygame.Rect(364, 130, 550, 310), 3)
        if self.session:
            self._draw_text(self.session.info, 1020, 64, MUTED, size="small")

    def _draw_players(self, players: list[dict[str, Any]], current: str | None, me: str | None) -> None:
        self._draw_text("Players", 42, 124, TEXT)
        y = 162
        for player in players:
            active = player.get("id") == current
            mine = player.get("id") == me
            row = pygame.Rect(38, y - 8, 205, 32)
            if active:
                pygame.draw.rect(self.screen, (255, 237, 225), row, border_radius=8)
                pygame.draw.rect(self.screen, ACCENT, row, 2, border_radius=8)
            color = ACCENT if active else TEXT
            tag = "YOU" if mine else ("BOT" if player.get("is_bot") else ("OFF" if not player.get("connected", True) else ""))
            label = f"{player.get('name')}  {player.get('card_count')}"
            self._draw_text(label, 48, y, color, size="small")
            if tag:
                self._draw_chip(tag, 172, y - 5, GOOD if tag == "YOU" else ACCENT_2 if tag == "BOT" else BAD, width=52)
            y += 38

    def _draw_center_pile(self, top_card: dict[str, str] | None, active_color: str | None, pending_draw: int) -> None:
        assert self.screen is not None
        assert self.card_renderer is not None
        pile = pygame.Rect(565, 178, CARD_W + 38, CARD_H + 38)
        self._draw_panel(pile, (252, 244, 232), radius=10)
        if top_card:
            card = card_from_dict(top_card)
            self.card_renderer.draw_card(self.screen, card, pygame.Rect(584, 197, CARD_W, CARD_H))
        self._draw_card_back(pygame.Rect(450, 197, CARD_W, CARD_H))
        if active_color:
            color = color_tuple(active_color)
            pygame.draw.circle(self.screen, color, (714, 230), 20)
            pygame.draw.circle(self.screen, TEXT, (714, 230), 20, 2)
        if pending_draw:
            self._draw_chip(f"+{pending_draw}", 690, 282, BAD, width=64)

    def _draw_hand(self, hand: list[dict[str, str]], state: dict[str, Any], can_play: bool) -> None:
        assert self.screen is not None
        assert self.card_renderer is not None
        if not hand:
            self._draw_text("No visible hand yet", 640, 646, MUTED, center=True)
            return
        available_width = 900
        step = min(CARD_W + 12, max(34, available_width // max(1, len(hand))))
        start_x = 640 - ((len(hand) - 1) * step + CARD_W) // 2
        y = 582
        mouse = pygame.mouse.get_pos()
        for index, card_data in enumerate(hand):
            rect = pygame.Rect(start_x + index * step, y, CARD_W, CARD_H)
            playable = can_play and is_card_playable(card_data, state)
            hover = rect.collidepoint(mouse) and playable
            draw_rect = rect.move(0, -16 if hover else 0)
            if hover:
                halo = draw_rect.inflate(10, 10)
                pygame.draw.rect(self.screen, ACCENT, halo, 3, border_radius=12)
            self.card_renderer.draw_card(self.screen, card_from_dict(card_data), draw_rect)
            if not playable:
                dim = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 105 if can_play else 150))
                self.screen.blit(dim, draw_rect)
            if playable:
                self.hand_targets.append((draw_rect, card_data))

    def _draw_reaction_controls(self, state: dict[str, Any]) -> None:
        reaction = state.get("reaction", {})
        source = reaction.get("source_player_id")
        responders = set(reaction.get("responders", []))
        if isinstance(self.session, LocalGameSession):
            x = 1028
            y = 148
            self._draw_text("React", x, y - 28, TEXT)
            for player in state.get("players", []):
                player_id = player.get("id")
                done = player_id in responders
                self._add_button(x, y, 190, 38, f"{player.get('name')}", "react_player", player_id, enabled=not done)
                y += 46
        else:
            me = self.session.player_id if self.session else None
            self._add_button(1070, 612, 150, 44, "React", "react", enabled=me not in responders)

    def _draw_prompt(self, state: dict[str, Any]) -> None:
        if self.pending_card is None:
            return
        self._draw_overlay("Choose")
        if self.pending_card["rank"] == "0" and self.pending_pass_direction is None:
            self._add_button(470, 396, 150, 44, "Clockwise", "choose_pass_direction", "clockwise")
            self._add_button(660, 396, 190, 44, "Counter", "choose_pass_direction", "counter_clockwise")
            return
        if self.pending_card["rank"] in {"wild", "wild_draw_four"} and self.pending_color is None:
            colors = [("red", 430), ("yellow", 520), ("green", 610), ("blue", 700)]
            for color, x in colors:
                self._add_button(x, 396, 80, 44, color.title(), "choose_color", color)
            return
        if self.pending_card["rank"] == "7":
            players = state.get("players", [])
            x = 390
            y = 388
            me = self.session.player_id if self.session else state.get("current_player_id")
            for player in players:
                if player.get("id") != me:
                    self._add_button(x, y, 150, 42, player.get("name", "Player"), "choose_target", player.get("id"))
                    x += 166

    def _draw_overlay(self, title: str) -> None:
        assert self.screen is not None
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((24, 40, 37, 154))
        self.screen.blit(overlay, (0, 0))
        self._draw_panel(pygame.Rect(360, 300, 560, 190), PANEL)
        self._draw_text(title, 640, 332, TEXT, center=True, size="big")

    def _draw_card_back(self, rect: pygame.Rect) -> None:
        assert self.screen is not None
        assert self.card_renderer is not None
        # Optional card back falls back to assets/images/placeholder.jfif.
        image = self.card_renderer.assets.load_card_back()
        if image is not None:
            self.screen.blit(pygame.transform.smoothscale(image, (rect.width, rect.height)), rect)
            return
        pygame.draw.rect(self.screen, (255, 251, 242), rect, border_radius=10)
        inner = rect.inflate(-8, -8)
        pygame.draw.rect(self.screen, (188, 213, 232), inner, border_radius=8)
        pygame.draw.ellipse(self.screen, (238, 185, 145), inner.inflate(-12, -42))
        self._draw_text("UNO", rect.centerx, rect.centery - 11, TEXT, center=True, size="big")

    def _draw_background(self, name: str) -> None:
        assert self.screen is not None
        self._draw_table_texture()
        if self.card_renderer is None:
            return
        if not self.user_settings.show_background_art:
            return
        # Optional backgrounds use assets/images/placeholder.jfif until real art is added.
        image = self.card_renderer.assets.load_background(name)
        if image is None:
            return
        scaled = pygame.transform.smoothscale(image, self.screen.get_size())
        scaled.set_alpha(34 if name == "table_background" else 46)
        self.screen.blit(scaled, (0, 0))

    def _draw_title(self, title: str) -> None:
        self._draw_text(title, 640, 130, TEXT, center=True, size="big")
        self._draw_text("Host-authoritative UNO with local play, bots, and relay room codes", 640, 174, MUTED, center=True)

    def _draw_buttons(self) -> None:
        assert self.screen is not None
        font, small, _big = self._fonts()
        mouse = pygame.mouse.get_pos()
        for button in self.buttons:
            draw_rect = button.rect
            hovered = button.enabled and draw_rect.collidepoint(mouse)
            base = (248, 239, 226) if button.enabled else (229, 230, 225)
            color = (255, 232, 213) if hovered else base
            shadow = pygame.Surface((draw_rect.width + 8, draw_rect.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(shadow, SHADOW if button.enabled else (0, 0, 0, 24), shadow.get_rect().move(4, 4), border_radius=8)
            self.screen.blit(shadow, (draw_rect.x - 4, draw_rect.y - 4))
            pygame.draw.rect(self.screen, color, draw_rect, border_radius=8)
            border = ACCENT if button.enabled else (184, 190, 188)
            pygame.draw.rect(self.screen, border, draw_rect, 2, border_radius=8)
            selected_font = small if font.size(button.label)[0] > draw_rect.width - 22 else font
            label = selected_font.render(button.label, True, TEXT if button.enabled else MUTED)
            self.screen.blit(label, label.get_rect(center=draw_rect.center))

    def _draw_panel(
        self,
        rect: pygame.Rect,
        color: tuple[int, int, int],
        border: tuple[int, int, int] = BORDER,
        radius: int = 8,
    ) -> None:
        assert self.screen is not None
        shadow = pygame.Surface((rect.width + 14, rect.height + 14), pygame.SRCALPHA)
        pygame.draw.rect(shadow, SHADOW, pygame.Rect(7, 8, rect.width, rect.height), border_radius=radius)
        self.screen.blit(shadow, (rect.x - 7, rect.y - 7))
        pygame.draw.rect(self.screen, color, rect, border_radius=radius)
        pygame.draw.rect(self.screen, border, rect, 1, border_radius=radius)

    def _draw_chip(self, label: str, x: int, y: int, color: tuple[int, int, int], width: int | None = None) -> None:
        assert self.screen is not None
        _font, small, _big = self._fonts()
        chip_width = width or max(74, small.size(label)[0] + 24)
        rect = pygame.Rect(x, y, chip_width, 26)
        fill = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(fill, (*color, 42), fill.get_rect(), border_radius=8)
        self.screen.blit(fill, rect.topleft)
        pygame.draw.rect(self.screen, color, rect, 1, border_radius=8)
        text = small.render(label, True, TEXT)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _draw_table_texture(self) -> None:
        assert self.screen is not None
        self.screen.fill(TABLE_GREEN)
        for x in range(0, 1280, 64):
            pygame.draw.line(self.screen, (190, 224, 210), (x, 0), (x + 160, 720), 1)
        for y in range(36, 720, 72):
            pygame.draw.line(self.screen, (219, 239, 229), (0, y), (1280, y - 32), 1)

    def _draw_menu_cards(self) -> None:
        assert self.screen is not None
        cards = [
            (pygame.Rect(166, 352, CARD_W, CARD_H), "red"),
            (pygame.Rect(238, 330, CARD_W, CARD_H), "blue"),
            (pygame.Rect(310, 352, CARD_W, CARD_H), "green"),
        ]
        for rect, color in cards:
            pygame.draw.rect(self.screen, color_tuple(color), rect, border_radius=12)
            pygame.draw.rect(self.screen, (255, 255, 250), rect.inflate(-12, -12), 3, border_radius=10)
            pygame.draw.ellipse(self.screen, (255, 255, 250), rect.inflate(-26, -56))
        self._draw_text("UNO", 285, 402, TEXT, center=True, size="big")

    def _draw_click_feedback(self) -> None:
        if not self.click_feedback or self.screen is None:
            return
        for pos, age in self.click_feedback:
            alpha = max(0, int(110 * (1 - age / 0.24)))
            radius = int(10 + 42 * (age / 0.24))
            ripple = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ripple, (*ACCENT, alpha), (radius + 2, radius + 2), radius, 2)
            self.screen.blit(ripple, (pos[0] - radius - 2, pos[1] - radius - 2))

    def _draw_transition(self) -> None:
        if self.transition_alpha <= 0 or self.screen is None:
            return
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((*TABLE_GREEN, min(210, self.transition_alpha)))
        self.screen.blit(overlay, (0, 0))

    def _draw_host_settings(self, state: dict[str, Any] | None) -> None:
        if self.screen is None or not isinstance(self.session, OnlineGameSession) or not self.session.is_host:
            return
        self._draw_overlay("Host Settings")
        connected = len([player for player in (state or {}).get("players", []) if player.get("connected", True)])
        max_players = int((state or {}).get("max_players", 4))
        lobby_locked = bool((state or {}).get("lobby_locked", False))
        self._draw_text("Max Players", 420, 374, TEXT)
        self._draw_text(str(max_players), 640, 374, MUTED, center=True)
        self._add_button(710, 360, 42, 38, "-", "host_max_down", enabled=max_players > max(2, connected))
        self._add_button(764, 360, 42, 38, "+", "host_max_up", enabled=max_players < 4)
        self._draw_text("Lobby", 420, 424, TEXT)
        self._draw_text("Locked" if lobby_locked else "Open", 640, 424, MUTED, center=True)
        self._add_button(710, 410, 96, 38, "Toggle", "host_toggle_lock")
        self._draw_text("Relay hosting prevents player-to-player IP exposure.", 640, 462, MUTED, center=True, size="small")
        self._add_button(530, 515, 220, 44, "Close", "host_settings_close")

    def _add_button(self, x: int, y: int, w: int, h: int, label: str, action: str, payload: Any = None, enabled: bool = True) -> None:
        self.buttons.append(Button(pygame.Rect(x, y, w, h), label, action, payload, enabled))

    def _draw_text(
        self,
        text: str,
        x: int,
        y: int,
        color: tuple[int, int, int],
        center: bool = False,
        size: str = "normal",
    ) -> None:
        assert self.screen is not None
        font, small, big = self._fonts()
        selected = big if size == "big" else small if size == "small" else font
        surface = selected.render(str(text), True, color)
        rect = surface.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surface, rect)

    def _draw_wrapped_lines(
        self,
        lines: list[str],
        x: int,
        y: int,
        width: int,
        line_height: int,
        color: tuple[int, int, int],
        size: str = "normal",
    ) -> None:
        font, small, _big = self._fonts()
        selected = small if size == "small" else font
        current_y = y
        for line in lines:
            words = line.split()
            current = "- "
            for word in words:
                candidate = f"{current}{word} "
                if selected.size(candidate)[0] <= width:
                    current = candidate
                    continue
                self._draw_text(current.rstrip(), x, current_y, color, size=size)
                current_y += line_height
                current = f"  {word} "
            if current.strip():
                self._draw_text(current.rstrip(), x, current_y, color, size=size)
                current_y += line_height
            current_y += 8

    def _fonts(self) -> tuple[pygame.font.Font, pygame.font.Font, pygame.font.Font]:
        # Optional asset: add assets/fonts/Inter-Regular.ttf for a custom UI font.
        font_path = self.assets_root / "fonts" / "Inter-Regular.ttf"
        path = str(font_path) if font_path.exists() else None
        return pygame.font.Font(path, 23), pygame.font.Font(path, 17), pygame.font.Font(path, 44)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        for button in reversed(self.buttons):
            if button.enabled and button.rect.collidepoint(pos):
                self.click_feedback.append((pos, 0.0))
                self._handle_action(button.action, button.payload)
                return
        if self.mode == "game" and self.pending_card is None:
            for rect, card_data in reversed(self.hand_targets):
                if rect.collidepoint(pos):
                    self._select_card(card_data)
                    return

    def _handle_action(self, action: str, payload: Any) -> None:
        if action == "menu":
            self._go_menu()
        elif action == "local":
            if isinstance(payload, tuple):
                self._start_local(int(payload[0]), int(payload[1]))
            else:
                self._start_local(int(payload or 2), 0)
        elif action == "host_room":
            self._set_mode("host_room")
            self.notice = ""
        elif action == "join_room":
            self._set_mode("join_room")
            self.notice = ""
        elif action == "settings":
            self._set_mode("settings")
            self.notice = ""
            self.notice_overlay = None
        elif action == "instructions":
            self._set_mode("instructions")
            self.notice = ""
            self.notice_overlay = None
        elif action == "dismiss_notice":
            self.notice_overlay = None
            self.notice = ""
        elif action == "host_settings":
            self.host_settings_open = True
        elif action == "host_settings_close":
            self.host_settings_open = False
        elif action == "host_max_down":
            self._adjust_host_max_players(-1)
        elif action == "host_max_up":
            self._adjust_host_max_players(1)
        elif action == "host_toggle_lock":
            self._toggle_host_lock()
        elif action.startswith("toggle_"):
            self._toggle_setting(action.removeprefix("toggle_"))
        elif action == "volume_down":
            self._adjust_volume(-0.1)
        elif action == "volume_up":
            self._adjust_volume(0.1)
        elif action == "save_settings":
            self._save_settings()
        elif action == "connect":
            self._connect_from_form()
        elif action == "start" and self.session:
            self.session.start_game()
            self.sounds.play("card_play")
        elif action == "draw" and self.session:
            self.session.draw_card()
            self.sounds.play("card_draw")
        elif action == "pass_turn" and self.session:
            self.session.pass_turn()
        elif action == "react" and self.session:
            self.session.react()
            self.sounds.play("reaction_hit")
        elif action == "react_player" and self.session:
            self.session.react(str(payload))
            self.sounds.play("reaction_hit")
        elif action == "choose_color":
            self.pending_color = str(payload)
            if self.pending_card and self.pending_card["rank"] != "7":
                self._send_pending_card()
        elif action == "choose_pass_direction":
            self.pending_pass_direction = str(payload)
            if self.pending_card and self.pending_card["rank"] != "7":
                self._send_pending_card()
        elif action == "choose_target":
            self._send_pending_card(str(payload))

    def _select_card(self, card_data: dict[str, str]) -> None:
        if card_data["rank"] in {"wild", "wild_draw_four", "7", "0"}:
            self.pending_card = card_data
            self.pending_color = None
            self.pending_pass_direction = None
            return
        if self.session:
            self.session.play_card(card_data["id"])
            self.sounds.play("card_play")

    def _send_pending_card(self, target_player_id: str | None = None) -> None:
        if self.session and self.pending_card:
            self.session.play_card(self.pending_card["id"], self.pending_color, target_player_id, self.pending_pass_direction)
            self.sounds.play("card_play")
        self.pending_card = None
        self.pending_color = None
        self.pending_pass_direction = None

    def _start_local(self, player_count: int = 2, bot_count: int = 0) -> None:
        self._close_session()
        self.session = LocalGameSession(player_count=player_count, bot_count=bot_count)
        self._set_mode("game")
        self.notice = ""

    def _start_online_host(self, relay_host: str, name: str) -> None:
        self._close_session()
        try:
            self.session = OnlineGameSession(relay_host, 5051, name, is_host=True)
            self.session.info = "Hosting through relay"
            self._set_mode("game")
            self.notice = ""
        except Exception as exc:
            self.notice = str(exc)
            self._close_session()

    def _connect_from_form(self) -> None:
        try:
            name = self.input_boxes[0].value or "Player"
            relay_host = self.input_boxes[1].value or "127.0.0.1"
            if self.mode == "host_room":
                self._start_online_host(relay_host, name)
                return
            room_code = self.input_boxes[2].value.strip().upper()
            self._close_session()
            self.session = OnlineGameSession(relay_host, 5051, name, is_host=False, room_code=room_code)
            self._set_mode("game")
            self.notice = ""
        except Exception as exc:
            self.notice = str(exc)

    def _go_menu(self) -> None:
        self._close_session()
        self.input_boxes.clear()
        self.pending_card = None
        self.pending_color = None
        self.pending_pass_direction = None
        self.host_settings_open = False
        self.notice_overlay = None
        self._set_mode("menu")

    def _close_session(self) -> None:
        if self.session is not None:
            self.session.close()
        self.session = None

    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        self.transition_alpha = 255
        scene = self.scenes.get(mode)
        if scene is not None:
            scene.enter()

    def _handle_session_error(self) -> None:
        if self.mode != "game" or not isinstance(self.session, OnlineGameSession):
            return
        error = self.session.error
        if not error:
            return
        if error.strip().lower() == "room is full":
            self._go_menu()
            self.notice = "room is full"
            self.notice_overlay = "room is full"

    def _draw_notice_overlay(self) -> None:
        if not self.notice_overlay or self.screen is None:
            return
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((24, 40, 37, 84))
        self.screen.blit(overlay, (0, 0))
        self.buttons.clear()
        panel = pygame.Rect(410, 246, 460, 190)
        self._draw_panel(panel, PANEL)
        self._draw_chip("Notice", 584, 272, BAD, width=112)
        self._draw_text(self.notice_overlay, 640, 336, TEXT, center=True, size="big")
        self._draw_text("Please choose another room or ask the host to increase max players.", 640, 382, MUTED, center=True, size="small")
        self._add_button(565, 414, 150, 42, "OK", "dismiss_notice")
        self._draw_buttons()

    def _adjust_host_max_players(self, delta: int) -> None:
        if not isinstance(self.session, OnlineGameSession) or not self.session.is_host:
            return
        state = self.session.snapshot() or {}
        self.session.client.host_settings(max_players=int(state.get("max_players", 4)) + delta)

    def _toggle_host_lock(self) -> None:
        if not isinstance(self.session, OnlineGameSession) or not self.session.is_host:
            return
        state = self.session.snapshot() or {}
        self.session.client.host_settings(lobby_locked=not bool(state.get("lobby_locked", False)))

    def _toggle_setting(self, name: str) -> None:
        if not hasattr(self.user_settings, name):
            return
        current = getattr(self.user_settings, name)
        if isinstance(current, bool):
            setattr(self.user_settings, name, not current)
            self._apply_user_settings()
            self._save_settings(show_notice=False)

    def _adjust_volume(self, delta: float) -> None:
        self.user_settings.volume = max(0.0, min(1.0, self.user_settings.volume + delta))
        self._apply_user_settings()
        self._save_settings(show_notice=False)

    def _save_settings(self, show_notice: bool = True) -> None:
        save_user_settings(self.user_settings)
        self._apply_user_settings()
        if show_notice:
            self.notice = "Settings saved"

    def _apply_user_settings(self) -> None:
        self.sounds.configure(self.user_settings.sound_enabled, self.user_settings.volume)
        if self.card_renderer is not None:
            self.card_renderer.show_missing_labels = self.user_settings.show_missing_card_labels
        if self.screen is not None:
            flags = pygame.FULLSCREEN if self.user_settings.fullscreen else 0
            is_fullscreen = bool(self.screen.get_flags() & pygame.FULLSCREEN)
            if is_fullscreen != self.user_settings.fullscreen:
                self.screen = pygame.display.set_mode((self.settings.width, self.settings.height), flags)

    def _player_name(self, players: list[dict[str, Any]], player_id: str | None) -> str:
        for player in players:
            if player.get("id") == player_id:
                return str(player.get("name"))
        return "None"

def card_from_dict(data: dict[str, str]) -> Card:
    return Card(data["id"], CardColor(data["color"]), CardRank(data["rank"]))


def local_ip_hint() -> str:
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


def is_card_playable(card: dict[str, str], state: dict[str, Any]) -> bool:
    top = state.get("top_card")
    if not top:
        return True
    if state.get("reaction", {}).get("active"):
        return False
    if state.get("drew_this_turn") and state.get("drawn_card_id") and card["id"] != state.get("drawn_card_id"):
        return False
    pending_draw = int(state.get("pending_draw") or 0)
    pending_draw_value = int(state.get("pending_draw_value") or 0)
    if pending_draw and card["rank"] not in {"draw_two", "wild_draw_four"}:
        return False
    if pending_draw and card_penalty_value(card["rank"]) < pending_draw_value:
        return False
    visible_owner = next(
        (
            player
            for player in state.get("players", [])
            if any(hand_card.get("id") == card["id"] for hand_card in player.get("hand", ()))
        ),
        None,
    )
    if visible_owner and int(visible_owner.get("card_count", 0)) == 1 and card["rank"] in {"skip", "reverse", "draw_two", "wild", "wild_draw_four"}:
        return False
    if card["color"] == "wild":
        return True
    return card["color"] == state.get("active_color") or card["rank"] == top.get("rank")


def card_penalty_value(rank: str) -> int:
    if rank == "draw_two":
        return 2
    if rank == "wild_draw_four":
        return 4
    return 0
