import pygame


class DirectionIndicator:
    def draw(self, surface: pygame.Surface, direction: str, font: pygame.font.Font) -> None:
        rendered = font.render(f"Direction: {direction}", True, (105, 121, 130))
        surface.blit(rendered, rendered.get_rect(center=(surface.get_width() // 2, 62)))
