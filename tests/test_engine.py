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
