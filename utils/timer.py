from time import monotonic


class Timer:
    def __init__(self, duration: float) -> None:
        self.duration = duration
        self.started_at = monotonic()

    def expired(self) -> bool:
        return monotonic() - self.started_at >= self.duration

    def reset(self) -> None:
        self.started_at = monotonic()

