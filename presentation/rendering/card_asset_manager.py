from pathlib import Path

from domain.entities.card import Card


class CardAssetManager:
    def __init__(self, assets_root: Path | None = None) -> None:
        package_root = Path(__file__).resolve().parents[2]
        self.assets_root = assets_root or package_root / "assets" / "images"
        self._cache: dict[str, object] = {}

    def image_path_for(self, card: Card) -> Path | None:
        # Card files are documented in assets/README.md. The lookup checks the
        # preferred cards folder first, then the legacy images folder.
        for candidate in self._candidate_names(card):
            for directory in (self.assets_root / "cards", self.assets_root):
                path = directory / candidate
                if path.exists():
                    return path
        return None

    def load(self, card: Card) -> object | None:
        path = self.image_path_for(card)
        if path is None:
            return self.load_placeholder()
        return self._load_path(path)

    def load_card_back(self) -> object | None:
        for directory in (self.assets_root / "cards", self.assets_root):
            for filename in ("Card_Back.png", "Card_Back.jpg", "card_back.png", "card_back.jpg"):
                path = directory / filename
                if path.exists():
                    return self._load_path(path)
        return self.load_placeholder()

    def load_background(self, name: str) -> object | None:
        # Optional backgrounds fall back to assets/images/placeholder.jfif.
        for ext in ("png", "jpg", "jpeg", "jfif"):
            path = self.assets_root / f"{name}.{ext}"
            if path.exists():
                return self._load_path(path)
        return self.load_placeholder()

    def load_placeholder(self) -> object | None:
        for filename in ("placeholder.jfif", "placeholder.jpg", "placeholder.png"):
            path = self.assets_root / filename
            if path.exists():
                return self._load_path(path)
        return None

    def _load_path(self, path: Path) -> object:
        key = str(path)
        if key not in self._cache:
            import pygame

            self._cache[key] = pygame.image.load(key).convert_alpha()
        return self._cache[key]

    def _candidate_names(self, card: Card) -> tuple[str, ...]:
        color = card.color.value.title()
        rank = card.rank.value
        rank_name = {
            "draw_two": "Draw_2",
            "wild_draw_four": "Draw_4",
            "wild": "",
        }.get(rank, rank.title())
        if card.color.value == "wild":
            stem = "Wild" if card.rank.value == "wild" else "Wild_Draw_4"
            return (f"{stem}.jpg", f"{stem}.png")
        stems = (
            f"{color}_{rank_name}",
            f"{color.upper()}_{rank_name}",
            f"{color}_{rank_name.lower()}",
        )
        return tuple(f"{stem}.{ext}" for stem in stems for ext in ("jpg", "png"))
