from dataclasses import dataclass
from typing import Any

from uno_game.config.enums import ActionType


@dataclass(frozen=True)
class ActionDTO:
    type: ActionType
    payload: dict[str, Any]

