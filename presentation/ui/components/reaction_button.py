from uno_game.presentation.ui.components.button import Button


class ReactionButton(Button):
    def mark_done(self) -> None:
        self.enabled = False
