from presentation.scenes.base_scene import BaseScene


class MenuScene(BaseScene):
    def enter(self) -> None:
        self.app.buttons.clear()
        self.app.input_boxes.clear()
        self.app.hand_targets.clear()
        self.app.pending_card = None
        self.app.pending_color = None

    def draw(self, surface) -> None:
        
        if self.app.mode == "play_menu":  
            self.app._draw_background("menu_background")
            self.app._draw_play_menu()
        else: 
            self.app._draw_main_menu()
