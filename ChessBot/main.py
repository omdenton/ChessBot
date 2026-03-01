"""ChessBot entry point.

Usage:
    python main.py         # Run UCI loop (default, for use with chess GUIs)
    python main.py --cli   # Run interactive CLI for manual testing
    python main.py --lichess # Run the Lichess bot
"""

import sys
import asyncio # Import asyncio

def main() -> None:
    if "--cli" in sys.argv:
        from chessbot.cli import run_cli
        run_cli()
    elif "--lichess" in sys.argv: # New condition for Lichess bot
        from chessbot.lichess import main as run_lichess_main # Import lichess main
        run_lichess_main()
    else:
        from chessbot.uci import run_uci_loop
        run_uci_loop()


if __name__ == "__main__":
    main()
