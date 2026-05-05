import pygame


class Renderer:
    def clear(self, surface: pygame.Surface, color: tuple[int, int, int]) -> None:
        surface.fill(color)

    def draw_panel(self, surface: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int]) -> None:
        pygame.draw.rect(surface, color, rect, border_radius=8)

    def draw_text(
        self,
        surface: pygame.Surface,
        text: str,
        pos: tuple[int, int],
        font: pygame.font.Font,
        color: tuple[int, int, int],
        center: bool = False,
    ) -> None:
        rendered = font.render(text, True, color)
        rect = rendered.get_rect()
        rect.center = pos if center else rect.center
        if not center:
            rect.topleft = pos
        surface.blit(rendered, rect)
