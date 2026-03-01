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

## Ralph-Loop Readiness
- **Modularity:** Separate the UCI handling from the search/evaluation logic to allow for easy unit testing.
- **Validation:** Every core component (eval function, search depth, move application) should have associated tests to ensure the Ralph Loop can verify progress at each step.
