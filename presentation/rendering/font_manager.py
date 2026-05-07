from pathlib import Path
import pygame

class FontManager:
    def __init__(self, assets_root: Path | None = None) -> None:
        package_root = Path(__file__).resolve().parents[2]
        self.assets_root = assets_root or package_root / "assets" / "fonts"
        
        self._cache: dict[tuple[str, int], pygame.font.Font] = {}

    def get(self, font_name: str, size: int) -> pygame.font.Font:
        key = (font_name, size)
        
        if key not in self._cache:
            path = self.assets_root / f"{font_name}.ttf"
            
            if path.exists():
                self._cache[key] = pygame.font.Font(str(path), size)
            else:
                print(f"Warning: Could not find font {font_name}.ttf")
                self._cache[key] = pygame.font.Font(None, size) 
                
        return self._cache[key]