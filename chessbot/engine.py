"""Minimax search with Alpha-Beta pruning for ChessBot.

Uses the negamax formulation: the score returned by `search` is always
from the perspective of the *side to move* — positive means the current
player is better off, negative means they are worse off.

Public entry points:
  get_best_move(board, depth)                              – fixed depth
  get_best_move_timed(board, wtime_ms, btime_ms, ...)     – time-managed
"""

import time

import chess

from chessbot.evaluation import evaluate

# Score magnitude used for checkmate — larger than any material/PST score.
CHECKMATE_SCORE = 1_000_000

# Default search depth (plies).
DEFAULT_DEPTH = 3


def _order_moves(board: chess.Board) -> list[chess.Move]:
    """Return legal moves with captures first to improve alpha-beta pruning."""
    captures: list[chess.Move] = []
    quiets: list[chess.Move] = []
    for move in board.legal_moves:
        if board.is_capture(move):
            captures.append(move)
        else:
            quiets.append(move)
    return captures + quiets


def search(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
) -> tuple[int, chess.Move | None]:
    """Negamax alpha-beta search.

    Scores are always from the perspective of the side to move:
      - positive → current player is winning
      - negative → current player is losing

    Alpha-beta bounds are in the same perspective:
      alpha = best score the current player can guarantee
      beta  = best score the *opponent* can guarantee (upper bound for us)

    Args:
        board: Position to search; mutated in place during search and restored
               before returning (via board.push / board.pop).
        depth: Remaining search depth in plies.
        alpha: Lower bound on the score achievable (current player's perspective).
        beta:  Upper bound — if we exceed this, the opponent will avoid this line.

    Returns:
        (best_score, best_move). best_move is None at leaf/terminal nodes.
    """
    # --- Terminal node: game is over ---
    if board.is_game_over():
        if board.is_checkmate():
            # The side to move has been checkmated — they lose.
            return -CHECKMATE_SCORE, None
        # Stalemate, insufficient material, 50-move rule, or repetition.
        return 0, None

    # --- Leaf node: static evaluation ---
    if depth == 0:
        # evaluate() returns score from White's perspective (+ = White better).
        # Negate for Black so the returned value is always side-to-move relative.
        score = evaluate(board)
        if board.turn == chess.BLACK:
            score = -score
        return score, None

    # --- Internal node: iterate over moves ---
    best_score = -(CHECKMATE_SCORE + 1)
    best_move: chess.Move | None = None

    for move in _order_moves(board):
        board.push(move)
        # Recurse with negated bounds (opponent's perspective).
        child_score, _ = search(board, depth - 1, -beta, -alpha)
        board.pop()

        # Flip the child score back to our perspective.
        score = -child_score

        if score > best_score:
            best_score = score
            best_move = move

        if score > alpha:
            alpha = score

        if alpha >= beta:
            break  # Beta cutoff: opponent won't allow this line.

    return best_score, best_move


def get_best_move(board: chess.Board, depth: int = DEFAULT_DEPTH) -> chess.Move:
    """Return the best move for the current position via alpha-beta search.

    Args:
        board: Current board position.
        depth: Search depth in plies (default: DEFAULT_DEPTH = 3).

    Returns:
        The best chess.Move found.

    Raises:
        ValueError: If there are no legal moves (caller should check first).
    """
    if not any(board.legal_moves):
        raise ValueError("get_best_move called on a position with no legal moves")

    _, move = search(board, depth, -(CHECKMATE_SCORE + 1), CHECKMATE_SCORE + 1)

    # `search` guarantees a move when legal moves exist; this should never fire.
    assert move is not None, "search returned None despite legal moves existing"
    return move


# Safety margin: never use more than this fraction of the allocated budget
# to leave a small buffer for overhead / communication latency.
_BUDGET_SAFETY = 0.95


def get_best_move_timed(
    board: chess.Board,
    wtime_ms: int,
    btime_ms: int,
    movestogo: int | None = None,
) -> chess.Move:
    """Return the best move using iterative deepening within a time budget.

    The time budget is derived from the remaining time for the side to move:
        budget = player_time_ms / (movestogo or 30) * safety_margin

    Search starts at depth 1 and deepens as long as the budget allows.
    The search is only interrupted *between* depths (never mid-search), so
    the move returned is always from a fully completed search depth.

    Args:
        board:       Current board position.
        wtime_ms:    White's remaining time in milliseconds.
        btime_ms:    Black's remaining time in milliseconds.
        movestogo:   Expected number of moves until the next time control
                     (None → assume 30 moves remaining).

    Returns:
        The best chess.Move found within the budget.

    Raises:
        ValueError: If there are no legal moves (caller should check first).
    """
    if not any(board.legal_moves):
        raise ValueError("get_best_move_timed called on a position with no legal moves")

    # Select the time for the side to move.
    player_time_ms = wtime_ms if board.turn == chess.WHITE else btime_ms
    divisor = movestogo if movestogo and movestogo > 0 else 30
    budget_s = (player_time_ms / 1000) / divisor * _BUDGET_SAFETY

    deadline = time.monotonic() + budget_s

    # Always complete at least depth 1 regardless of budget.
    _, best_move = search(board, 1, -(CHECKMATE_SCORE + 1), CHECKMATE_SCORE + 1)
    assert best_move is not None  # legal moves exist, so search must find one

    depth = 2
    while time.monotonic() < deadline:
        _, candidate = search(board, depth, -(CHECKMATE_SCORE + 1), CHECKMATE_SCORE + 1)
        assert candidate is not None
        best_move = candidate
        depth += 1

    return best_move
