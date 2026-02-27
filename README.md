# ChessBot

A UCI-compatible chess engine built in Python. This bot uses a custom search and evaluation algorithm, leveraging the `python-chess` library for move generation and board mechanics.

## Features

- **UCI Protocol Support**: Compatible with chess GUIs like Arena, Cute Chess, and Lichess bridges.
- **Search Algorithm**: Minimax search with Alpha-Beta pruning and move ordering (captures first).
- **Evaluation Heuristic**: Board scoring based on:
  - Material balance (Pawn=100, Knight=320, Bishop=330, Rook=500, Queen=900, King=20000).
  - Piece-Square Tables (PST) for positional advantages like center control and king safety.
- **Time Management**: Iterative deepening with time-budgeting logic to ensure moves are returned within limits.
- **Interactive CLI**: A built-in mode to play against the bot directly in the terminal.

## Installation

1.  Ensure you have Python 3.12 or later installed.
2.  Clone the repository and navigate to the `project/` directory.
3.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

### UCI Mode (Default)
Run the bot in UCI mode for use with external chess interfaces (GUIs) like Arena, Cute Chess, or Nibbler:

```bash
python main.py
```

**How UCI Works:**
The Universal Chess Interface (UCI) is a standard protocol that allows a chess engine (this bot) to communicate with a graphical interface (the GUI) via standard input and output (stdin/stdout). When running in this mode, the bot listens for text commands and responds accordingly:

- `uci`: The initial handshake. The bot identifies itself and responds with `uciok`.
- `isready`: Used to synchronize the GUI and the engine. The bot responds with `readyok` once initialized.
- `ucinewgame`: Informs the engine that a new game is starting so it can reset internal state.
- `position [startpos | fen <FEN>] moves <moves>`: Updates the engine's internal board state.
- `go [wtime <ms> btime <ms> | depth <n>]`: Triggers the search. The engine analyzes the position and eventually outputs its choice: `bestmove <move>`.
- `quit`: Gracefully terminates the engine process.

### Interactive CLI Mode
Play against the bot manually in your terminal:

```bash
python main.py --cli
```

### Running Tests
Run the test suite using `pytest`:

```bash
pytest
```

## GUI and External Testing

While the bot includes a CLI, it is designed to be used with more powerful external tools for a better visual experience and rigorous testing:

### Lichess (Web UI)
You can play against your bot in a web browser by connecting it to Lichess using the [lichess-bot](https://github.com/lichess-bot-devs/lichess-bot) bridge.
1. Create a "Bot Account" on Lichess.
2. Configure `lichess-bot` to point to `python main.py` in this directory.
3. Your bot will appear online and can accept challenges from anyone.

### Cute Chess (Engine Testing)
[Cute Chess](https://cutechess.com/) is the industry standard for automated engine-to-engine testing. Use it to:
- Run 100s of matches against other engines (like Stockfish at low levels).
- Calculate the Elo difference between different versions of your own bot.
- Verify that changes to your evaluation function actually improve performance.

## Project Structure

- `chessbot/`
  - `evaluation.py`: Heuristic scoring functions.
  - `engine.py`: Search algorithm and time management.
  - `uci.py`: UCI protocol communication loop.
  - `cli.py`: Interactive command-line interface.
- `tests/`: Comprehensive test suite for search, evaluation, and protocol handling.
- `main.py`: Main entry point.
- `requirements.txt`: Project dependencies (`python-chess`, `pytest`).
