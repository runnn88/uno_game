import os
import threading
import time
import unittest
from unittest.mock import patch


class PresentationTests(unittest.TestCase):
    def test_pygame_app_boots_with_dummy_video_driver(self) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        import pygame

        from presentation.pygame_app import PygameUnoApp

        threading.Timer(0.2, lambda: pygame.event.post(pygame.event.Event(pygame.QUIT))).start()
        PygameUnoApp().run()
        self.assertFalse(pygame.get_init())

    def test_playable_preview_matches_stack_and_final_action_rules(self) -> None:
        from presentation.pygame_app import is_card_playable, parse_relay_url

        self.assertEqual(parse_relay_url("tcp://relay.example.com:5051"), ("relay.example.com", 5051))

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

    def test_local_game_feedback_observe_does_not_require_online_viewer(self) -> None:
        from presentation.pygame_app import PygameUnoApp

        app = PygameUnoApp()
        app._start_local(2, 0)
        app.feedback.observe()
        self.assertTrue(app.card_motions)

    def test_reaction_return_to_playing_does_not_replay_deal_animation(self) -> None:
        from presentation.pygame_app import PygameUnoApp

        class FakeSession:
            @property
            def player_id(self):
                return "p1"

            def snapshot(self):
                return {}

        previous = {
            "phase": "reaction",
            "current_player_id": "p2",
            "top_card": {"id": "red_8_0", "color": "red", "rank": "8"},
            "players": [{"id": "p1", "card_count": 3}, {"id": "p2", "card_count": 3}],
        }
        current = {
            "phase": "playing",
            "current_player_id": "p2",
            "top_card": {"id": "red_8_0", "color": "red", "rank": "8"},
            "players": [{"id": "p1", "card_count": 3}, {"id": "p2", "card_count": 3}],
        }
        app = PygameUnoApp()
        app.mode = "game"
        app.session = FakeSession()
        app.feedback._animate_phase_changes(previous, current)
        app.feedback._animate_count_changes(previous, current)
        self.assertEqual(app.card_motions, [])

    def test_replay_from_ended_local_game_restarts_in_room(self) -> None:
        from config.enums import GamePhase
        from presentation.pygame_app import PygameUnoApp

        app = PygameUnoApp()
        app._start_local(2, 0)
        assert app.session is not None
        app.session.state.phase = GamePhase.ENDED
        app.session.state.winner_id = "p1"
        app._handle_action("replay", None)
        self.assertEqual(app.mode, "game")
        self.assertEqual(app.session.snapshot()["phase"], "playing")

    def test_missing_relay_connect_does_not_block_ui_flow(self) -> None:
        import pygame

        from presentation.pygame_app import PygameUnoApp
        from presentation.ui.components.input_box import InputBox

        class SlowFailingSession:
            def __init__(self, *args, **kwargs) -> None:
                time.sleep(0.2)
                raise TimeoutError("timed out")

        app = PygameUnoApp()
        app.mode = "join_room"
        app.input_boxes = [
            InputBox(pygame.Rect(0, 0, 1, 1), "Name", "Player"),
            InputBox(pygame.Rect(0, 0, 1, 1), "Room Code", "ABCDE"),
        ]
        with patch("presentation.pygame_app.OnlineGameSession", SlowFailingSession):
            start = time.monotonic()
            app._connect_from_form()
            self.assertLess(time.monotonic() - start, 0.1)
        self.assertTrue(app.connecting)
        time.sleep(0.25)
        app._finish_pending_connection()
        self.assertFalse(app.connecting)
        self.assertEqual(app.mode, "join_room")
        self.assertTrue("not responding" in app.notice.lower() or "unavailable" in app.notice.lower())

    def test_nonexistent_room_returns_home_instead_of_game_screen(self) -> None:
        import pygame

        from infrastructure.network.relay_server import RelayServer
        from presentation.pygame_app import PygameUnoApp
        from presentation.ui.components.input_box import InputBox

        relay = RelayServer(host="127.0.0.1", port=0)
        thread = threading.Thread(target=relay.start, daemon=True)
        thread.start()
        while relay.port == 0:
            time.sleep(0.01)

        previous_relay_url = os.environ.get("UNO_RELAY_URL")
        os.environ["UNO_RELAY_URL"] = f"tcp://127.0.0.1:{relay.port}"
        app = PygameUnoApp()
        app.mode = "join_room"
        app.input_boxes = [
            InputBox(pygame.Rect(0, 0, 1, 1), "Name", "Player"),
            InputBox(pygame.Rect(0, 0, 1, 1), "Room Code", "NOPE1"),
        ]
        try:
            app._connect_from_form()
            deadline = time.monotonic() + 4.0
            while app.connecting and time.monotonic() < deadline:
                app._finish_pending_connection()
                time.sleep(0.02)
            app._finish_pending_connection()
            self.assertFalse(app.connecting)
            self.assertEqual(app.mode, "join_room")
            self.assertIsNone(app.session)
            self.assertIn("room does not exist", app.notice)
        finally:
            relay.stop()
            if previous_relay_url is None:
                os.environ.pop("UNO_RELAY_URL", None)
            else:
                os.environ["UNO_RELAY_URL"] = previous_relay_url

    def test_action_exception_returns_to_menu_with_notice(self) -> None:
        from presentation.pygame_app import PygameUnoApp

        app = PygameUnoApp()
        app.mode = "game"
        app._safe_run("Boom", lambda: (_ for _ in ()).throw(RuntimeError("broken state")))
        self.assertEqual(app.mode, "menu")
        self.assertEqual(app.notice, "broken state")
        self.assertEqual(app.toasts[-1].title, "Boom")

    def test_settings_save_exception_is_not_fatal(self) -> None:
        from presentation.pygame_app import PygameUnoApp

        app = PygameUnoApp()
        with patch("presentation.pygame_app.save_user_settings", side_effect=OSError("disk locked")):
            app._save_settings()
        self.assertIn("Could not save settings", app.notice)
        self.assertEqual(app.toasts[-1].title, "Settings not saved")

    def test_transient_online_error_clears_after_toast_window(self) -> None:
        from presentation.pygame_app import PygameUnoApp
        from presentation.game_sessions import OnlineGameSession

        app = PygameUnoApp()
        app.mode = "game"
        app.session = object.__new__(OnlineGameSession)
        app.session.error = "You have a legal card to play"
        app._handle_session_error()
        self.assertTrue(app.session.error)
        app._session_error_clear_at = 0.0
        app._handle_session_error()
        self.assertTrue(app.session.error)
        app._session_error_clear_at = 1.0
        with patch("presentation.pygame_app.monotonic", return_value=2.0):
            app._handle_session_error()
        self.assertIsNone(app.session.error)

    def test_duplicate_name_error_is_player_friendly(self) -> None:
        from presentation.pygame_app import PygameUnoApp

        app = PygameUnoApp()
        self.assertEqual(app._connection_error_message(ValueError("Name already taken")), "That name is already in this room.")
        self.assertEqual(app._friendly_session_error("Name already taken"), "That name is already in this room.")

    def test_escape_in_game_uses_overlay_before_leaving_room(self) -> None:
        from presentation.pygame_app import PygameUnoApp

        class FakeSession:
            error = None
            room_code = None

            @property
            def player_id(self):
                return "p1"

            @property
            def can_start_game(self):
                return False

            def snapshot(self):
                return {"phase": "playing", "players": [{"id": "p1", "name": "A", "card_count": 1, "hand": []}]}

            def close(self):
                self.closed = True

        app = PygameUnoApp()
        app.mode = "game"
        app.session = FakeSession()
        app._handle_game_escape()
        self.assertEqual(app.mode, "game")
        self.assertEqual(app.game_escape_overlay, "pause")
        app._handle_game_escape()
        self.assertEqual(app.mode, "game")
        self.assertIsNone(app.game_escape_overlay)
        app._handle_action("game_leave_request", None)
        self.assertEqual(app.game_escape_overlay, "leave_confirm")
        app._handle_action("game_resume", None)
        self.assertEqual(app.mode, "game")
        app._handle_action("game_leave_confirm", None)
        self.assertEqual(app.mode, "menu")


if __name__ == "__main__":
    unittest.main()
