import pygame

from presentation.theme import TEXT


class Chip:
    def __init__(
        self,
        label: str,
        rect: pygame.Rect,
        color: tuple[int, int, int],
    ) -> None:
        self.label = label
        self.rect = rect
        self.color = color

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        fill = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(fill, (*self.color, 42), fill.get_rect(), border_radius=8)
        surface.blit(fill, self.rect.topleft)
        pygame.draw.rect(surface, self.color, self.rect, 1, border_radius=8)
        text = font.render(self.label, True, TEXT)
        surface.blit(text, text.get_rect(center=self.rect.center))
