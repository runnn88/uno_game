from __future__ import annotations

from typing import Any

import pygame

from presentation.theme import ACCENT, ACCENT_2, BAD, GOOD, TEXT
from presentation.ui.components.chip import Chip


class PlayerPanel:
    def __init__(self, player: dict[str, Any], rect: pygame.Rect, active: bool = False, mine: bool = False) -> None:
        self.player = player
        self.rect = rect
        self.active = active
        self.mine = mine

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small: pygame.font.Font) -> None:
        if self.active:
            pygame.draw.rect(surface, (255, 237, 225), self.rect, border_radius=8)
            pygame.draw.rect(surface, ACCENT, self.rect, 2, border_radius=8)

        color = ACCENT if self.active else TEXT
        label = f"{self.player.get('name')}  {self.player.get('card_count')}"
        surface.blit(small.render(label, True, color), (self.rect.x + 10, self.rect.y + 8))

        tag = self._tag()
        if tag:
            chip_color = GOOD if tag == "YOU" else ACCENT_2 if tag == "BOT" else BAD
            Chip(tag, pygame.Rect(self.rect.right - 72, self.rect.y + 3, 52, 26), chip_color).draw(surface, small)

    def _tag(self) -> str:
        if self.mine:
            return "YOU"
        if self.player.get("is_bot"):
            return "BOT"
        if not self.player.get("connected", True):
            return "OFF"
        return ""
