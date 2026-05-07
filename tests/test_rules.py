import unittest

from application.commands.draw_card import DrawCardCommand
from application.commands.pass_turn import PassTurnCommand
from application.commands.play_card import PlayCardCommand
from application.commands.react_event import ReactEventCommand
from application.handlers.draw_handler import DrawHandler
from application.handlers.pass_turn_handler import PassTurnHandler
from application.handlers.play_card_handler import PlayCardHandler
from application.handlers.reaction_handler import ReactionHandler
from config.constants import REACTION_PENALTY_CARDS
from config.enums import CardColor, CardRank, GamePhase, PassDirection
from domain.entities.card import Card
from domain.entities.player import Player
from domain.state.game_state import GameState
from systems.ai.bot_player import BotPlayerController
from systems.turn.turn_manager import TurnManager


class RuleTests(unittest.TestCase):
    def make_state(self) -> GameState:
        state = GameState(players=[Player("p1", "A"), Player("p2", "B")], phase=GamePhase.PLAYING)
        state.players[0].hand.add(Card("red_1_0", CardColor.RED, CardRank.ONE))
        state.players[0].hand.add(Card("blue_2_0", CardColor.BLUE, CardRank.TWO))
        state.players[1].hand.add(Card("green_1_0", CardColor.GREEN, CardRank.ONE))
        state.deck.discard(Card("red_5_0", CardColor.RED, CardRank.FIVE))
        state.active_color = CardColor.RED
        return state

    def test_valid_play_advances_turn(self) -> None:
        state = self.make_state()
        PlayCardHandler().handle(state, PlayCardCommand("p1", "red_1_0"))
        self.assertEqual(state.current_player.id, "p2")
        self.assertEqual(state.deck.top_discard.id, "red_1_0")

    def test_invalid_card_is_rejected(self) -> None:
        state = self.make_state()
        with self.assertRaises(ValueError):
            PlayCardHandler().handle(state, PlayCardCommand("p1", "blue_2_0"))

    def test_draw_penalty_ignores_malicious_client_count(self) -> None:
        state = self.make_state()
        state.players[0].hand.add(Card("red_draw_2_0", CardColor.RED, CardRank.DRAW_TWO))
        state.deck.draw_pile = [
            Card("draw_a", CardColor.BLUE, CardRank.ONE),
            Card("draw_b", CardColor.GREEN, CardRank.TWO),
            Card("draw_c", CardColor.RED, CardRank.THREE),
        ]
        PlayCardHandler().handle(state, PlayCardCommand("p1", "red_draw_2_0"))
        DrawHandler().handle(state, DrawCardCommand("p2", 99))
        self.assertEqual(len(state.players[1].hand.cards), 3)
        self.assertEqual(state.turn.pending_draw, 0)

    def test_reaction_timeout_penalizes_missing_player(self) -> None:
        state = self.make_state()
        state.players[0].hand.add(Card("red_8_0", CardColor.RED, CardRank.EIGHT))
        state.deck.draw_pile = [
            Card(f"penalty_{index}", CardColor.BLUE, CardRank.ONE)
            for index in range(REACTION_PENALTY_CARDS * 2)
        ]
        PlayCardHandler().handle(state, PlayCardCommand("p1", "red_8_0"))
        state.reaction.expires_at = 0
        ReactionHandler().finish_if_ready(state)
        self.assertEqual(state.phase, GamePhase.PLAYING)
        self.assertEqual(len(state.players[0].hand.cards), 2 + REACTION_PENALTY_CARDS)
        self.assertEqual(len(state.players[1].hand.cards), 1 + REACTION_PENALTY_CARDS)

    def test_turn_order_skips_disconnected_players(self) -> None:
        state = GameState(players=[Player("p1", "A"), Player("p2", "B"), Player("p3", "C")])
        state.players[1].connected = False
        TurnManager().advance(state)
        self.assertEqual(state.current_player.id, "p3")

    def test_zero_requires_direction(self) -> None:
        state = self.make_state()
        state.players[0].hand.add(Card("red_0_0", CardColor.RED, CardRank.ZERO))
        with self.assertRaises(ValueError):
            PlayCardHandler().handle(state, PlayCardCommand("p1", "red_0_0"))
        PlayCardHandler().handle(state, PlayCardCommand("p1", "red_0_0", pass_direction=PassDirection.CLOCKWISE))
        self.assertEqual(state.deck.top_discard.id, "red_0_0")

    def test_reverse_acts_as_skip_with_two_players(self) -> None:
        state = GameState(players=[Player("p1", "A"), Player("p2", "B")], phase=GamePhase.PLAYING)
        state.players[0].hand.add(Card("red_reverse_0", CardColor.RED, CardRank.REVERSE))
        state.players[0].hand.add(Card("red_1_0", CardColor.RED, CardRank.ONE))
        state.players[1].hand.add(Card("green_1_0", CardColor.GREEN, CardRank.ONE))
        state.deck.discard(Card("red_5_0", CardColor.RED, CardRank.FIVE))
        state.active_color = CardColor.RED
        PlayCardHandler().handle(state, PlayCardCommand("p1", "red_reverse_0"))
        self.assertEqual(state.current_player.id, "p1")
        self.assertEqual(state.turn.direction.name, "CLOCKWISE")

    def test_reverse_changes_direction_with_three_players(self) -> None:
        state = GameState(players=[Player("p1", "A"), Player("p2", "B"), Player("p3", "C")], phase=GamePhase.PLAYING)
        state.players[0].hand.add(Card("red_reverse_0", CardColor.RED, CardRank.REVERSE))
        state.players[0].hand.add(Card("red_1_0", CardColor.RED, CardRank.ONE))
        state.players[1].hand.add(Card("green_1_0", CardColor.GREEN, CardRank.ONE))
        state.players[2].hand.add(Card("blue_1_0", CardColor.BLUE, CardRank.ONE))
        state.deck.discard(Card("red_5_0", CardColor.RED, CardRank.FIVE))
        state.active_color = CardColor.RED
        PlayCardHandler().handle(state, PlayCardCommand("p1", "red_reverse_0"))
        self.assertEqual(state.current_player.id, "p3")
        self.assertEqual(state.turn.direction.name, "COUNTER_CLOCKWISE")

    def test_cannot_win_with_action_card(self) -> None:
        state = GameState(players=[Player("p1", "A"), Player("p2", "B")], phase=GamePhase.PLAYING)
        state.players[0].hand.add(Card("red_skip_0", CardColor.RED, CardRank.SKIP))
        state.players[1].hand.add(Card("green_1_0", CardColor.GREEN, CardRank.ONE))
        state.deck.discard(Card("red_5_0", CardColor.RED, CardRank.FIVE))
        state.active_color = CardColor.RED
        with self.assertRaises(ValueError):
            PlayCardHandler().handle(state, PlayCardCommand("p1", "red_skip_0"))

    def test_last_card_seven_is_legal_but_swapped_empty_hand_wins(self) -> None:
        state = GameState(players=[Player("p1", "A"), Player("p2", "B")], phase=GamePhase.PLAYING)
        state.players[0].hand.add(Card("red_7_0", CardColor.RED, CardRank.SEVEN))
        state.players[1].hand.add(Card("green_1_0", CardColor.GREEN, CardRank.ONE))
        state.players[1].hand.add(Card("blue_2_0", CardColor.BLUE, CardRank.TWO))
        state.deck.discard(Card("red_5_0", CardColor.RED, CardRank.FIVE))
        state.active_color = CardColor.RED
        PlayCardHandler().handle(state, PlayCardCommand("p1", "red_7_0", target_player_id="p2"))
        self.assertEqual(state.phase, GamePhase.ENDED)
        self.assertEqual(state.winner_id, "p2")
        self.assertEqual(len(state.players[0].hand.cards), 2)
        self.assertEqual(len(state.players[1].hand.cards), 0)

    def test_stack_after_plus_four_requires_plus_four(self) -> None:
        state = GameState(players=[Player("p1", "A"), Player("p2", "B")], phase=GamePhase.PLAYING)
        state.players[0].hand.add(Card("wild_draw_four_0", CardColor.WILD, CardRank.WILD_DRAW_FOUR))
        state.players[0].hand.add(Card("red_1_0", CardColor.RED, CardRank.ONE))
        state.players[1].hand.add(Card("red_draw_2_0", CardColor.RED, CardRank.DRAW_TWO))
        state.players[1].hand.add(Card("green_1_0", CardColor.GREEN, CardRank.ONE))
        state.deck.discard(Card("red_5_0", CardColor.RED, CardRank.FIVE))
        state.active_color = CardColor.RED
        PlayCardHandler().handle(state, PlayCardCommand("p1", "wild_draw_four_0", chosen_color=CardColor.RED))
        with self.assertRaises(ValueError):
            PlayCardHandler().handle(state, PlayCardCommand("p2", "red_draw_2_0"))

    def test_drawn_playable_card_can_be_passed(self) -> None:
        state = GameState(players=[Player("p1", "A"), Player("p2", "B")], phase=GamePhase.PLAYING)
        state.players[0].hand.add(Card("blue_2_0", CardColor.BLUE, CardRank.TWO))
        state.players[1].hand.add(Card("green_1_0", CardColor.GREEN, CardRank.ONE))
        state.deck.discard(Card("red_5_0", CardColor.RED, CardRank.FIVE))
        state.active_color = CardColor.RED
        state.deck.draw_pile = [Card("red_9_0", CardColor.RED, CardRank.NINE)]
        DrawHandler().handle(state, DrawCardCommand("p1"))
        self.assertEqual(state.current_player.id, "p1")
        self.assertTrue(state.turn.drew_this_turn)
        PassTurnHandler().handle(state, PassTurnCommand("p1"))
        self.assertEqual(state.current_player.id, "p2")

    def test_player_with_legal_card_cannot_draw(self) -> None:
        state = self.make_state()
        state.deck.draw_pile = [Card("red_9_0", CardColor.RED, CardRank.NINE)]
        with self.assertRaises(ValueError):
            DrawHandler().handle(state, DrawCardCommand("p1"))

    def test_last_card_eight_resolves_reaction_before_win(self) -> None:
        state = GameState(players=[Player("p1", "A"), Player("p2", "B")], phase=GamePhase.PLAYING)
        state.players[0].hand.add(Card("red_8_0", CardColor.RED, CardRank.EIGHT))
        state.players[1].hand.add(Card("green_1_0", CardColor.GREEN, CardRank.ONE))
        state.deck.draw_pile = [Card("penalty_1", CardColor.BLUE, CardRank.ONE), Card("penalty_2", CardColor.BLUE, CardRank.TWO)]
        state.deck.discard(Card("red_5_0", CardColor.RED, CardRank.FIVE))
        state.active_color = CardColor.RED
        PlayCardHandler().handle(state, PlayCardCommand("p1", "red_8_0"))
        self.assertEqual(state.phase, GamePhase.REACTION)
        self.assertIsNone(state.winner_id)
        ReactionHandler().handle(state, ReactEventCommand("p1"))
        ReactionHandler().handle(state, ReactEventCommand("p2"))
        self.assertEqual(state.phase, GamePhase.ENDED)
        self.assertEqual(state.winner_id, "p1")

    def test_bot_plays_legal_card(self) -> None:
        state = GameState(players=[Player("p1", "Bot", is_bot=True), Player("p2", "Human")], phase=GamePhase.PLAYING)
        state.players[0].hand.add(Card("red_1_0", CardColor.RED, CardRank.ONE))
        state.players[0].hand.add(Card("blue_9_0", CardColor.BLUE, CardRank.NINE))
        state.players[1].hand.add(Card("green_1_0", CardColor.GREEN, CardRank.ONE))
        state.deck.discard(Card("red_5_0", CardColor.RED, CardRank.FIVE))
        state.active_color = CardColor.RED
        BotPlayerController().take_turn(state, state.players[0])
        self.assertEqual(state.deck.top_discard.id, "red_1_0")


if __name__ == "__main__":
    unittest.main()
