from uno_game.application.commands.play_card import PlayCardCommand
from uno_game.config.enums import CardRank
from uno_game.domain.state.game_state import GameState
from uno_game.rules.validator.card_playability import card_matches_state, is_action_final_card, penalty_value


class MoveValidator:
    def validate(self, state: GameState, command: PlayCardCommand) -> None:
        player = state.player_by_id(command.player_id)
        if state.current_player is None or state.current_player.id != command.player_id:
            raise ValueError("It is not this player's turn")

        card = player.hand.find(command.card_id)
        if card is None:
            raise ValueError("Player does not hold this card")

        if state.reaction.active:
            raise ValueError("Resolve the reaction before playing another card")

        if state.turn.drew_this_turn and state.turn.drawn_card_id is not None and command.card_id != state.turn.drawn_card_id:
            raise ValueError("After drawing, you may only play the drawn card or pass")

        if len(player.hand.cards) == 1 and is_action_final_card(card):
            raise ValueError("You cannot win with an action or special card")

        if state.turn.pending_draw > 0:
            value = penalty_value(card)
            if value == 0:
                raise ValueError("You must stack a draw card or draw the pending penalty")
            if value < state.turn.pending_draw_value:
                raise ValueError("Stacked draw card must be greater than or equal to the previous penalty")

        if card.rank == CardRank.SEVEN:
            if command.target_player_id is None:
                raise ValueError("Seven requires a target player")
            if command.target_player_id == command.player_id:
                raise ValueError("Seven must target another player")
            if not state.player_by_id(command.target_player_id).connected:
                raise ValueError("Seven target must be connected")

        if card.rank == CardRank.ZERO and command.pass_direction is None:
            raise ValueError("Zero requires a hand passing direction")

        if card_matches_state(state, card):
            return
        raise ValueError("Card does not match color or rank")
