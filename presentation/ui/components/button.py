from dataclasses import dataclass
from typing import Any

import pygame

from presentation.theme import ACCENT, MUTED, SHADOW, TEXT


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: str | None = None
    payload: Any = None
    enabled: bool = True

    def contains(self, point: tuple[int, int]) -> bool:
        return self.enabled and self.rect.collidepoint(point)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font | None = None) -> None:
        draw_rect = self.rect
        hovered = self.contains(pygame.mouse.get_pos())
        fill = (255, 232, 213) if hovered else (248, 239, 226) if self.enabled else (229, 230, 225)
        border = ACCENT if self.enabled else (184, 190, 188)
        text = TEXT if self.enabled else MUTED
        shadow = pygame.Surface((draw_rect.width + 8, draw_rect.height + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow, SHADOW if self.enabled else (0, 0, 0, 24), shadow.get_rect().move(4, 4), border_radius=8)
        surface.blit(shadow, (draw_rect.x - 4, draw_rect.y - 4))
        pygame.draw.rect(surface, fill, draw_rect, border_radius=8)
        pygame.draw.rect(surface, border, draw_rect, 2, border_radius=8)
        selected_font = small_font if small_font is not None and font.size(self.label)[0] > draw_rect.width - 22 else font
        rendered = selected_font.render(self.label, True, text)
        surface.blit(rendered, rendered.get_rect(center=draw_rect.center))
