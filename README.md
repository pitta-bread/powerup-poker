# Power-Up Poker

## Play

Run `uv run powerup-poker` (optionally `--seed 42 --name Pete`). You play
against a simple random bot until one player owns all 40 chips. Enter `help`
for commands, or `quit` to leave. No runtime dependencies are required.

Run tests and lint with `make` (or `make check`). Run either separately with
`make test` or `make lint`. These commands use `uv` to manage dependencies.

The engine implements [the rules](docs/rules.md) with these clarifications:

- Check, bet one chip, call one chip, or fold; there are no raises or blinds.
  The dealer acts first pre-flop, the other player first post-flop, and the
  dealer alternates each hand. A checked player may respond to a later bet.
- After post-flop betting, burn/deal the turn and river without more betting.
  The best five of seven cards wins; an Ace may also be low in a wheel straight.
  Equal hands split the pot. A fold immediately awards the pot to the opponent.
- A power-up is optional and usable once with a pre-flop bet or call. Only
  whether each player used a power-up is revealed, together at the start of
  post-flop betting. The type stays private, even at showdown. A pre-flop fold
  also leaves usage private.
  Opposing hole cards are shown at showdown; unused powers remain private.
- +1/−1 creates a replacement hole card of the same suit, even if an identical
  card exists elsewhere. The deck is unchanged. Ace cannot increase and 2 cannot
  decrease. Five matching ranks score as four of a kind with the fifth as kicker.
- Auto-ace and pocket pair exchange the replaced hole card with a uniformly
  chosen eligible deck card at that card's deck position. Pocket pair must use
  a different suit from the kept card. Re-deal discards both old cards and draws
  the top two. An unavailable effect rejects the action without spending chips
  or consuming the power-up; choose another target or bet without it.
- Each hand starts with fresh shuffled playing and power-up decks. If either
  player runs out of chips after the ante or a matched bet, remaining betting
  rounds are skipped and the board runs out. There are no unmatched bets or
  side pots. Chips remain in play until one player has all 40.

## Game concept

Simplified Power-up Texas Hold'Em Poker. 2 players max. All cards. Only 2 rounds of betting, pre-flop, and immediately after the flop. 1 chip max per round (non-continuous betting). Balatro-style power-ups, 5 of them, 1 randomly dealt to each player along with their 2 hole cards, if used must be used pre-flop and at same time as confirming the bet. Only power-up usage is revealed when post-flop betting begins; the effect stays private.

## Power-ups

1. Increase the value of a card by +1. King goes to Ace.
2. Decrease the value of a card by -1. Ace goes to King.
3. Auto-ace. Swap one hole card of your choice with a random Ace remaining in the deck.
4. Pocket pair. Choose a hole card. Swap the other card with a card from the deck with the same value as the chosen card (but by necessity, different suit, randomly found).
5. Re-deal. Discard your current hole cards and draw 2 new ones from the top of the deck.

## Step by step
- [x] Define the rules. Decide antes, turn order, ties, and when hands end.
- [x] Define the power-ups. 5 of them. Specify timing, visibility, legal targets, and edge cases such as aces and duplicate cards.
- [ ] Build the game engine. SQLModel + FastAPI. Implement dealing, betting, power-ups, hand evaluation, and chip accounting. Keep it separate from the UI so simulations run quickly.
- [ ] Write coding agent rules. Minimal code. Keep me in the loop.
- [ ] Build a playable version. Have coding agents create the UI. Gradio. Add a simple scripted opponent and check that the game is enjoyable and the rules work.
- [ ] Generate supervised data. Sample situations after the power-up phase. Simulate many legal opponent hands and remaining cards to estimate showdown equity. Document assumptions about hidden information.
- [ ] Train an equity predictor. Compare simple models on held-out situations. Use only information the player can observe.
- [ ] Build an equity-based bot. Combine predicted equity with explicit betting rules. Add opponents with different styles. Like bets 80% of the time randomly.
- [ ] Train an RL agent. Let it play fresh games against those bots, learning from net chips won or lost.
- [ ] Introduce self-play. Add saved versions of the learner to its training opponents as it improves.
- [ ] Evaluate and iterate. Measure average net chips per hand against a separate, fixed opponent pool, with uncertainty estimates. Play it yourself and expand the rules gradually.
