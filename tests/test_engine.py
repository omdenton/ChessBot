"""Tests for chessbot/engine.py."""

import chess
import pytest

from chessbot.engine import CHECKMATE_SCORE, get_best_move, search


# ---------------------------------------------------------------------------
# 1. Returns a legal move from the starting position
# ---------------------------------------------------------------------------

def test_returns_legal_move_from_start():
    """get_best_move must return a legal move from the opening position."""
    board = chess.Board()
    move = get_best_move(board, depth=1)
    assert move in board.legal_moves, f"{move} is not a legal move in the starting position"


# ---------------------------------------------------------------------------
# 2. Does not return None when legal moves exist
# ---------------------------------------------------------------------------

def test_does_not_return_none():
    """get_best_move must never return None when there are legal moves."""
    board = chess.Board()
    move = get_best_move(board, depth=2)
    assert move is not None


# ---------------------------------------------------------------------------
# 3. Finds checkmate-in-1
# ---------------------------------------------------------------------------

def test_finds_checkmate_in_one():
    """Engine must choose the mating move in a simple back-rank mate position.

    Position: White king b6, White rook h1, Black king b8.
    White plays Rh8# — the only move that delivers immediate checkmate.
    """
    # 1k6/8/1K6/8/8/8/8/7R w - - 0 1
    board = chess.Board("1k6/8/1K6/8/8/8/8/7R w - - 0 1")
    move = get_best_move(board, depth=1)
    # Verify the chosen move actually delivers checkmate.
    board.push(move)
    assert board.is_checkmate(), (
        f"Expected checkmate after {move.uci()}, but position is not mate"
    )


# ---------------------------------------------------------------------------
# 4. Terminal-state handling: stalemate returns 0
# ---------------------------------------------------------------------------

def test_search_returns_zero_for_stalemate():
    """search() must return 0 for a stalemate position (draw)."""
    # Classic stalemate: Black king a8, White king c7, White queen b6
    # It is Black's turn and Black has no legal moves → stalemate.
    board = chess.Board("k7/2K5/1Q6/8/8/8/8/8 b - - 0 1")
    assert board.is_stalemate(), "Test setup error: position is not stalemate"
    score, move = search(board, depth=3, alpha=-(CHECKMATE_SCORE + 1), beta=CHECKMATE_SCORE + 1)
    assert score == 0
    assert move is None


# ---------------------------------------------------------------------------
# 5. Terminal-state handling: checkmate position returns -CHECKMATE_SCORE
# ---------------------------------------------------------------------------

def test_search_returns_negative_checkmate_score_when_mated():
    """search() must return -CHECKMATE_SCORE when the side to move is mated."""
    # White delivers Scholar's mate: queen on f7 with bishop cover — Black is mated.
    board = chess.Board("r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4")
    assert board.is_checkmate(), "Test setup error: expected checkmate position"
    score, move = search(board, depth=1, alpha=-(CHECKMATE_SCORE + 1), beta=CHECKMATE_SCORE + 1)
    assert score == -CHECKMATE_SCORE
    assert move is None


# ---------------------------------------------------------------------------
# 6. Avoids threefold repetition when winning
# ---------------------------------------------------------------------------

def test_avoids_repetition_when_winning():
    """Engine must not repeat positions when it has a winning advantage (Q+R vs K).

    We set up a position where White has Q+R vs lone K, then play out the
    move history so one more repeat would trigger threefold repetition.
    The engine should avoid the repeating move.
    """
    # White: Kg1, Qd1, Ra1 — Black: Kg8 (Q+R vs lone K)
    board = chess.Board("6k1/8/8/8/8/8/8/R2Q2K1 w - - 0 1")

    # Simulate a move sequence that creates a repeated position:
    # 1. Qd1-d2 Kg8-h8  2. Qd2-d1 Kh8-g8  (back to near-start)
    # Now if White plays Qd1-d2 again, the position after Kg8-h8 would repeat.
    moves = ["d1d2", "g8h8", "d2d1", "h8g8"]
    for uci in moves:
        board.push(chess.Move.from_uci(uci))

    # White to move — the engine should NOT play Qd1-d2 (which would set up
    # the third repetition after Black's forced reply).
    move = get_best_move(board, depth=3)
    assert move != chess.Move.from_uci("d1d2"), (
        "Engine repeated Qd1-d2 despite having Q+R vs K — draw avoidance failed"
    )


# ---------------------------------------------------------------------------
# 7. Seeks threefold repetition when losing
# ---------------------------------------------------------------------------

def test_seeks_repetition_when_losing():
    """Engine should seek repetition when it's losing (K vs Q+R).

    Black has a lone king vs White's Q+R. We set up a position where Black
    can force a draw by repetition and verify the engine chooses it.
    """
    # Black: Kg8 — White: Kg1, Qd2, Ra1.  Black to move.
    board = chess.Board("6k1/8/8/8/8/8/3Q4/R5K1 b - - 0 1")

    # History: 1... Kg8-h8  2. Qd2-d1 Kh8-g8  3. Qd1-d2 ...
    # Now Black can play Kg8-h8 again to create the second repeat.
    moves = ["g8h8", "d2d1", "h8g8", "d1d2"]
    for uci in moves:
        board.push(chess.Move.from_uci(uci))

    # Black to move — the engine should play Kg8-h8 to head toward a draw.
    move = get_best_move(board, depth=3)
    assert move == chess.Move.from_uci("g8h8"), (
        f"Engine played {move.uci()} instead of Kg8-h8 — expected it to seek repetition draw"
    )
