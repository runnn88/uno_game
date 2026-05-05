from dataclasses import dataclass


@dataclass(frozen=True)
class ReactionResult:
    loser_player_ids: tuple[str, ...]
    responders: tuple[str, ...]
