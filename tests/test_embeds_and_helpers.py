import unittest
from datetime import datetime
from bot import (
    normalize_time,
    resolve_role_mention,
    create_puzzle_embed,
    create_not_found_embed,
    build_api_url
)


class TestEmbedsAndHelpers(unittest.TestCase):
    def test_normalize_time(self):
        self.assertEqual(normalize_time("12:00"), "12:00")
        self.assertEqual(normalize_time("12:00 PM"), "12:00")
        self.assertEqual(normalize_time("12:00 AM"), "00:00")
        self.assertEqual(normalize_time("9:30 AM"), "09:30")
        self.assertEqual(normalize_time("2:15 PM"), "14:15")
        self.assertEqual(normalize_time("14:30"), "14:30")
        self.assertIsNone(normalize_time("not-a-time"))

    def test_resolve_role_mention(self):
        # Numeric role ID
        self.assertEqual(resolve_role_mention(None, "123456789"), "<@&123456789>")
        # Role formatted tag
        self.assertEqual(resolve_role_mention(None, "<@&123456789>"), "<@&123456789>")
        # Default / plain text
        self.assertEqual(resolve_role_mention(None, "CROSSWORD"), "@CROSSWORD")
        self.assertEqual(resolve_role_mention(None, None), "@CROSSWORD")

    def test_create_puzzle_embed(self):
        sample_puzzle = {
            "pid": "1001",
            "content": {
                "info": {
                    "title": "NY Times, Monday, October 12, 2026",
                    "author": "Sample Author"
                }
            },
            "stats": {
                "numSolves": 120,
                "ratingAverage": 4.5
            }
        }
        play_url = "https://www.crosswithfriends.com/beta/game/1001-abcd"
        target_date = datetime(2026, 10, 12).date()

        embed = create_puzzle_embed(
            sample_puzzle,
            search_query="NY Times",
            target_date=target_date,
            play_url=play_url
        )

        self.assertEqual(embed.url, play_url)
        self.assertIn("NY Times, Monday, October 12, 2026", embed.title)
        field_names = [f.name for f in embed.fields]
        self.assertIn("✍️ Author / Editor", field_names)
        self.assertIn("🎮 Multiplayer Room Link", field_names)
        self.assertIn("📅 Target Puzzle Date", field_names)

    def test_create_not_found_embed(self):
        target_date = datetime(2026, 10, 11).date()
        embed = create_not_found_embed("NY Times", target_date)

        self.assertIn("Crossword Not Found", embed.title)
        self.assertIn("Sunday, October 11, 2026", embed.description)
        field_dict = {f.name: f.value for f in embed.fields}
        self.assertIn("🔎 Search Query", field_dict)
        self.assertIn("📅 Target Date", field_dict)
        self.assertIn("🔗 Search Links", field_dict)
        self.assertIn("https://www.crosswithfriends.com/", field_dict["🔗 Search Links"])


if __name__ == "__main__":
    unittest.main()
