import random
from collections.abc import Iterator
from dataclasses import dataclass
from enum import IntEnum, StrEnum
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

        if deck_type is DeckType.PLAYING:
            self._cards: list[PlayingCard] = [
                PlayingCard(rank, suit) for suit in Suit for rank in Rank
            ]
        elif deck_type is DeckType.POWER_UP:
            self._cards: list[PowerUpCard] = [
                PowerUpCard(effect) for effect in (list(PowerUpType) * 3)
            ]

    def __len__(self) -> int:
        return len(self._cards)

    def __iter__(self) -> Iterator[Card]:
        return iter(self._cards)

    def shuffle(self) -> None:
        """Shuffle the remaining cards in place."""
        random.shuffle(x=self._cards)

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

    def add_player(self, player: "Player") -> None:
        """Add a player to the game."""
        self.players.append(player)


class Player:
    """A player in the game."""

    def __init__(self, name: str, chips: int = 20) -> None:
        self.name: str = name
        self.hand: list[PlayingCard] = []
        self.power_ups: list[PowerUpCard] = []
        self.chips: int = chips

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
        if amount > self.chips:
            raise ValueError(f"{self.name} does not have enough chips to bet {amount}.")
        self.chips -= amount


class GameEngine:
    """The engine that runs the PowerUp Poker game."""

    def __init__(self) -> None:
        self.state: GameState = GameState()

    def add_player(self, player: Player) -> None:
        """Add a player to the game."""
        self.state.add_player(player)

    def start_hand(self) -> None:
        """Start a new hand by drawing cards for each player."""
        self.state.hand_number += 1
        for player in self.state.players:
            player.draw_hand(game_state=self.state)
