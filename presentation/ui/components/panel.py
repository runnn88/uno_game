import pygame

from presentation.theme import BORDER, SHADOW


class Panel:
    def __init__(
        self,
        rect: pygame.Rect,
        color: tuple[int, int, int],
        border: tuple[int, int, int] = BORDER,
        radius: int = 8,
    ) -> None:
        self.rect = rect
        self.color = color
        self.border = border
        self.radius = radius

    def draw(self, surface: pygame.Surface) -> None:
        shadow = pygame.Surface((self.rect.width + 14, self.rect.height + 14), pygame.SRCALPHA)
        pygame.draw.rect(shadow, SHADOW, pygame.Rect(7, 8, self.rect.width, self.rect.height), border_radius=self.radius)
        surface.blit(shadow, (self.rect.x - 7, self.rect.y - 7))
        pygame.draw.rect(surface, self.color, self.rect, border_radius=self.radius)
        pygame.draw.rect(surface, self.border, self.rect, 1, border_radius=self.radius)
