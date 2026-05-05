from __future__ import annotations

import socket
import threading
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any

import pygame

from application.commands.draw_card import DrawCardCommand
from application.commands.play_card import PlayCardCommand
from application.commands.react_event import ReactEventCommand
from application.dto.game_state_dto import game_state_to_dto
from application.handlers.draw_handler import DrawHandler
from application.handlers.play_card_handler import PlayCardHandler
from application.handlers.reaction_handler import ReactionHandler
from config.enums import CardColor, CardRank, PassDirection
from config.settings import DEFAULT_SETTINGS
from config.user_settings import UserSettings, load_user_settings, save_user_settings
from domain.entities.card import Card
from domain.entities.player import Player
from domain.state.game_state import GameState
from infrastructure.network.client import GameClient
from infrastructure.network.protocol import MessageType, NetworkMessage
from presentation.audio.sound_manager import SoundManager
from presentation.rendering.card_renderer import CardRenderer
from presentation.scenes.end_scene import EndScene
from presentation.scenes.game_scene import GameScene
from presentation.scenes.lobby_scene import LobbyScene
from presentation.scenes.menu_scene import MenuScene
from presentation.scenes.settings_scene import SettingsScene
from systems.setup.game_initializer import GameInitializer
from systems.ai.bot_player import BotPlayerController


CARD_W = 94
CARD_H = 132
TABLE_GREEN = (213, 239, 224)
PANEL = (250, 246, 235)
PANEL_2 = (230, 244, 247)
TEXT = (49, 61, 73)
MUTED = (105, 121, 130)
ACCENT = (238, 185, 145)
BAD = (220, 119, 124)
GOOD = (139, 202, 166)


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
        pygame.draw.rect(surface, PANEL_2, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=6)
        surface.blit(small.render(self.label, True, MUTED), (self.rect.x, self.rect.y - 22))
        clipped = self.value[-24:]
        surface.blit(font.render(clipped, True, TEXT), (self.rect.x + 12, self.rect.y + 10))


class LocalGameSession:
    def __init__(self, player_count: int = 2, bot_count: int = 0) -> None:
        human_count = max(1, player_count - bot_count)
        players = [Player(f"p{i + 1}", f"Player {i + 1}") for i in range(human_count)]
        for index in range(bot_count):
            bot_id = len(players) + 1
            players.append(Player(f"p{bot_id}", f"Bot {index + 1}", is_bot=True))
        self.state = GameState(players=players)
        self.initializer = GameInitializer()
        self.play_handler = PlayCardHandler()
        self.draw_handler = DrawHandler()
        self.reaction_handler = ReactionHandler()
        self.bot_controller = BotPlayerController()
        self._bot_action_at = 0.0
        self.error: str | None = None
        self.info = "Local hotseat"
        self.start_game()

    @property
    def player_id(self) -> str | None:
        return self.state.current_player.id if self.state.current_player else None

    @property
    def can_start_game(self) -> bool:
        return True

    def snapshot(self) -> dict[str, Any] | None:
        return game_state_to_dto(self.state, self.player_id).to_dict()

    def start_game(self) -> None:
        self._run(lambda: self.initializer.start(self.state))

    def play_card(
        self,
        card_id: str,
        chosen_color: str | None = None,
        target_player_id: str | None = None,
        pass_direction: str | None = None,
    ) -> None:
        player_id = self.player_id
        if player_id is None:
            return
        color = CardColor(chosen_color) if chosen_color else None
        direction = PassDirection(pass_direction) if pass_direction else None
        self._run(lambda: self.play_handler.handle(self.state, PlayCardCommand(player_id, card_id, color, target_player_id, direction)))

    def draw_card(self) -> None:
        player_id = self.player_id
        if player_id is None:
            return
        self._run(lambda: self.draw_handler.handle(self.state, DrawCardCommand(player_id)))

    def pass_turn(self) -> None:
        player_id = self.player_id
        if player_id is None:
            return
        from application.commands.pass_turn import PassTurnCommand
        from application.handlers.pass_turn_handler import PassTurnHandler

        self._run(lambda: PassTurnHandler().handle(self.state, PassTurnCommand(player_id)))

    def react(self, player_id: str | None = None) -> None:
        target = player_id or self.player_id
        if target is None:
            return
        self._run(lambda: self.reaction_handler.handle(self.state, ReactEventCommand(target)))

    def update(self) -> None:
        if self.state.reaction.active:
            for player in self.state.players:
                if player.is_bot and player.id not in self.state.reaction.responders:
                    self.react(player.id)
        if self.state.reaction.active and self.reaction_handler.finish_if_ready(self.state):
            self.error = None
            self._bot_action_at = monotonic() + 0.5
        current = self.state.current_player
        if current is not None and current.is_bot and not self.state.reaction.active and self.state.winner_id is None:
            now = monotonic()
            if self._bot_action_at == 0.0:
                self._bot_action_at = now + 0.6
            elif now >= self._bot_action_at:
                self._run(lambda: self.bot_controller.take_turn(self.state, current))
                self._bot_action_at = monotonic() + 0.6
        elif current is not None and not current.is_bot:
            self._bot_action_at = 0.0

    def close(self) -> None:
        pass

    def _run(self, fn) -> None:
        try:
            fn()
            self.error = None
        except Exception as exc:
            self.error = str(exc)


class OnlineGameSession:
    def __init__(
        self,
        host: str,
        port: int,
        name: str,
        is_host: bool = False,
        room_code: str | None = None,
    ) -> None:
        self.is_host = is_host
        self.room_code = room_code
        self.client = GameClient(self._on_message)
        self._lock = threading.RLock()
        self._state: dict[str, Any] | None = None
        self.error: str | None = None
        self.info = "Connected through relay"
        self.client.connect_to_server(host, port)
        if is_host:
            self.client.create_room(name)
        else:
            if room_code is None:
                raise ValueError("Room code is required")
            self.client.join_room(room_code, name)

    @property
    def player_id(self) -> str | None:
        return self.client.player_id

    @property
    def can_start_game(self) -> bool:
        return self.is_host

    def snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            return dict(self._state) if self._state else None

    def start_game(self) -> None:
        self.client.start_game()

    def play_card(
        self,
        card_id: str,
        chosen_color: str | None = None,
        target_player_id: str | None = None,
        pass_direction: str | None = None,
    ) -> None:
        self.client.play_card(card_id, chosen_color, target_player_id, pass_direction)

    def draw_card(self) -> None:
        self.client.draw_card()

    def pass_turn(self) -> None:
        self.client.pass_turn()

    def react(self, player_id: str | None = None) -> None:
        self.client.react()

    def update(self) -> None:
        pass

    def close(self) -> None:
        self.client.disconnect()

    def _on_message(self, message: NetworkMessage) -> None:
        with self._lock:
            if message.type == MessageType.GAME_STATE:
                self._state = dict(message.payload)
            elif message.type == MessageType.ERROR:
                self.error = str(message.payload.get("message", "Network error"))
            elif message.type == MessageType.PLAYER_JOINED:
                self.error = None
            elif message.type == MessageType.ROOM_CREATED:
                self.room_code = str(message.payload.get("room_code", ""))
                self.error = None


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
        self.notice = ""
        self.assets_root = Path(__file__).resolve().parents[2] / "assets"
        self.scenes = {
            "menu": MenuScene(self),
            "host_room": LobbyScene(self, "host_room"),
            "join_room": LobbyScene(self, "join_room"),
            "game": GameScene(self),
            "end": EndScene(self),
            "settings": SettingsScene(self),
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
                if self.mode in {"game", "host_room", "join_room", "settings"}:
                    self._go_menu()
                else:
                    self.running = False
                continue

            self._current_scene().handle_event(event)

    def _update(self, dt: float) -> None:
        self.transition_alpha = max(0, self.transition_alpha - int(950 * dt))
        self.click_feedback = [(pos, age + dt) for pos, age in self.click_feedback if age + dt < 0.24]
        self._current_scene().update(dt)

    def _draw(self) -> None:
        assert self.screen is not None
        self.screen.fill(TABLE_GREEN)
        self._current_scene().draw(self.screen)
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
        assert self.screen is not None
        self.buttons.clear()
        self.input_boxes.clear()
        self._draw_title("UNO Online")
        x = 475
        y = 230
        self._add_button(x, y, 102, 48, "2P Local", "local", 2)
        self._add_button(x + 114, y, 102, 48, "3P Local", "local", 3)
        self._add_button(x + 228, y, 102, 48, "4P Local", "local", 4)
        self._add_button(x, y + 62, 159, 48, "1P + Bot", "local", (2, 1))
        self._add_button(x + 171, y + 62, 159, 48, "1P + 3 Bots", "local", (4, 3))
        self._add_button(x, y + 124, 330, 48, "Host Relay Room", "host_room")
        self._add_button(x, y + 186, 330, 48, "Join Relay Code", "join_room")
        self._add_button(x, y + 248, 330, 48, "Settings", "settings")
        self._draw_buttons()
        self._draw_text("Online play uses a relay room code. Players never connect directly to the host.", 640, 670, MUTED, center=True)
        if self.notice:
            self._draw_text(self.notice, 640, 696, BAD, center=True)

    def _draw_settings(self) -> None:
        assert self.screen is not None
        self.buttons.clear()
        self.input_boxes.clear()
        self._draw_title("Settings")
        panel = pygame.Rect(375, 220, 530, 320)
        pygame.draw.rect(self.screen, PANEL, panel, border_radius=8)
        rows = [
            ("Sound", "sound_enabled", "On" if self.user_settings.sound_enabled else "Off"),
            ("Volume", "volume", f"{int(self.user_settings.volume * 100)}%"),
            ("Background Art", "show_background_art", "On" if self.user_settings.show_background_art else "Off"),
            ("Missing Card Labels", "show_missing_card_labels", "On" if self.user_settings.show_missing_card_labels else "Off"),
            ("Fullscreen", "fullscreen", "On" if self.user_settings.fullscreen else "Off"),
        ]
        y = 252
        for label, key, value in rows:
            self._draw_text(label, 420, y + 8, TEXT)
            self._draw_text(value, 668, y + 8, MUTED)
            if key == "volume":
                self._add_button(735, y, 42, 38, "-", "volume_down")
                self._add_button(790, y, 42, 38, "+", "volume_up")
            else:
                self._add_button(735, y, 97, 38, "Toggle", f"toggle_{key}")
            y += 55
        self._add_button(420, 570, 185, 44, "Save", "save_settings")
        self._add_button(620, 570, 185, 44, "Back", "menu")
        self._draw_text("Settings are saved to config/user_settings.json.", 640, 640, MUTED, center=True)
        if self.notice:
            self._draw_text(self.notice, 640, 670, GOOD, center=True)
        self._draw_buttons()

    def _draw_join(self) -> None:
        assert self.screen is not None
        self.buttons.clear()
        if not self.input_boxes:
            if self.mode == "host_room":
                self.input_boxes = [
                    InputBox(pygame.Rect(420, 260, 440, 42), "Name", "Host"),
                    InputBox(pygame.Rect(420, 340, 440, 42), "Relay Host", "127.0.0.1"),
                ]
            else:
                self.input_boxes = [
                    InputBox(pygame.Rect(420, 240, 440, 42), "Name", "Player"),
                    InputBox(pygame.Rect(420, 315, 440, 42), "Relay Host", "127.0.0.1"),
                    InputBox(pygame.Rect(420, 390, 440, 42), "Room Code", ""),
                ]
        self._draw_title("Host Game" if self.mode == "host_room" else "Join Game")
        font, small, _big = self._fonts()
        for box in self.input_boxes:
            box.draw(self.screen, font, small)
        self._add_button(420, 470, 210, 46, "Create" if self.mode == "host_room" else "Connect", "connect")
        self._add_button(650, 470, 210, 46, "Back", "menu")
        self._draw_buttons()
        if self.notice:
            self._draw_text(self.notice, 640, 560, BAD, center=True)

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
            self._draw_text(f"Room code: {self.session.room_code}", 1020, 34, ACCENT)

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
            self._add_button(1068, 22, 154, 34, "Host Settings", "host_settings")
        if self.host_settings_open:
            self._draw_host_settings(state)
        self._add_button(28, 22, 92, 34, "Menu", "menu")
        self._draw_buttons()
        error = self.session.error if self.session else None
        if error:
            self._draw_text(error, 640, 690, BAD, center=True)

    def _draw_game_frame(self, state: dict[str, Any] | None) -> None:
        assert self.screen is not None
        pygame.draw.rect(self.screen, (199, 231, 218), pygame.Rect(0, 0, 1280, 92))
        pygame.draw.rect(self.screen, PANEL, pygame.Rect(22, 104, 245, 470), border_radius=8)
        pygame.draw.rect(self.screen, PANEL, pygame.Rect(1014, 104, 244, 470), border_radius=8)
        pygame.draw.rect(self.screen, (226, 244, 236), pygame.Rect(0, 584, 1280, 136))
        if self.session:
            self._draw_text(self.session.info, 1020, 64, MUTED)

    def _draw_players(self, players: list[dict[str, Any]], current: str | None, me: str | None) -> None:
        self._draw_text("Players", 42, 124, TEXT)
        y = 164
        for player in players:
            active = player.get("id") == current
            mine = player.get("id") == me
            color = ACCENT if active else TEXT
            tag = "YOU" if mine else ("BOT" if player.get("is_bot") else ("OFF" if not player.get("connected", True) else ""))
            label = f"{player.get('name')}  {player.get('card_count')} cards {tag}"
            self._draw_text(label, 42, y, color)
            y += 34

    def _draw_center_pile(self, top_card: dict[str, str] | None, active_color: str | None, pending_draw: int) -> None:
        assert self.screen is not None
        assert self.card_renderer is not None
        pile = pygame.Rect(575, 190, CARD_W + 18, CARD_H + 18)
        pygame.draw.rect(self.screen, (246, 238, 225), pile, border_radius=12)
        if top_card:
            card = card_from_dict(top_card)
            self.card_renderer.draw_card(self.screen, card, pygame.Rect(584, 199, CARD_W, CARD_H))
        self._draw_card_back(pygame.Rect(462, 199, CARD_W, CARD_H))
        if active_color:
            color = color_tuple(active_color)
            pygame.draw.circle(self.screen, color, (704, 238), 18)
            pygame.draw.circle(self.screen, TEXT, (704, 238), 18, 2)
        if pending_draw:
            self._draw_text(f"+{pending_draw}", 708, 288, BAD, center=True, size="big")

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
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, PANEL, pygame.Rect(360, 300, 560, 190), border_radius=8)
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
        if self.card_renderer is None:
            return
        if not self.user_settings.show_background_art:
            return
        # Optional backgrounds use assets/images/placeholder.jfif until real art is added.
        image = self.card_renderer.assets.load_background(name)
        if image is None:
            return
        scaled = pygame.transform.smoothscale(image, self.screen.get_size())
        scaled.set_alpha(55 if name == "table_background" else 80)
        self.screen.blit(scaled, (0, 0))

    def _draw_title(self, title: str) -> None:
        self._draw_text(title, 640, 130, TEXT, center=True, size="big")
        self._draw_text("Host-authoritative rules, online commands, card assets", 640, 174, MUTED, center=True)

    def _draw_buttons(self) -> None:
        assert self.screen is not None
        font, _small, _big = self._fonts()
        mouse = pygame.mouse.get_pos()
        for button in self.buttons:
            draw_rect = button.rect
            color = (240, 232, 220) if button.enabled else (224, 224, 218)
            if button.enabled and draw_rect.collidepoint(mouse):
                color = (246, 218, 194)
                draw_rect = draw_rect.inflate(2, 2)
            pygame.draw.rect(self.screen, color, draw_rect, border_radius=6)
            pygame.draw.rect(self.screen, ACCENT if button.enabled else (184, 190, 188), draw_rect, 2, border_radius=6)
            label = font.render(button.label, True, TEXT if button.enabled else MUTED)
            self.screen.blit(label, label.get_rect(center=draw_rect.center))

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


def color_tuple(color: str) -> tuple[int, int, int]:
    return {
        "red": (239, 154, 154),
        "yellow": (245, 218, 137),
        "green": (159, 215, 178),
        "blue": (161, 196, 235),
        "wild": (154, 145, 166),
    }.get(color, (235, 232, 224))


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
