import unittest
import asyncio
from datetime import datetime, timedelta
from bot import fetch_puzzle_by_criteria, create_shared_game_room, ET_TZ


class TestAPIIntegration(unittest.TestCase):
    """Live integration tests against crosswithfriends.com API."""

    def test_live_fetch_nyt_puzzle(self):
        async def run_fetch():
            now_et = datetime.now(ET_TZ).date()
            # Fetch today's puzzle
            puzzle = await fetch_puzzle_by_criteria("NY Times", now_et)
            return puzzle

        puzzle = asyncio.run(run_fetch())
        self.assertIsNotNone(puzzle, "Should fetch today's NY Times puzzle from API")
        title = puzzle.get("content", {}).get("info", {}).get("title", "")
        self.assertIn("NY Times", title)

    def test_live_create_shared_game_room(self):
        async def run_room_creation():
            # Test game room creation for a known puzzle ID
            url = await create_shared_game_room("100013620")
            return url

        url = asyncio.run(run_room_creation())
        self.assertIsNotNone(url)
        self.assertTrue(
            url.startswith("https://www.crosswithfriends.com/beta/game/"),
            f"Expected game room URL but got: {url}"
        )


if __name__ == "__main__":
    unittest.main()
