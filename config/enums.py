from enum import Enum


class CardColor(str, Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    WILD = "wild"


class CardRank(str, Enum):
    ZERO = "0"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    SKIP = "skip"
    REVERSE = "reverse"
    DRAW_TWO = "draw_two"
    WILD = "wild"
    WILD_DRAW_FOUR = "wild_draw_four"


class Direction(int, Enum):
    CLOCKWISE = 1
    COUNTER_CLOCKWISE = -1


class PassDirection(str, Enum):
    CLOCKWISE = "clockwise"
    COUNTER_CLOCKWISE = "counter_clockwise"


class GamePhase(str, Enum):
    MENU = "menu"
    LOBBY = "lobby"
    PLAYING = "playing"
    REACTION = "reaction"
    ENDED = "ended"


class ActionType(str, Enum):
    PLAY_CARD = "play_card"
    DRAW_CARD = "draw_card"
    CHOOSE_COLOR = "choose_color"
    CHOOSE_TARGET = "choose_target"
    REACT_EVENT = "react_event"
