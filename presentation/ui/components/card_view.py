from domain.entities.card import Card
from presentation.rendering.card_asset_manager import CardAssetManager


class CardView:
    def __init__(self, card: Card, assets: CardAssetManager | None = None) -> None:
        self.card = card
        self.assets = assets or CardAssetManager()

    @property
    def asset_path(self) -> str | None:
        path = self.assets.image_path_for(self.card)
        return str(path) if path else None
