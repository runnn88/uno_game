from dataclasses import dataclass, field
from typing import Any


@dataclass
class EffectState:
    queue: list[dict[str, Any]] = field(default_factory=list)

