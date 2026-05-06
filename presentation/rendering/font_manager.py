from pathlib import Path
import pygame

class FontManager:
    def __init__(self, assets_root: Path | None = None) -> None:
        package_root = Path(__file__).resolve().parents[2]
        self.assets_root = assets_root or package_root / "assets" / "fonts"
        
        self.font_file = "SansitaOne-Regular.ttf" 
        
        self._cache: dict[int, pygame.font.Font] = {}

    def get(self, size: int) -> pygame.font.Font:
        if size not in self._cache:
            path = self.assets_root / self.font_file
            
            if path.exists():
                self._cache[size] = pygame.font.Font(str(path), size)
            else:
                self._cache[size] = pygame.font.Font(None, size) 
                
        return self._cache[size]