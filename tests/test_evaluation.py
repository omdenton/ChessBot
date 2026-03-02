"""Tests for chessbot/evaluation.py."""

import chess
import pytest

from chessbot.evaluation import MATERIAL, PST, evaluate


# ---------------------------------------------------------------------------
# 1. Starting position is exactly 0 (perfect material and positional symmetry)
# ---------------------------------------------------------------------------

def test_starting_position_is_zero():
    """Starting position must evaluate to 0: both sides are symmetric."""
    board = chess.Board()
    assert evaluate(board) == 0


# ---------------------------------------------------------------------------
# 2. Material imbalance – White advantage
# ---------------------------------------------------------------------------

def test_white_extra_queen_scores_positive():
    """Removing Black's queen gives White a large positive score (~900 cp)."""
    # "rnb1kbnr/…" – Black's d8 queen is absent
    board = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    score = evaluate(board)
    assert score > 0, f"Expected positive score, got {score}"
    # The queen is worth 900 cp; PST noise is well under 100 cp
    assert score > 800, f"Expected score > 800 (one queen), got {score}"


# ---------------------------------------------------------------------------
# 3. Material imbalance – Black advantage
# ---------------------------------------------------------------------------

def test_black_extra_rook_scores_negative():
    """Removing White's a1 rook gives Black a rook-worth advantage (~500 cp)."""
    # "1NBQKBNR" on rank 1 – White's a1 rook is absent
    board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/1NBQKBNR w Kkq - 0 1")
    score = evaluate(board)
    assert score < 0, f"Expected negative score, got {score}"
    assert score < -400, f"Expected score < -400 (one rook), got {score}"


# ---------------------------------------------------------------------------
# 4. Mirror symmetry: evaluate(mirror_pos) == -evaluate(pos)
# ---------------------------------------------------------------------------

def test_mirror_symmetry_negation():
    """A position and its colour-flipped mirror must have equal and opposite scores.

    White queen on d5, kings on e1/e8  →  evaluate() = +X
    Black queen on d4, kings on e1/e8  →  evaluate() = -X
    (d4 is the vertical mirror of d5, so PST bonuses are equal.)
    """
    # White queen on d5 (sq=35), kings e1/e8
    board_white = chess.Board("4k3/8/8/3Q4/8/8/8/4K3 w - - 0 1")
    score_white = evaluate(board_white)

    # Black queen on d4 (sq=27, mirror of d5 via sq^56=35)
    board_black = chess.Board("4k3/8/8/8/3q4/8/8/4K3 w - - 0 1")
    score_black = evaluate(board_black)

    assert score_white > 0, f"Expected positive score for White queen advantage, got {score_white}"
    assert score_black < 0, f"Expected negative score for Black queen advantage, got {score_black}"
    assert score_white == -score_black, (
        f"Mirror symmetry violated: {score_white} != {-score_black}"
    )


# ---------------------------------------------------------------------------
# 5. Insufficient material → 0
# ---------------------------------------------------------------------------

def test_king_vs_king_is_zero():
    """King vs King is insufficient material; evaluate() must return 0."""
    board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    assert evaluate(board) == 0


def test_king_and_bishop_vs_king_is_zero():
    """KBK is a theoretical draw; evaluate() must return 0."""
    board = chess.Board("4k3/8/8/8/8/8/8/4KB2 w - - 0 1")
    assert evaluate(board) == 0


# ---------------------------------------------------------------------------
# 6. Positional bonus – rook on the 7th rank
# ---------------------------------------------------------------------------

def test_rook_seventh_rank_bonus():
    """A rook on the 7th rank should outscore the same rook on the 3rd rank
    (all other material being equal)."""
    # White rook on d7 (sq=51), kings on e1/e8
    board_7th = chess.Board("4k3/3R4/8/8/8/8/8/4K3 w - - 0 1")
    score_7th = evaluate(board_7th)

    # White rook on d3 (sq=19), same kings
    board_3rd = chess.Board("4k3/8/8/8/8/3R4/8/4K3 w - - 0 1")
    score_3rd = evaluate(board_3rd)

    assert score_7th > score_3rd, (
        f"Rook on 7th rank ({score_7th}) should beat rook on 3rd rank ({score_3rd})"
    )


# ---------------------------------------------------------------------------
# 7. PST sanity – all tables are exactly 64 entries
# ---------------------------------------------------------------------------

def test_pst_tables_have_64_entries():
    """Every PST table must have exactly 64 squares."""
    for piece_type, table in PST.items():
        assert len(table) == 64, (
            f"PST for piece_type={piece_type} has {len(table)} entries, expected 64"
        )
