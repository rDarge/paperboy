import unittest
from datetime import datetime
from bot import match_puzzle_by_date, build_api_url


class TestPuzzleMatching(unittest.TestCase):
    def setUp(self):
        self.sample_puzzles = [
            {
                "pid": "1001",
                "content": {
                    "info": {
                        "title": "NY Times, Monday, October 12, 2026",
                        "type": "Daily Puzzle",
                        "author": "Test Author / Will Shortz"
                    }
                }
            },
            {
                "pid": "1002",
                "content": {
                    "info": {
                        "title": "NY Times, Sunday, October 11, 2026 Heart Transplants",
                        "type": "Daily Puzzle",
                        "author": "Sunday Author"
                    }
                }
            },
            {
                "pid": "1003",
                "content": {
                    "info": {
                        "title": "L. A. Times, Sun, Oct 11, 2026 - RECIPE FOR DISASTER",
                        "type": "Daily Puzzle",
                        "author": "LA Author"
                    }
                }
            },
            {
                "pid": "1004",
                "content": {
                    "info": {
                        "title": "NY Times Mini: Monday, October 12, 2026",
                        "type": "Mini",
                        "author": "Joel Fagliano"
                    }
                }
            },
            {
                "pid": "1005",
                "content": {
                    "info": {
                        "title": "NY Times Midi: Monday, October 12, 2026",
                        "type": "Midi",
                        "author": "Midi Author"
                    }
                }
            }
        ]

    def test_match_standard_weekday_nyt(self):
        target = datetime(2026, 10, 12).date()
        matched = match_puzzle_by_date(self.sample_puzzles, "ny times", target)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["pid"], "1001")

    def test_match_sunday_large_nyt(self):
        # Sunday Oct 11, 2026
        target = datetime(2026, 10, 11).date()
        matched = match_puzzle_by_date(self.sample_puzzles, "ny times", target)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["pid"], "1002")
        self.assertIn("Sunday, October 11, 2026", matched["content"]["info"]["title"])

    def test_match_la_times(self):
        target = datetime(2026, 10, 11).date()
        matched = match_puzzle_by_date(self.sample_puzzles, "la times", target)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["pid"], "1003")

    def test_mini_and_midi_are_excluded(self):
        # Even if Mini/Midi matches the date, it should never be chosen as the regular crossword
        mini_only_list = [self.sample_puzzles[3], self.sample_puzzles[4]]
        target = datetime(2026, 10, 12).date()
        matched = match_puzzle_by_date(mini_only_list, "ny times", target)
        self.assertIsNone(matched)

    def test_no_blind_fallback_when_date_missing(self):
        # Requesting a date not present in sample_puzzles (e.g. October 10)
        # Should return None, NOT silently return Monday's or Sunday's puzzle
        target = datetime(2026, 10, 10).date()
        matched = match_puzzle_by_date(self.sample_puzzles, "ny times", target)
        self.assertIsNone(matched)

    def test_build_api_url_includes_large_and_standard(self):
        url = build_api_url("NY Times")
        self.assertIn("filter%5BsizeFilter%5D%5BLarge%5D=true", url)
        self.assertIn("filter%5BsizeFilter%5D%5BStandard%5D=true", url)
        self.assertIn("filter%5BsizeFilter%5D%5BMini%5D=false", url)
        self.assertIn("filter%5BsizeFilter%5D%5BMidi%5D=false", url)


if __name__ == "__main__":
    unittest.main()
