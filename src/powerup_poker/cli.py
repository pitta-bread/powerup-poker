"""Play against a simple random opponent: python -m powerup_poker.cli."""

import argparse
import random

from .engine import HAND_NAMES, GameEngine, Player, PowerUpType, evaluate_hand

HELP = """Actions: check, bet, call, fold, help, quit.
To use your power-up: bet power 1 (or call power 2).
The number selects a hole card; pocket pair keeps that card.
For re-deal: bet power (or call power). Bets and calls cost one chip.
Power-ups require a pre-flop bet/call. Ace cannot increase; 2 cannot decrease.
Power-up use is revealed at the start of post-flop betting; the type stays private.
"""


def show(game: GameEngine) -> None:
    view = game.view(0)
    print(f"\nHand {view['hand_number']} | {view['phase']} | Pot: {view['pot']}")
    print("Board:", ", ".join(card.name for card in view["board"]) or "—")
    for player in view["players"]:
        print(f"{player['name']}: {player['chips']} chips")
        if player["hand"]:
            print(
                "  "
                + " | ".join(
                    f"{i + 1}: {card.name}" for i, card in enumerate(player["hand"])
                )
            )
        if player["played_power_up"]:
            print("  Played:", player["played_power_up"].name)
        elif player["power_up_used"] is not None:
            print("  Power-up played:", "yes" if player["power_up_used"] else "no")
        for power in player["power_ups"]:
            print("  Power-up:", power.effect.value)


def bot_turn(game: GameEngine, rng: random.Random) -> None:
    actions = game.legal_actions()
    if "call" in actions:
        action = "call" if rng.random() < 0.85 else "fold"
    else:
        action = "bet" if "bet" in actions and rng.random() < 0.7 else "check"
    player = game.view(1)["players"][1]
    use = (
        game.state.phase == "pre-flop"
        and action in ("bet", "call")
        and bool(player["power_ups"])
        and rng.random() < 0.75
    )
    target = None
    if use and player["power_ups"][0].effect != PowerUpType.RE_DEAL:
        target = rng.randrange(2)
    try:
        game.act(1, action, use_power_up=use, target=target)
    except ValueError:
        game.act(1, action)  # An unavailable power-up does not cancel the bet.
    print(f"\nBot: {action}")


def human_turn(game: GameEngine) -> bool:
    while True:
        parts = input(f"{', '.join(game.legal_actions())}> ").lower().split()
        if parts == ["quit"]:
            return False
        if parts == ["help"]:
            print(HELP)
            continue
        try:
            if not parts or len(parts) > 3 or (len(parts) > 1 and parts[1] != "power"):
                raise ValueError("Try 'bet', 'bet power 1', or 'help'.")
            target = int(parts[2]) - 1 if len(parts) == 3 else None
            game.act(0, parts[0], use_power_up=len(parts) > 1, target=target)
            return True
        except ValueError as error:
            print(error)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Two-player Power-Up Poker versus a bot."
    )
    parser.add_argument("--seed", type=int, help="Reproduce deals and bot choices.")
    parser.add_argument("--name", default="You", help="Your name at the table.")
    args = parser.parse_args()
    game = GameEngine(seed=args.seed)
    game.add_player(Player(args.name))
    game.add_player(Player("Bot"))
    rng = random.Random(args.seed)
    print("Power-Up Poker — 20 chips each, 1-chip antes, two betting rounds.")
    print(HELP)
    try:
        while not game.game_over:
            game.start_hand()
            while game.state.phase != "finished":
                show(game)
                if game.state.turn == 0:
                    if not human_turn(game):
                        print("Goodbye!")
                        return
                else:
                    bot_turn(game, rng)
            show(game)
            s = game.state
            if s.showdown:
                for player in s.players:
                    score = evaluate_hand(player.hand + s.community_cards)
                    print(f"{player.name}: {HAND_NAMES[score[0]]}")
            winners = " and ".join(s.players[i].name for i in s.winners)
            verb = "split" if len(s.winners) == 2 else "wins"
            print(f"{winners} {verb} the {s.payout}-chip pot.")
        winner = next(player for player in game.state.players if player.chips)
        print(f"{winner.name} wins the match with {winner.chips} chips!")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
