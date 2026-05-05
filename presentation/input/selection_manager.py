class SelectionManager:
    def __init__(self) -> None:
        self.selected_card_id: str | None = None
        self.selected_color: str | None = None
        self.selected_target_id: str | None = None

    def select_card(self, card_id: str) -> None:
        self.selected_card_id = card_id

    def select_color(self, color: str) -> None:
        self.selected_color = color

    def select_target(self, player_id: str) -> None:
        self.selected_target_id = player_id

    def clear(self) -> None:
        self.selected_card_id = None
        self.selected_color = None
        self.selected_target_id = None
