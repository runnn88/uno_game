from collections.abc import Callable


class GameLoop:
    def __init__(self, tick: Callable[[float], None], fps: int) -> None:
        self.tick = tick
        self.fps = fps
        self.running = False

    def run_once(self, dt: float) -> None:
        self.tick(dt)

