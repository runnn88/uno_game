from uno_game.presentation.scenes.base_scene import BaseScene


class GameScene(BaseScene):
    def enter(self) -> None:
        self.app.input_boxes.clear()
        self.app.buttons.clear()
        self.app.hand_targets.clear()

    def update(self, dt: float) -> None:
        if self.app.session is not None:
            self.app.session.update()

    def draw(self, surface) -> None:
        self.app._draw_background("table_background")
        self.app._draw_game()
