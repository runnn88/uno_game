from config.settings import DEFAULT_SETTINGS
from core.event_bus import EventBus
from core.game_loop import GameLoop
from core.state_manager import StateManager


class App:
    def __init__(self) -> None:
        self.settings = DEFAULT_SETTINGS
        self.events = EventBus()
        self.state_manager = StateManager()
        self.loop = GameLoop(self.update, self.settings.fps)

    def update(self, dt: float) -> None:
        self.events.emit("APP_TICK", {"dt": dt})

    def run(self) -> None:
        from presentation.pygame_app import PygameUnoApp

        PygameUnoApp().run()
