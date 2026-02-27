"""Tests for chessbot/uci.py.

Tests call handle_command() directly to avoid subprocess/stdin overhead.
Board state mutations from ``position`` commands are verified against FEN or
board attributes.
"""

import re

import chess
import pytest

from chessbot.uci import handle_command

# Starting-position FEN for comparison.
STARTING_FEN = chess.Board().fen()


# ---------------------------------------------------------------------------
# 1. position startpos — resets to starting position
# ---------------------------------------------------------------------------


def test_position_startpos_resets_board():
    """'position startpos' must set the board to the initial position."""
    fen = "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
    board = chess.Board(fen)
    handle_command(board, "position startpos")
    assert board.fen() == STARTING_FEN


# ---------------------------------------------------------------------------
# 2. position startpos moves e2e4 — applies moves correctly
# ---------------------------------------------------------------------------


def test_position_startpos_with_moves():
    """'position startpos moves e2e4' must advance the board one half-move."""
    board = chess.Board()
    handle_command(board, "position startpos moves e2e4")
    # After 1. e4 it is Black's turn and the e-pawn should be on e4.
    assert board.turn == chess.BLACK
    assert board.piece_at(chess.E4) == chess.Piece(chess.PAWN, chess.WHITE)


# ---------------------------------------------------------------------------
# 3. position fen <FEN> — sets board from FEN
# ---------------------------------------------------------------------------


def test_position_fen():
    """'position fen <FEN>' must set the board to the given FEN."""
    fen = "1k6/8/1K6/8/8/8/8/7R w - - 0 1"
    board = chess.Board()
    handle_command(board, f"position fen {fen}")
    assert board.fen() == chess.Board(fen).fen()


# ---------------------------------------------------------------------------
# 4. position fen <FEN> moves — applies moves on top of the FEN
# ---------------------------------------------------------------------------


def test_position_fen_with_moves():
    """'position fen <FEN> moves h1h8' must apply the move on top of the FEN."""
    fen = "1k6/8/1K6/8/8/8/8/7R w - - 0 1"
    board = chess.Board()
    handle_command(board, f"position fen {fen} moves h1h8")
    # Rh8# is checkmate in this position.
    assert board.is_checkmate()


# ---------------------------------------------------------------------------
# 5. go depth 1 — returns a valid bestmove string
# ---------------------------------------------------------------------------


def test_go_depth_one_returns_bestmove():
    """'go depth 1' must return a string matching 'bestmove <move>'."""
    board = chess.Board()
    response = handle_command(board, "go depth 1")
    assert response is not None
    # Accepts standard moves (e2e4) and promotions (e7e8q).
    assert re.match(r"bestmove [a-h][1-8][a-h][1-8][qrbn]?$", response), (
        f"Unexpected response: {response!r}"
    )


# ---------------------------------------------------------------------------
# 6. uci — returns id lines and uciok
# ---------------------------------------------------------------------------


def test_uci_response():
    """'uci' must return at least one 'id name' line and end with 'uciok'."""
    board = chess.Board()
    response = handle_command(board, "uci")
    assert response is not None
    assert "id name" in response
    assert "uciok" in response


# ---------------------------------------------------------------------------
# 7. isready — returns readyok
# ---------------------------------------------------------------------------


def test_isready_response():
    """'isready' must return exactly 'readyok'."""
    board = chess.Board()
    response = handle_command(board, "isready")
    assert response == "readyok"


# ---------------------------------------------------------------------------
# 8. ucinewgame — resets the board to starting position
# ---------------------------------------------------------------------------


def test_ucinewgame_resets_board():
    """'ucinewgame' must reset the board and produce no output."""
    fen = "1k6/8/1K6/8/8/8/8/7R w - - 0 1"
    board = chess.Board(fen)
    response = handle_command(board, "ucinewgame")
    assert response is None
    assert board.fen() == STARTING_FEN


# ---------------------------------------------------------------------------
# 9. Unknown commands — silently ignored
# ---------------------------------------------------------------------------


def test_unknown_command_returns_none():
    """Unknown UCI commands must be silently ignored (no output)."""
    board = chess.Board()
    response = handle_command(board, "setoption name Hash value 64")
    assert response is None
