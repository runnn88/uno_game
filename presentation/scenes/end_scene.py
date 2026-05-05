from uno_game.presentation.scenes.base_scene import BaseScene


class EndScene(BaseScene):
    def handle_event(self, event) -> None:
        super().handle_event(event)

    def update(self, dt: float) -> None:
        if self.app.session is not None:
            self.app.session.update()

    def draw(self, surface) -> None:
        self.app._draw_background("table_background")
        self.app._draw_game()
