import pygame


class TurnIndicator:
    def draw(self, surface: pygame.Surface, current_player_name: str, font: pygame.font.Font) -> None:
        rendered = font.render(f"Turn: {current_player_name}", True, (49, 61, 73))
        surface.blit(rendered, rendered.get_rect(center=(surface.get_width() // 2, 34)))
