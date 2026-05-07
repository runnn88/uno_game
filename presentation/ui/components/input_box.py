import pygame

from presentation.theme import ACCENT, MUTED, SHADOW, TEXT


class InputBox:
    def __init__(self, rect: pygame.Rect, label: str, value: str = "") -> None:
        self.rect = rect
        self.label = label
        self.value = value
        self.active = False
        self.cursor_index = len(value)
        self.max_length = 32

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            if self.active:
                self.cursor_index = len(self.value)
            return self.active
        if event.type == pygame.KEYDOWN and self.active:
            event_mod = getattr(event, "mod", None)
            if event_mod is None:
                event_mod = pygame.key.get_mods()
            ctrl_down = bool(event_mod & pygame.KMOD_CTRL)
            if ctrl_down and event.key == pygame.K_c:
                self._copy_to_clipboard(self.value)
            elif ctrl_down and event.key == pygame.K_v:
                self._insert_text(self._paste_from_clipboard())
            elif ctrl_down and event.key == pygame.K_x:
                self._copy_to_clipboard(self.value)
                self.value = ""
                self.cursor_index = 0
            elif ctrl_down and event.key == pygame.K_a:
                self.cursor_index = len(self.value)
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_index > 0:
                    self.value = self.value[: self.cursor_index - 1] + self.value[self.cursor_index :]
                    self.cursor_index -= 1
            elif event.key == pygame.K_DELETE:
                if self.cursor_index < len(self.value):
                    self.value = self.value[: self.cursor_index] + self.value[self.cursor_index + 1 :]
            elif event.key == pygame.K_LEFT:
                self.cursor_index = max(0, self.cursor_index - 1)
            elif event.key == pygame.K_RIGHT:
                self.cursor_index = min(len(self.value), self.cursor_index + 1)
            elif event.key == pygame.K_HOME:
                self.cursor_index = 0
            elif event.key == pygame.K_END:
                self.cursor_index = len(self.value)
            elif event.key in {pygame.K_RETURN, pygame.K_TAB}:
                self.active = False
            elif event.unicode:
                self._insert_text(event.unicode)
            return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small: pygame.font.Font) -> None:
        border = ACCENT if self.active else (176, 197, 199)
        shadow = pygame.Surface((self.rect.width + 8, self.rect.height + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow, SHADOW, shadow.get_rect().move(4, 4), border_radius=8)
        surface.blit(shadow, (self.rect.x - 4, self.rect.y - 4))
        pygame.draw.rect(surface, (249, 253, 251), self.rect, border_radius=8)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=8)
        surface.blit(small.render(self.label.upper(), True, (255, 255, 255)), (self.rect.x, self.rect.y - 23))
        start = max(0, len(self.value) - 24)
        clipped = self.value[start:]
        surface.blit(font.render(clipped, True, TEXT), (self.rect.x + 12, self.rect.y + 10))
        if self.active and (pygame.time.get_ticks() // 450) % 2 == 0:
            visible_cursor_index = max(0, self.cursor_index - start)
            cursor_x = self.rect.x + 12 + font.size(clipped[:visible_cursor_index])[0]
            cursor_y = self.rect.y + 9
            pygame.draw.line(surface, TEXT, (cursor_x, cursor_y), (cursor_x, cursor_y + font.get_height()), 2)

    def _insert_text(self, text: str) -> None:
        remaining = max(0, self.max_length - len(self.value))
        clean = "".join(ch for ch in text if ch.isprintable())[:remaining]
        if not clean:
            return
        self.value = self.value[: self.cursor_index] + clean + self.value[self.cursor_index :]
        self.cursor_index += len(clean)

    def _copy_to_clipboard(self, text: str) -> None:
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
        except Exception:
            pass

    def _paste_from_clipboard(self) -> str:
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            raw = pygame.scrap.get(pygame.SCRAP_TEXT)
            if raw:
                return raw.decode("utf-8", errors="ignore").replace("\x00", "")
        except Exception:
            return ""
        return ""
