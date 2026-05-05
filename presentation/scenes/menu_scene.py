from uno_game.presentation.scenes.base_scene import BaseScene


class MenuScene(BaseScene):
    def enter(self) -> None:
        self.app.buttons.clear()
        self.app.input_boxes.clear()
        self.app.hand_targets.clear()
        self.app.pending_card = None
        self.app.pending_color = None

    def draw(self, surface) -> None:
        self.app._draw_background("menu_background")
        self.app._draw_menu()
