"""Tests for chessbot/lichess.py.

Focuses on the first-move abort timeout logic and the _abort_game helper.
Uses mock HTTP responses to simulate the Lichess game stream.
"""

import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

import chessbot.lichess as lichess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _game_full_event(bot_color: str, bot_id: str = "testbot", moves: str = "") -> str:
    """Build a gameFull JSON line. bot_color is 'white' or 'black'."""
    white_id = bot_id if bot_color == "white" else "opponent"
    black_id = bot_id if bot_color == "black" else "opponent"
    event = {
        "type": "gameFull",
        "initialFen": "startpos",
        "white": {"id": white_id, "name": white_id.title()},
        "black": {"id": black_id, "name": black_id.title()},
        "state": {"moves": moves, "wtime": 180000, "btime": 180000},
    }
    return json.dumps(event)


def _game_state_event(moves: str, wtime: int = 180000, btime: int = 180000) -> str:
    """Build a gameState JSON line."""
    return json.dumps({
        "type": "gameState",
        "moves": moves,
        "wtime": wtime,
        "btime": btime,
    })


def _game_over_event() -> str:
    return json.dumps({"type": "gameOver"})


class FakeStreamResponse:
    """Simulates an httpx streaming response that yields lines on demand."""

    def __init__(self, lines: list[str], hang_after: int | None = None):
        """
        lines: JSON lines to yield.
        hang_after: if set, after yielding this many lines, the iterator
                    will block forever (simulating opponent not moving).
        """
        self._lines = lines
        self._hang_after = hang_after

    def raise_for_status(self):
        pass

    async def aiter_lines(self):
        for i, line in enumerate(self._lines):
            yield line
            if self._hang_after is not None and i + 1 >= self._hang_after:
                # Block forever after yielding hang_after lines — the test
                # relies on asyncio.wait_for to break out via TimeoutError.
                await asyncio.Event().wait()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# 1. _abort_game calls the correct endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_abort_game_calls_api():
    """_abort_game should POST to /api/bot/game/{id}/abort."""
    client = AsyncMock()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    client.post.return_value = mock_response

    await lichess._abort_game(client, "tok", "game123")

    client.post.assert_called_once()
    call_url = client.post.call_args[0][0]
    assert call_url == "https://lichess.org/api/bot/game/game123/abort"


# ---------------------------------------------------------------------------
# 2. Bot is black, opponent (white) never moves → game aborted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_abort_when_opponent_never_moves():
    """When bot is black and white never plays, the game should be aborted."""
    game_full = _game_full_event("black")

    # gameFull is yielded, then the stream hangs (opponent never moves).
    fake_resp = FakeStreamResponse([game_full], hang_after=1)

    client = AsyncMock()
    client.stream = MagicMock(return_value=fake_resp)
    # Mock abort so we can verify it was called.
    client.post = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))

    # Use a very short timeout so the test runs fast.
    original_timeout = lichess._FIRST_MOVE_TIMEOUT
    lichess._FIRST_MOVE_TIMEOUT = 0.1
    lichess._active_games.clear()
    try:
        await lichess._handle_game_start(client, "tok", "testbot", "game1")
    finally:
        lichess._FIRST_MOVE_TIMEOUT = original_timeout

    # Verify abort was called.
    abort_calls = [
        c for c in client.post.call_args_list
        if "abort" in str(c)
    ]
    assert len(abort_calls) == 1
    assert "game1" in str(abort_calls[0])


# ---------------------------------------------------------------------------
# 3. Bot is black, opponent moves in time → no abort
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_abort_when_opponent_moves():
    """When opponent plays their first move, no abort should happen."""
    game_full = _game_full_event("black")
    game_state = _game_state_event("e2e4")
    game_over = _game_over_event()

    fake_resp = FakeStreamResponse([game_full, game_state, game_over])

    client = AsyncMock()
    client.stream = MagicMock(return_value=fake_resp)
    # Mock both post (for potential move sending) and track abort calls.
    post_mock = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))
    client.post = post_mock

    lichess._active_games.clear()

    # Patch the engine so the bot doesn't actually think.
    with patch("chessbot.lichess.get_best_move_timed") as mock_engine:
        import chess
        mock_engine.return_value = chess.Move.from_uci("e7e5")
        await lichess._handle_game_start(client, "tok", "testbot", "game2")

    # Verify abort was NOT called.
    abort_calls = [c for c in post_mock.call_args_list if "abort" in str(c)]
    assert len(abort_calls) == 0


# ---------------------------------------------------------------------------
# 4. Bot is white → no abort timeout (it's our turn first)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_abort_timeout_when_bot_is_white():
    """When bot is white (moves first), there should be no first-move timeout."""
    game_full = _game_full_event("white")
    game_over = _game_over_event()

    fake_resp = FakeStreamResponse([game_full, game_over])

    client = AsyncMock()
    client.stream = MagicMock(return_value=fake_resp)
    post_mock = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))
    client.post = post_mock

    lichess._active_games.clear()

    with patch("chessbot.lichess.get_best_move_timed") as mock_engine:
        import chess
        mock_engine.return_value = chess.Move.from_uci("e2e4")
        await lichess._handle_game_start(client, "tok", "testbot", "game3")

    abort_calls = [c for c in post_mock.call_args_list if "abort" in str(c)]
    assert len(abort_calls) == 0
