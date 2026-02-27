"""ChessBot entry point.

Usage:
    python main.py         # Run UCI loop (default, for use with chess GUIs)
    python main.py --cli   # Run interactive CLI for manual testing
"""

import sys


def main() -> None:
    if "--cli" in sys.argv:
        from chessbot.cli import run_cli
        run_cli()
    else:
        from chessbot.uci import run_uci_loop
        run_uci_loop()


if __name__ == "__main__":
    main()
