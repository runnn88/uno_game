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
        pastel_pink = (255, 182, 193)
        light_pink_boarder = (255, 192, 203)

        fill = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(fill, (*pastel_pink, 255), fill.get_rect(), border_radius=8)
        surface.blit(fill, self.rect.topleft)
        pygame.draw.rect(surface, light_pink_boarder, self.rect, 2, border_radius=8)
        
        text = font.render(self.label, True, (255, 255, 255))
        surface.blit(text, text.get_rect(center=self.rect.center))
