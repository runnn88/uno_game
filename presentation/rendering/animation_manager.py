from dataclasses import dataclass


@dataclass
class Animation:
    duration: float
    elapsed: float = 0.0

    @property
    def progress(self) -> float:
        if self.duration <= 0:
            return 1.0
        return min(1.0, self.elapsed / self.duration)


class AnimationManager:
    def __init__(self) -> None:
        self.animations: list[Animation] = []

    def add(self, duration: float) -> Animation:
        animation = Animation(duration)
        self.animations.append(animation)
        return animation

    def update(self, dt: float) -> None:
        for animation in self.animations:
            animation.elapsed += dt
        self.animations = [animation for animation in self.animations if animation.progress < 1.0]
