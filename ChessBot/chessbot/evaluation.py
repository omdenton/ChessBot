"""Board evaluation heuristic for ChessBot.

Scores are in centipawns from White's perspective:
  positive = White advantage, negative = Black advantage.

For PST indexing:
  White pieces: use square index directly (a1=0 .. h8=63).
  Black pieces: use sq ^ 56 (vertical mirror) so the same
                table rewards equivalent positional goals.
"""

import chess

# ---------------------------------------------------------------------------
# Material values (centipawns)
# ---------------------------------------------------------------------------
MATERIAL: dict[int, int] = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:  20000,
}

# ---------------------------------------------------------------------------
# Piece-Square Tables
# Each table has 64 entries ordered a1=0, b1=1, … h1=7, a2=8, … h8=63.
# Comments show rank 1 at the top of each block for readability, which
# matches the index ordering (low indices = White's back rank = rank 1).
# ---------------------------------------------------------------------------

# fmt: off
_PST_PAWN = [
    # rank 1  (sq  0– 7) – pawns cannot legally be here
     0,  0,  0,  0,  0,  0,  0,  0,
    # rank 2  (sq  8–15) – most pawns start here; penalise d/e, reward flanks
     5, 10, 10,-20,-20, 10, 10,  5,
    # rank 3  (sq 16–23)
     5, -5,-10,  0,  0,-10, -5,  5,
    # rank 4  (sq 24–31) – reward central occupation
     0,  0,  0, 20, 20,  0,  0,  0,
    # rank 5  (sq 32–39)
     5,  5, 10, 25, 25, 10,  5,  5,
    # rank 6  (sq 40–47)
    10, 10, 20, 30, 30, 20, 10, 10,
    # rank 7  (sq 48–55) – passed / near-promotion pawns
    50, 50, 50, 50, 50, 50, 50, 50,
    # rank 8  (sq 56–63) – pawns cannot legally be here (promotion rank)
     0,  0,  0,  0,  0,  0,  0,  0,
]

_PST_KNIGHT = [
    # rank 1
   -50,-40,-30,-30,-30,-30,-40,-50,
    # rank 2
   -40,-20,  0,  5,  5,  0,-20,-40,
    # rank 3
   -30,  5, 10, 15, 15, 10,  5,-30,
    # rank 4 – centre is best
   -30,  0, 15, 20, 20, 15,  0,-30,
    # rank 5
   -30,  5, 15, 20, 20, 15,  5,-30,
    # rank 6
   -30,  0, 10, 15, 15, 10,  0,-30,
    # rank 7
   -40,-20,  0,  5,  5,  0,-20,-40,
    # rank 8
   -50,-40,-30,-30,-30,-30,-40,-50,
]

_PST_BISHOP = [
    # rank 1
   -20,-10,-10,-10,-10,-10,-10,-20,
    # rank 2
   -10,  0,  0,  0,  0,  0,  0,-10,
    # rank 3
   -10,  0,  5, 10, 10,  5,  0,-10,
    # rank 4
   -10,  5,  5, 10, 10,  5,  5,-10,
    # rank 5
   -10,  0, 10, 10, 10, 10,  0,-10,
    # rank 6
   -10, 10, 10, 10, 10, 10, 10,-10,
    # rank 7
   -10,  5,  0,  0,  0,  0,  5,-10,
    # rank 8
   -20,-10,-10,-10,-10,-10,-10,-20,
]

_PST_ROOK = [
    # rank 1 – small bonus for d/e file (semi-open lines)
     0,  0,  0,  5,  5,  0,  0,  0,
    # rank 2
    -5,  0,  0,  0,  0,  0,  0, -5,
    # rank 3
    -5,  0,  0,  0,  0,  0,  0, -5,
    # rank 4
    -5,  0,  0,  0,  0,  0,  0, -5,
    # rank 5
    -5,  0,  0,  0,  0,  0,  0, -5,
    # rank 6
    -5,  0,  0,  0,  0,  0,  0, -5,
    # rank 7 – rook on 7th is very powerful
     5, 10, 10, 10, 10, 10, 10,  5,
    # rank 8
     0,  0,  0,  0,  0,  0,  0,  0,
]

_PST_QUEEN = [
    # rank 1
   -20,-10,-10, -5, -5,-10,-10,-20,
    # rank 2
   -10,  0,  0,  0,  0,  0,  0,-10,
    # rank 3
   -10,  0,  5,  5,  5,  5,  0,-10,
    # rank 4
    -5,  0,  5,  5,  5,  5,  0, -5,
    # rank 5
    -5,  0,  5,  5,  5,  5,  0, -5,
    # rank 6
   -10,  5,  5,  5,  5,  5,  5,-10,
    # rank 7
   -10,  0,  5,  0,  0,  5,  0,-10,
    # rank 8
   -20,-10,-10, -5, -5,-10,-10,-20,
]

# Middlegame king safety: encourage castling to g1/c1 (White) / g8/c8 (Black).
_PST_KING = [
    # rank 1 – safe after castling (g1=30, b1/c1 area also good)
    20, 30, 10,  0,  0, 10, 30, 20,
    # rank 2
    20, 20,  0,  0,  0,  0, 20, 20,
    # rank 3
   -10,-20,-20,-20,-20,-20,-20,-10,
    # rank 4
   -20,-30,-30,-40,-40,-30,-30,-20,
    # rank 5
   -30,-40,-40,-50,-50,-40,-40,-30,
    # rank 6
   -30,-40,-40,-50,-50,-40,-40,-30,
    # rank 7
   -30,-40,-40,-50,-50,-40,-40,-30,
    # rank 8
   -30,-40,-40,-50,-50,-40,-40,-30,
]
# fmt: on

PST: dict[int, list[int]] = {
    chess.PAWN:   _PST_PAWN,
    chess.KNIGHT: _PST_KNIGHT,
    chess.BISHOP: _PST_BISHOP,
    chess.ROOK:   _PST_ROOK,
    chess.QUEEN:  _PST_QUEEN,
    chess.KING:   _PST_KING,
}


def evaluate(board: chess.Board) -> int:
    """Return a centipawn evaluation of *board* from White's perspective.

    Positive values favour White; negative values favour Black.
    Returns 0 for positions with insufficient material (drawn by rule).
    Stalemate / checkmate detection is intentionally left to the caller
    (the search), which can assign ±INF / 0 appropriately.
    """
    if board.is_insufficient_material():
        return 0

    score = 0
    for piece_type in chess.PIECE_TYPES:
        pst = PST[piece_type]
        value = MATERIAL[piece_type]

        for sq in board.pieces(piece_type, chess.WHITE):
            score += value + pst[sq]

        for sq in board.pieces(piece_type, chess.BLACK):
            # sq ^ 56 mirrors the square vertically so the same table
            # rewards equivalent positional goals for Black.
            score -= value + pst[sq ^ 56]

    return score
