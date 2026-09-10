# Power-Up Poker

## Game concept

Simplified Power-up Texas Hold'Em Poker. 2 players max. All cards. Only 2 rounds of betting, pre-flop, and immediately after the flop. 1 chip max per round (non-continuous betting). Balatro-style power-ups, 5 of them, 1 randomly dealt to each player along with their 2 hole cards, if used must be used pre-flop and at same time as confirming the bet. Revealed if played.

## Power-ups

1. Increase the value of a card by +1. King goes to Ace.
2. Decrease the value of a card by -1. Ace goes to King.
3. Auto-ace. Swap one hole card of your choice with a random Ace remaining in the deck.
4. Pocket pair. Choose a hole card. Swap the other card with a card from the deck with the same value as the chosen card (but by necessity, different suit, randomly found).
5. Re-deal. Discard your current hole cards and draw 2 new ones from the top of the deck.

## Step by step
- [ ] Define the rules. Decide antes, turn order, ties, and when hands end.
- [ ] Define the power-ups. 5 of them. Specify timing, visibility, legal targets, and edge cases such as aces and duplicate cards.
- [ ] Build the game engine. Django + FastAPI (or just Django if antipattern). Implement dealing, betting, power-ups, hand evaluation, and chip accounting. Keep it separate from the UI so simulations run quickly.
- [ ] Write coding agent rules. Minimal code. Keep me in the loop.
- [ ] Build a playable version. Have coding agents create the UI. Gradio. Add a simple scripted opponent and check that the game is enjoyable and the rules work.
- [ ] Generate supervised data. Sample situations after the power-up phase. Simulate many legal opponent hands and remaining cards to estimate showdown equity. Document assumptions about hidden information.
- [ ] Train an equity predictor. Compare simple models on held-out situations. Use only information the player can observe.
- [ ] Build an equity-based bot. Combine predicted equity with explicit betting rules. Add opponents with different styles. Like bets 80% of the time randomly.
- [ ] Train an RL agent. Let it play fresh games against those bots, learning from net chips won or lost.
- [ ] Introduce self-play. Add saved versions of the learner to its training opponents as it improves.
- [ ] Evaluate and iterate. Measure average net chips per hand against a separate, fixed opponent pool, with uncertainty estimates. Play it yourself and expand the rules gradually.
