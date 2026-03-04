"""One-shot script: abort or resign all ongoing games for the Lichess bot.

Usage:
    LICHESS_API_TOKEN=xxx python abort_games.py
    # or place token in ../.env as LICHESS_API_TOKEN=xxx
"""

import asyncio
import json
import os
import sys

import httpx

BASE = "https://lichess.org"


def _load_token() -> str:
    token = os.environ.get("LICHESS_API_TOKEN", "")
    if not token:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        try:
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("LICHESS_API_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except FileNotFoundError:
            pass
    if not token:
        print("LICHESS_API_TOKEN not set. Set env var or add to .env")
        sys.exit(1)
    return token


async def get_ongoing_games(client: httpx.AsyncClient, token: str) -> list[dict]:
    """Return list of ongoing game dicts via /api/account/playing."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get(f"{BASE}/api/account/playing", headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data.get("nowPlaying", [])


async def abort_game(client: httpx.AsyncClient, token: str, game_id: str) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(f"{BASE}/api/bot/game/{game_id}/abort", headers=headers)
    return resp.status_code == 200


async def resign_game(client: httpx.AsyncClient, token: str, game_id: str) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(f"{BASE}/api/bot/game/{game_id}/resign", headers=headers)
    return resp.status_code == 200


async def main() -> None:
    token = _load_token()
    async with httpx.AsyncClient(timeout=30) as client:
        games = await get_ongoing_games(client, token)
        if not games:
            print("No ongoing games found.")
            return
        print(f"Found {len(games)} ongoing game(s).")
        for g in games:
            game_id = g.get("gameId") or g.get("id", "?")
            moves = g.get("moves", "")
            move_count = len(moves.split()) if moves else 0
            print(f"  Game {game_id} ({move_count} moves played) — ", end="")
            # Abort only works in the first couple of moves; resign otherwise.
            if move_count <= 2:
                ok = await abort_game(client, token, game_id)
                if ok:
                    print("aborted.")
                else:
                    ok = await resign_game(client, token, game_id)
                    print("resigned." if ok else "FAILED to abort/resign.")
            else:
                ok = await resign_game(client, token, game_id)
                print("resigned." if ok else "FAILED to resign.")


if __name__ == "__main__":
    asyncio.run(main())
