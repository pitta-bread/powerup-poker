"""Rule-numbered unit tests: uv run python -m unittest -v tests."""

import io
import pickle
import random
import unittest
from collections import Counter
from contextlib import redirect_stdout
from unittest.mock import patch

from powerup_poker import cli
from powerup_poker.engine import (
    Deck,
    DeckType,
    GameEngine,
    Player,
    PlayingCard,
    PowerUpCard,
    PowerUpType,
    Rank,
    Suit,
    evaluate_hand,
)


def cards(text):
    return [
        PlayingCard(
            Rank("23456789TJQKA".index(rank) + 2), dict(zip("cdhs", Suit))[suit]
        )
        for rank, suit in text.split()
    ]


def game(chips=(20, 20), seed=42):
    engine = GameEngine(seed)
    for name, stack in zip(("Alice", "Bob"), chips):
        engine.add_player(Player(name, stack))
    engine.start_hand()
    return engine


def check_down(engine):
    while engine.state.turn is not None:
        engine.act(engine.state.turn, "check")


class HandTests(unittest.TestCase):
    """Rules 1, 3, 10: Hold'em ranking, best five, ties and Ace handling."""

    def test_rule_01_all_categories_in_order(self):
        hands = [
            "Ac Jd 9h 5s 2c",
            "Ac Ad 9h 5s 2c",
            "Ac Ad 9h 9s 2c",
            "Ac Ad Ah 5s 2c",
            "2c 3d 4h 5s 6c",
            "Ac Jc 9c 5c 2c",
            "Ac Ad Ah 5s 5c",
            "Ac Ad Ah As 2c",
            "Tc Jc Qc Kc Ac",
        ]
        scores = [evaluate_hand(cards(hand)) for hand in hands]
        self.assertEqual([score[0] for score in scores], list(range(9)))
        self.assertEqual(scores, sorted(scores))

    def test_rule_01_tiebreakers_in_every_category(self):
        for stronger, weaker in [
            ("Ac Jd 9h 5s 3c", "Ac Jd 9h 5s 2c"),
            ("Ac Ad 9h 5s 3c", "Ac Ad 9h 5s 2c"),
            ("Ac Ad 9h 9s 3c", "Ac Ad 9h 9s 2c"),
            ("Ac Ad Ah 5s 3c", "Ac Ad Ah 5s 2c"),
            ("3c 4d 5h 6s 7c", "2c 3d 4h 5s 6c"),
            ("Ac Jc 9c 5c 3c", "Ac Jc 9c 5c 2c"),
            ("Ac Ad Ah 6s 6c", "Ac Ad Ah 5s 5c"),
            ("Ac Ad Ah As 3c", "Ac Ad Ah As 2c"),
            ("3c 4c 5c 6c 7c", "2c 3c 4c 5c 6c"),
            ("Kc Kd 9h 5s 2c", "Qc Qd Ah Js Tc"),
            ("Kc Kd 9h 9s 2c", "Qc Qd Jh Js Ac"),
            ("Kc Kd Jh Js 2c", "Kc Kd Th Ts Ac"),
            ("Kc Kd Kh 2s 2c", "Qc Qd Qh As Ac"),
        ]:
            with self.subTest(stronger=stronger):
                self.assertGreater(
                    evaluate_hand(cards(stronger)), evaluate_hand(cards(weaker))
                )

    def test_rule_03_ace_high_and_wheel(self):
        self.assertEqual(list(Rank), list(range(2, 15)))
        self.assertEqual(evaluate_hand(cards("Ac 2d 3h 4s 5c")), (4, 5))
        self.assertEqual(evaluate_hand(cards("Tc Jd Qh Ks Ac")), (4, 14))
        self.assertEqual(evaluate_hand(cards("Qc Kd Ah 2s 3c"))[0], 0)
        self.assertEqual(evaluate_hand(cards("Ac 2c 3c 4c 5c")), (8, 5))

    def test_rule_01_best_five_of_seven(self):
        for hand, score in [
            ("Ac Ad Ah Kc Kd Kh 2s", (6, 14, 13)),
            ("Ac Ad Kc Kd Qc Qd 2s", (2, 14, 13, 12)),
            ("Ac Jc 9c 7c 5c 3c 2d", (5, 14, 11, 9, 7, 5)),
            ("Ac 2d 3h 4s 5c 6d 7h", (4, 7)),
        ]:
            with self.subTest(hand=hand):
                self.assertEqual(evaluate_hand(cards(hand)), score)

    def test_rule_01_can_use_zero_one_or_two_hole_cards(self):
        for hole, board, score in [
            ("2d 3h", "Tc Jc Qc Kc Ac", (8, 14)),
            ("Ac 3h", "Tc Jc Qc Kc 2d", (8, 14)),
            ("Kc Ac", "Tc Jc Qc 2d 3h", (8, 14)),
        ]:
            self.assertEqual(evaluate_hand(cards(hole + " " + board)), score)

    def test_rule_01_suits_do_not_break_ties(self):
        self.assertEqual(
            evaluate_hand(cards("Ac Jc 9c 5c 2c")),
            evaluate_hand(cards("Ad Jd 9d 5d 2d")),
        )

    def test_rule_09_duplicates_and_five_matching_ranks(self):
        self.assertEqual(evaluate_hand(cards("Ac Ac 9h 5s 2c")), (1, 14, 9, 5, 2))
        five = evaluate_hand(cards("Kc Kc Kd Kh Ks"))
        self.assertEqual(five, (7, 13, 13))
        self.assertLess(five, evaluate_hand(cards("Kc Kd Kh Ks Ac")))
        self.assertLess(five, evaluate_hand(cards("2c 3c 4c 5c 6c")))
        self.assertEqual(evaluate_hand(cards("Kc Kc Kd Kh Ks Ac 2c")), (7, 13, 14))

    def test_reject_incomplete_or_oversized_hands(self):
        for count in (0, 2, 4, 8):
            with self.assertRaises(ValueError):
                evaluate_hand(cards("Ac") * count)


class RulesTests(unittest.TestCase):
    def test_rule_02_standard_deck(self):
        deck = Deck(DeckType.PLAYING)
        self.assertEqual(len(deck), 52)
        self.assertEqual(
            set(deck), {PlayingCard(rank, suit) for rank in Rank for suit in Suit}
        )
        drawn = [deck.draw() for _ in range(52)]
        self.assertEqual(len(set(drawn)), 52)
        with self.assertRaises(IndexError):
            deck.draw()

    def test_rule_04_exactly_two_distinct_players(self):
        engine = GameEngine()
        with self.assertRaises(ValueError):
            engine.start_hand()
        player = Player("A")
        engine.add_player(player)
        with self.assertRaises(ValueError):
            engine.start_hand()
        with self.assertRaises(ValueError):
            engine.add_player(player)
        engine.add_player(Player("B"))
        with self.assertRaises(ValueError):
            engine.add_player(Player("C"))
        engine.start_hand()
        with self.assertRaises(ValueError):
            engine.add_player(Player("D"))

    def test_rule_05_deal_and_privacy(self):
        engine = game()
        s = engine.state
        self.assertEqual(len(s.playing_deck), 48)
        self.assertEqual(len(s.power_up_deck), 13)
        self.assertEqual(len(set(s.players[0].hand + s.players[1].hand)), 4)
        for i in (0, 1):
            self.assertEqual(len(s.players[i].hand), 2)
            self.assertEqual(len(s.players[i].power_ups), 1)
            view = engine.view(i)
            self.assertEqual(len(view["players"][i]["hand"]), 2)
            self.assertEqual(len(view["players"][i]["power_ups"]), 1)
            self.assertEqual(view["players"][1 - i]["hand"], ())
            self.assertEqual(view["players"][1 - i]["power_ups"], ())
        self.assertNotIn("deck", engine.view(0))

    def test_rule_06_two_betting_rounds_then_runout(self):
        engine = game()
        s = engine.state
        self.assertEqual((s.phase, s.turn, len(s.community_cards)), ("pre-flop", 0, 0))
        engine.act(0, "check")
        engine.act(1, "check")
        self.assertEqual((s.phase, s.turn, len(s.community_cards)), ("post-flop", 1, 3))
        engine.act(1, "check")
        engine.act(0, "check")
        self.assertEqual(
            (s.phase, s.turn, len(s.community_cards)), ("finished", None, 5)
        )
        self.assertEqual(len(s.discards), 3)  # One burn per street.
        self.assertEqual(len(s.playing_deck), 40)
        self.assertEqual(
            len(
                set(
                    list(s.playing_deck)
                    + s.discards
                    + s.community_cards
                    + s.players[0].hand
                    + s.players[1].hand
                )
            ),
            52,
        )

    def test_rule_07_one_chip_per_player_per_round(self):
        engine = game()
        s = engine.state
        engine.act(0, "bet")
        self.assertEqual(s.pot, 3)
        self.assertEqual(engine.legal_actions(), ("call", "fold"))
        before = pickle.dumps(engine)
        for illegal in ("bet", "check", "raise"):
            with self.assertRaises(ValueError):
                engine.act(1, illegal)
            self.assertEqual(pickle.dumps(engine), before)
        engine.act(1, "call")
        self.assertEqual((s.phase, s.pot), ("post-flop", 4))
        self.assertEqual([p.chips for p in s.players], [18, 18])
        engine.act(1, "bet")
        self.assertEqual(s.pot, 5)
        engine.act(0, "call")
        self.assertEqual(s.payout, 6)
        self.assertEqual(s.round_bets, [1, 1])

    def test_rule_01_check_then_respond_to_bet(self):
        engine = game()
        engine.act(0, "check")
        engine.act(1, "bet")
        self.assertEqual(engine.state.turn, 0)
        self.assertEqual(engine.state.phase, "pre-flop")
        engine.act(0, "call")
        self.assertEqual(engine.state.phase, "post-flop")

    def test_rule_01_wrong_turn_and_inactive_actions_rejected(self):
        engine = game()
        for actor in (1, -1, 2, 0.0, False):
            with self.assertRaises(ValueError):
                engine.act(actor, "check")
        with self.assertRaises(ValueError):
            engine.start_hand()
        with self.assertRaises(ValueError):
            engine.act(0, "call")
        engine.act(0, "fold")
        with self.assertRaises(ValueError):
            engine.act(1, "check")
        self.assertEqual(engine.legal_actions(), ())

    def test_rule_01_fold_awards_pot_and_keeps_cards_private(self):
        for post_flop in (False, True):
            with self.subTest(post_flop=post_flop):
                engine = game()
                if post_flop:
                    engine.act(0, "check")
                    engine.act(1, "check")
                bettor = engine.state.turn
                engine.act(bettor, "bet")
                engine.act(1 - bettor, "fold")
                self.assertEqual(engine.state.winners, [bettor])
                self.assertEqual(engine.state.payout, 3)
                self.assertEqual(engine.state.players[bettor].chips, 21)
                self.assertFalse(engine.state.showdown)
                self.assertEqual(engine.view(1 - bettor)["players"][bettor]["hand"], ())

    def test_rule_10_best_hand_wins_entire_pot(self):
        engine = game()
        s = engine.state
        s.players[0].hand = cards("Ac Ad")
        s.players[1].hand = cards("Kc Kd")
        # Pop order: burn, flop, burn, turn, burn, river.
        s.playing_deck._cards = cards("9c 2c 3d 7h 9d 8s Tc Jh")[::-1]
        check_down(engine)
        self.assertEqual(s.winners, [0])
        self.assertEqual([p.chips for p in s.players], [21, 19])
        self.assertEqual((s.payout, s.pot), (2, 0))
        self.assertTrue(engine.view(1)["players"][0]["hand"])
        self.assertFalse(engine.view(1)["players"][0]["power_ups"])

    def test_rule_01_tied_board_splits_pot(self):
        engine = game()
        s = engine.state
        s.players[0].hand = cards("2d 3h")
        s.players[1].hand = cards("4d 5h")
        s.playing_deck._cards = cards("9d Tc Jc Qc 8d Kc 7d Ac")[::-1]
        check_down(engine)
        self.assertEqual(s.winners, [0, 1])
        self.assertEqual([p.chips for p in s.players], [20, 20])

    def test_rule_11_power_deck_has_three_of_each(self):
        deck = Deck(DeckType.POWER_UP)
        self.assertEqual(len(deck), 15)
        self.assertEqual(
            Counter(deck),
            Counter(PowerUpCard(effect) for effect in PowerUpType for _ in range(3)),
        )

    def test_rule_12_starting_chips_and_match_end(self):
        self.assertEqual(Player("A").chips, 20)
        engine = game((1, 39))
        self.assertEqual(engine.state.phase, "finished")
        self.assertEqual(len(engine.state.community_cards), 5)
        # If the short stack survived, fold its next hand to end the match.
        while not engine.game_over:
            engine.start_hand()
            if engine.state.turn is not None:
                if engine.state.turn != 0:
                    engine.act(1, "check")
                engine.act(0, "fold")
        self.assertEqual(sorted(p.chips for p in engine.state.players), [0, 40])
        with self.assertRaises(ValueError):
            engine.start_hand()

    def test_rule_12_fresh_hands_rotate_dealer_and_reset_decks(self):
        engine = game()
        for number in range(1, 21):
            s = engine.state
            self.assertEqual(s.hand_number, number)
            self.assertEqual(s.dealer, (number - 1) % 2)
            self.assertEqual(s.turn, s.dealer)
            self.assertEqual((len(s.playing_deck), len(s.power_up_deck)), (48, 13))
            self.assertEqual((s.community_cards, s.discards, s.winners), ([], [], []))
            self.assertFalse(s.showdown)
            engine.act(s.turn, "fold")
            if number < 20:
                engine.start_hand()

    def test_rule_13_antes_and_maximum_pot(self):
        engine = game()
        self.assertEqual([p.chips for p in engine.state.players], [19, 19])
        self.assertEqual(engine.state.pot, 2)
        for action in ("bet", "call", "bet", "call"):
            engine.act(engine.state.turn, action)
            self.assertLessEqual(engine.state.pot, 6)
            self.assertEqual(
                sum(p.chips for p in engine.state.players) + engine.state.pot, 40
            )
        self.assertEqual(engine.state.payout, 6)

    def test_rule_13_short_stack_skips_unfunded_betting(self):
        for chips in ((1, 39), (39, 1), (1, 1)):
            with self.subTest(chips=chips):
                engine = game(chips)
                self.assertEqual(engine.state.phase, "finished")
                self.assertEqual(engine.state.payout, 2)
                self.assertEqual(sum(p.chips for p in engine.state.players), sum(chips))
        engine = game((2, 38))
        engine.act(0, "bet")
        engine.act(1, "call")
        self.assertEqual(engine.state.phase, "finished")
        self.assertEqual(engine.state.payout, 4)


class PowerTests(unittest.TestCase):
    """Rules 8 and 9: timing, disclosure, all effects, targets and failure cases."""

    def setUp(self):
        self.engine = game()
        self.player = self.engine.state.players[0]
        self.player.hand = cards("Kc 7d")

    def power(self, effect):
        self.player.power_ups = [PowerUpCard(effect)]

    def reject(self, action="bet", target=0, use=True):
        before = pickle.dumps(self.engine)
        with self.assertRaises(ValueError):
            self.engine.act(0, action, use_power_up=use, target=target)
        self.assertEqual(pickle.dumps(self.engine), before)

    def test_rule_09_plus_one_creates_card_without_touching_deck(self):
        self.power(PowerUpType.INCREASE_CARD_VALUE)
        self.engine.state.players[1].hand = cards("Ac 2s")
        before = list(self.engine.state.playing_deck)
        self.engine.act(0, "bet", use_power_up=True, target=0)
        self.assertEqual(self.player.hand, cards("Ac 7d"))
        self.assertEqual(list(self.engine.state.playing_deck), before)
        self.assertEqual(self.engine.state.players[1].hand, cards("Ac 2s"))

    def test_rule_09_minus_one_preserves_suit_and_deck(self):
        self.power(PowerUpType.DECREASE_CARD_VALUE)
        self.player.hand = cards("Ac 7d")
        before = list(self.engine.state.playing_deck)
        self.engine.act(0, "bet", use_power_up=True, target=0)
        self.assertEqual(self.player.hand, cards("Kc 7d"))
        self.assertEqual(list(self.engine.state.playing_deck), before)

    def test_rule_09_every_legal_rank_change(self):
        for effect, delta, ranks in [
            (PowerUpType.INCREASE_CARD_VALUE, 1, range(2, 14)),
            (PowerUpType.DECREASE_CARD_VALUE, -1, range(3, 15)),
        ]:
            for rank in ranks:
                with self.subTest(effect=effect, rank=rank):
                    engine = game()
                    player = engine.state.players[0]
                    player.hand[1] = PlayingCard(Rank(rank), Suit.HEARTS)
                    player.power_ups = [PowerUpCard(effect)]
                    engine.act(0, "bet", use_power_up=True, target=1)
                    self.assertEqual(
                        player.hand[1], PlayingCard(Rank(rank + delta), Suit.HEARTS)
                    )

    def test_rule_09_rank_boundaries_reject_without_consuming_power_or_bet(self):
        for effect, hand in [
            (PowerUpType.INCREASE_CARD_VALUE, "Ac 7d"),
            (PowerUpType.DECREASE_CARD_VALUE, "2c 7d"),
        ]:
            self.power(effect)
            self.player.hand = cards(hand)
            self.reject()

    def test_rule_09_change_can_duplicate_own_hole_card(self):
        self.power(PowerUpType.INCREASE_CARD_VALUE)
        self.player.hand = cards("Kc Ac")
        self.engine.act(0, "bet", use_power_up=True, target=0)
        self.assertEqual(self.player.hand, cards("Ac Ac"))

    def test_rule_09_auto_ace_swaps_only_selected_hole(self):
        self.power(PowerUpType.AUTO_ACE)
        self.engine.state.playing_deck._cards = cards("2c Ah 9s")
        self.engine.act(0, "bet", use_power_up=True, target=0)
        self.assertEqual(self.player.hand, cards("Ah 7d"))
        self.assertEqual(list(self.engine.state.playing_deck), cards("2c Kc 9s"))

    def test_rule_09_pocket_pair_keeps_target_and_requires_different_suit(self):
        self.power(PowerUpType.POCKET_PAIR)
        self.engine.state.playing_deck._cards = cards("Kc Kh 9s")
        self.engine.act(0, "bet", use_power_up=True, target=0)
        self.assertEqual(self.player.hand, cards("Kc Kh"))
        self.assertEqual(list(self.engine.state.playing_deck), cards("Kc 7d 9s"))

    def test_rule_09_pocket_pair_can_keep_second_card(self):
        self.power(PowerUpType.POCKET_PAIR)
        self.engine.state.playing_deck._cards = cards("7h 9s")
        self.engine.act(0, "bet", use_power_up=True, target=1)
        self.assertEqual(self.player.hand, cards("7h 7d"))

    def test_rule_09_swaps_choose_randomly_among_eligible_deck_cards(self):
        for effect, hand, deck in [
            (PowerUpType.AUTO_ACE, "Kc 7d", "Ac Ad Ah As 2c"),
            (PowerUpType.POCKET_PAIR, "Kc 7d", "Kd Kh Ks 2c"),
        ]:
            seen = set()
            for seed in range(30):
                engine = game(seed=seed)
                player = engine.state.players[0]
                player.hand = cards(hand)
                player.power_ups = [PowerUpCard(effect)]
                engine.state.playing_deck._cards = cards(deck)
                engine.act(0, "bet", use_power_up=True, target=0)
                seen.add(player.hand[0 if effect == PowerUpType.AUTO_ACE else 1])
            self.assertEqual(seen, set(cards(deck)[:-1]))

    def test_rule_09_swaps_cannot_take_cards_from_opponent_or_discards(self):
        for effect in (PowerUpType.AUTO_ACE, PowerUpType.POCKET_PAIR):
            self.power(effect)
            self.engine.state.playing_deck._cards = cards("2c 3h")
            self.engine.state.players[1].hand = cards("Ac Kh")
            self.engine.state.discards = cards("Ad Kd")
            self.reject()

    def test_rule_09_pocket_pair_rejects_only_same_suit_candidate(self):
        self.power(PowerUpType.POCKET_PAIR)
        self.engine.state.playing_deck._cards = cards("Kc 2h")
        self.reject()

    def test_rule_09_redeal_discards_and_draws_top_two_in_order(self):
        self.power(PowerUpType.RE_DEAL)
        self.engine.state.playing_deck._cards = cards("2c 3h 4s")
        self.engine.act(0, "bet", use_power_up=True)
        self.assertEqual(self.player.hand, cards("4s 3h"))
        self.assertEqual(self.engine.state.discards, cards("Kc 7d"))
        self.assertEqual(list(self.engine.state.playing_deck), cards("2c"))

    def test_rule_09_redeal_failure_is_atomic(self):
        self.power(PowerUpType.RE_DEAL)
        self.reject(target=0)
        self.engine.state.playing_deck._cards = cards("2c")
        self.reject(target=None)

    def test_rule_08_use_with_bet_stays_private_and_consumes_power(self):
        self.power(PowerUpType.INCREASE_CARD_VALUE)
        self.engine.act(0, "bet", use_power_up=True, target=0)
        self.assertEqual(self.player.power_ups, [])
        self.assertEqual(self.player.chips, 18)
        visible = self.engine.view(1)["players"][0]
        self.assertIsNone(visible["played_power_up"])
        self.assertIsNone(visible["power_up_used"])
        self.assertEqual(visible["hand"], ())
        self.assertEqual(
            self.engine.view(0)["players"][0]["played_power_up"].effect,
            PowerUpType.INCREASE_CARD_VALUE,
        )

    def test_rule_08_both_players_reveal_usage_only_at_flop(self):
        for bettor in (0, 1):
            for ending in ("fold", "showdown"):
                with self.subTest(bettor=bettor, ending=ending):
                    engine = game()
                    for player in engine.state.players:
                        player.hand = cards("Kc 7d")
                        player.power_ups = [
                            PowerUpCard(PowerUpType.INCREASE_CARD_VALUE)
                        ]
                    if bettor == 1:
                        engine.act(0, "check")
                    before = engine.view(1 - bettor)["players"][bettor]
                    engine.act(bettor, "bet", use_power_up=True, target=0)
                    after = engine.view(1 - bettor)["players"][bettor]
                    # Only the chip count reveals the bet; power usage leaves no hint.
                    self.assertEqual(after, {**before, "chips": before["chips"] - 1})
                    engine.act(1 - bettor, "call", use_power_up=True, target=0)
                    self.assertEqual(engine.state.phase, "post-flop")
                    for viewer in (0, 1):
                        view = engine.view(viewer)
                        self.assertTrue(
                            all(p["power_up_used"] is True for p in view["players"])
                        )
                        self.assertIsNone(
                            view["players"][1 - viewer]["played_power_up"]
                        )
                        self.assertEqual(view["players"][1 - viewer]["hand"], ())
                    if ending == "fold":
                        engine.act(engine.state.turn, "fold")
                    else:
                        check_down(engine)
                    for viewer in (0, 1):
                        view = engine.view(viewer)
                        self.assertTrue(
                            all(p["power_up_used"] is True for p in view["players"])
                        )
                        self.assertIsNone(
                            view["players"][1 - viewer]["played_power_up"]
                        )
                        self.assertEqual(view["players"][1 - viewer]["power_ups"], ())

    def test_rule_08_pre_flop_fold_does_not_reveal_power(self):
        for bettor in (0, 1):
            with self.subTest(bettor=bettor):
                engine = game()
                player = engine.state.players[bettor]
                player.hand = cards("Kc 7d")
                player.power_ups = [PowerUpCard(PowerUpType.INCREASE_CARD_VALUE)]
                if bettor == 1:
                    engine.act(0, "check")
                engine.act(bettor, "bet", use_power_up=True, target=0)
                engine.act(1 - bettor, "fold")
                self.assertIsNone(
                    engine.view(1 - bettor)["players"][bettor]["played_power_up"]
                )
                self.assertIsNone(
                    engine.view(1 - bettor)["players"][bettor]["power_up_used"]
                )
                self.assertIsNotNone(
                    engine.view(bettor)["players"][bettor]["played_power_up"]
                )

    def test_rule_08_unused_status_revealed_without_revealing_type(self):
        self.power(PowerUpType.INCREASE_CARD_VALUE)
        self.engine.act(0, "bet", use_power_up=True, target=0)
        self.assertIsNone(self.engine.view(0)["players"][1]["power_up_used"])
        self.engine.act(1, "call")
        for viewer in (0, 1):
            view = self.engine.view(viewer)
            self.assertIs(view["players"][0]["power_up_used"], True)
            self.assertIs(view["players"][1]["power_up_used"], False)
            self.assertIsNone(view["players"][1 - viewer]["played_power_up"])
            self.assertEqual(view["players"][1 - viewer]["power_ups"], ())

    def test_rule_08_use_with_call_after_check(self):
        self.power(PowerUpType.INCREASE_CARD_VALUE)
        self.engine.act(0, "check")
        self.engine.act(1, "bet")
        self.engine.act(0, "call", use_power_up=True, target=0)
        self.assertEqual(self.player.hand, cards("Ac 7d"))
        self.assertEqual(self.engine.state.phase, "post-flop")

    def test_rule_08_optional_and_unused_power_stays_hidden(self):
        power = self.player.power_ups[:]
        self.engine.act(0, "bet")
        self.assertEqual(self.player.power_ups, power)
        self.assertIsNone(self.engine.view(1)["players"][0]["played_power_up"])

    def test_rules_05_08_new_hand_deals_new_power_and_clears_reveal(self):
        self.power(PowerUpType.INCREASE_CARD_VALUE)
        self.engine.act(0, "bet", use_power_up=True, target=0)
        self.engine.act(1, "fold")
        self.engine.start_hand()
        self.assertEqual(len(self.player.power_ups), 1)
        self.assertIsNone(self.player.played_power_up)
        self.assertEqual(len(self.engine.state.power_up_deck), 13)
        self.assertIs(self.engine.view(0)["players"][0]["power_up_used"], False)
        self.assertIsNone(self.engine.view(1)["players"][0]["power_up_used"])

    def test_rule_08_no_power_with_check_fold_or_post_flop(self):
        self.power(PowerUpType.INCREASE_CARD_VALUE)
        self.reject(action="check")
        self.reject(action="fold")
        self.engine.act(0, "check")
        self.engine.act(1, "check")
        self.engine.act(1, "check")
        self.reject()

    def test_rule_08_missing_power_and_invalid_targets_rejected(self):
        self.power(PowerUpType.INCREASE_CARD_VALUE)
        for target in (None, -1, 2, 0.5, True):
            self.reject(target=target)
        self.reject(use=False)
        self.player.power_ups = []
        self.reject()


class PlayTests(unittest.TestCase):
    def test_cli_reveals_opponent_usage_without_effect(self):
        for used in (False, True):
            with self.subTest(used=used):
                engine = game()
                opponent = engine.state.players[1]
                opponent.hand = cards("Kc 7d")
                opponent.power_ups = [PowerUpCard(PowerUpType.INCREASE_CARD_VALUE)]
                engine.act(0, "check")
                engine.act(1, "bet", use_power_up=used, target=0 if used else None)
                with redirect_stdout(io.StringIO()) as out:
                    cli.show(engine)
                self.assertNotIn("Power-up", out.getvalue().split("Bob:")[1])
                engine.act(0, "call")
                with redirect_stdout(io.StringIO()) as out:
                    cli.show(engine)
                opponent_output = out.getvalue().split("Bob:")[1]
                self.assertIn(
                    "Power-up played: " + ("yes" if used else "no"), opponent_output
                )
                self.assertNotIn("Increase", opponent_output)
                self.assertNotIn("Plus 1", opponent_output)

    def test_seed_reproduces_deals(self):
        self.assertEqual(pickle.dumps(game(seed=123)), pickle.dumps(game(seed=123)))
        self.assertNotEqual(game(seed=123).view(0), game(seed=124).view(0))

    def test_many_complete_matches_conserve_chips_and_terminate(self):
        for seed in range(10):
            engine = game(seed=seed)
            rng = random.Random(seed)
            for _ in range(10000):
                s = engine.state
                if s.phase == "finished":
                    self.assertLessEqual(s.payout, 6)
                    if engine.game_over:
                        break
                    engine.start_hand()
                    continue
                i = s.turn
                action = rng.choice(engine.legal_actions())
                power = s.players[i].power_ups
                use = (
                    s.phase == "pre-flop" and action in ("bet", "call") and bool(power)
                )
                target = (
                    rng.randrange(2)
                    if use and power[0].effect != PowerUpType.RE_DEAL
                    else None
                )
                try:
                    engine.act(i, action, use_power_up=use, target=target)
                except ValueError:
                    engine.act(i, action)
                self.assertEqual(sum(p.chips for p in s.players) + s.pot, 40)
                self.assertTrue(all(p.chips >= 0 for p in s.players))
                self.assertTrue(all(bet <= 1 for bet in s.round_bets))
            self.assertTrue(engine.game_over, f"seed {seed} did not finish")
            self.assertEqual(sorted(p.chips for p in engine.state.players), [0, 40])

    def test_cli_bad_input_then_power_bet(self):
        engine = game()
        engine.state.players[0].hand = cards("Kc 7d")
        engine.state.players[0].power_ups = [
            PowerUpCard(PowerUpType.INCREASE_CARD_VALUE)
        ]
        with (
            patch(
                "builtins.input",
                side_effect=["", "help", "raise", "bet power x", "bet power 1"],
            ),
            redirect_stdout(io.StringIO()),
        ):
            self.assertTrue(cli.human_turn(engine))
        self.assertEqual(engine.state.players[0].hand, cards("Ac 7d"))
        self.assertEqual(engine.state.pot, 3)

    def test_cli_plays_complete_match(self):
        output = io.StringIO()
        with (
            patch("sys.argv", ["powerup-poker", "--seed", "42"]),
            patch("builtins.input", return_value="fold"),
            redirect_stdout(output),
        ):
            cli.main()
        self.assertIn("wins the match with 40 chips!", output.getvalue())

    def test_cli_quit_and_eof(self):
        for reply in ("quit", EOFError()):
            with (
                patch("sys.argv", ["powerup-poker", "--seed", "42"]),
                patch("builtins.input", side_effect=[reply]),
                redirect_stdout(io.StringIO()) as out,
            ):
                cli.main()
            self.assertIn("Goodbye!", out.getvalue())


if __name__ == "__main__":
    unittest.main()
