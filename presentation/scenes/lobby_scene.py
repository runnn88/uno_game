from presentation.scenes.base_scene import BaseScene


class LobbyScene(BaseScene):
    def __init__(self, app, join_mode: str) -> None:
        super().__init__(app)
        self.join_mode = join_mode

    def enter(self) -> None:
        self.app.input_boxes.clear()
        self.app.buttons.clear()
        self.app.hand_targets.clear()
        self.app.pending_card = None
        self.app.pending_color = None

    def handle_event(self, event) -> None:
        consumed = any(box.handle_event(event) for box in self.app.input_boxes)
        if consumed:
            return
        super().handle_event(event)

    def draw(self, surface) -> None:
        self.app._draw_background("table_background")
        self.app._draw_join()
