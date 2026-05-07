import time
import pygame

from presentation.theme import ACCENT, MUTED, SHADOW, TEXT


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
        surface.blit(small.render(self.label.upper(), True, (255, 255, 255)), (self.rect.x, self.rect.y - 23))
        clipped = self.value[-24:]
        text_surf = font.render(clipped, True, TEXT)
        text_x = self.rect.x + 12
        text_y = self.rect.y + 10
        surface.blit(text_surf, (text_x, text_y))
        
        if self.active:
            if int(time.time() * 2) % 2 == 0:
                text_width = text_surf.get_width()
                
                cursor_x = text_x + text_width + 2
                
                cursor_y1 = text_y + 2
                cursor_y2 = text_y + text_surf.get_height() - 2
                
                pygame.draw.line(surface, TEXT, (cursor_x, cursor_y1), (cursor_x, cursor_y2), 2)
        