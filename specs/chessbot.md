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
Upgrade the static evaluation function with knowledge-based heuristics that don't require an engine. These are patterns strong human players use:

- **Mobility:** Bonus for the number of legal moves available. More mobile pieces = better position.
- **King safety:** Penalty for open files near the king, bonus for pawn shield in front of a castled king.
- **Pawn structure:** Penalty for doubled pawns (two pawns on the same file), isolated pawns (no friendly pawns on adjacent files), and backward pawns. Bonus for passed pawns (no enemy pawns can block/capture it on the way to promotion).
- **Bishop pair:** Bonus (~50cp) for having both bishops, since they complement each other on light and dark squares.
- **Rook on open/semi-open file:** Bonus when a rook sits on a file with no friendly pawns (semi-open) or no pawns at all (open).
- **Connected rooks:** Bonus when both rooks defend each other (no pieces between them on the same rank).
- **Game phase detection:** Use total material to determine opening/middlegame/endgame phase, and blend PSTs accordingly (e.g. king should centralize in endgames, not hide in the corner).

### 7. Search Improvements
Make the search deeper and smarter without adding an external engine:

- **Quiescence search:** At depth 0, don't just return the static eval — continue searching capture sequences until the position is "quiet." This prevents the horizon effect where the bot misses a hanging piece one move past its search depth.
- **Transposition table:** Cache `(position_hash, depth, score, flag)` entries to avoid re-evaluating the same position reached via different move orders. Use `board.zobrist_hash()` from python-chess.
- **Killer move heuristic:** Remember moves that caused beta cutoffs at each depth and try them early in sibling nodes. These are often good moves even in unrelated positions at the same depth.
- **Null move pruning:** If skipping a turn (giving the opponent a free move) still results in a beta cutoff, the position is so good we can prune safely. Reduces the search tree significantly.
- **Late move reductions (LMR):** Moves ordered late (not captures, not killer moves) are likely bad — search them at reduced depth first, and only re-search at full depth if they look promising.

## Ralph-Loop Readiness
- **Modularity:** Separate the UCI handling from the search/evaluation logic to allow for easy unit testing.
- **Validation:** Every core component (eval function, search depth, move application) should have associated tests to ensure the Ralph Loop can verify progress at each step.
