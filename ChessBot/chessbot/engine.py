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

from chessbot.evaluation import MATERIAL, evaluate

# Score magnitude used for checkmate — larger than any material/PST score.
CHECKMATE_SCORE = 1_000_000

# Default search depth (plies).
DEFAULT_DEPTH = 3

# Maximum depth for quiescence search to prevent explosion.
_MAX_QDEPTH = 8


def _mvv_lva_score(board: chess.Board, move: chess.Move) -> int:
    """Return MVV-LVA score for a capture move.

    Score = MATERIAL[victim] * 10 - MATERIAL[attacker].
    Higher scores are tried first (e.g. PxQ = 8900 >> QxP = 100).
    """
    victim_type = board.piece_type_at(move.to_square)
    # En passant: captured pawn is not on the destination square.
    if victim_type is None:
        victim_type = chess.PAWN
    attacker_type = board.piece_type_at(move.from_square)
    assert attacker_type is not None
    return MATERIAL[victim_type] * 10 - MATERIAL[attacker_type]


def _order_moves(board: chess.Board) -> list[chess.Move]:
    """Return legal moves with captures sorted by MVV-LVA, then quiets."""
    captures: list[tuple[int, chess.Move]] = []
    quiets: list[chess.Move] = []
    for move in board.legal_moves:
        if board.is_capture(move):
            captures.append((_mvv_lva_score(board, move), move))
        else:
            quiets.append(move)
    # Sort captures by descending MVV-LVA score.
    captures.sort(key=lambda t: t[0], reverse=True)
    return [m for _, m in captures] + quiets


def _order_captures(board: chess.Board) -> list[chess.Move]:
    """Return legal captures sorted by MVV-LVA score (descending)."""
    scored: list[tuple[int, chess.Move]] = []
    for move in board.generate_legal_captures():
        scored.append((_mvv_lva_score(board, move), move))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [m for _, m in scored]


def quiescence(
    board: chess.Board,
    alpha: int,
    beta: int,
    qdepth: int = 0,
) -> int:
    """Quiescence search: continue searching captures until the position is quiet.

    Uses stand-pat score as baseline. Only captures are explored (via
    board.generate_legal_captures()), ordered by MVV-LVA. Capped at
    _MAX_QDEPTH plies to prevent explosion.

    Returns score from the side-to-move perspective.
    """
    # Stand-pat: static evaluation as a baseline.
    stand_pat = evaluate(board)
    if board.turn == chess.BLACK:
        stand_pat = -stand_pat

    if stand_pat >= beta:
        return beta

    if stand_pat > alpha:
        alpha = stand_pat

    # Stop deepening if we hit the quiescence depth cap.
    if qdepth >= _MAX_QDEPTH:
        return alpha

    for move in _order_captures(board):
        board.push(move)
        score = -quiescence(board, -beta, -alpha, qdepth + 1)
        board.pop()

        if score >= beta:
            return beta

        if score > alpha:
            alpha = score

    return alpha


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

    # --- Leaf node: drop into quiescence search ---
    if depth == 0:
        return quiescence(board, alpha, beta), None

    # --- Internal node: iterate over moves ---
    best_score = -(CHECKMATE_SCORE + 1)
    best_move: chess.Move | None = None

    for move in _order_moves(board):
        board.push(move)
        # Treat repeated positions as draws to avoid threefold repetition.
        if board.is_repetition(2):
            child_score = 0
        else:
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
    # Cap thinking time to 10 seconds for unlimited/correspondence games
    budget_s = min(budget_s, 10.0)

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
