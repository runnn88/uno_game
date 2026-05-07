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

    bg_color: tuple[int, int, int] = (240, 232, 220)
    border_color: tuple[int, int, int] = (238, 185, 145)
    text_color: tuple[int, int, int] = (49, 61, 73)
    border_radius: int = 6
    outline_width: int = 2
    hover_bg_color: tuple[int, int, int] | None = None
    
    def contains(self, point: tuple[int, int]) -> bool:
        return self.enabled and self.rect.collidepoint(point)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font | None = None) -> None:
        color = self.bg_color if self.enabled else (224, 224, 218)
        border = self.border_color if self.enabled else (184, 190, 188)
        text = self.text_color if self.enabled else (105, 121, 130)
        
        is_hover = self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())
        if is_hover:
            color = self.hover_bg_color if self.hover_bg_color else (min(255, self.bg_color[0]+15), min(255, self.bg_color[1]+15), min(255, self.bg_color[2]+15))
            
        draw_rect = self.rect.inflate(4, 4) if is_hover else self.rect

        pygame.draw.rect(surface, border, draw_rect.inflate(self.outline_width*2, self.outline_width*2), border_radius=self.border_radius)
  
        pygame.draw.rect(surface, color, draw_rect, border_radius=self.border_radius)
        
        rendered = font.render(self.label, True, text)
        surface.blit(rendered, rendered.get_rect(center=draw_rect.center))