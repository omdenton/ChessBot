Status: IN_PROGRESS

# Implementation Plan — ChessBot

## Overview

Build a UCI-compatible Python chess engine using `python-chess` for move generation and a custom minimax/alpha-beta search with heuristic evaluation.

## Module Structure

```
chessbot/
  __init__.py
  evaluation.py   # Material balance + PSTs + advanced heuristics
  engine.py       # Search (negamax, quiescence, TT, pruning) + time management
  uci.py          # UCI protocol stdin/stdout loop
  cli.py          # Interactive CLI wrapper for manual testing
  lichess.py      # Lichess bot integration
tests/
  test_evaluation.py
  test_engine.py
  test_uci.py
main.py           # Entry point (UCI by default, --cli, --lichess, --build-book)
requirements.txt  # python-chess, pytest, httpx
```

---

## Completed Tasks (Phase 1 — Core Engine)

### Task 1 — Project Setup ✅ DONE
### Task 2 — Evaluation Function ✅ DONE
### Task 3 — Minimax + Alpha-Beta ✅ DONE
### Task 4 — Time Management ✅ DONE
### Task 5 — UCI Protocol Handler ✅ DONE
### Task 6 — CLI Wrapper ✅ DONE
### Task 7 — Comprehensive Test Suite ✅ DONE

---

## Phase 2 — Search Improvements (HIGH PRIORITY)

### Task 8 — MVV-LVA Capture Ordering (Spec 7c) ✅ DONE
**Description:** Replace the current "captures before quiets" ordering with Most Valuable Victim / Least Valuable Attacker scoring.

**Dependencies:** None (improves existing `_order_moves()`)
**Complexity:** S

---

### Task 9 — Quiescence Search (Spec 7a) ✅ DONE
**Description:** At depth 0, continue searching capture sequences until the position is quiet instead of returning static eval immediately.

**Dependencies:** Task 8 (MVV-LVA ordering should apply to quiescence captures too)
**Complexity:** M

---

### Task 10 — Transposition Table (Spec 7b) ✅ DONE
**Description:** Cache search results keyed by Zobrist hash to avoid re-evaluating positions reached via different move orders.

**Dependencies:** None (but benefits from Task 8/9 for move ordering)
**Complexity:** L

---

### Task 11 — Check Extensions (Spec 7k)
**Description:** When a move gives check, extend search by 1 ply.

**Acceptance Criteria:**
- After making a move in `search()`, if `board.is_check()` is true, search with `depth` instead of `depth - 1`.
- New test: engine finds a mate that requires seeing through a check extension (e.g. a 2-move forced sequence where the first move is a check).
- All existing tests still pass.

**Dependencies:** None
**Complexity:** S

---

## Phase 3 — Evaluation Improvements (HIGH PRIORITY)

### Task 12 — Tapered Evaluation / Game Phase Detection (Spec 6a)
**Description:** Use game phase to blend middlegame and endgame PSTs. This fixes the known repetition-draw bug by making the king move toward the center in endgames.

**Acceptance Criteria:**
- Game phase computed from total non-pawn material: 0 = endgame, 24 = opening (knight/bishop = 1, rook = 2, queen = 4).
- Two PST sets per piece type: middlegame and endgame.
- Score blended: `score = (mg * phase + eg * (24 - phase)) / 24`.
- Endgame king PST rewards central squares (d4/e4/d5/e5) instead of castled corners.
- Existing PSTs become the middlegame set; new endgame PSTs created.
- All existing evaluation tests updated/pass with new scoring (values may shift slightly).
- New test: in a K+Q vs K endgame, king is incentivized toward center (endgame PST active).

**Dependencies:** None
**Complexity:** M

---

### Task 13 — Passed Pawns (Spec 6c)
**Description:** Detect passed pawns and award bonuses that scale with rank.

**Acceptance Criteria:**
- A passed pawn is one with no enemy pawns blocking or flanking it on the way to promotion.
- Bonus by rank: rank 2=10cp, rank 3=20cp, rank 4=40cp, rank 5=70cp, rank 6=120cp, rank 7=200cp.
- Extra bonus if protected by another pawn.
- Extra bonus if enemy king is far from the pawn.
- New tests: passed pawn on rank 6 scores higher than rank 3; protected passed pawn scores higher than unprotected.
- All existing tests still pass.

**Dependencies:** Task 12 (bonuses should be tapered)
**Complexity:** S

---

### Task 14 — Mop-Up Evaluation (Spec 6h)
**Description:** When the engine has a large material advantage and the opponent has no queens/rooks, add terms that drive progress toward checkmate.

**Acceptance Criteria:**
- Triggers when material advantage > 200cp AND losing side has no queens or rooks.
- Bonus for losing king being close to a corner: `(3.5 - distance_to_closest_corner) * 20`.
- Bonus for winning king being close to losing king: `(14 - manhattan_distance) * 10`.
- New test: in K+Q vs K, mop-up evaluation rewards positions where the lone king is cornered and winning king is nearby.
- Existing repetition-avoidance tests still pass and the engine now actively progresses toward mate.

**Dependencies:** None
**Complexity:** S

---

### Task 15 — Draw Contempt (Spec 6k)
**Description:** Score repetitions with contempt instead of exactly 0.

**Acceptance Criteria:**
- If engine is materially ahead, score repetition as -50cp (discourage draw).
- If engine is materially behind, score repetition as +50cp (encourage draw).
- If roughly equal, keep repetition score at 0.
- Applied in `search()` where threefold repetition is detected.
- New test: in a winning position, repetition move is scored negatively; in a losing position, scored positively.
- All existing tests still pass.

**Dependencies:** None
**Complexity:** S

---

## Phase 4 — Additional Evaluation Heuristics

### Task 16 — Pawn Structure (Spec 6b)
**Description:** Evaluate doubled, isolated, backward pawns, and pawn islands.

**Acceptance Criteria:**
- Doubled pawns: penalty ~20-30cp each.
- Isolated pawns: penalty ~15-25cp.
- Backward pawns: penalty ~10-15cp.
- Pawn islands: penalty ~5cp per extra island.
- New tests: position with doubled pawns scores lower than clean pawn structure; isolated pawn detected and penalized.
- All existing tests still pass.

**Dependencies:** Task 12 (penalties should be tapered)
**Complexity:** M

---

### Task 17 — Bishop Pair (Spec 6d)
**Description:** Award a bonus for having both bishops.

**Acceptance Criteria:**
- Bonus of ~40cp for having both bishops.
- Optionally scale up in open positions (fewer pawns on the board).
- New test: position with bishop pair scores higher than equivalent with two knights.
- All existing tests still pass.

**Dependencies:** None
**Complexity:** S

---

### Task 18 — Rook Placement (Spec 6e)
**Description:** Improve rook evaluation with open/semi-open file detection and connected rooks.

**Acceptance Criteria:**
- Open file (no pawns of either color): bonus ~20cp.
- Semi-open file (no friendly pawns): bonus ~10cp.
- Rook on 7th rank: bonus ~20cp (already partially implemented — verify and keep consistent).
- Connected rooks: bonus for both rooks defending each other on same rank.
- New tests: rook on open file scores higher than rook on closed file.
- All existing tests still pass.

**Dependencies:** None
**Complexity:** S

---

### Task 19 — King Safety / Pawn Shield (Spec 6f)
**Description:** Evaluate pawn shield around castled king.

**Acceptance Criteria:**
- If king is castled (g1/h1/b1/c1 for White, mirrored for Black), check for pawns on shielding squares.
- Penalty ~20cp per missing shield pawn, ~10cp per advanced shield pawn.
- Scale term to zero in endgame via tapered eval phase.
- New test: king with intact pawn shield scores higher than king with missing shield pawns.
- All existing tests still pass.

**Dependencies:** Task 12 (tapered eval to scale down in endgame)
**Complexity:** S

---

### Task 20 — Mobility (Spec 6g)
**Description:** Per-piece bonus for the number of attacked squares.

**Acceptance Criteria:**
- Knight: ~4cp/square, Bishop: ~3cp, Rook: ~2cp, Queen: ~1cp.
- Uses `board.attacks(sq)` to count attacked squares per piece.
- New test: position with centralized knight (many squares) scores higher than knight on rim.
- Performance: consider computing only for knights and bishops to limit overhead.
- All existing tests still pass.

**Dependencies:** None
**Complexity:** M

---

### Task 21 — Drawn Endgame Detection (Spec 6j)
**Description:** Recognize specific drawn endgames beyond `board.is_insufficient_material()`.

**Acceptance Criteria:**
- KBP vs K with wrong-color bishop: if only pawn is a rook pawn (a/h file) and bishop doesn't control promotion square, return 0.
- Opposite-color bishops: KBP vs KB with opposite-color bishops — scale evaluation down by ~50%.
- New tests: KBP vs K with wrong-color bishop returns 0; opposite-color bishop position returns reduced score.
- All existing tests still pass.

**Dependencies:** None
**Complexity:** S

---

## Phase 5 — Advanced Search Techniques

### Task 22 — Killer Move Heuristic (Spec 7d)
**Description:** Store quiet moves that cause beta cutoffs and try them early in move ordering.

**Acceptance Criteria:**
- `killers[ply] = [move1, move2]` (two slots per ply).
- When a quiet move causes beta cutoff, store it as a killer for that ply.
- In move ordering: TT move → captures (MVV-LVA) → killers → remaining quiets.
- All existing tests still pass.

**Dependencies:** Task 10 (TT move is highest priority in ordering)
**Complexity:** S

---

### Task 23 — History Heuristic (Spec 7e)
**Description:** Track quiet moves that cause cutoffs and use them for move ordering.

**Acceptance Criteria:**
- `history[color][from_sq][to_sq]` counters, incremented by `depth * depth` on beta cutoff.
- Remaining quiet moves (after TT, captures, killers) sorted by descending history score.
- History table cleared on `ucinewgame`.
- All existing tests still pass.

**Dependencies:** Task 22 (killers come before history-sorted quiets)
**Complexity:** S

---

### Task 24 — Null Move Pruning (Spec 7f)
**Description:** Skip searching if giving the opponent an extra move still results in a score >= beta.

**Acceptance Criteria:**
- Before searching moves: if not in check and side to move has pieces beyond king+pawns, try null move.
- Null move via `board.push(chess.Move.null())`, search at `depth - 1 - R` (R=2 or 3).
- If null move search score >= beta, return beta (prune).
- Never allow two consecutive null moves.
- New test: null move pruning reduces node count vs without it (benchmark test).
- All existing tests still pass.

**Dependencies:** Task 10 (TT needed for full benefit)
**Complexity:** M

---

### Task 25 — Principal Variation Search / PVS (Spec 7g)
**Description:** Search first move with full window, subsequent moves with null window.

**Acceptance Criteria:**
- First move (expected best from TT/ordering) searched with full (alpha, beta) window.
- All subsequent moves searched with null window (alpha, alpha+1).
- If null-window search fails high, re-search with full window.
- All existing tests still pass.

**Dependencies:** Task 10 (TT best move as first move is critical for PVS)
**Complexity:** M

---

### Task 26 — Late Move Reductions / LMR (Spec 7h)
**Description:** Reduce search depth for moves late in the move list that are unlikely to be good.

**Acceptance Criteria:**
- Moves after the first 3-4 that are not captures, checks, or killers are searched at reduced depth.
- Reduction: R=1 for moves 4-6, R=2 for moves 7+.
- If reduced search returns score > alpha, re-search at full depth.
- All existing tests still pass.

**Dependencies:** Task 22 (need killers to exempt from reduction), Task 25 (PVS)
**Complexity:** M

---

### Task 27 — Aspiration Windows (Spec 7i)
**Description:** Use narrow search windows around previous iteration's score in iterative deepening.

**Acceptance Criteria:**
- Instead of (-INF, +INF), use (prev_score - 50, prev_score + 50) at each ID iteration.
- If search fails low or high, widen window and re-search.
- First iteration (depth 1) uses full window.
- All existing tests still pass.

**Dependencies:** None (but most effective with TT, Task 10)
**Complexity:** S

---

### Task 28 — Futility Pruning (Spec 7j)
**Description:** At low remaining depths, skip quiet moves when static eval is far below alpha.

**Acceptance Criteria:**
- At depth 1-2: if `static_eval + margin < alpha` (margin ~200cp for depth 1, ~500cp for depth 2), skip quiet moves.
- Still search captures and checks.
- All existing tests still pass.

**Dependencies:** Task 9 (quiescence search handles captures at depth 0)
**Complexity:** S

---

## Phase 6 — Move Generation Optimisation

### Task 29 — Lazy Move Generation (Spec 8)
**Description:** Don't generate all legal moves upfront; generate in stages.

**Acceptance Criteria:**
- Move generation order: TT move → captures (MVV-LVA) → killers → remaining quiets (history-sorted).
- Only generate each category when previous didn't cause cutoff.
- Replace `board.is_game_over()` per node with: check for no legal moves + `board.is_check()` for mate/stalemate; use `board.halfmove_clock >= 100` for 50-move rule.
- All existing tests still pass.

**Dependencies:** Task 10, Task 22, Task 23 (TT, killers, history all needed for full lazy gen)
**Complexity:** M

---

## Phase 7 — Opening Book

### Task 30 — Game History Learning / Opening Book (Spec 5)
**Description:** Pull the bot's Lichess game history and build a personal opening book.

**Acceptance Criteria:**
- `--build-book` CLI flag fetches games from `GET /api/games/user/OlisRalphBot` using existing Lichess token.
- Parses first 10-15 moves of each game, aggregates win/loss/draw stats per position+move.
- Only includes moves from games the bot won or drew.
- Stores results in `data/openings.json` as `{fen: {move_uci: {wins, losses, draws, count}}}`.
- At runtime, before alpha-beta search, check if current position exists in the book.
- Play the move with best win rate (minimum sample size >= 3 games).
- Small random factor so bot doesn't always play the same line.
- New tests: book building produces correct JSON structure; book lookup returns move with best win rate.

**Dependencies:** None (but most valuable after search/eval improvements)
**Complexity:** L

---

## Phase 8 — Correctness & Testing

### Task 31 — Perft Testing (Spec 9)
**Description:** Implement perft function and validate against published results.

**Acceptance Criteria:**
- `perft(board, depth)` counts leaf nodes.
- Compare against published perft results for starting position (depth 1-5).
- Test tricky positions: castling, en passant, promotion.
- All perft counts match published values exactly.

**Dependencies:** None
**Complexity:** M

---

## Implementation Order

| # | Task | Spec | Complexity | Depends On | Status |
|---|------|------|------------|------------|--------|
| 1 | Project Setup | — | S | — | ✅ Done |
| 2 | Evaluation Function | §2 | S | 1 | ✅ Done |
| 3 | Minimax + Alpha-Beta | §2 | M | 2 | ✅ Done |
| 4 | Time Management | §2 | S | 3 | ✅ Done |
| 5 | UCI Protocol Handler | §1 | M | 4 | ✅ Done |
| 6 | CLI Wrapper | §3 | S | 3 | ✅ Done |
| 7 | Comprehensive Tests | §9 | M | 2,3,5 | ✅ Done |
| 8 | MVV-LVA Capture Ordering | §7c | S | — | ✅ Done |
| 9 | Quiescence Search | §7a | M | 8 | ✅ Done |
| 10 | Transposition Table | §7b | L | — | ✅ Done |
| 11 | Check Extensions | §7k | S | — | ⬚ |
| 12 | Tapered Eval / Game Phase | §6a | M | — | ⬚ |
| 13 | Passed Pawns | §6c | S | 12 | ⬚ |
| 14 | Mop-Up Evaluation | §6h | S | — | ⬚ |
| 15 | Draw Contempt | §6k | S | — | ⬚ |
| 16 | Pawn Structure | §6b | M | 12 | ⬚ |
| 17 | Bishop Pair | §6d | S | — | ⬚ |
| 18 | Rook Placement | §6e | S | — | ⬚ |
| 19 | King Safety / Pawn Shield | §6f | S | 12 | ⬚ |
| 20 | Mobility | §6g | M | — | ⬚ |
| 21 | Drawn Endgame Detection | §6j | S | — | ⬚ |
| 22 | Killer Move Heuristic | §7d | S | 10 | ⬚ |
| 23 | History Heuristic | §7e | S | 22 | ⬚ |
| 24 | Null Move Pruning | §7f | M | 10 | ⬚ |
| 25 | PVS | §7g | M | 10 | ⬚ |
| 26 | LMR | §7h | M | 22,25 | ⬚ |
| 27 | Aspiration Windows | §7i | S | — | ⬚ |
| 28 | Futility Pruning | §7j | S | 9 | ⬚ |
| 29 | Lazy Move Generation | §8 | M | 10,22,23 | ⬚ |
| 30 | Opening Book | §5 | L | — | ⬚ |
| 31 | Perft Testing | §9 | M | — | ⬚ |
