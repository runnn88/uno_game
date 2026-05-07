from __future__ import annotations

import os
import threading
from pathlib import Path
from time import monotonic
from typing import Any

import pygame

from config.constants import DEFAULT_RELAY_URL
from config.env import load_env
from config.enums import CardColor, CardRank
from config.settings import DEFAULT_SETTINGS
from config.user_settings import UserSettings, load_user_settings, save_user_settings
from domain.entities.card import Card
from presentation.audio.sound_manager import SoundManager
from presentation.rendering.font_manager import FontManager
from presentation.game_feedback import CardMotion, GameFeedback, Toast
from presentation.game_sessions import LocalGameSession, OnlineGameSession
from presentation.rendering.gameplay_effects import draw_card_motions, draw_toasts
from presentation.rendering.card_renderer import CardRenderer
from presentation.screen_drawers import draw_instructions, draw_join, draw_play_menu, draw_main_menu, draw_settings, draw_choose_mode
from presentation.scenes.end_scene import EndScene
from presentation.scenes.game_scene import GameScene
from presentation.scenes.instructions_scene import InstructionsScene
from presentation.scenes.lobby_scene import LobbyScene
from presentation.scenes.menu_scene import MenuScene
from presentation.scenes.settings_scene import SettingsScene
from presentation.scenes.choose_mode import ChooseModeScene
from presentation.theme import (
    ACCENT,
    BAD,
    BORDER,
    CARD_H,
    CARD_W,
    GOOD,
    MUTED,
    PANEL,
    TABLE_GREEN,
    TEXT,
    color_tuple,
)
from presentation.ui.components.button import Button
from presentation.ui.components.chip import Chip
from presentation.ui.components.input_box import InputBox
from presentation.ui.components.panel import Panel
from presentation.ui.components.room_code_panel import RoomCodePanel
from presentation.ui.components.settings_row import SettingsRow


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
        self.fonts = FontManager()
        self.buttons: list[Button] = []
        self.input_boxes: list[InputBox] = []
        self.hand_targets: list[tuple[pygame.Rect, dict[str, str]]] = []
        self.selected_card: dict[str, str] | None = None
        self.pending_card: dict[str, str] | None = None
        self.pending_color: str | None = None
        self.pending_pass_direction: str | None = None
        self.game_escape_overlay: str | None = None
        self.host_settings_open = False
        self.transition_alpha = 255
        self.click_feedback: list[tuple[tuple[int, int], float]] = []
        self.card_motions: list[CardMotion] = []
        self.toasts: list[Toast] = []
        self._last_game_state: dict[str, Any] | None = None
        self.feedback = GameFeedback(self)
        self.notice = ""
        self.notice_overlay: str | None = None
        self.connecting = False
        self._connection_id = 0
        self._connection_result: tuple[int, bool, OnlineGameSession | None, str] | None = None
        self._connection_lock = threading.Lock()
        self._last_session_error: str | None = None
        self._session_error_clear_at = 0.0
        self._last_room_notice_sequence = 0
        self.assets_root = Path(__file__).resolve().parents[2] / "assets"
        self.scenes = {
            "menu": MenuScene(self),
            "host_room": LobbyScene(self, "host_room"),
            "join_room": LobbyScene(self, "join_room"),
            "game": GameScene(self),
            "end": EndScene(self),
            "settings": SettingsScene(self),
            "instructions": InstructionsScene(self),
            "choose_mode": ChooseModeScene(self),
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
                if self.mode == "game":
                    self._handle_game_escape()
                elif self.mode in {"host_room", "join_room", "settings", "instructions", "choose_mode"}:
                    self._go_menu()
                else:
                    self.running = False
                continue
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_u:
                if self._handle_uno_shortcut():
                    continue
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                if self._handle_play_shortcut():
                    continue

            try:
                self._current_scene().handle_event(event)
            except Exception as exc:
                self._handle_runtime_error("Input problem", exc)

    def _update(self, dt: float) -> None:
        try:
            self.transition_alpha = max(0, self.transition_alpha - int(950 * dt))
            self.click_feedback = [(pos, age + dt) for pos, age in self.click_feedback if age + dt < 0.24]
            self.card_motions = [motion for motion in self.card_motions if motion.age + dt < motion.duration]
            for motion in self.card_motions:
                motion.age += dt
            self.toasts = [toast for toast in self.toasts if toast.age + dt < toast.duration]
            for toast in self.toasts:
                toast.age += dt
            self._current_scene().update(dt)
            self._finish_pending_connection()
            self.feedback.observe()
            self._observe_room_notices()
            self._handle_session_error()
        except Exception as exc:
            self._handle_runtime_error("Update problem", exc)

    def _draw(self) -> None:
        assert self.screen is not None
        try:
            self.screen.fill(TABLE_GREEN)
            self._current_scene().draw(self.screen)
            draw_card_motions(self)
            draw_toasts(self)
            self._draw_transition()
            self._draw_click_feedback()
        except Exception as exc:
            self._handle_runtime_error("Render problem", exc)
            self.screen.fill(TABLE_GREEN)
            self._draw_text("Something went wrong", 640, 314, BAD, center=True, size="big")
            self._draw_text(self.notice or str(exc), 640, 374, TEXT, center=True)
        pygame.display.flip()

    def _current_scene(self):
        if self.mode == "game":
            state = self.session.snapshot() if self.session else None
            if state and state.get("phase") == "ended":
                return self.scenes["end"]
        return self.scenes.get(self.mode, self.scenes["menu"])

    def _draw_main_menu(self) -> None:
        draw_main_menu(self)
        
    def _draw_play_menu(self) -> None:
        draw_play_menu(self)

    def _draw_choose_mode(self) -> None:
        draw_choose_mode(self)

    def _draw_instructions(self) -> None:
        draw_instructions(self)

    def _draw_settings(self) -> None:
        draw_settings(self)

    def _draw_join(self) -> None:
        draw_join(self, InputBox)

    def _draw_cute_button(
        self,
        rect: pygame.Rect,
        label: str,
        bg_color: tuple[int, int, int],
        border_color: tuple[int, int, int],
        font_size: int = 26,
    ) -> None:
        assert self.screen is not None

        mouse = pygame.mouse.get_pos()
        is_hover = rect.collidepoint(mouse)

        draw_rect = rect.inflate(4, 4) if is_hover else rect

        # Outer border
        pygame.draw.rect(
            self.screen,
            border_color,
            draw_rect.inflate(12, 12),
            border_radius=20,
        )

        # Main button
        pygame.draw.rect(
            self.screen,
            bg_color,
            draw_rect,
            border_radius=20,
        )

        # Highlight
        # pygame.draw.rect(
        #     self.screen,
        #     (255, 255, 255),
        #     draw_rect,
        #     width=3,
        #     border_radius=20,
        # )

        # Font
        font = pygame.font.Font(
            "assets/fonts/SansitaOne.ttf",
            font_size,
        )

        text = font.render(
            label,
            True,
            (255, 255, 255),
        )

        outline = font.render(
            label,
            True,
            (0, 0, 0),
        )

        text_rect = text.get_rect(
            center=draw_rect.center,
        )

        # Outline
        thickness = 2

        for ox in range(-thickness, thickness + 1):
            for oy in range(-thickness, thickness + 1):

                if ox == 0 and oy == 0:
                    continue

                self.screen.blit(
                    outline,
                    text_rect.move(ox, oy),
                )

        # Main text
        self.screen.blit(text, text_rect)

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

        # =========================================
        # DRAW PLAYER INFO AND TABLE
        # =========================================
        players = state.get("players", [])
        phase = state.get("phase")
        current = state.get("current_player_id")
        me = self.session.player_id if self.session else None
        current_name = self._player_name(players, current)
        top_card = state.get("top_card")
        reaction_active = bool(state.get("reaction", {}).get("active"))
        
        self._draw_players(players, current, me)
        self._draw_center_pile(top_card, state.get("active_color"), state.get("pending_draw", 0))
        
        # =========================================
        # TOP INFO PANEL
        # =========================================
        info_width = 520
        info_height = 72

        info_x = (1280 - info_width) // 2
        info_y = 8

        info_rect = pygame.Rect(
            info_x,
            info_y,
            info_width,
            info_height,
        )

        # Transparent pastel yellow surface
        info_surface = pygame.Surface(
            (info_width, info_height),
            pygame.SRCALPHA,
        )

        # Main pastel yellow fill
        pygame.draw.rect(
            info_surface,
            (255, 245, 190, 190),
            info_surface.get_rect(),
            border_radius=24,
        )

        # Outer border
        pygame.draw.rect(
            info_surface,
            (255, 205, 120),
            info_surface.get_rect(),
            width=3,
            border_radius=24,
        )

        # Inner highlight
        pygame.draw.rect(
            info_surface,
            (255, 255, 255, 90),
            info_surface.get_rect().inflate(-8, -8),
            width=2,
            border_radius=20,
        )

        self.screen.blit(info_surface, info_rect.topleft)

        # =========================================
        # TURN TEXT
        # =========================================
        self._draw_text(
            f"Turn: {current_name}",
            info_rect.centerx,
            info_rect.y + 22,
            (215, 110, 140),
            center=True,
        )

        # =========================================
        # DIRECTION TEXT
        # =========================================
        self._draw_text(
            f"Direction: {state.get('direction')}   Phase: {phase}",
            info_rect.centerx,
            info_rect.y + 48,
            (235, 140, 170),
            center=True,
            size="small",
        )
        # self._draw_text(f"Turn: {current_name}", 640, 34, TEXT, center=True)
        # self._draw_text(f"Direction: {state.get('direction')}  Phase: {phase}", 640, 62, MUTED, center=True)
        
        # self._draw_room_code_panel()
        # =========================================
        # TOP RIGHT PANELS
        # =========================================

        top_right_x = 1050
        room_y = 70

        # -----------------------------------------
        # ROOM CODE PANEL
        # -----------------------------------------
        if isinstance(self.session, OnlineGameSession) and self.session.room_code:
            room_rect = pygame.Rect(
                top_right_x,
                room_y,
                200,
                110,
            )

            room_surface = pygame.Surface(
                (room_rect.width, room_rect.height),
                pygame.SRCALPHA,
            )

            # pastel background
            pygame.draw.rect(
                room_surface,
                (255, 245, 200, 210),
                room_surface.get_rect(),
                border_radius=22,
            )

            # border
            pygame.draw.rect(
                room_surface,
                (255, 185, 130),
                room_surface.get_rect(),
                width=3,
                border_radius=22,
            )

            # inner glow
            pygame.draw.rect(
                room_surface,
                (255, 255, 255, 90),
                room_surface.get_rect().inflate(-8, -8),
                width=2,
                border_radius=18,
            )

            self.screen.blit(room_surface, room_rect.topleft)

            # title
            self._draw_text(
                "ROOM CODE",
                room_rect.centerx,
                room_rect.y + 18,
                (210, 120, 120),
                center=True,
                size="small",
            )

            # code
            self._draw_text(
                self.session.room_code,
                room_rect.centerx,
                room_rect.y + 50,
                (120, 70, 70),
                center=True,
                size="big",
            )

            # copy button
            copy_rect = pygame.Rect(
                room_rect.x + 28,
                room_rect.bottom - 34,
                144,
                24,
            )

            pygame.draw.rect(
                self.screen,
                (255, 200, 170),
                copy_rect,
                border_radius=12,
            )

            self._draw_text(
                "Copy",
                copy_rect.centerx,
                copy_rect.centery,
                (140, 80, 80),
                center=True,
                size="small",
            )

            self._add_button(
                copy_rect.x,
                copy_rect.y,
                copy_rect.width,
                copy_rect.height,
                "",
                "copy_room_code",
            )

        my_player = next((player for player in players if player.get("id") == me), None)
        hand = list(my_player.get("hand", [])) if my_player else []
        self._sync_selected_card(hand, state, phase == "playing" and current == me)
        self._draw_hand(hand, state, can_play=phase == "playing" and current == me)
        catchable = self._catchable_uno_player(state, me)

        if phase in {"menu", "lobby"} or not top_card:
            can_start = bool(self.session and self.session.can_start_game)
            # self._add_button(1070, 612, 150, 44, "Start", "start", enabled=can_start)
            action_rect = pygame.Rect(1070, 612, 150, 44)
            self._draw_cute_button(
                action_rect,
                "Start",
                (120, 200, 255) if can_start else (180, 220, 255),
                (80, 160, 255) if can_start else (140, 200, 255),
            )
            
            self._add_button(
                action_rect.x,
                action_rect.y,
                action_rect.width,
                action_rect.height,
                "",
                "start",
                enabled=can_start,
            )
        elif phase == "reaction" or reaction_active:
            self._draw_reaction_controls(state)
        elif phase == "playing":
            selected = self.selected_card if current == me else None
            if selected is not None:
                will_have_uno = my_player is not None and int(my_player.get("card_count", 0)) == 2
                action_label = "UNO" if will_have_uno else "Play"
                action_rect = pygame.Rect(1070, 612, 150, 44)
                self._draw_cute_button(
                    action_rect,
                    action_label,
                    (190, 224, 255),
                    (120, 185, 245),
                )
                self._add_button(
                    action_rect.x,
                    action_rect.y,
                    action_rect.width,
                    action_rect.height,
                    action_label,
                    "play_selected",
                    enabled=True
                )
            elif state.get("drew_this_turn") and current == me:
                action_rect = pygame.Rect(1070, 612, 150, 44)
                self._draw_cute_button(
                    action_rect,
                    "Pass",
                    (255, 180, 150),
                    (255, 130, 100),
                )
                self._add_button(
                    action_rect.x,
                    action_rect.y,
                    action_rect.width,
                    action_rect.height,
                    "Pass",
                    "pass_turn",
                    enabled=True
                )
            else:
                draw_label = "Draw Penalty" if state.get("pending_draw", 0) else "Draw"
                action_rect = pygame.Rect(1070, 612, 150, 44)
                self._draw_cute_button(
                    action_rect,
                    draw_label,
                    (255, 180, 150),
                    (255, 130, 100),
                )
                self._add_button(
                    action_rect.x,
                    action_rect.y,
                    action_rect.width,
                    action_rect.height,
                    draw_label,
                    "draw",
                    enabled=current == me
                )
            protected = set(state.get("uno_protected_player_ids", ()))
            if my_player and int(my_player.get("card_count", 0)) == 1:
                action_rect = pygame.Rect(1055, 520, 174, 44)
                self._draw_cute_button(
                    action_rect,
                    "Call UNO",
                    (255, 200, 170) if me not in protected else (255, 150, 120),
                    (255, 150, 120) if me not in protected else (255, 100, 80),
                )
                self._add_button(
                    action_rect.x,
                    action_rect.y,
                    action_rect.width,
                    action_rect.height,
                    "Call UNO",
                    "call_uno",
                    enabled=me not in protected
                )
            if catchable:
                action_rect = pygame.Rect(1055, 468, 174, 44)
                self._draw_cute_button(
                    action_rect,
                    "Catch UNO",
                    (255, 180, 150),
                    (255, 130, 100),
                )
                self._add_button(
                    action_rect.x,
                    action_rect.y,
                    action_rect.width,
                    action_rect.height,
                    "Catch UNO",
                    "catch_uno",
                    catchable.get("id"),
                    enabled=True
                )

        if phase == "ended":
            winner = self._player_name(players, state.get("winner_id"))
            self._draw_overlay(f"{winner} wins")
            # Replay button
            can_replay = bool(self.session and self.session.can_start_game)
            replay_label = "Replay" if can_replay else "Waiting For Host"
            replay_rect = pygame.Rect(425, 410, 200, 46)
            self._draw_cute_button(
                replay_rect,
                replay_label,
                (120, 200, 255) if can_replay else (180, 220, 255),
                (80, 160, 255) if can_replay else (140, 200, 255),
            )
            self._add_button(
                replay_rect.x,
                replay_rect.y,
                replay_rect.width,
                replay_rect.height,
                replay_label,
                "replay",
                enabled=can_replay
            )

            # Back to menu button
            menu_rect = pygame.Rect(655, 410, 200, 46)
            self._draw_cute_button(
                menu_rect,
                "Back To Menu",
                (255, 180, 150),
                (255, 130, 100),
            )
            self._add_button(
                menu_rect.x,
                menu_rect.y,
                menu_rect.width,
                menu_rect.height,
                "Back To Menu",
                "menu"
            )

        self._draw_prompt(state)
        if isinstance(self.session, OnlineGameSession):
            if self.session and self.session.can_start_game and phase in {"menu", "lobby", "playing"}:
                action_rect = pygame.Rect(1075, 18, 154, 36)
                self._draw_cute_button(
                    action_rect,
                    "Host Settings",
                    (255, 220, 180),
                    (255, 170, 120),
                    font_size=22,
                )
                self._add_button(
                    action_rect.x,
                    action_rect.y,
                    action_rect.width,
                    action_rect.height,
                    "Host Settings",
                    "host_settings"
                )
        if self.host_settings_open:
            self._draw_host_settings(state)
        
        # =========================================
        # DRAW MENU BUTTON
        # =========================================
        action_rect = pygame.Rect(28, 22, 92, 34)
        self._draw_cute_button(
            action_rect,
            "Menu",
            (255, 200, 170),
            (255, 150, 120),
            font_size=22,
        )
        self._add_button(
            action_rect.x,
            action_rect.y,
            action_rect.width,
            action_rect.height,
            "Menu",
            "game_pause"
        )
        
        if self.game_escape_overlay:
            self.buttons.clear()
            self.hand_targets.clear()
            self._draw_game_escape_overlay()
        
        
        #self._draw_buttons()
        error = self.session.error if self.session else None
        if error:
            self._draw_text(error, 640, 690, BAD, center=True)

    def _draw_game_frame(self, state: dict[str, Any] | None) -> None:
        assert self.screen is not None
        # ===== TOP BAR =====
        # pygame.draw.rect(self.screen, (222, 241, 232), pygame.Rect(0, 0, 1280, 92))
        # pygame.draw.rect(self.screen, (232, 246, 239), pygame.Rect(0, 0, 1280, 46))
        # pygame.draw.line(self.screen, BORDER, (0, 92), (1280, 92), 2)
        
        # pygame.draw.rect(self.screen, (229, 244, 237), pygame.Rect(0, 584, 1280, 136))
        # pygame.draw.line(self.screen, BORDER, (0, 584), (1280, 584), 2)
        
        # ===== TABLE CENTER =====
        # table = pygame.Rect(314, 124, 652, 332)
        # table_fill = pygame.Surface(table.size, pygame.SRCALPHA)
        # pygame.draw.ellipse(table_fill, (236, 249, 241, 185), table_fill.get_rect())
        # pygame.draw.ellipse(table_fill, (126, 188, 165, 90), table_fill.get_rect().inflate(-18, -18), 3)
        # pygame.draw.ellipse(table_fill, (255, 255, 255, 110), pygame.Rect(84, 24, 400, 112))
        # self.screen.blit(table_fill, table.topleft)
        
        # ===== SESSION INFO =====
        if self.session:
            self._draw_chip(self.session.info, 144, 22, MUTED, width=224, height=34)

    def _draw_players(self, players: list[dict[str, Any]], current: str | None, me: str | None) -> None:
        assert self.screen is not None
        ordered = players[:]
        if me:
            my_index = next((index for index, player in enumerate(players) if player.get("id") == me), None)
            if my_index is not None:
                ordered = players[my_index:] + players[:my_index]

        slots = [
            {
                "name_rect": pygame.Rect(528, 534, 224, 34),
                "stack_anchor": None,
            },
            {
                "name_rect": pygame.Rect(78, 334, 220, 34),
                "stack_anchor": (110, 198),
            },
            {
                "name_rect": pygame.Rect(528, 114, 224, 34),
                "stack_anchor": (640, 148),
            },
            {
                "name_rect": pygame.Rect(982, 334, 220, 34),
                "stack_anchor": (1114, 198),
            },
        ]

        for index, slot in enumerate(slots):
            player = ordered[index] if index < len(ordered) else None
            active = bool(player and player.get("id") == current)
            mine = bool(player and player.get("id") == me)
            panel_color = (255, 240, 220) if not active else (224, 247, 235)
            border = (255, 160, 180) if active else (255, 200, 210)
            self._draw_panel(slot["name_rect"], panel_color, border=border)

            if player is None:
                label = f"Player {index + 1}: Empty"
                self._draw_text(label, slot["name_rect"].centerx, slot["name_rect"].centery, MUTED, center=True, size="small")
                continue

            card_count = int(player.get("card_count", 0))
            fallback_name = f"Player {index + 1}"
            name = str(player.get("name") or fallback_name)
            label = f"{name}  ({card_count})"
            self._draw_text(label, slot["name_rect"].centerx, slot["name_rect"].centery, TEXT, center=True, size="small")

            if mine:
                continue

            anchor = slot["stack_anchor"]
            if anchor is not None:
                self._draw_opponent_card_stack(anchor[0], anchor[1], card_count)

    def _draw_opponent_card_stack(self, center_x: int, top_y: int, card_count: int) -> None:
        small_w = max(48, int(CARD_W * 0.78))
        small_h = max(72, int(CARD_H * 0.78))
        visible_cards = max(1, min(6, card_count))
        start_x = center_x - (small_w // 2)
        for index in range(visible_cards):
            rect = pygame.Rect(start_x + index * 4, top_y + index * 2, small_w, small_h)
            self._draw_card_back(rect)
        if card_count > visible_cards:
            self._draw_chip(f"+{card_count - visible_cards}", center_x - 36, top_y + small_h + 16, MUTED, width=72)

    def _draw_center_pile(self, top_card: dict[str, str] | None, active_color: str | None, pending_draw: int) -> None:
        assert self.screen is not None
        assert self.card_renderer is not None

        # =========================================
        # CENTER FRAME
        # =========================================
        frame_width = 250
        frame_height = 160

        frame_x = (1280 - frame_width) // 2
        frame_y = (720 - frame_height) // 2 - 20

        frame_rect = pygame.Rect(
            frame_x,
            frame_y,
            frame_width,
            frame_height,
        )

        # Transparent surface
        frame_surface = pygame.Surface(
            (frame_width, frame_height),
            pygame.SRCALPHA,
        )

        # Soft transparent pink fill
        pygame.draw.rect(
            frame_surface,
            (255, 210, 230, 35),
            frame_surface.get_rect(),
            border_radius=24,
        )

        # Outer pink border
        pygame.draw.rect(
            frame_surface,
            (255, 120, 170),
            frame_surface.get_rect(),
            width=2,
            border_radius=24,
        )

        # Inner glow border
        inner_rect = frame_surface.get_rect().inflate(-8, -8)

        pygame.draw.rect(
            frame_surface,
            (255, 220, 235, 120),
            inner_rect,
            width=2,
            border_radius=20,
        )

        self.screen.blit(frame_surface, frame_rect.topleft)
        
        # =========================================
        # CARD POSITIONS
        # =========================================
        deck_x = frame_rect.centerx - CARD_W - 18
        discard_x = frame_rect.centerx + 18

        cards_y = frame_rect.centery - CARD_H // 2

        deck_rect = pygame.Rect(
            deck_x,
            cards_y,
            CARD_W,
            CARD_H,
        )

        discard_rect = pygame.Rect(
            discard_x,
            cards_y,
            CARD_W,
            CARD_H,
        )

        # =========================================
        # CENTER GLOW
        # =========================================
        # glow = pygame.Surface((260, 260), pygame.SRCALPHA)

        # pygame.draw.circle(
        #     glow,
        #     (255, 255, 255, 55),
        #     (130, 130),
        #     110,
        # )

        # self.screen.blit(
        #     glow,
        #     (
        #         frame_rect.centerx - 130,
        #         frame_rect.centery - 130,
        #     ),
        # )

        # =========================================
        # DRAW STACK
        # =========================================
        self._draw_card_back(deck_rect)

        # =========================================
        # DISCARD STACK
        # =========================================
        if top_card:
            card = card_from_dict(top_card)

            self.card_renderer.draw_card(
                self.screen,
                card,
                discard_rect,
            )

        # =========================================
        # ACTIVE COLOR DOT
        # =========================================
        if active_color:
            color = color_tuple(active_color)

            indicator_x = frame_rect.right + 55
            indicator_y = frame_rect.centery - 8

            pygame.draw.circle(
                self.screen,
                color,
                (indicator_x, indicator_y),
                24,
            )

            pygame.draw.circle(
                self.screen,
                (255, 255, 255),
                (indicator_x, indicator_y),
                3,
                width=2,
            )

        # =========================================
        # PENDING DRAW CHIP
        # =========================================
        if pending_draw:

            self._draw_chip(
                f"+{pending_draw}",
                frame_rect.centerx - 36,
                frame_rect.bottom + 18,
                BAD,
                width=72,
            )
        # # Positions for deck and discard stacks
        # deck_card_rect = pygame.Rect(410, 200, CARD_W, CARD_H)
        # discard_card_rect = pygame.Rect(580, 200, CARD_W, CARD_H)
        
        # # Frame bounding both stacks with padding
        # frame_padding = 24
        # frame_left = deck_card_rect.left - frame_padding
        # frame_top = deck_card_rect.top - frame_padding
        # frame_width = discard_card_rect.right - deck_card_rect.left + frame_padding
        # frame_height = deck_card_rect.height + 2 * frame_padding
        # frame_rect = pygame.Rect(frame_left, frame_top, frame_width, frame_height)
        
        # # Draw transparent frame background
        # frame_surface = pygame.Surface((frame_rect.width, frame_rect.height), pygame.SRCALPHA)
        # frame_surface.fill((255, 255, 255, 15))
        # self.screen.blit(frame_surface, frame_rect.topleft)
        
        # # Draw pink border around frame
        # pink_border = (255, 120, 160)
        # pygame.draw.rect(self.screen, pink_border, frame_rect, 3, border_radius=12)
        
        # # Draw deck card back
        # self._draw_card_back(deck_card_rect)
        
        # # Draw discard card
        # if top_card:
        #     card = card_from_dict(top_card)
        #     self.card_renderer.draw_card(self.screen, card, discard_card_rect)
        # else:
        #     self._draw_card_back(discard_card_rect)
        
        # # Draw active color indicator
        # if active_color:
        #     color = color_tuple(active_color)
        #     circle_x = (frame_left + frame_rect.right) // 2
        #     circle_y = frame_rect.bottom + 32
        #     pygame.draw.circle(self.screen, color, (circle_x, circle_y), 22)
        #     pygame.draw.circle(self.screen, TEXT, (circle_x, circle_y), 22, 2)
        
        # # Draw pending draw counter
        # if pending_draw:
        #     counter_x = (frame_left + frame_rect.right) // 2 - 36
        #     counter_y = frame_rect.bottom + 60
        #     self._draw_chip(f"+{pending_draw}", counter_x, counter_y, BAD, width=72)

    def _draw_room_code_panel(self) -> None:
        if not isinstance(self.session, OnlineGameSession) or not self.session.room_code:
            return
        assert self.screen is not None
        font, small, big = self._fonts()
        panel = RoomCodePanel(self.session.room_code, pygame.Rect(1032, 168, 198, 110))
        panel.draw(self.screen, font, small, big)
        self._add_button(panel.copy_rect.x, panel.copy_rect.y, panel.copy_rect.width, panel.copy_rect.height, "Copy Code", "copy_room_code")

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
            selected = self.selected_card is not None and card_data["id"] == self.selected_card.get("id")
            lift = 28 if selected else 16 if hover else 0
            draw_rect = rect.move(0, -lift)
            if hover or selected:
                halo = draw_rect.inflate(10, 10)
                pygame.draw.rect(self.screen, ACCENT if not selected else GOOD, halo, 3, border_radius=12)
            self.card_renderer.draw_card(self.screen, card_from_dict(card_data), draw_rect)
            if selected:
                self._draw_text("Chosen", draw_rect.centerx, draw_rect.y - 12, GOOD, center=True, size="small")
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
        players = state.get("players", [])
        source_name = self._player_name(players, source)
        if isinstance(self.session, LocalGameSession):
            x = 1028
            y = 148
            self._draw_text(f"{source_name} played an 8!", x, y - 52, TEXT, size="small")
            self._draw_text("React fast", x, y - 28, TEXT)
            for player in players:
                player_id = player.get("id")
                done = player_id in responders
                rect = pygame.Rect(x, y, 190, 38)
                self._draw_cute_button(
                    rect,
                    f"{player.get('name')}",
                    (190, 224, 255) if not done else (218, 226, 230),
                    (120, 185, 245) if not done else (176, 188, 196),
                    font_size=22,
                )
                self._add_button(rect.x, rect.y, rect.width, rect.height, f"{player.get('name')}", "react_player", player_id, enabled=not done)
                y += 46
        else:
            me = self.session.player_id if self.session else None
            done = me in responders
            self._draw_text(f"{source_name} played an 8!", 1055, 520, TEXT, size="small")
            rect = pygame.Rect(1070, 552, 150, 44)
            self._draw_cute_button(
                rect,
                "React!",
                (190, 224, 255) if not done else (218, 226, 230),
                (120, 185, 245) if not done else (176, 188, 196),
            )
            self._add_button(rect.x, rect.y, rect.width, rect.height, "React!", "react", enabled=not done)

    def _draw_prompt(self, state: dict[str, Any]) -> None:
        if self.pending_card is None:
            return
        self._draw_overlay("Choose")
        if self.pending_card["rank"] == "0" and self.pending_pass_direction is None:
            clockwise_rect = pygame.Rect(470, 396, 150, 44)
            counter_rect = pygame.Rect(660, 396, 190, 44)
            self._draw_cute_button(clockwise_rect, "Clockwise", (255, 180, 150), (255, 130, 100))
            self._draw_cute_button(counter_rect, "Counter", (255, 180, 150), (255, 130, 100))
            self._add_button(470, 396, 150, 44, "Clockwise", "choose_pass_direction", "clockwise")
            self._add_button(660, 396, 190, 44, "Counter", "choose_pass_direction", "counter_clockwise")
            return
        if self.pending_card["rank"] in {"wild", "wild_draw_four"} and self.pending_color is None:
            colors = [("red", 430), ("yellow", 540), ("green", 650), ("blue", 760)]
            for color, x in colors:
                color_rect = pygame.Rect(x, 396, 80, 44)
                self._draw_cute_button(color_rect, color.title(), color_tuple(color), color_tuple(color), font_size=22)
                self._add_button(x, 396, 80, 44, color.title(), "choose_color", color)
            return
        if self.pending_card["rank"] == "7":
            players = state.get("players", [])
            x = 390
            y = 388
            me = self.session.player_id if self.session else state.get("current_player_id")
            for player in players:
                if player.get("id") != me:
                    player_rect = pygame.Rect(x, y, 150, 42)
                    self._draw_cute_button(player_rect, player.get("name", "Player"), (255, 180, 150), (255, 130, 100))
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
        # self._draw_table_texture()
        if self.card_renderer is None:
            return
        if not self.user_settings.show_background_art:
            self.screen.fill(TABLE_GREEN)
            return
        # Optional backgrounds use assets/images/placeholder.jfif until real art is added.
        image = self.card_renderer.assets.load_background(name)
        if image is None:
            self.screen.fill(TABLE_GREEN)
            return
        scaled = pygame.transform.smoothscale(image, self.screen.get_size())
        scaled.set_alpha(255 if name == "table_background" else 255)
        self.screen.blit(scaled, (0, 0))

    def _draw_title(self, title: str) -> None:
        self._draw_text(title, 640, 130, TEXT, center=True, size="big")

    def _draw_buttons(self) -> None:
        assert self.screen is not None
        font, small, _big = self._fonts()
        for button in self.buttons:
            button.draw(self.screen, font, small)

    def _draw_panel(
        self,
        rect: pygame.Rect,
        color: tuple[int, int, int],
        border: tuple[int, int, int] = BORDER,
        radius: int = 8,
    ) -> None:
        assert self.screen is not None
        Panel(rect, color, border, radius).draw(self.screen)

    def _draw_chip(self, label: str, x: int, y: int, color: tuple[int, int, int], width: int | None = None, height: int | None = None) -> None:
        assert self.screen is not None
        _font, small, _big = self._fonts()
        chip_width = width or max(74, small.size(label)[0] + 24)
        chip_height = height or max(74, small.size(label)[0] + 24)
        Chip(label, pygame.Rect(x, y, chip_width, chip_height), color).draw(self.screen, _font)

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
        
        # =========================================
        # MAX PLAYERS ROW
        # =========================================
        row_y = 380

        # label
        self._draw_text(
            "Max Players",
            420,
            row_y,
            TEXT,
        )

        # value
        self._draw_text(
            str(max_players),
            640,
            row_y + 12,
            MUTED,
            center=True,
        )

        # minus button
        host_min_rect = pygame.Rect(
            710,
            row_y - 10,
            42,
            38,
        )

        # plus button
        host_max_rect = pygame.Rect(
            780,
            row_y - 10,
            42,
            38,
        )

        self._draw_cute_button(
            host_min_rect,
            "-",
            (255, 180, 150),
            (255, 130, 100),
        )

        self._draw_cute_button(
            host_max_rect,
            "+",
            (120, 200, 255),
            (80, 160, 255),
        )

        self._add_button(
            host_min_rect.x,
            host_min_rect.y,
            host_min_rect.width,
            host_min_rect.height,
            "-",
            "host_max_down",
            enabled=max_players > max(2, connected),
        )

        self._add_button(
            host_max_rect.x,
            host_max_rect.y,
            host_max_rect.width,
            host_max_rect.height,
            "+",
            "host_max_up",
            enabled=max_players < 4,
        )
        # self._draw_text("Max Players", 420, 374, TEXT)
        # self._draw_text(str(max_players), 640, 374, MUTED, center=True)
        # host_min_rect = pygame.Rect(710, 360, 42, 38)
        # host_max_rect = pygame.Rect(764, 360, 42, 38)
        # self._draw_cute_button(host_min_rect, "-", (255, 180, 150), (255, 130, 100))
        # self._draw_cute_button(host_max_rect, "+", (120, 200, 255), (80, 160, 255))
        # self._add_button(710, 360, 42, 38, "-", "host_max_down", enabled=max_players > max(2, connected))
        # self._add_button(764, 360, 42, 38, "+", "host_max_up", enabled=max_players < 4)
        
        # =========================================
        # LOBBY ROW
        # =========================================

        row_y = 430

        # Label
        self._draw_text(
            "Lobby",
            420,
            row_y,
            TEXT,
        )

        # Status text (center aligned)
        self._draw_text(
            "Locked" if lobby_locked else "Open",
            640,
            row_y + 12,
            MUTED,
            center=True,
        )

        # Toggle button aligned with row
        toggle_rect = pygame.Rect(
            710,
            row_y - 10,
            110,
            38,
        )

        self._draw_cute_button(
            toggle_rect,
            "Toggle",
            (255, 200, 170),
            (255, 150, 120),
        )

        self._add_button(
            toggle_rect.x,
            toggle_rect.y,
            toggle_rect.width,
            toggle_rect.height,
            "Toggle",
            "host_toggle_lock",
        )
        # self._draw_text("Lobby", 420, 424, TEXT)
        # self._draw_text("Locked" if lobby_locked else "Open", 640, 424, MUTED, center=True)
        # toggle_rect = pygame.Rect(710, 410, 96, 38)
        # self._draw_cute_button(toggle_rect, "Toggle", (255, 200, 170), (255, 150, 120))
        # self._add_button(710, 410, 96, 38, "Toggle", "host_toggle_lock")
        
        # self._draw_text("These settings apply to this online room.", 640, 462, MUTED, center=True, size="small")
        close_rect = pygame.Rect(530, 515, 220, 44)
        self._draw_cute_button(close_rect, "Close", (255, 180, 150), (255, 130, 100))
        self._add_button(530, 515, 220, 44, "Close", "host_settings_close")

    def _draw_game_escape_overlay(self) -> None:
        if self.game_escape_overlay == "settings":
            self._draw_game_settings_overlay()
        elif self.game_escape_overlay == "leave_confirm":
            self._draw_leave_confirm_overlay()
        else:
            self._draw_pause_overlay()

    def _draw_pause_overlay(self) -> None:
        self._draw_overlay("Game Room")
        self._draw_text("Paused. The room is still running.", 640, 374, MUTED, center=True, size="small")
        resume_rect = pygame.Rect(430, 414, 130, 44)
        settings_rect = pygame.Rect(575, 414, 130, 44)
        leave_rect = pygame.Rect(720, 414, 130, 44)

        self._draw_cute_button(resume_rect, "Resume", (120, 200, 255), (80, 160, 255))
        self._draw_cute_button(settings_rect, "Settings", (255, 200, 170), (255, 150, 120))
        self._draw_cute_button(leave_rect, "Leave", (255, 180, 150), (255, 130, 100))

        self._add_button(430, 414, 130, 44, "Resume", "game_resume")
        self._add_button(575, 414, 130, 44, "Settings", "game_settings")
        self._add_button(720, 414, 130, 44, "Leave", "game_leave_request")

    def _draw_game_settings_overlay(self) -> None:
        self._draw_overlay("Settings")
        rows = [
            ("Volume", "volume", f"{int(self.user_settings.volume * 100)}%"),
            ("Fullscreen", "fullscreen", "On" if self.user_settings.fullscreen else "Off"),
        ]
        font, small, _big = self._fonts()
        y = 360
        for label, key, value in rows:
            row_rect = pygame.Rect(430, y - 10, 420, 52)
            SettingsRow(row_rect, label, value).draw(self.screen, font, small)
            if key == "volume":
                volume_up_rect = pygame.Rect(802, y, 42, 36)
                volume_down_rect = pygame.Rect(750, y, 42, 36)
                self._draw_cute_button(volume_down_rect, "-", (255, 180, 150), (255, 130, 100))
                self._draw_cute_button(volume_up_rect, "+", (120, 200, 255), (80, 160, 255))
                self._add_button(750, y, 42, 36, "-", "volume_down")
                self._add_button(802, y, 42, 36, "+", "volume_up")
            else:
                toggle_rect = pygame.Rect(750, y, 94, 36)
                self._draw_cute_button(toggle_rect, "Toggle", (255, 200, 170), (255, 150, 120))
                self._add_button(742, y, 102, 36, "Toggle", f"toggle_{key}")
            y += 58
        back_rect = pygame.Rect(475, 514, 150, 42)
        confirm_rect = pygame.Rect(655, 514, 150, 42)
        self._draw_cute_button(back_rect, "Back", (255, 180, 150), (255, 130, 100))
        self._draw_cute_button(confirm_rect, "Confirm", (120, 200, 255), (80, 160, 255))
        self._add_button(475, 514, 150, 42, "Back", "game_resume")
        self._add_button(655, 514, 150, 42, "Confirm", "game_settings_confirm")

    def _draw_leave_confirm_overlay(self) -> None:
        self._draw_overlay("Leave Room?")
        self._draw_text("You will leave this room and return to the menu.", 640, 374, MUTED, center=True, size="small")
        cancel_rect = pygame.Rect(470, 414, 150, 44)
        leave_rect = pygame.Rect(660, 414, 150, 44)
        self._draw_cute_button(cancel_rect, "Cancel", (255, 180, 150), (255, 130, 100))
        self._draw_cute_button(leave_rect, "Leave", (255, 180, 150), (255, 130, 100))
        self._add_button(470, 414, 150, 44, "Cancel", "game_resume")
        self._add_button(660, 414, 150, 44, "Leave", "game_leave_confirm")

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
        return (
            self.fonts.get("SansitaOne",24),  #font
            self.fonts.get("SansitaOne",17),  #small
            self.fonts.get("SansitaOne", 30)   #big
        )

    def _handle_click(self, pos: tuple[int, int]) -> None:
        for button in reversed(self.buttons):
            if button.contains(pos):
                self.click_feedback.append((pos, 0.0))
                self._safe_handle_action(button.action, button.payload)
                return
        if self.mode == "game" and self.pending_card is None:
            for rect, card_data in reversed(self.hand_targets):
                if rect.collidepoint(pos):
                    self._safe_run("Could not select that card", lambda: self._select_card(card_data))
                    return

    def _safe_handle_action(self, action: str, payload: Any) -> None:
        self._safe_run("Action failed", lambda: self._handle_action(action, payload))

    def _safe_run(self, title: str, fn) -> None:
        try:
            fn()
        except Exception as exc:
            self._handle_runtime_error(title, exc)

    def _handle_action(self, action: str, payload: Any) -> None:
        if action == "menu":
            self._go_menu()
        elif action == "game_pause":
            self.game_escape_overlay = "pause"
        elif action == "game_resume":
            self.game_escape_overlay = None
        elif action == "game_settings":
            self.game_escape_overlay = "settings"
        elif action == "game_settings_confirm":
            self._save_settings(show_notice=False)
            self.game_escape_overlay = None
        elif action == "game_leave_request":
            self.game_escape_overlay = "leave_confirm"
        elif action == "game_leave_confirm":
            self._go_menu()
        elif action == "bot_room":
            self._start_bot_room(int(payload or 1))
        elif action == "choose_mode":
            self._set_mode("choose_mode")
            self.notice = ""
            self.notice_overlay = None
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
        elif action == "copy_room_code":
            self._copy_room_code()
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
        elif action == "replay" and self.session:
            self.game_escape_overlay = None
            self.card_motions.clear()
            self.session.start_game()
            self.sounds.play("card_play")
        elif action == "draw" and self.session:
            self.session.draw_card()
            self.sounds.play("card_draw")
        elif action == "pass_turn" and self.session:
            self.selected_card = None
            self.session.pass_turn()
        elif action == "play_selected":
            self._play_selected_card()
        elif action == "call_uno" and self.session:
            self.session.call_uno()
            self.sounds.play("reaction_hit")
        elif action == "catch_uno" and self.session:
            self.session.catch_uno(str(payload))
            self.sounds.play("reaction_hit")
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
        if self.selected_card is not None and self.selected_card.get("id") == card_data.get("id"):
            self.selected_card = None
            return
        self.selected_card = card_data
        self.pending_card = None
        self.pending_color = None
        self.pending_pass_direction = None

    def _play_selected_card(self) -> None:
        if self.selected_card is None:
            return
        card_data = self.selected_card
        if card_data["rank"] in {"wild", "wild_draw_four", "7", "0"}:
            self.pending_card = card_data
            self.pending_color = None
            self.pending_pass_direction = None
            return
        if self.session:
            auto_uno = self._selected_play_would_leave_uno()
            self.session.play_card(card_data["id"])
            if auto_uno:
                self.session.call_uno()
            self.sounds.play("card_play")
        self.selected_card = None

    def _send_pending_card(self, target_player_id: str | None = None) -> None:
        if self.session and self.pending_card:
            auto_uno = self._selected_play_would_leave_uno()
            self.session.play_card(self.pending_card["id"], self.pending_color, target_player_id, self.pending_pass_direction)
            if auto_uno:
                self.session.call_uno()
            self.sounds.play("card_play")
        self.selected_card = None
        self.pending_card = None
        self.pending_color = None
        self.pending_pass_direction = None

    def _handle_game_escape(self) -> None:
        if self.game_escape_overlay is None:
            self.game_escape_overlay = "pause"
        else:
            self.game_escape_overlay = None

    def _handle_uno_shortcut(self) -> bool:
        if self.mode != "game" or self.session is None:
            return False
        if any(box.active for box in self.input_boxes):
            return False
        state = self.session.snapshot()
        if not state:
            return False
        me = self.session.player_id
        my_player = self._state_player(state, me)
        protected = set(state.get("uno_protected_player_ids", ()))
        if my_player and int(my_player.get("card_count", 0)) == 1 and me not in protected:
            self._safe_handle_action("call_uno", None)
            return True
        target = self._catchable_uno_player(state, me)
        if target:
            self._safe_handle_action("catch_uno", target.get("id"))
            return True
        return True

    def _handle_play_shortcut(self) -> bool:
        if self.mode != "game" or self.session is None:
            return False
        if any(box.active for box in self.input_boxes):
            return False
        if self.selected_card is None or self.pending_card is not None or self.game_escape_overlay:
            return False
        self._safe_handle_action("play_selected", None)
        return True

    def _selected_play_would_leave_uno(self) -> bool:
        if self.session is None or self.selected_card is None:
            return False
        state = self.session.snapshot()
        if not state:
            return False
        me = self.session.player_id
        my_player = self._state_player(state, me)
        return bool(my_player and int(my_player.get("card_count", 0)) == 2)

    def _sync_selected_card(self, hand: list[dict[str, str]], state: dict[str, Any], can_play: bool) -> None:
        if self.selected_card is None:
            return
        selected_id = self.selected_card.get("id")
        fresh = next((card for card in hand if card.get("id") == selected_id), None)
        if fresh is None or not can_play or not is_card_playable(fresh, state):
            self.selected_card = None
            if self.pending_card is not None and self.pending_card.get("id") == selected_id:
                self.pending_card = None
                self.pending_color = None
                self.pending_pass_direction = None
            return
        self.selected_card = fresh

    def _state_player(self, state: dict[str, Any], player_id: str | None) -> dict[str, Any] | None:
        return next((player for player in state.get("players", []) if player.get("id") == player_id), None)

    def _catchable_uno_player(self, state: dict[str, Any], viewer_id: str | None) -> dict[str, Any] | None:
        protected = set(state.get("uno_protected_player_ids", ()))
        for player in state.get("players", []):
            player_id = player.get("id")
            if player_id == viewer_id or not player.get("connected", True):
                continue
            if int(player.get("card_count", 0)) == 1 and player_id not in protected:
                return player
        return None

    def _start_bot_room(self, bot_count: int = 1) -> None:
        self._close_session()
        bot_count = max(1, min(3, bot_count))
        self.session = LocalGameSession(player_count=bot_count + 1, bot_count=bot_count)
        self.game_escape_overlay = None
        self._last_room_notice_sequence = 0
        self._set_mode("game")
        self.notice = ""

    def _start_local(self, player_count: int = 2, bot_count: int = 0) -> None:
        if bot_count <= 0:
            raise ValueError("Pure local hotseat mode has been removed. Choose a bot room or online multiplayer.")
        self._start_bot_room(bot_count)

    def _connect_from_form(self) -> None:
        if self.connecting:
            self.notice = "Still connecting. Please wait a moment."
            return
        name = self.input_boxes[0].value.strip() or "Player"
        room_code = None if self.mode == "host_room" else self.input_boxes[1].value.strip().upper()
        if self.mode == "join_room" and not room_code:
            self.notice = "Enter a room code before connecting."
            self.feedback.push_toast("Room code needed", "Ask the host for the room code, then try again.", BAD, duration=3.2)
            return
        self._begin_online_connection(name, room_code)

    def _relay_endpoint(self) -> tuple[str, int]:
        relay_url = self._relay_url()
        return parse_relay_url(relay_url)

    def _relay_url(self) -> str:
        load_env()
        return os.environ.get("UNO_RELAY_URL", DEFAULT_RELAY_URL).strip() or DEFAULT_RELAY_URL

    def _begin_online_connection(self, name: str, room_code: str | None) -> None:
        is_host = self.mode == "host_room"
        self._connection_id += 1
        token = self._connection_id
        self.connecting = True
        self.notice = "Creating room..." if is_host else "Joining room..."
        self.feedback.push_toast(self.notice, "One moment, please.", ACCENT, duration=2.2)

        def worker() -> None:
            try:
                if is_host:
                    relay_host, relay_port = self._relay_endpoint()
                    target_room_code = None
                else:
                    relay_host, relay_port = self._relay_endpoint()
                    target_room_code = room_code
                session = OnlineGameSession(relay_host, relay_port, name, is_host=is_host, room_code=target_room_code)
                session.info = "Room owner" if is_host else "Online player"
                result = (token, True, session, "")
            except Exception as exc:
                result = (token, False, None, self._connection_error_message(exc))
            with self._connection_lock:
                self._connection_result = result

        threading.Thread(target=worker, daemon=True).start()

    def _finish_pending_connection(self) -> None:
        with self._connection_lock:
            result = self._connection_result
            self._connection_result = None
        if result is None:
            return
        token, ok, session, message = result
        if token != self._connection_id:
            if session is not None:
                session.close()
            return
        self.connecting = False
        if ok and session is not None:
            self._close_session()
            self.session = session
            self.notice = ""
            self.game_escape_overlay = None
            snapshot = session.snapshot() or {}
            self._last_room_notice_sequence = int(snapshot.get("room_notice_sequence", 0))
            self._set_mode("game")
            if session.is_host:
                self.feedback.push_toast("Room created", "Share the room code when you are ready.", GOOD, duration=3.4)
            else:
                self.feedback.push_toast("Joined room", "You are in. Wait for the host to start.", GOOD, duration=3.4)
            return
        title = "Could not create room" if self.mode == "host_room" else "Could not join room"
        self.feedback.push_toast(title, message, BAD, duration=5.0)
        self.notice = message

    def _connection_error_message(self, exc: Exception) -> str:
        raw = str(exc).strip()
        if isinstance(exc, TimeoutError) or "timed out" in raw.lower():
            return "Online service is not responding. Please try again in a moment."
        if "did not confirm the room" in raw.lower():
            return "Online service is not responding. Please try again in a moment."
        if "did not return a room code" in raw.lower():
            return "The room could not be created. Please try again."
        if "did not assign a player slot" in raw.lower():
            return "The room could not add you. Please try again."
        if "refused" in raw.lower() or "actively refused" in raw.lower():
            return "Online service is unavailable right now."
        if "forbidden by its access permissions" in raw.lower():
            return "Online service is unavailable right now."
        if "room code is required" in raw.lower():
            return "Enter a room code to join."
        if "room not found" in raw.lower():
            return "That room does not exist. Check the code and try again."
        if raw.lower() == "room is full":
            return "That room is full."
        if "name already taken" in raw.lower():
            return "That name is already in this room."
        return raw or "Could not connect."

    def _copy_room_code(self) -> None:
        if not isinstance(self.session, OnlineGameSession) or not self.session.room_code:
            return
        code = self.session.room_code
        try:
            self._copy_text_to_clipboard(code)
            self.feedback.push_toast("Room code copied!", f"{code} is ready to paste.", GOOD, duration=2.6)
        except Exception as exc:
            self.feedback.push_toast("Copy failed", str(exc), BAD, duration=3.0)

    def _copy_text_to_clipboard(self, text: str) -> None:
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
            return
        except Exception:
            pass
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()

    def _go_menu(self) -> None:
        self._close_session()
        self.input_boxes.clear()
        self.selected_card = None
        self.pending_card = None
        self.pending_color = None
        self.pending_pass_direction = None
        self.game_escape_overlay = None
        self.host_settings_open = False
        self.connecting = False
        self._connection_id += 1
        self._last_session_error = None
        self._last_room_notice_sequence = 0
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

    def _return_home_with_notice(self, message: str) -> None:
        self._go_menu()
        self.notice = message

    def _observe_room_notices(self) -> None:
        if self.mode != "game" or self.session is None:
            return
        state = self.session.snapshot()
        if not state:
            return
        sequence = int(state.get("room_notice_sequence", 0) or 0)
        if sequence <= self._last_room_notice_sequence:
            return
        self._last_room_notice_sequence = sequence
        message = str(state.get("room_notice") or "").strip()
        if message:
            self.feedback.push_toast("Room update", message, MUTED, duration=3.8)

    def _handle_session_error(self) -> None:
        if self.mode != "game" or self.session is None:
            return
        error = self.session.error
        if not error:
            self._last_session_error = None
            self._session_error_clear_at = 0.0
            return
        is_online = isinstance(self.session, OnlineGameSession)
        persistent = is_online and (error.strip().lower() == "room is full" or "lost connection" in error.lower())
        if error != self._last_session_error:
            self._last_session_error = error
            self.feedback.push_toast("Notice", self._friendly_session_error(error), BAD, duration=4.8)
            self._session_error_clear_at = 0.0 if persistent else monotonic() + 4.8
        elif self._session_error_clear_at and monotonic() >= self._session_error_clear_at:
            self.session.error = None
            self._last_session_error = None
            self._session_error_clear_at = 0.0
            return
        if is_online and error.strip().lower() == "room is full":
            self._go_menu()
            self.notice = "That room is full."
            self.notice_overlay = "That room is full."
        elif is_online and "lost connection" in error.lower():
            self.notice = self._friendly_session_error(error)

    def _friendly_session_error(self, error: str) -> str:
        normalized = error.strip().lower()
        if normalized == "room not found":
            return "That room does not exist. Check the code and try again."
        if normalized == "room is full":
            return "That room is full."
        if "lost connection" in normalized:
            return "Connection lost. Please return to the menu and try again."
        if "legal card" in normalized:
            return "You still have a playable card."
        if "already called uno" in normalized:
            return "UNO was already called."
        if "does not have uno" in normalized:
            return "That player does not have one card."
        if "already in a room" in normalized:
            return "You are already in a room."
        if "name already taken" in normalized:
            return "That name is already in this room."
        return error or "Something went wrong."

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
        self.session.host_settings(max_players=int(state.get("max_players", 4)) + delta)

    def _toggle_host_lock(self) -> None:
        if not isinstance(self.session, OnlineGameSession) or not self.session.is_host:
            return
        state = self.session.snapshot() or {}
        self.session.host_settings(lobby_locked=not bool(state.get("lobby_locked", False)))

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
        try:
            save_user_settings(self.user_settings)
            self._apply_user_settings()
            if show_notice:
                self.notice = "Settings saved"
                self.feedback.push_toast("Settings saved", "Your preferences are updated.", GOOD, duration=2.8)
        except Exception as exc:
            self.notice = f"Could not save settings: {exc}"
            self.feedback.push_toast("Settings not saved", str(exc), BAD, duration=4.0)

    def _apply_user_settings(self) -> None:
        try:
            self.sounds.configure(self.user_settings.sound_enabled, self.user_settings.volume)
            if self.card_renderer is not None:
                self.card_renderer.show_missing_labels = self.user_settings.show_missing_card_labels
            if self.screen is not None:
                flags = pygame.FULLSCREEN if self.user_settings.fullscreen else 0
                is_fullscreen = bool(self.screen.get_flags() & pygame.FULLSCREEN)
                if is_fullscreen != self.user_settings.fullscreen:
                    self.screen = pygame.display.set_mode((self.settings.width, self.settings.height), flags)
        except pygame.error as exc:
            self.notice = f"Could not apply display settings: {exc}"
            self.feedback.push_toast("Display setting failed", str(exc), BAD, duration=4.0)

    def _player_name(self, players: list[dict[str, Any]], player_id: str | None) -> str:
        for player in players:
            if player.get("id") == player_id:
                return str(player.get("name"))
        return "None"

    def _handle_runtime_error(self, title: str, exc: Exception) -> None:
        message = str(exc) or exc.__class__.__name__
        self.notice = message
        self.feedback.push_toast(title, message, BAD, duration=5.0)
        if self.mode not in {"menu", "settings", "instructions"}:
            self._return_home_with_notice(message)

def card_from_dict(data: dict[str, str]) -> Card:
    return Card(data["id"], CardColor(data["color"]), CardRank(data["rank"]))


def parse_relay_url(relay_url: str) -> tuple[str, int]:
    cleaned = relay_url.strip()
    if "://" in cleaned:
        _scheme, cleaned = cleaned.split("://", 1)
    try:
        host, raw_port = cleaned.rsplit(":", 1)
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("Relay URL must look like tcp://HOST:PORT.") from exc
    host = host.strip()
    if not host or port <= 0:
        raise ValueError("Relay URL must include host and port.")
    return host, port


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
