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

## How the Bot Thinks

At its core, ChessBot finds the best move by looking into the future and evaluating potential board positions. It does this using a combination of classic chess engine techniques, designed to play a strong and logical game. Here’s a step-by-step breakdown of its thought process, aimed at chess players rather than programmers.

### 1. The Search Tree: Looking Ahead

The bot doesn't just look at the next move; it explores a vast "tree" of possibilities. It starts with the current position and looks at all of its legal moves. For each of those moves, it considers all of the opponent's possible replies, and for each of those replies, it looks at its own next set of moves, and so on. This process of going deeper and deeper into move sequences is called **search**. The number of half-moves the bot looks ahead is called the **search depth**.

### 2. The Evaluation Function: "Is this position good for me?"

The bot can't search forever. When it reaches its maximum search depth, it needs a way to judge how good the resulting board position is. This is the job of the **evaluation function**. The bot's evaluation is based on two key factors:

*   **Material:** This is the most important factor. The bot counts the pieces on the board for both sides and assigns them their standard values (e.g., a Rook is worth 5 pawns, a Queen is worth 9, etc.). Having more material than the opponent results in a higher score.
*   **Piece-Square Tables (Positional Play):** The bot also understands that some squares are better for a piece than others. It uses **Piece-Square Tables**, which are essentially built-in charts that give bonuses or penalties to pieces based on their location. For example:
    *   A knight in the center of the board gets a bonus because it controls many squares.
    *   A pawn that has advanced to the 6th or 7th rank gets a large bonus because it's close to promoting.
    *   The king gets a bonus for being safely tucked in the corner after castling.

The evaluation function combines the material and positional scores into a single number that represents who is winning and by how much.

### 3. Minimax: Assuming the Opponent is Smart

The search and evaluation work together through an algorithm called **Minimax**. It's based on a simple but powerful principle: *assume your opponent will always make the best possible move for them*.

As the bot searches deeper into the move tree, it uses the evaluation function at the "leaves" of the tree. Then, it works its way backward, applying the minimax logic:

*   On a turn where it's the **bot's move**, it will choose the move that leads to the **highest** possible score.
*   On a turn where it's the **opponent's move**, it assumes the opponent will choose the move that leads to the **lowest** possible score (from the bot's perspective).

By doing this, the bot chooses the path that guarantees the best possible outcome for itself, even if the opponent plays perfectly.

### 4. Alpha-Beta Pruning: A Clever Shortcut

Searching every single possible move sequence would take far too long. To speed things up, the bot uses a technique called **alpha-beta pruning**.

Imagine the bot is analyzing one of its moves and sees that it leads to a good position. Then, it starts analyzing a *different* move. If it quickly sees that this second move can be forced into a worse outcome by the opponent, the bot doesn't need to analyze it any further. It "prunes" that entire branch of the search tree and moves on. This allows the bot to search much deeper in the same amount of time.

By combining these techniques, ChessBot can play a competent game of chess, balancing material, positional advantages, and tactical awareness to find the best move.
