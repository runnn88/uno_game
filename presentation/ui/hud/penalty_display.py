import pygame


class PenaltyDisplay:
    def draw(self, surface: pygame.Surface, pending_draw: int, font: pygame.font.Font, pos: tuple[int, int]) -> None:
        if pending_draw <= 0:
            return
        rendered = font.render(f"+{pending_draw}", True, (220, 119, 124))
        surface.blit(rendered, rendered.get_rect(center=pos))
