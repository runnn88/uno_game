from __future__ import annotations

import pygame

from presentation.theme import GOOD, MUTED, TEXT
from presentation.ui.components.chip import Chip


class SettingsRow:
    def __init__(self, rect: pygame.Rect, label: str, value: str) -> None:
        self.rect = rect
        self.label = label
        self.value = value

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small: pygame.font.Font) -> None:
        surface.blit(font.render(self.label, True, (255, 255, 255)), (self.rect.x + 24, self.rect.y + 12))
        color = GOOD if self.value == "On" else MUTED
        
        Chip(self.value, pygame.Rect(self.rect.x + 200, self.rect.y + 8, 98, 33), color).draw(surface, small)
