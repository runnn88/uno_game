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
        fill_color = (253, 238, 103)  #yellow
        text_color = (255, 175, 1)    #orange
        
        fill = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(fill, (*fill_color, 255), fill.get_rect(), border_radius=10 )
        surface.blit(fill, self.rect.topleft)
        
        text = font.render(self.label, True, text_color)
        surface.blit(text, text.get_rect(center=self.rect.center))
