import os
import json
import random
import time
import httpx
import chess
import asyncio

from chessbot.engine import get_best_move_timed

LICHESS_API_BASE_URL = "https://lichess.org"

# Track active games so the auto-challenge loop waits while playing.
_active_games: set[str] = set()

# How long to wait for the opponent's first move before aborting (seconds).
_FIRST_MOVE_TIMEOUT = 90

async def _get_lichess_token() -> str:
    """Retrieves the Lichess API token from environment variables."""
    token = os.environ.get("LICHESS_API_TOKEN")
    if not token:
        print("LICHESS_API_TOKEN environment variable not set.")
        print("Please set it to your Lichess bot's API token.")
        # In a real bot, you might want to exit or raise an error here.
        # For now, we'll just return an empty string and let downstream
        # errors occur to highlight the missing token.
    return token

async def _get_bot_id(client: httpx.AsyncClient, token: str) -> str | None:
    """Fetches the bot's user ID from the Lichess API."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = await client.get(f"{LICHESS_API_BASE_URL}/api/account", headers=headers)
        response.raise_for_status()
        account_info = response.json()
        bot_id = account_info["id"]
        print(f"Bot ID: {bot_id}")
        return bot_id
    except httpx.HTTPStatusError as e:
        print(f"HTTP error fetching bot ID: {e}")
        print(f"Response: {e.response.text}")
    except httpx.RequestError as e:
        print(f"Request error fetching bot ID: {e}")
    return None

async def _handle_challenge(client: httpx.AsyncClient, token: str, bot_id: str, challenge: dict, compat: dict):
    """Handles an incoming challenge event."""
    challenge_id = challenge["id"]
    challenger_name = challenge["challenger"]["name"]
    print(f"Received challenge from {challenger_name} (ID: {challenge_id})")

    # Check for bot compatibility (compat is a sibling of challenge in the event, not nested inside it)
    if not compat.get("bot", False):
        print(f"Declining challenge {challenge_id} because it is not bot-compatible.")
        try:
            decline_url = f"{LICHESS_API_BASE_URL}/api/challenge/{challenge_id}/decline"
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.post(decline_url, headers=headers, json={"reason": "bot incompatible"})
            response.raise_for_status()
            print(f"Declined challenge {challenge_id}.")
        except httpx.HTTPStatusError as e:
            print(f"Failed to decline challenge {challenge_id}: {e}")
            print(f"Response: {e.response.text}")
        except httpx.RequestError as e:
            print(f"Request error declining challenge {challenge_id}: {e}")
        return

    # Accept the challenge if it's compatible
    try:
        accept_url = f"{LICHESS_API_BASE_URL}/api/challenge/{challenge_id}/accept"
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(accept_url, headers=headers)
        response.raise_for_status()
        print(f"Accepted challenge {challenge_id}.")
    except httpx.HTTPStatusError as e:
        print(f"Failed to accept challenge {challenge_id}: {e}")
        print(f"Response: {e.response.text}")
    except httpx.RequestError as e:
        print(f"Request error accepting challenge {challenge_id}: {e}")

async def _abort_game(client: httpx.AsyncClient, token: str, game_id: str):
    """Aborts a game via the Lichess API."""
    url = f"{LICHESS_API_BASE_URL}/api/bot/game/{game_id}/abort"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = await client.post(url, headers=headers)
        response.raise_for_status()
        print(f"[{game_id}] Game aborted.")
    except httpx.HTTPStatusError as e:
        print(f"[{game_id}] Failed to abort game: {e}")
        try:
            await e.response.aread()
            print(f"[{game_id}] Response: {e.response.text}")
        except Exception:
            pass
    except httpx.RequestError as e:
        print(f"[{game_id}] Request error aborting game: {e}")

async def _send_move(client: httpx.AsyncClient, token: str, game_id: str, move_uci: str):
    """Sends a move to Lichess."""
    move_url = f"{LICHESS_API_BASE_URL}/api/bot/game/{game_id}/move/{move_uci}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = await client.post(move_url, headers=headers)
        response.raise_for_status()
        print(f"[{game_id}] Sent move: {move_uci}")
    except httpx.HTTPStatusError as e:
        print(f"[{game_id}] Failed to send move {move_uci}: {e}")
        print(f"[{game_id}] Response: {e.response.text}")
    except httpx.RequestError as e:
        print(f"[{game_id}] Request error sending move {move_uci}: {e}")

async def _handle_game_start(client: httpx.AsyncClient, token: str, bot_id: str, game_id: str):
    """Handles a game start event, initiating the game loop."""
    _active_games.add(game_id)
    await asyncio.sleep(2)  # Add a small delay to avoid race conditions
    print(f"Game started! ID: {game_id}. Connecting to game stream...")

    board = chess.Board()
    my_color: chess.Color | None = None
    white_time_ms: int = 0
    black_time_ms: int = 0
    moves_played = [] # To keep track of moves and apply them to the board

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{LICHESS_API_BASE_URL}/api/bot/game/stream/{game_id}"

    # Wall-clock deadline for the opponent's first move.  Set to a real
    # timestamp once we know we're waiting (bot is black, no moves yet).
    # Lichess sends empty keep-alive lines every ~15s, so we can't rely on
    # asyncio.wait_for — instead we check elapsed time on every iteration.
    first_move_deadline: float | None = None

    try:
        async with client.stream("GET", url, headers=headers, timeout=None) as response:
            response.raise_for_status()
            print(f"Connected to game stream for game {game_id}. Waiting for events...")
            async for line in response.aiter_lines():
                # Check the first-move deadline before processing each line
                # (including keep-alive blanks).
                if first_move_deadline is not None and time.monotonic() >= first_move_deadline:
                    print(f"[{game_id}] Opponent hasn't moved in {_FIRST_MOVE_TIMEOUT}s — aborting game.")
                    await _abort_game(client, token, game_id)
                    break

                if not line.strip():
                    continue

                try:
                    game_event = json.loads(line)
                    print(f"Received game event for {game_id}: {json.dumps(game_event, indent=2)}")

                    event_type = game_event.get("type")

                    if event_type == "gameFull":
                        initial_fen = game_event.get("initialFen", "startpos")
                        if initial_fen == "startpos":
                            board.reset()
                        else:
                            board.set_fen(initial_fen)

                        # Determine bot's color
                        if game_event["white"].get("id") == bot_id:
                            my_color = chess.WHITE
                        elif game_event["black"].get("id") == bot_id:
                            my_color = chess.BLACK
                        else:
                            print(f"[{game_id}] Could not determine bot's color from gameFull data. This should not happen.")
                            return

                        state = game_event["state"]
                        white_time_ms = state["wtime"]
                        black_time_ms = state["btime"]
                        moves_played = state["moves"].split() if state["moves"] else []

                        # Apply initial moves
                        for uci_move in moves_played:
                            board.push_uci(uci_move)

                        print(f"[{game_id}] Initialized game. Bot plays as {'White' if my_color == chess.WHITE else 'Black'}.")
                        print(f"[{game_id}] Current FEN: {board.fen()}")

                        # After initialization, if it's our turn, make a move
                        if not board.is_game_over() and board.turn == my_color:
                            print(f"[{game_id}] It's our turn after gameFull! Bot is thinking...")
                            try:
                                loop = asyncio.get_running_loop()
                                move = await loop.run_in_executor(None, get_best_move_timed, board, white_time_ms, black_time_ms)
                                print(f"[{game_id}] Bot calculated move: {move.uci()}")
                                await _send_move(client, token, game_id, move.uci())
                            except ValueError as e:
                                print(f"[{game_id}] Error calculating move: {e}")
                        elif not board.is_game_over() and not moves_played:
                            # No moves yet and it's not our turn — opponent
                            # is white and hasn't played their first move.
                            first_move_deadline = time.monotonic() + _FIRST_MOVE_TIMEOUT
                            print(f"[{game_id}] Waiting for opponent's first move (timeout: {_FIRST_MOVE_TIMEOUT}s)...")

                    elif event_type == "gameState":
                        # Opponent moved — cancel the first-move deadline.
                        first_move_deadline = None

                        # Update times
                        white_time_ms = game_event["wtime"]
                        black_time_ms = game_event["btime"]

                        # Apply new moves
                        # The 'moves' string contains all moves played so far, separated by spaces.
                        # We need to find the new moves since our last update.
                        all_moves = game_event["moves"].split() if game_event["moves"] else []
                        new_moves_count = len(all_moves) - len(moves_played)

                        if new_moves_count > 0:
                            for uci_move in all_moves[-new_moves_count:]:
                                try:
                                    board.push_uci(uci_move)
                                    moves_played.append(uci_move) # Keep track of moves played
                                except ValueError:
                                    print(f"[{game_id}] Invalid move received from Lichess: {uci_move}")
                                    break # Stop processing if we get an invalid move

                        print(f"[{game_id}] Board updated. Current FEN: {board.fen()}")
                        print(f"[{game_id}] White time: {white_time_ms}ms, Black time: {black_time_ms}ms")

                        # --- Game over check after opponent's move ---
                        if board.is_game_over():
                            print(f"[{game_id}] Game over according to local board state.")
                            outcome = board.outcome()
                            if outcome:
                                print(f"[{game_id}] Result: {outcome.result()}")
                                if outcome.termination:
                                    print(f"[{game_id}] Termination: {outcome.termination.name}")
                            break # Exit the game stream loop

                        # Check if it's our turn
                        if board.turn == my_color: # Removed 'not board.is_game_over()' as it's checked above
                            print(f"[{game_id}] It's our turn! Bot is thinking...")
                            try:
                                # Calculate move in a separate thread to avoid blocking
                                loop = asyncio.get_running_loop()
                                move = await loop.run_in_executor(None, get_best_move_timed, board, white_time_ms, black_time_ms)
                                print(f"[{game_id}] Bot calculated move: {move.uci()}")
                                # Send move
                                await _send_move(client, token, game_id, move.uci())
                            except ValueError as e:
                                print(f"[{game_id}] Error calculating move: {e}")

                    elif event_type == "chatLine":
                        # Optional: log chat
                        print(f"[{game_id}] Chat from {game_event.get('username', '?')}: {game_event.get('text', '')}")

                    elif event_type in ["gameOver", "close"]:
                        print(f"[{game_id}] Game over event received.")
                        break # Exit the game stream loop

                except json.JSONDecodeError:
                    print(f"[{game_id}] Could not decode JSON: {line}")
    except httpx.HTTPStatusError as e:
        print(f"[{game_id}] HTTP error connecting to game stream: {e}")
        try:
            await e.response.aread()
            print(f"[{game_id}] Response: {e.response.text}")
        except Exception:
            pass
    except httpx.RequestError as e:
        print(f"[{game_id}] Request error connecting to game stream: {e}")
    finally:
        _active_games.discard(game_id)
        print(f"[{game_id}] Game removed from active games.")

async def _stream_events(client: httpx.AsyncClient, token: str, bot_id: str):
    """Connects to the Lichess event stream and processes events."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{LICHESS_API_BASE_URL}/api/stream/event"

    print(f"Connecting to Lichess event stream: {url}")
    try:
        async with client.stream("GET", url, headers=headers, timeout=None) as response:
            response.raise_for_status()
            print("Connected to event stream. Waiting for events...")
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        event = json.loads(line)
                        print(f"Received event: {json.dumps(event, indent=2)}")

                        event_type = event.get("type")
                        if event_type == "challenge":
                            # Schedule challenge handling as a separate task
                            compat = event.get("compat", {})
                            asyncio.create_task(_handle_challenge(client, token, bot_id, event["challenge"], compat))
                        elif event_type == "gameStart":
                            game = event["game"]
                            if not game.get("compat", {}).get("bot", False):
                                print(f"Skipping non-bot-compatible game {game['gameId']}")
                                continue
                            # Schedule game handling as a separate task
                            asyncio.create_task(_handle_game_start(client, token, bot_id, game["gameId"]))
                        # else:
                        #     print(f"Unhandled event type: {event_type}")

                    except json.JSONDecodeError:
                        print(f"Could not decode JSON: {line}")
    except httpx.HTTPStatusError as e:
        print(f"HTTP error connecting to event stream: {e}")
        try:
            await e.response.aread()
            print(f"Response: {e.response.text}")
        except Exception:
            pass
    except httpx.RequestError as e:
        print(f"Request error connecting to event stream: {e}")

async def _get_online_bots(client: httpx.AsyncClient, token: str, bot_id: str) -> list[str]:
    """Fetch a list of online bot usernames (excluding ourselves)."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/x-ndjson"}
    bots: list[str] = []
    try:
        async with client.stream("GET", f"{LICHESS_API_BASE_URL}/api/bot/online", headers=headers, timeout=30) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        username = data.get("username", "")
                        if username.lower() != bot_id:
                            bots.append(username)
                    except json.JSONDecodeError:
                        pass
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        print(f"[auto-challenge] Error fetching online bots: {e}")
    return bots


async def _auto_challenge_loop(client: httpx.AsyncClient, token: str, bot_id: str):
    """Continuously challenge online bots when not already playing."""
    headers = {"Authorization": f"Bearer {token}"}
    # Wait a bit on startup for the event stream to connect first.
    await asyncio.sleep(5)
    print("[auto-challenge] Auto-challenge loop started.")

    while True:
        if _active_games:
            await asyncio.sleep(10)
            continue

        bots = await _get_online_bots(client, token, bot_id)
        if not bots:
            print("[auto-challenge] No online bots found. Waiting 30s...")
            await asyncio.sleep(30)
            continue

        target = random.choice(bots)
        print(f"[auto-challenge] Challenging {target} (rated blitz 3+2)...")

        try:
            response = await client.post(
                f"{LICHESS_API_BASE_URL}/api/challenge/{target}",
                headers=headers,
                data={
                    "rated": "true",
                    "clock.limit": "180",
                    "clock.increment": "2",
                    "color": "random",
                },
            )
            if response.status_code == 429:
                print("[auto-challenge] Rate limited. Waiting 60s...")
                await asyncio.sleep(60)
                continue
            response.raise_for_status()
            print(f"[auto-challenge] Challenge sent to {target}.")
        except httpx.HTTPStatusError as e:
            print(f"[auto-challenge] Challenge to {target} failed: {e.response.status_code} {e.response.text}")
        except httpx.RequestError as e:
            print(f"[auto-challenge] Request error challenging {target}: {e}")

        await asyncio.sleep(30)


async def run_lichess_bot():
    """Main function to run the Lichess bot."""
    token = await _get_lichess_token()
    if not token:
        return

    # Using httpx.AsyncClient for persistent connection and better performance.
    async with httpx.AsyncClient() as client:
        bot_id = await _get_bot_id(client, token)
        if not bot_id:
            print("Failed to get bot ID. Exiting.")
            return
        await asyncio.gather(
            _stream_events(client, token, bot_id),
            _auto_challenge_loop(client, token, bot_id),
        )

def main():
    """Synchronous entry point for the Lichess bot."""
    asyncio.run(run_lichess_bot())
