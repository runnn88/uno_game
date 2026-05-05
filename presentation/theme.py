CARD_W = 94
CARD_H = 132
TABLE_GREEN = (204, 232, 216)
TABLE_DARK = (78, 142, 122)
PANEL = (255, 250, 241)
PANEL_2 = (233, 245, 246)
TEXT = (37, 47, 56)
MUTED = (99, 115, 121)
ACCENT = (232, 141, 105)
ACCENT_2 = (82, 151, 171)
BAD = (209, 91, 99)
GOOD = (92, 169, 124)
BORDER = (183, 204, 198)
SHADOW = (52, 78, 72, 48)


def readable_card(data: dict[str, str]) -> str:
    rank = str(data.get("rank", "")).replace("_", " ")
    color = str(data.get("color", "")).replace("_", " ")
    if color == "wild":
        return rank.title()
    return f"{color.title()} {rank.title()}"


def color_tuple(color: str) -> tuple[int, int, int]:
    return {
        "red": (239, 154, 154),
        "yellow": (245, 218, 137),
        "green": (159, 215, 178),
        "blue": (161, 196, 235),
        "wild": (154, 145, 166),
    }.get(color, (235, 232, 224))
