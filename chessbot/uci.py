"""UCI protocol handler for ChessBot.

Supported commands: uci, isready, ucinewgame, position, go, quit.
Unknown commands are silently ignored per the UCI specification.

Public API:
  run_uci_loop()                 – blocking stdin/stdout loop (for chess GUIs)
  handle_command(board, line)    – process a single command and return response
"""

import sys

import chess

from chessbot.engine import DEFAULT_DEPTH, get_best_move, get_best_move_timed, tt


def handle_command(board: chess.Board, line: str) -> str | None:
    """Process a single UCI command against the given board state.

    Returns the response string (which may contain newlines), or None if the
    command produces no output (or is unrecognized).

    Side effects:
        - Mutates `board` for ``position`` and ``ucinewgame`` commands.
    """
    tokens = line.strip().split()
    if not tokens:
        return None

    cmd = tokens[0]

    if cmd == "uci":
        return "id name ChessBot\nid author ChessBot\nuciok"

    if cmd == "isready":
        return "readyok"

    if cmd == "ucinewgame":
        board.reset()
        tt.clear()
        return None

    if cmd == "position":
        _handle_position(board, tokens[1:])
        return None

    if cmd == "go":
        return _handle_go(board, tokens[1:])

    if cmd == "quit":
        sys.exit(0)

    # Unknown commands are silently ignored per the UCI spec.
    return None


def _handle_position(board: chess.Board, args: list[str]) -> None:
    """Apply a ``position`` command's arguments to the board in place."""
    if not args:
        return

    # Split on the keyword "moves" to separate position spec from move list.
    # "moves" won't appear as a standalone token inside a FEN string.
    if "moves" in args:
        moves_idx = args.index("moves")
        position_args = args[:moves_idx]
        move_tokens = args[moves_idx + 1 :]
    else:
        position_args = args
        move_tokens = []

    # Set the board to the specified position.
    if position_args and position_args[0] == "startpos":
        board.reset()
    elif position_args and position_args[0] == "fen":
        fen = " ".join(position_args[1:])
        board.set_fen(fen)

    # Apply the move list.
    for uci_move in move_tokens:
        try:
            move = chess.Move.from_uci(uci_move)
            board.push(move)
        except (ValueError, chess.IllegalMoveError):
            # Stop on the first invalid move rather than silently skipping it.
            break


def _handle_go(board: chess.Board, args: list[str]) -> str:
    """Handle a ``go`` command and return the ``bestmove`` response string."""
    params: dict[str, str] = {}
    i = 0
    while i < len(args):
        if args[i] in ("wtime", "btime", "movestogo", "depth") and i + 1 < len(args):
            params[args[i]] = args[i + 1]
            i += 2
        else:
            i += 1

    if "depth" in params:
        move = get_best_move(board, depth=int(params["depth"]))
    elif "wtime" in params or "btime" in params:
        wtime_ms = int(params.get("wtime", 60_000))
        btime_ms = int(params.get("btime", 60_000))
        movestogo = int(params["movestogo"]) if "movestogo" in params else None
        move = get_best_move_timed(board, wtime_ms, btime_ms, movestogo)
    else:
        # No time or depth info — fall back to a fixed-depth search.
        move = get_best_move(board, depth=DEFAULT_DEPTH)

    return f"bestmove {move.uci()}"


def run_uci_loop() -> None:
    """Read UCI commands from stdin and write responses to stdout.

    Runs until a ``quit`` command is received or EOF is reached.
    All output is flushed immediately so chess GUIs receive responses promptly.
    """
    board = chess.Board()

    for line in sys.stdin:
        response = handle_command(board, line)
        if response is not None:
            print(response, flush=True)
