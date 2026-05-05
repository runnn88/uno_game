import os
import threading
import unittest


class PresentationTests(unittest.TestCase):
    def test_pygame_app_boots_with_dummy_video_driver(self) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        import pygame

        from presentation.pygame_app import PygameUnoApp

        threading.Timer(0.2, lambda: pygame.event.post(pygame.event.Event(pygame.QUIT))).start()
        PygameUnoApp().run()
        self.assertFalse(pygame.get_init())

    def test_playable_preview_matches_stack_and_final_action_rules(self) -> None:
        from presentation.pygame_app import is_card_playable

        stack_state = {
            "top_card": {"id": "wild_draw_four_0", "color": "wild", "rank": "wild_draw_four"},
            "active_color": "red",
            "pending_draw": 4,
            "pending_draw_value": 4,
            "reaction": {"active": False},
            "players": [{"id": "p1", "card_count": 2, "hand": [{"id": "red_draw_2_0", "color": "red", "rank": "draw_two"}]}],
        }
        self.assertFalse(is_card_playable({"id": "red_draw_2_0", "color": "red", "rank": "draw_two"}, stack_state))

        final_action_state = {
            "top_card": {"id": "red_5_0", "color": "red", "rank": "5"},
            "active_color": "red",
            "pending_draw": 0,
            "reaction": {"active": False},
            "players": [{"id": "p1", "card_count": 1, "hand": [{"id": "red_skip_0", "color": "red", "rank": "skip"}]}],
        }
        self.assertFalse(is_card_playable({"id": "red_skip_0", "color": "red", "rank": "skip"}, final_action_state))


if __name__ == "__main__":
    unittest.main()
