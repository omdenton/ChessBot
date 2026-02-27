Status: IN_PROGRESS

# Implementation Plan — ChessBot

## Overview

Build a UCI-compatible Python chess engine using `python-chess` for move generation and a custom minimax/alpha-beta search with heuristic evaluation.

## Proposed Module Structure

```
chessbot/
  __init__.py
  evaluation.py   # Material balance + Piece-Square Tables
  engine.py       # Minimax search with Alpha-Beta pruning + time management
  uci.py          # UCI protocol stdin/stdout loop
  cli.py          # Interactive CLI wrapper for manual testing
tests/
  test_evaluation.py
  test_engine.py
  test_uci.py
main.py           # Entry point (runs UCI loop by default)
requirements.txt  # python-chess, pytest
```

---

## Tasks

### Task 1 — Project Setup ✅ DONE
**Description:** Create the package skeleton, entry point, and dependency manifest.

**Acceptance Criteria:**
- `chessbot/` package directory with `__init__.py` exists.
- `requirements.txt` lists `python-chess` and `pytest`.
- `main.py` exists as an entry point (initially just a placeholder that imports the uci module).
- `tests/` directory exists with empty `__init__.py`.

**Dependencies:** None
**Complexity:** S

---

### Task 2 — Evaluation Function ✅ DONE
**Description:** Implement a board evaluation heuristic in `chessbot/evaluation.py`.

**Acceptance Criteria:**
- `evaluate(board) -> int` returns a centipawn score (positive = White advantage, negative = Black advantage).
- Material balance is computed using standard values: Pawn=100, Knight=320, Bishop=330, Rook=500, Queen=900, King=20000.
- Piece-Square Tables (PST) are applied per piece type and side: encourage center control for pawns/knights/bishops, open files/7th rank for rooks, castled safety for kings.
- Returns 0 for draw (insufficient material, stalemate handled by the caller).
- At least 5 tests in `tests/test_evaluation.py` covering: starting position ≈ 0, material imbalance, mirror symmetry (same score if colors are flipped and eval is negated).

**Verified implementation notes:**
- 7 tests implemented (exceeds requirement of 5).
- Black PST mirroring uses `sq ^ 56` (vertical mirror), verified correct.

**Dependencies:** Task 1
**Complexity:** S

---

### Task 3 — Minimax Search with Alpha-Beta Pruning ✅ DONE
**Description:** Implement the search algorithm in `chessbot/engine.py`.

**Acceptance Criteria:**
- `search(board, depth, alpha, beta, maximizing) -> (score, move)` performs negamax (or minimax) with alpha-beta pruning.
- `get_best_move(board, depth) -> move` is the public entry point that returns a `chess.Move`.
- Handles terminal states: checkmate returns ±large value, stalemate returns 0.
- Depth is configurable (default = 3).
- Move ordering: captures are tried before quiet moves (improves pruning efficiency).
- Tests in `tests/test_engine.py`:
  - Finds checkmate-in-1 given a known position.
  - Returns a legal move from the starting position.
  - Does not return `None` when legal moves exist.

**Verified implementation notes:**
- 5 tests implemented (exceeds requirement of 3): legal move from start, no-None guarantee,
  checkmate-in-1 (Rh8#), stalemate returns 0, mated position returns -CHECKMATE_SCORE.
- Pure negamax formulation; `search(board, depth, alpha, beta)` — no `maximizing` param needed.
- `CHECKMATE_SCORE = 1_000_000`; checkmate at root returns `-CHECKMATE_SCORE`.
- Move ordering: captures before quiet moves via `_order_moves()`.
- All 12 tests (7 evaluation + 5 engine) pass.

**Dependencies:** Task 2
**Complexity:** M

---

### Task 4 — Time Management ✅ DONE
**Description:** Add basic time-budgeting logic to `chessbot/engine.py` so the engine respects `go` time limits.

**Acceptance Criteria:**
- `get_best_move_timed(board, wtime_ms, btime_ms, movestogo=None) -> move` computes a time budget and iterates deepening until the budget is exhausted.
- Budget heuristic: allocate `time / (movestogo or 30)` milliseconds per move, with a safety margin (e.g. 95% of budget).
- Uses `time.monotonic()` for timing; search is interrupted between depths (not mid-search).
- Returns the best move found at the deepest completed depth even if time runs out.
- Minimum depth of 1 is always completed.

**Verified implementation notes:**
- `_BUDGET_SAFETY = 0.95`; budget = `player_time_ms / 1000 / divisor * 0.95` seconds.
- Iterative deepening starts at depth 1 (always completed) then increments while `time.monotonic() < deadline`.
- White/Black time selected based on `board.turn`.
- All 13 existing tests continue to pass.

**Dependencies:** Task 3
**Complexity:** S

---

### Task 5 — UCI Protocol Handler
**Description:** Implement the UCI stdin/stdout loop in `chessbot/uci.py`.

**Acceptance Criteria:**
- `run_uci_loop()` reads lines from stdin and dispatches commands.
- Supported commands: `uci`, `isready`, `ucinewgame`, `position`, `go`, `quit`.
- `uci` → responds with `id name ChessBot`, `id author <name>`, `uciok`.
- `isready` → responds `readyok`.
- `ucinewgame` → resets internal board to starting position.
- `position startpos moves e2e4 ...` → applies moves from starting position.
- `position fen <FEN> moves ...` → sets board from FEN then applies moves.
- `go wtime <ms> btime <ms> [movestogo <n>]` → calls timed search, outputs `bestmove <uci_move>`.
- `go depth <n>` → calls depth-limited search, outputs `bestmove <uci_move>`.
- `quit` → exits cleanly.
- All output goes to stdout; flush after each line.
- Tests in `tests/test_uci.py`:
  - Parsing of `position` command (startpos, FEN, with and without moves).
  - `go depth 1` returns a valid UCI move string from a known position.

**Dependencies:** Task 4
**Complexity:** M

---

### Task 6 — CLI Wrapper
**Description:** Implement an interactive command-line game in `chessbot/cli.py`.

**Acceptance Criteria:**
- `run_cli()` prompts the user to pick a color (White/Black).
- After each human move, displays the board using `python-chess` ASCII representation.
- Validates human moves; re-prompts on illegal input.
- Engine responds with its chosen move (using `get_best_move` or `get_best_move_timed`).
- Game ends with a message when checkmate, stalemate, or draw is detected.
- Accepts moves in UCI notation (e.g. `e2e4`) or algebraic notation via `chess.Board.parse_san`.
- `main.py` supports a `--cli` flag to launch the CLI wrapper instead of the UCI loop.

**Note:** `main.py` already has the `--cli` flag dispatch wired up (imports `run_cli` from `chessbot.cli`).

**Dependencies:** Task 5 (for timed search) or Task 3 (minimum viable)
**Complexity:** S

---

### Task 7 — Comprehensive Test Suite
**Description:** Ensure all modules have adequate test coverage.

**Acceptance Criteria:**
- `pytest` runs without errors from the project root.
- `tests/test_evaluation.py`: ≥ 5 tests (see Task 2 criteria) — **already satisfied with 7 tests**.
- `tests/test_engine.py`: ≥ 3 tests (see Task 3 criteria), including at least one checkmate-in-1 — **already satisfied with 5 tests**.
- `tests/test_uci.py`: ≥ 3 tests (see Task 5 criteria).
- No tests import from `main.py` or depend on stdin/stdout of the UCI loop directly — they call module functions.

**Dependencies:** Tasks 2, 3, 5
**Complexity:** M

---

## Implementation Order

| # | Task | Complexity | Depends On | Status |
|---|------|------------|------------|--------|
| 1 | Project Setup | S | — | ✅ Done |
| 2 | Evaluation Function | S | 1 | ✅ Done |
| 3 | Minimax + Alpha-Beta | M | 2 | ✅ Done |
| 4 | Time Management | S | 3 | ✅ Done |
| 5 | UCI Protocol Handler | M | 4 | ⬜ TODO |
| 6 | CLI Wrapper | S | 3 | ⬜ TODO |
| 7 | Comprehensive Tests | M | 2, 3, 5 | ⬜ TODO (eval ✅ + engine ✅ tests done; test_uci.py missing) |
