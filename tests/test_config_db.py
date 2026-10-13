import os
import unittest
import tempfile
import config_db


class TestConfigDB(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for isolation
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_guild_configs.db")
        config_db.DB_FILE = self.db_path
        config_db.init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_guild_config_crud(self):
        guild_id = "111222333"
        # Initial create
        cfg = config_db.set_guild_config(
            guild_id=guild_id,
            guild_name="Crossword Club",
            channel_id="444555",
            role_id="666777",
            schedule_time="12:00",
            enabled=1
        )
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["guild_id"], guild_id)
        self.assertEqual(cfg["channel_id"], "444555")
        self.assertEqual(cfg["schedule_time"], "12:00")

        # Fetch
        fetched = config_db.get_guild_config(guild_id)
        self.assertEqual(fetched["guild_name"], "Crossword Club")

        # Update time (should reset last_posted_date to None)
        config_db.update_last_posted_date(guild_id, "2026-10-12")
        self.assertEqual(config_db.get_guild_config(guild_id)["last_posted_date"], "2026-10-12")

        # Changing schedule_time should clear last_posted_date for testing
        config_db.set_guild_config(guild_id=guild_id, schedule_time="13:00")
        updated = config_db.get_guild_config(guild_id)
        self.assertEqual(updated["schedule_time"], "13:00")
        self.assertIsNone(updated["last_posted_date"])

    def test_day_overrides_crud(self):
        guild_id = "111222333"

        # Set overrides
        config_db.set_day_override(guild_id, "monday", "ny times", -1)
        config_db.set_day_override(guild_id, "wednesday", "la times", -4)
        config_db.set_day_override(guild_id, "saturday", "SKIP", 0)

        # Get specific day override
        mon_ov = config_db.get_day_override(guild_id, "monday")
        self.assertIsNotNone(mon_ov)
        self.assertEqual(mon_ov["search_query"], "ny times")
        self.assertEqual(mon_ov["day_offset"], -1)

        sat_ov = config_db.get_day_override(guild_id, "saturday")
        self.assertEqual(sat_ov["search_query"], "SKIP")

        # Get all overrides
        all_ovs = config_db.get_all_day_overrides(guild_id)
        self.assertEqual(len(all_ovs), 3)

        # Delete override
        deleted = config_db.delete_day_override(guild_id, "monday")
        self.assertTrue(deleted)
        self.assertIsNone(config_db.get_day_override(guild_id, "monday"))
        self.assertEqual(len(config_db.get_all_day_overrides(guild_id)), 2)

    def test_get_guilds_to_notify(self):
        guild_id = "111222333"
        config_db.set_guild_config(
            guild_id=guild_id,
            channel_id="444555",
            schedule_time="12:00",
            enabled=1
        )

        # Should be notified if not posted yet today
        to_notify = config_db.get_guilds_to_notify("12:00", "2026-10-12")
        self.assertEqual(len(to_notify), 1)
        self.assertEqual(to_notify[0]["guild_id"], guild_id)

        # After posting, should not be notified again today
        config_db.update_last_posted_date(guild_id, "2026-10-12")
        to_notify_after = config_db.get_guilds_to_notify("12:00", "2026-10-12")
        self.assertEqual(len(to_notify_after), 0)

        # But should be notified tomorrow
        to_notify_tomorrow = config_db.get_guilds_to_notify("12:00", "2026-10-13")
        self.assertEqual(len(to_notify_tomorrow), 1)


if __name__ == "__main__":
    unittest.main()
