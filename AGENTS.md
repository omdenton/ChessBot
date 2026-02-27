# AGENTS.md — Operational Guide

## Project Context

ChessBot: a UCI-compatible Python chess engine using `python-chess` for move generation and a custom minimax/alpha-beta search with heuristic evaluation (material balance + Piece-Square Tables).

## Key Directories

- `specs/` — Specification files (note: `specs/`, not `spec/`)
- `IMPLEMENTATION_PLAN.md` — Auto-generated plan; updated each planning iteration
- `chessbot/` — Main package (to be created)
- `tests/` — pytest test suite (to be created)

## Conventions

- Specs live in `specs/` (the directory is `specs/`, not `spec/`)
- Planning mode reads specs, compares against existing code, and writes tasks to `IMPLEMENTATION_PLAN.md`
- Score from `evaluate()` is in centipawns; positive = White advantage
- Negamax convention: score is always from the perspective of the side to move
- UCI output must be flushed immediately (use `flush=True` in print calls)
- Moves in UCI notation: lowercase, e.g. `e2e4`, `e7e8q` for promotion

## Tech Stack

- Python 3.12+
- `python-chess` — board state, move generation, FEN/PGN, legal move enumeration
- `pytest` — test runner
- Entry point: `main.py` (UCI loop by default; `--cli` flag for interactive CLI)

## Key Design Decisions

- `evaluation.py` is stateless — takes a `chess.Board`, returns int score
- `engine.py` contains both the search (minimax/alpha-beta) and time management
- `uci.py` owns the board state across commands; calls into `engine.py` for moves
- Separate modules allow unit testing without touching UCI I/O

## Gotchas

- Both `AGENTS.md` and `IMPLEMENTATION_PLAN.md` were found empty on first iteration
- The spec directory is `specs/` but a previous AGENTS.md note said `spec/` — `specs/` is correct
- `python-chess` uses `chess.Move.from_uci()` and `board.push()` for move application
- For PST: White uses tables as-is; Black uses vertically-mirrored tables (index `sq ^ 56`, NOT `63 - sq` which would be 180° rotation)
- `board.is_game_over()` checks checkmate/stalemate/draws; check `board.outcome()` for details
- Time management interrupts between depth iterations, not mid-search — always return last completed depth's best move
- `python-chess` is NOT pre-installed; run `pip install -r requirements.txt` before running tests
- `search(board, depth, alpha, beta)` uses pure negamax (no `maximizing` param); score is always side-to-move relative
- `CHECKMATE_SCORE = 1_000_000`; initial alpha/beta window: `-(CHECKMATE_SCORE+1)` to `CHECKMATE_SCORE+1`
- Stalemate FEN for tests (Black to move, no legal moves): `"k7/2K5/1Q6/8/8/8/8/8 b - - 0 1"`
- Back-rank mate-in-1 FEN: `"1k6/8/1K6/8/8/8/8/7R w - - 0 1"` → Rh8# is the mating move
