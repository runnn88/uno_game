from uno_game.domain.entities.card import Card
from uno_game.presentation.rendering.card_asset_manager import CardAssetManager


class CardRenderer:
    def __init__(self, assets: CardAssetManager | None = None) -> None:
        self.assets = assets or CardAssetManager()
        self.show_missing_labels = True

    def draw_card(self, surface: object, card: Card, rect: object) -> None:
        import pygame

        image = self.assets.load(card)
        if image is not None:
            surface.blit(pygame.transform.smoothscale(image, (rect.width, rect.height)), rect)
            if self.show_missing_labels and self.assets.image_path_for(card) is None:
                self._draw_label(surface, card, rect)
            return
        self._draw_fallback(surface, card, rect)

    def _draw_fallback(self, surface: object, card: Card, rect: object) -> None:
        import pygame

        color = {
            "red": (239, 154, 154),
            "yellow": (245, 218, 137),
            "green": (159, 215, 178),
            "blue": (161, 196, 235),
            "wild": (154, 145, 166),
        }[card.color.value]
        pygame.draw.rect(surface, (255, 251, 242), rect, border_radius=10)
        inner = rect.inflate(-8, -8)
        pygame.draw.rect(surface, color, inner, border_radius=8)
        font = pygame.font.Font(None, max(18, rect.width // 4))
        text = font.render(card.rank.value.replace("_", " ").upper(), True, (49, 61, 73))
        text_rect = text.get_rect(center=rect.center)
        surface.blit(text, text_rect)

    def _draw_label(self, surface: object, card: Card, rect: object) -> None:
        import pygame

        label_rect = pygame.Rect(rect.x + 8, rect.centery - 22, rect.width - 16, 44)
        overlay = pygame.Surface((label_rect.width, label_rect.height), pygame.SRCALPHA)
        overlay.fill((255, 251, 242, 215))
        surface.blit(overlay, label_rect)
        font = pygame.font.Font(None, max(16, rect.width // 5))
        text = f"{card.color.value} {card.rank.value}".replace("_", " ").upper()
        rendered = font.render(text, True, (49, 61, 73))
        surface.blit(rendered, rendered.get_rect(center=label_rect.center))
