from application.commands.draw_card import DrawCardCommand
from application.commands.pass_turn import PassTurnCommand
from application.commands.play_card import PlayCardCommand
from application.commands.react_event import ReactEventCommand
from application.handlers.draw_handler import DrawHandler
from application.handlers.pass_turn_handler import PassTurnHandler
from application.handlers.play_card_handler import PlayCardHandler
from application.handlers.reaction_handler import ReactionHandler
from config.constants import MAX_PLAYERS
from config.enums import CardColor, PassDirection
from infrastructure.network.protocol import MessageType, NetworkMessage
from infrastructure.network.relay_room import RelayRoom
from systems.draw.draw_manager import DrawManager
from systems.setup.game_initializer import GameInitializer


class RelayCommandProcessor:
    def __init__(self) -> None:
        self.initializer = GameInitializer()
        self.play_handler = PlayCardHandler()
        self.draw_handler = DrawHandler()
        self.pass_handler = PassTurnHandler()
        self.reaction_handler = ReactionHandler()
        self.draws = DrawManager()

    def process(self, room: RelayRoom, player_id: str, message: NetworkMessage) -> None:
        if message.type == MessageType.START_GAME:
            self._start_game(room, player_id)
        elif message.type == MessageType.HOST_SETTINGS:
            self._host_settings(room, player_id, message)
        elif message.type == MessageType.PLAY_CARD:
            self._play_card(room, player_id, message)
        elif message.type == MessageType.DRAW_CARD:
            self.draw_handler.handle(room.state, DrawCardCommand(player_id, message.payload.get("count", 1)))
        elif message.type == MessageType.PASS_TURN:
            self.pass_handler.handle(room.state, PassTurnCommand(player_id))
        elif message.type == MessageType.CALL_UNO:
            self._call_uno(room, player_id)
        elif message.type == MessageType.CATCH_UNO:
            self._catch_uno(room, player_id, str(message.payload.get("target_player_id", "")))
        elif message.type == MessageType.REACTION:
            self.reaction_handler.handle(room.state, ReactEventCommand(player_id))
        else:
            raise ValueError(f"Unsupported message type: {message.type.value}")
        room.state.prune_uno_protections()

    def finish_reactions(self, room: RelayRoom) -> bool:
        return self.reaction_handler.finish_if_ready(room.state)

    def _start_game(self, room: RelayRoom, player_id: str) -> None:
        if player_id != room.host_player_id:
            raise ValueError("Only the host can start the game")
        self.initializer.start(room.state)

    def _host_settings(self, room: RelayRoom, player_id: str, message: NetworkMessage) -> None:
        if player_id != room.host_player_id:
            raise ValueError("Only the host can change settings")
        if "max_players" in message.payload:
            connected = len([player for player in room.state.players if player.connected])
            room.max_players = max(max(2, connected), min(MAX_PLAYERS, int(message.payload["max_players"])))
        if "lobby_locked" in message.payload:
            room.lobby_locked = bool(message.payload["lobby_locked"])

    def _play_card(self, room: RelayRoom, player_id: str, message: NetworkMessage) -> None:
        chosen = message.payload.get("chosen_color")
        self.play_handler.handle(
            room.state,
            PlayCardCommand(
                player_id,
                message.payload["card_id"],
                CardColor(chosen) if chosen else None,
                message.payload.get("target_player_id"),
                PassDirection(message.payload["pass_direction"]) if message.payload.get("pass_direction") else None,
            ),
        )

    def _call_uno(self, room: RelayRoom, player_id: str) -> None:
        player = room.state.player_by_id(player_id)
        if len(player.hand.cards) != 1:
            raise ValueError("You can only call UNO with one card left")
        room.state.prune_uno_protections()
        if player_id in room.state.uno_protected_player_ids:
            raise ValueError("You already called UNO")
        room.state.uno_protected_player_ids.add(player_id)
        room.state.uno_call_player_id = player_id
        room.state.uno_call_sequence += 1

    def _catch_uno(self, room: RelayRoom, catcher_id: str, target_player_id: str) -> None:
        if not target_player_id:
            raise ValueError("Choose a player to catch")
        if catcher_id == target_player_id:
            raise ValueError("You cannot catch yourself. Call UNO instead")
        room.state.prune_uno_protections()
        target = room.state.player_by_id(target_player_id)
        if len(target.hand.cards) != 1:
            raise ValueError("That player does not have UNO")
        if target_player_id in room.state.uno_protected_player_ids:
            raise ValueError("They already called UNO")
        self.draws.draw_for_player(room.state, target_player_id, 2)
        room.state.uno_catch_player_id = catcher_id
        room.state.uno_caught_player_id = target_player_id
        room.state.uno_catch_sequence += 1
        room.state.prune_uno_protections()
