import os
import threading
import unittest


class PresentationTests(unittest.TestCase):
    def test_pygame_app_boots_with_dummy_video_driver(self) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        import pygame

        from uno_game.presentation.pygame_app import PygameUnoApp

        threading.Timer(0.2, lambda: pygame.event.post(pygame.event.Event(pygame.QUIT))).start()
        PygameUnoApp().run()
        self.assertFalse(pygame.get_init())


if __name__ == "__main__":
    unittest.main()

