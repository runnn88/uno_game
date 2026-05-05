from dataclasses import dataclass
from typing import Any

import pygame


@dataclass
class Button:
    label: str
    rect: pygame.Rect
    action: str | None = None
    payload: Any = None
    enabled: bool = True

    def contains(self, point: tuple[int, int]) -> bool:
        return self.enabled and self.rect.collidepoint(point)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        color = (240, 232, 220) if self.enabled else (224, 224, 218)
        if self.enabled and self.rect.collidepoint(pygame.mouse.get_pos()):
            color = (246, 218, 194)
        border = (238, 185, 145) if self.enabled else (184, 190, 188)
        text = (49, 61, 73) if self.enabled else (105, 121, 130)
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=6)
        rendered = font.render(self.label, True, text)
        surface.blit(rendered, rendered.get_rect(center=self.rect.center))
        self.label = label
