# ChessBot Specification

## Overview
A UCI-compatible chess engine built in Python. The engine will focus on a custom search and evaluation algorithm while leveraging the `python-chess` library for move generation and board mechanics.

## Technical Stack
- **Language:** Python 3.12+
- **Library:** `python-chess` (for move generation, FEN/PGN parsing, and board state)
- **Protocol:** UCI (Universal Chess Interface)
- **Testing:** `pytest`

## Core Requirements

### 1. UCI Protocol Compliance
The bot must implement the standard UCI loop to allow it to communicate with chess GUIs (like Arena, Cute Chess, or Lichess bridges). It should support at least:
- `uci`: Identify the engine.
- `isready`: Sync with the GUI.
- `ucinewgame`: Reset state for a new match.
- `position [fen | startpos] moves ...`: Update the internal board state.
- `go [wtime | btime | movestogo]`: Start searching for the best move.
- `quit`: Gracefully exit.

### 2. Engine Logic (Custom Implementation)
- **Search:** Implement a Minimax search with Alpha-Beta pruning.
- **Evaluation:** A heuristic function to score board positions based on:
  - Material balance (Pawn=1, Knight=3, etc.).
  - Piece-Square Tables (encouraging center control, king safety, and active pieces).
- **Time Management:** Basic logic to ensure the bot returns a move within the time limits provided in the `go` command.

### 3. Interface
- **Primary:** Standard input/output (UCI) for use with external tools.
- **Secondary:** A simple CLI wrapper that allows a user to manually input moves and pick a color for testing.

### 4. Draw Avoidance
The engine must avoid drawing games it is winning. Specifically:
- **Threefold repetition**: When the engine has a significant material advantage, it must not repeat positions. The search should detect when a candidate move would cause a threefold repetition and penalise that move.
- **Progress in winning positions**: In endgames with a large material advantage (e.g. Q+R vs lone K), the engine should actively drive toward checkmate rather than shuffling pieces aimlessly.

### 5. Game History Learning (Opening Book from Own Games)
Pull the bot's own game history from Lichess and use it to build a personal opening book. The bot learns from its wins and avoids repeating its losses.

- **Data source:** `GET /api/games/user/OlisRalphBot` to fetch the bot's past games as PGN (uses the existing Lichess token already configured for the bot).
- **Storage:** A local JSON file (`data/openings.json`) mapping FEN positions (first N moves) to move statistics: `{fen: {move_uci: {wins, losses, draws, count}}}`.
- **Book building:** A CLI command (`python main.py --build-book`) that fetches games, parses the first 10-15 moves of each, and aggregates win/loss/draw stats per position+move. Only include moves from games the bot won or drew (skip losing lines).
- **Book lookup at runtime:** Before starting alpha-beta search, check if the current position exists in the book. If it does, play the move with the best win rate (with a minimum sample size threshold, e.g. >= 3 games). Add a small random factor so the bot doesn't always play the same line.
- **Staleness:** Re-build the book periodically (e.g. every 50 games or on manual trigger).

### 6. Improved Evaluation Heuristics
Upgrade the static evaluation function with knowledge-based heuristics. These are patterns strong human players use:

#### 6a. Tapered Evaluation / Game Phase Detection (HIGH PRIORITY)
Use total non-pawn material to compute a game phase (0=endgame, 24=opening). Maintain two PSTs per piece type — one for middlegame, one for endgame. Blend them: `score = (mg * phase + eg * (24 - phase)) / 24`. The endgame king PST should reward central squares (d4/e4/d5/e5) instead of castled corners. This directly fixes the known repetition-draw bug by making the king move toward the opponent in won endgames.

#### 6b. Pawn Structure
- **Doubled pawns:** Two pawns of the same color on the same file. Penalty ~20-30cp each.
- **Isolated pawns:** A pawn with no friendly pawns on adjacent files. Penalty ~15-25cp.
- **Backward pawns:** A pawn that cannot advance because the enemy controls its stop square and has no friendly pawn support. Penalty ~10-15cp.
- **Pawn islands:** Count groups of connected pawns. Fewer islands = better. Penalty ~5cp per extra island.

#### 6c. Passed Pawns (HIGH PRIORITY)
A passed pawn has no enemy pawns blocking or flanking it on the way to promotion. Bonus scales with rank: rank 2=10cp, rank 3=20cp, rank 4=40cp, rank 5=70cp, rank 6=120cp, rank 7=200cp. Extra bonus if protected by another pawn. Extra bonus if the enemy king is far from the pawn.

#### 6d. Bishop Pair
Bonus of ~40cp for having both bishops, since they complement each other covering all square colors. Optionally scale up in open positions (fewer pawns on the board).

#### 6e. Rook Placement
- **Open file:** Rook on a file with no pawns of either color. Bonus ~20cp.
- **Semi-open file:** Rook on a file with no friendly pawns but enemy pawns present. Bonus ~10cp.
- **Rook on 7th rank:** Rook on the opponent's second rank, pressuring pawns and restricting the king. Bonus ~20cp.
- **Connected rooks:** Both rooks defend each other on the same rank with no pieces between them.

#### 6f. King Safety (Pawn Shield)
If the king is castled (g1/h1 or b1/c1 for White), check for pawns on the shielding squares (f2/g2/h2 for kingside). Penalty ~20cp per missing pawn, ~10cp per advanced pawn. Scale this term to zero in the endgame via the tapered eval phase.

#### 6g. Mobility
Per-piece bonus for the number of attacked squares (via `board.attacks(sq)`). Coefficients: knight ~4cp/square, bishop ~3cp, rook ~2cp, queen ~1cp. This is the most expensive eval term — consider computing only for major pieces.

#### 6h. Mop-Up Evaluation (FIXES REPETITION-DRAW BUG)
When the engine has a large material advantage (>200cp) and the losing side has no queens/rooks, add terms that drive progress toward checkmate:
- Bonus for the losing king being close to a corner: `(3.5 - distance_to_closest_corner) * 20`.
- Bonus for the winning king being close to the losing king: `(14 - manhattan_distance) * 10`.
This gives the engine a reason to make progress when all moves look equally "winning" in material terms.

#### 6i. Endgame-Specific Piece Values
In the endgame, pawns increase in value (~+20cp, closer to promotion), knights decrease relative to bishops in open positions, and rooks increase slightly. The tapered eval PSTs handle this naturally if tuned separately for middlegame and endgame.

#### 6j. Drawn Endgame Detection
Beyond `board.is_insufficient_material()`, recognise specific draws:
- **KBP vs K with wrong-color bishop:** If the only pawn is a rook pawn (a/h file) and the bishop doesn't control the promotion square, return 0.
- **Opposite-color bishops:** KBP vs KB with opposite-color bishops is very drawish. Scale evaluation down by ~50%.

#### 6k. Draw Contempt
Instead of scoring repetitions as exactly 0, use a contempt-adjusted score: if the engine is materially ahead, score a repetition as -50cp (discourage the draw). If losing, score it as +50cp (encourage the draw). This single change would have prevented the Q+R vs K repetition draw.

### 7. Search Improvements
Make the search deeper and smarter — all pure algorithmic improvements:

#### 7a. Quiescence Search (HIGH PRIORITY)
At depth 0, don't just return the static eval — continue searching capture sequences until the position is "quiet." Use `board.generate_legal_captures()` to only generate captures. Start with a "stand-pat" score (the static eval): if it >= beta, return beta; if > alpha, raise alpha. Cap quiescence depth at ~8 plies to prevent explosion. Optionally also search moves that give check.

#### 7b. Transposition Table (HIGH PRIORITY)
Cache `(zobrist_hash, depth, score, flag, best_move)` entries to skip re-evaluating positions reached via different move orders. Use `board.zobrist_hash()` from python-chess. Flag is EXACT, LOWERBOUND, or UPPERBOUND. Size: fixed dict of ~2^20 entries with depth-preferred replacement. The TT best move from the previous iterative deepening iteration becomes the top move-ordering hint for the next — this alone dramatically improves cutoff rates. **Mate score adjustment:** When storing checkmate scores, adjust relative to root ply (store `score - ply` for positive mates, `score + ply` for negative) and reverse when retrieving.

#### 7c. MVV-LVA Capture Ordering (HIGH PRIORITY)
Replace the current "captures before quiets" ordering with Most Valuable Victim / Least Valuable Attacker scoring: `score = MATERIAL[captured] * 10 - MATERIAL[attacker]`. Example: PxQ = 8900, QxP = 100. Very cheap to implement, immediately improves cutoff rates.

#### 7d. Killer Move Heuristic
Maintain `killers[ply] = [move1, move2]` (two slots per ply). When a quiet move causes a beta cutoff, store it as a killer. In move ordering, try killers after captures but before other quiets.

#### 7e. History Heuristic
Maintain `history[color][from_sq][to_sq]` counters. When a quiet move causes a beta cutoff, increment by `depth * depth`. Sort remaining quiet moves by descending history score. Moves that have been good elsewhere in the tree tend to be good here too.

#### 7f. Null Move Pruning
Before searching moves, if not in check and the side to move has pieces beyond king+pawns, make a null move (`board.push(chess.Move.null())`) and search at reduced depth (depth - 1 - R, R=2 or 3). If it fails high (score >= beta), prune. Never allow two consecutive null moves.

#### 7g. Principal Variation Search (PVS)
Search the first move (expected best from TT/ordering) with the full (alpha, beta) window. Search all subsequent moves with a null window (alpha, alpha+1). If a move fails high, re-search with the full window. With good move ordering the first move is usually best, so null-window searches are very cheap.

#### 7h. Late Move Reductions (LMR)
Moves searched late in the move list (after the first 3-4) that are not captures, checks, or killers are statistically unlikely to be good. Search them at reduced depth: `R = 1` for moves 4-6, `R = 2` for moves 7+. If the reduced search returns score > alpha, re-search at full depth.

#### 7i. Aspiration Windows
Instead of searching with (-INF, +INF) at each iterative deepening iteration, use a narrow window around the previous score: (S-50, S+50). If the search fails low or high, widen and re-search. The narrow window causes many more cutoffs.

#### 7j. Futility Pruning
At low remaining depths (1-2 plies), if `static_eval + margin < alpha` (margin ~200cp), skip quiet moves and only search captures/checks. The position is too far below alpha for quiet moves to matter.

#### 7k. Check Extensions
When a move gives check, extend the search by 1 ply (search with `depth` instead of `depth - 1`). Checks are forcing and adding them costs few extra nodes but captures critical tactics.

### 8. Move Generation Optimisation
- **Lazy move generation:** Don't generate all legal moves upfront. Try the TT move first, then captures (MVV-LVA), then killers, then remaining quiets (history-sorted). Only generate each category when the previous one didn't cause a cutoff. This saves significant time when cutoffs happen early.
- **Avoid `board.is_game_over()` per node:** It is expensive in python-chess (checks multiple conditions). Instead: if no legal moves exist and `board.is_check()`, it's checkmate; if no legal moves and not in check, it's stalemate. Check 50-move rule via `board.halfmove_clock >= 100`. Check repetition via the Zobrist hash / TT.

### 9. Correctness and Testing
- **Perft testing:** Implement a `perft(board, depth)` function that counts leaf nodes and compare against published perft results for the starting position and tricky positions (castling, en passant, promotion). A single move-generation bug silently corrupts everything.
- **Incremental testing:** Add one feature at a time. Run the engine against the previous version (100+ self-play games at fast time control) to confirm each change is an actual improvement. A feature that looks correct can still lose Elo if weights are wrong or it interacts badly with search.
- **Rule of the square test:** In K+P vs K endgames, verify the engine correctly identifies unstoppable passed pawns (enemy king outside the "square" of the pawn).

## Ralph-Loop Readiness
- **Modularity:** Separate the UCI handling from the search/evaluation logic to allow for easy unit testing.
- **Validation:** Every core component (eval function, search depth, move application) should have associated tests to ensure the Ralph Loop can verify progress at each step.
