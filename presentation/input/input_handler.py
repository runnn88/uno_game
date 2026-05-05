from collections.abc import Callable

import pygame


class InputHandler:
    def __init__(self) -> None:
        self._key_bindings: dict[int, Callable[[], None]] = {}

    def bind_key(self, key: int, action: Callable[[], None]) -> None:
        self._key_bindings[key] = action

    def handle(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and event.key in self._key_bindings:
            self._key_bindings[event.key]()
            return True
        return False
