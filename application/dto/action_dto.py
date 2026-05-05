from dataclasses import dataclass
from typing import Any

from config.enums import ActionType


@dataclass(frozen=True)
class ActionDTO:
    type: ActionType
    payload: dict[str, Any]

