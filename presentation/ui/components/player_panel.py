from domain.entities.player import Player
import pygame


class PlayerPanel:
    def __init__(self, player: Player) -> None:
        self.player = player

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, font: pygame.font.Font, active: bool = False) -> None:
        color = (218, 126, 103) if active else (49, 61, 73)
        status = "" if self.player.connected else " OFF"
        label = f"{self.player.name}  {len(self.player.hand.cards)} cards{status}"
        surface.blit(font.render(label, True, color), rect.topleft)
