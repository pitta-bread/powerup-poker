import random
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from itertools import combinations
from typing import cast


class Suit(StrEnum):
    """The four suits in a standard deck of playing cards."""

    CLUBS = "Clubs"
    DIAMONDS = "Diamonds"
    HEARTS = "Hearts"
    SPADES = "Spades"


class Rank(IntEnum):
    """Card ranks, with values chosen to make comparison and arithmetic natural."""

    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


class Card:
    """
    ABC for a card in any deck. Subclasses should be frozen dataclasses with slots.
    """

    name: str


@dataclass(frozen=True, slots=True)
class PlayingCard(Card):
    """A single card from a standard deck."""

    rank: Rank
    suit: Suit

    @property
    def name(self) -> str:
        """Return the card's player-facing name."""
        return f"{self.rank.name.title()} of {self.suit.value.title()}"


class PowerUpType(StrEnum):
    """Types of power-ups that can be used in the game."""

    INCREASE_CARD_VALUE = (
        "Plus 1. Increase the value of a card by +1. King goes to Ace."
    )
    DECREASE_CARD_VALUE = (
        "Minus 1. Decrease the value of a card by -1. Ace goes to King."
    )
    AUTO_ACE = (
        "Auto-ace. Swap one hole card of your choice with a random Ace remaining in "
        "the deck."
    )
    POCKET_PAIR = (
        "Pocket pair. Choose a hole card. Swap the other card with a card from the "
        "deck with the same value as the chosen card (but by necessity, different "
        "suit, randomly found)."
    )
    RE_DEAL = (
        "Re-deal. Discard your current hole cards and draw 2 new ones from the top "
        "of the deck."
    )


@dataclass(frozen=True, slots=True)
class PowerUpCard(Card):
    """A special card that can optionally be used to gain an advantage in the game."""

    effect: PowerUpType

    @property
    def name(self) -> str:
        """Return the power-up type's key as a player-facing name."""
        return self.effect.name.replace("_", " ").title()


class DeckType(StrEnum):
    """Types of card decks used in the game."""

    POWER_UP = "Power-up"
    PLAYING = "Playing"


class Deck:
    """A playing-card or power-up deck, with the top card at the end."""

    def __init__(self, deck_type: DeckType) -> None:
        self.deck_type: DeckType = deck_type
        self._cards: list[Card]
        if deck_type is DeckType.PLAYING:
            self._cards = [
                PlayingCard(rank, suit) for suit in Suit for rank in Rank
            ]
        elif deck_type is DeckType.POWER_UP:
            self._cards = [
                PowerUpCard(effect) for effect in (list(PowerUpType) * 3)
            ]
        else:
            raise ValueError("Unknown deck type.")

    def __len__(self) -> int:
        return len(self._cards)

    def __iter__(self) -> Iterator[Card]:
        return iter(self._cards)

    def shuffle(self, rng: random.Random | None = None) -> None:
        """Shuffle the remaining cards in place."""
        (rng or random).shuffle(self._cards)

    def draw(self) -> Card:
        """Remove and return the top card.

        Raises:
            IndexError: If the deck has no cards remaining.
        """
        if not self._cards:
            raise IndexError("cannot draw from an empty deck")
        return self._cards.pop()


class GameState:
    """The state of our PowerUp Poker game."""

    def __init__(self) -> None:
        self.playing_deck: Deck = Deck(deck_type=DeckType.PLAYING)
        self.playing_deck.shuffle()
        self.power_up_deck: Deck = Deck(deck_type=DeckType.POWER_UP)
        self.power_up_deck.shuffle()
        self.players: list[Player] = []
        self.community_cards: list[PlayingCard] = []
        self.hand_number: int = 0
        self.phase = "ready"
        self.dealer = 0
        self.turn: int | None = None
        self.pot = 0
        self.round_bets = [0, 0]
        self.pending: set[int] = set()
        self.discards: list[PlayingCard] = []
        self.winners: list[int] = []
        self.payout = 0
        self.showdown = False

    def add_player(self, player: "Player") -> None:
        """Add a player to the game."""
        if self.hand_number or len(self.players) == 2 or player in self.players:
            raise ValueError("Add exactly two different players before starting.")
        self.players.append(player)


class Player:
    """A player in the game."""

    def __init__(self, name: str, chips: int = 20) -> None:
        if type(chips) is not int or chips < 0:
            raise ValueError("Chips must be a non-negative integer.")
        self.name: str = name
        self.hand: list[PlayingCard] = []
        self.power_ups: list[PowerUpCard] = []
        self.chips: int = chips
        self.played_power_up: PowerUpCard | None = None

    def draw_hand(self, game_state: GameState) -> None:
        """Draw two cards from the playing deck and one from the power-up deck."""
        self.hand: list[PlayingCard] = [
            cast(typ=PlayingCard, val=game_state.playing_deck.draw()) for _ in range(2)
        ]
        self.power_ups: list[PowerUpCard] = [
            cast(typ=PowerUpCard, val=game_state.power_up_deck.draw()) for _ in range(1)
        ]

    def show_hand(self) -> str:
        """Return a string representation of the player's hand."""
        start: str = f"{self.name}'s hand: "
        middle: str = ", ".join(
            f"{card.rank.name} of {card.suit.value}" for card in self.hand
        )
        power_up_end: str = (
            f" | Power-ups: {', '.join(card.effect.name for card in self.power_ups)}"
            if self.power_ups
            else ""
        )
        return start + middle + power_up_end

    def bet(self, amount: int) -> None:
        """Place a bet by reducing the player's chips."""
        if type(amount) is not int or not 0 <= amount <= self.chips:
            raise ValueError(f"Bet must be a whole number from 0 to {self.chips}.")
        self.chips -= amount


HAND_NAMES = (
    "high card", "pair", "two pair", "three of a kind", "straight",
    "flush", "full house", "four of a kind", "straight flush",
)


def evaluate_hand(cards: list[PlayingCard]) -> tuple[int, ...]:
    """Comparable best-five score, including kickers and ace-low straights.

    Duplicate cards created by rank power-ups count as separate cards.
    """
    if not 5 <= len(cards) <= 7:
        raise ValueError("Evaluate five to seven cards.")

    def score(hand: tuple[PlayingCard, ...]) -> tuple[int, ...]:
        ranks = sorted((int(card.rank) for card in hand), reverse=True)
        groups = sorted(((count, rank) for rank, count in Counter(ranks).items()),
                        reverse=True)
        counts = [count for count, _ in groups]
        values = tuple(rank for _, rank in groups)
        flush = len({card.suit for card in hand}) == 1
        straight = 0
        if len(set(ranks)) == 5:
            if ranks[0] - ranks[-1] == 4:
                straight = ranks[0]
            elif ranks == [14, 5, 4, 3, 2]:
                straight = 5
        if counts == [5]:
            return (7, values[0], values[0])
        if flush and straight:
            return (8, straight)
        if counts == [4, 1]:
            return (7, *values)
        if counts == [3, 2]:
            return (6, *values)
        if flush:
            return (5, *ranks)
        if straight:
            return (4, straight)
        category = {(3, 1, 1): 3, (2, 2, 1): 2, (2, 1, 1, 1): 1}
        return (category.get(tuple(counts), 0), *values)

    return max(score(hand) for hand in combinations(cards, 5))


class GameEngine:
    """The engine that runs the PowerUp Poker game."""

    def __init__(self, seed: int | None = None) -> None:
        self.state: GameState = GameState()
        self.rng = random.Random(seed)

    def add_player(self, player: Player) -> None:
        """Add a player to the game."""
        self.state.add_player(player)

    def start_hand(self) -> None:
        """Post antes and deal from fresh decks; rotate the dealer each hand."""
        s = self.state
        if len(s.players) != 2:
            raise ValueError("Exactly two players are required.")
        if s.phase not in ("ready", "finished"):
            raise ValueError("Finish the current hand first.")
        if any(player.chips < 1 for player in s.players):
            raise ValueError("The match is over: a player has no chips.")
        s.hand_number += 1
        s.dealer = (s.hand_number - 1) % 2
        s.playing_deck = Deck(DeckType.PLAYING)
        s.power_up_deck = Deck(DeckType.POWER_UP)
        s.playing_deck.shuffle(self.rng)
        s.power_up_deck.shuffle(self.rng)
        s.community_cards = []
        s.discards = []
        s.winners = []
        s.showdown = False
        s.payout = 0
        s.pot = 2
        for player in s.players:
            player.bet(1)
            player.draw_hand(s)
            player.played_power_up = None
        self._start_round("pre-flop", s.dealer)

    @property
    def game_over(self) -> bool:
        return (self.state.phase == "finished"
                and any(player.chips == 0 for player in self.state.players))

    def legal_actions(self) -> tuple[str, ...]:
        s = self.state
        if s.turn is None:
            return ()
        i = s.turn
        if s.round_bets[i] < s.round_bets[1 - i]:
            return ("call", "fold")
        if all(player.chips > 0 for player in s.players):
            return ("check", "bet", "fold")
        return ("check", "fold")

    def act(self, player: int, action: str, *, use_power_up: bool = False,
            target: int | None = None) -> None:
        """Check, bet one, call one, or fold. Target is a zero-based hole index.

        Validate before changing cards or chips, so a rejected move can be retried.
        """
        s = self.state
        if type(player) is not int or s.turn is None or player != s.turn:
            raise ValueError("It is not that player's turn.")
        if action not in self.legal_actions():
            raise ValueError(f"Choose from: {', '.join(self.legal_actions())}.")
        if target is not None and not use_power_up:
            raise ValueError("A target requires a power-up.")
        if use_power_up:
            if s.phase != "pre-flop" or action not in ("bet", "call"):
                raise ValueError("Use a power-up with a pre-flop bet or call.")
            self._play_power_up(s.players[player], target)
        if action == "fold":
            self._finish([1 - player])
            return
        if action in ("bet", "call"):
            s.players[player].bet(1)
            s.pot += 1
            s.round_bets[player] += 1
        if action == "bet":
            s.pending = {1 - player}
        else:
            s.pending.discard(player)
        if s.pending:
            s.turn = 1 - player
        else:
            self._end_round()

    def _play_power_up(self, player: Player, target: int | None) -> None:
        if not player.power_ups:
            raise ValueError("Your power-up has already been used.")
        power = player.power_ups[0]
        effect = power.effect
        deck = cast(list[PlayingCard], self.state.playing_deck._cards)
        if effect == PowerUpType.RE_DEAL:
            if target is not None:
                raise ValueError("Re-deal does not take a target.")
            if len(deck) < 2:
                raise ValueError("Not enough cards to re-deal.")
            self.state.discards.extend(player.hand)
            player.hand = [cast(PlayingCard, deck.pop()) for _ in range(2)]
        else:
            if type(target) is not int or target not in (0, 1):
                raise ValueError("Choose hole card 1 or 2.")
            chosen = player.hand[target]
            if effect in (PowerUpType.INCREASE_CARD_VALUE,
                          PowerUpType.DECREASE_CARD_VALUE):
                delta = 1 if effect == PowerUpType.INCREASE_CARD_VALUE else -1
                rank = int(chosen.rank) + delta
                if not 2 <= rank <= 14:
                    raise ValueError("Ranks cannot go above Ace or below 2.")
                player.hand[target] = PlayingCard(Rank(rank), chosen.suit)
            else:
                rank = Rank.ACE if effect == PowerUpType.AUTO_ACE else chosen.rank
                candidates = [i for i, card in enumerate(deck)
                              if card.rank == rank and
                              (effect == PowerUpType.AUTO_ACE or card.suit != chosen.suit)]
                if not candidates:
                    raise ValueError("No eligible card remains in the deck.")
                index = self.rng.choice(candidates)
                slot = target if effect == PowerUpType.AUTO_ACE else 1 - target
                player.hand[slot], deck[index] = deck[index], player.hand[slot]
        player.played_power_up = player.power_ups.pop()

    def _start_round(self, phase: str, first: int) -> None:
        s = self.state
        s.phase = phase
        s.round_bets = [0, 0]
        s.pending = {0, 1}
        s.turn = first
        if any(player.chips == 0 for player in s.players):
            self._end_round()

    def _deal_community(self, count: int) -> None:
        s = self.state
        s.discards.append(cast(PlayingCard, s.playing_deck.draw()))  # Burn.
        s.community_cards.extend(cast(PlayingCard, s.playing_deck.draw())
                                 for _ in range(count))

    def _end_round(self) -> None:
        s = self.state
        if s.phase == "pre-flop":
            self._deal_community(3)
            self._start_round("post-flop", 1 - s.dealer)
        else:
            self._deal_community(1)
            self._deal_community(1)
            scores = [evaluate_hand(p.hand + s.community_cards) for p in s.players]
            s.showdown = True
            self._finish([i for i, score in enumerate(scores) if score == max(scores)])

    def _finish(self, winners: list[int]) -> None:
        s = self.state
        s.winners = winners
        s.payout = s.pot
        for i in winners:
            s.players[i].chips += s.pot // len(winners)  # Tied pots are always even.
        s.pot = 0
        s.turn = None
        s.pending.clear()
        s.phase = "finished"

    def view(self, viewer: int) -> dict:
        """Reveal power usage at the flop; power types stay private to their owner."""
        if type(viewer) is not int or viewer not in (0, 1):
            raise ValueError("Viewer must be player 0 or 1.")
        s = self.state
        return {
            "hand_number": s.hand_number, "phase": s.phase, "turn": s.turn,
            "pot": s.pot, "board": tuple(s.community_cards),
            "players": tuple({
                "name": p.name, "chips": p.chips,
                "hand": tuple(p.hand) if i == viewer or s.showdown else (),
                "power_ups": tuple(p.power_ups) if i == viewer else (),
                "played_power_up": p.played_power_up if i == viewer else None,
                "power_up_used": (p.played_power_up is not None
                                  if i == viewer or len(s.community_cards) >= 3 else None),
            } for i, p in enumerate(s.players)),
        }
