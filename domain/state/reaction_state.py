from dataclasses import dataclass, field


@dataclass
class ReactionState:
    active: bool = False
    source_player_id: str | None = None
    responders: list[str] = field(default_factory=list)
    expires_at: float | None = None

