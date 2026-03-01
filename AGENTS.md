# AGENTS.md — Operational Guide

## Project Context

ChessBot: a UCI-compatible Python chess engine using `python-chess` for move generation and a custom minimax/alpha-beta search with heuristic evaluation (material balance + Piece-Square Tables).

## Key Directories

- `ChessBot/specs/` — Specification files (note: inside ChessBot/, not project root)
- `ChessBot/IMPLEMENTATION_PLAN.md` — ChessBot's internal plan (completed Phase 1)
- `IMPLEMENTATION_PLAN.md` — Master plan at project root (tracks all phases)
- `ChessBot/chessbot/` — Main Python package
- `ChessBot/tests/` — pytest test suite (25 tests across 3 files)

## Tech Stack

- Python 3.12+
- `python-chess` — board state, move generation, FEN/PGN, legal move enumeration
- `pytest` — test runner
- `httpx` — async HTTP for Lichess integration
- Entry point: `ChessBot/main.py` (UCI by default; `--cli`, `--lichess` flags)

## Conventions

- Specs live in `ChessBot/specs/`
- Score from `evaluate()` is in centipawns; positive = White advantage
- Negamax convention: score is always from the perspective of the side to move
- UCI output must be flushed immediately (use `flush=True` in print calls)
- Moves in UCI notation: lowercase, e.g. `e2e4`, `e7e8q` for promotion

## Key Design Decisions

- `evaluation.py` is stateless — takes a `chess.Board`, returns int score
- `engine.py` contains both the search (negamax/alpha-beta) and time management
- `uci.py` owns the board state across commands; calls into `engine.py` for moves
- Separate modules allow unit testing without touching UCI I/O

## Current State (as of planning iteration)

- **Phase 1 COMPLETE:** Basic engine works — UCI, CLI, Lichess bot, evaluation with PSTs, negamax+alpha-beta, time management.
- **Phase 2 IN PROGRESS:** Task 8 (MVV-LVA) done, Task 9 (quiescence) done. Next: Task 10 (TT), Task 11 (check extensions).
- **Tests:** 27 passing (all green)
- **All spec requirements mapped** to tasks 1-31; no gaps identified.

## Gotchas

- `python-chess` is NOT pre-installed; run `pip install -r ChessBot/requirements.txt` before running tests
- Run tests from ChessBot directory: `cd /app/project/ChessBot && python -m pytest tests/`
- `search(board, depth, alpha, beta)` uses pure negamax (no `maximizing` param); score is always side-to-move relative
- `CHECKMATE_SCORE = 1_000_000`; initial alpha/beta window: `-(CHECKMATE_SCORE+1)` to `CHECKMATE_SCORE+1`
- For PST: White uses tables as-is; Black uses vertically-mirrored tables (index `sq ^ 56`, NOT `63 - sq`)
- `board.is_game_over()` is expensive in python-chess — spec recommends replacing with direct checks (no legal moves + is_check for mate/stalemate)
- Time management interrupts between depth iterations, not mid-search — always return last completed depth's best move
- Rook on 7th rank bonus already partially implemented in current PSTs
- `board.zobrist_hash()` available in python-chess for transposition table
- `board.generate_legal_captures()` available for quiescence search
- `chess.Move.null()` available for null move pruning
- `board.attacks(sq)` returns SquareSet of attacked squares (for mobility calculation)
