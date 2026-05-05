import pygame

from presentation.theme import MUTED, TEXT
from presentation.ui.components.panel import Panel


class RoomCodePanel:
    def __init__(self, room_code: str, rect: pygame.Rect) -> None:
        self.room_code = room_code
        self.rect = rect
        self.copy_rect = pygame.Rect(rect.x + 20, rect.y + 76, rect.width - 40, 30)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small: pygame.font.Font, big: pygame.font.Font) -> None:
        Panel(self.rect, (255, 248, 237), radius=8).draw(surface)
        label = small.render("Room Code", True, MUTED)
        surface.blit(label, label.get_rect(center=(self.rect.centerx, self.rect.y + 18)))
        code = big.render(self.room_code, True, TEXT)
        surface.blit(code, code.get_rect(center=(self.rect.centerx, self.rect.y + 50)))
