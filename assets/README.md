# Assets

The game uses `assets/images/placeholder.jfif` anywhere optional visual art is missing. Every asset below is optional unless you want polished visuals or audio. Add files with these names and the code will pick them up where noted.

## Universal Placeholder

Used automatically for missing card faces, card backs, menu backgrounds, and table backgrounds.

```text
assets/images/placeholder.jfif
```

## Card Images

Primary location:

```text
assets/images/cards/
```

Fallback location:

```text
assets/images/
```

Expected card filenames:

```text
Red_0.jpg ... Red_9.jpg
Red_Skip.jpg
Red_Reverse.jpg
Red_Draw_2.jpg

Yellow_0.jpg ... Yellow_9.jpg
Yellow_Skip.jpg
Yellow_Reverse.jpg
Yellow_Draw_2.jpg

Green_0.jpg ... Green_9.jpg
Green_Skip.jpg
Green_Reverse.jpg
Green_Draw_2.jpg

Blue_0.jpg ... Blue_9.jpg
Blue_Skip.jpg
Blue_Reverse.jpg
Blue_Draw_2.jpg

Wild.jpg
Wild_Draw_4.jpg
```

The loader also accepts `.png` variants. If a card image is missing, `presentation/rendering/card_renderer.py` displays the placeholder and overlays the card color/rank so the game remains playable.

## Optional Card Back

Needed for a custom draw pile back. The current code uses `assets/images/placeholder.jfif` if this is absent.

```text
assets/images/cards/Card_Back.png
assets/images/cards/Card_Back.jpg
```

## Optional Fonts

Needed only if you want custom typography. The app uses pygame's default font if this file is missing.

```text
assets/fonts/Inter-Regular.ttf
```

## Optional Sounds

These are not required yet, but the names are reserved for a future `SoundManager`.

```text
assets/sounds/card_play.wav
assets/sounds/card_draw.wav
assets/sounds/invalid_move.wav
assets/sounds/reaction_start.wav
assets/sounds/reaction_hit.wav
assets/sounds/game_win.wav
```

## Optional Backgrounds

These are not required. The app uses `assets/images/placeholder.jfif` behind the pygame table/menu if these are absent.

```text
assets/images/table_background.png
assets/images/menu_background.png
```
