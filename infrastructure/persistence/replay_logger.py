from infrastructure.network.protocol import NetworkMessage


class ReplayLogger:
    def __init__(self) -> None:
        self.messages: list[NetworkMessage] = []

    def record(self, message: NetworkMessage) -> None:
        self.messages.append(message)
