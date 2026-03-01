"""Interactive CLI for playing against ChessBot.

Usage:
    python main.py --cli

The human enters moves in UCI notation (e2e4) or standard algebraic notation
(e4, Nf3, O-O).  The engine responds using iterative-deepening time search.
"""

import chess

from chessbot.engine import get_best_move, get_best_move_timed

# Generous dummy clock (ms) used when calling the timed search from the CLI.
_DUMMY_TIME_MS = 5_000


def _parse_move(board: chess.Board, text: str) -> chess.Move | None:
    """Return a legal chess.Move parsed from *text*, or None if invalid.

    Accepts UCI notation (e2e4, e7e8q) first; falls back to SAN (e4, Nf3).
    """
    text = text.strip()
    # Try UCI notation.
    try:
        move = chess.Move.from_uci(text)
        if move in board.legal_moves:
            return move
    except ValueError:
        pass
    # Fall back to SAN / algebraic notation.
    try:
        return board.parse_san(text)
    except ValueError:
        return None


def _print_board(board: chess.Board) -> None:
    """Print the board with rank/file labels."""
    print()
    print(str(board))
    print()


def _game_result_message(board: chess.Board) -> str:
    """Return a human-readable game-over string."""
    outcome = board.outcome()
    if outcome is None:
        return "Game over."
    if outcome.winner == chess.WHITE:
        return "White wins by checkmate!"
    if outcome.winner == chess.BLACK:
        return "Black wins by checkmate!"
    # Draw — include the specific termination reason.
    reason = outcome.termination.name.replace("_", " ").lower()
    return f"Draw by {reason}."


def run_cli() -> None:
    """Run an interactive chess game against the engine."""
    print("=== ChessBot CLI ===")
    print("Enter moves in UCI (e2e4) or algebraic (e4, Nf3) notation.")
    print("Press Ctrl+C to quit.\n")

    # --- Choose sides ---
    human_color: chess.Color | None = None
    while human_color is None:
        choice = input("Play as [W]hite or [B]lack? ").strip().lower()
        if choice in ("w", "white"):
            human_color = chess.WHITE
        elif choice in ("b", "black"):
            human_color = chess.BLACK
        else:
            print("Please enter 'W' or 'B'.")

    engine_color = not human_color
    print(
        f"\nYou are {'White' if human_color == chess.WHITE else 'Black'}. "
        f"Engine plays {'White' if engine_color == chess.WHITE else 'Black'}.\n"
    )

    board = chess.Board()

    try:
        while not board.is_game_over():
            _print_board(board)

            if board.turn == engine_color:
                # --- Engine's turn ---
                print("Engine is thinking…")
                try:
                    move = get_best_move_timed(
                        board,
                        wtime_ms=_DUMMY_TIME_MS,
                        btime_ms=_DUMMY_TIME_MS,
                    )
                except ValueError:
                    # No legal moves — game is already over.
                    break
                board.push(move)
                print(f"Engine plays: {move.uci()}")
            else:
                # --- Human's turn ---
                while True:
                    raw = input("Your move: ").strip()
                    if not raw:
                        continue
                    move = _parse_move(board, raw)
                    if move is not None:
                        board.push(move)
                        break
                    print(f"  Illegal move: '{raw}'. Try again.")

        # --- Game over ---
        _print_board(board)
        print(_game_result_message(board))

    except KeyboardInterrupt:
        print("\nGoodbye!")
