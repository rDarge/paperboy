# NY Times & Custom Daily Crossword Discord Bot 🧩

An automated Discord bot that fetches daily crossword puzzles from [Cross With Friends](https://www.crosswithfriends.com/) at a scheduled time in **Eastern Time (ET)**, posts a play link in your Discord channel, and tags your server's crossword role.

---

## 🌟 Features

- ⚙️ **Per-Server Custom Configuration**: Set notification role, channel, and daily post time directly in Discord.
- 🗓️ **Day-of-Week Search Overrides & Skipping**: Configure search sources/offsets or **skip specific days** (e.g. skip weekends).
- 🗣️ **Natural Setup Syntax**: Configure settings with simple Discord commands.
- 🧩 **Flexible Puzzle Search**: Supports NY Times, LA Times, WSJ, Universal, and custom crossword searches.
- 🎨 **Rich Embeds**: Displays puzzle title, author, target puzzle date, direct play link, and solve stats.
- 🔒 **Permission Protected**: Configuration commands require `Manage Server` permissions.

---

## ⚙️ Server Configuration Commands

### General Setup Commands

| Command | Description | Permission |
| :--- | :--- | :--- |
| `!crossword config notify @role in #channel at 12:00` | Sets role, channel, and daily post time in one command. | Manage Server |
| `!crossword config role @role` | Sets the role to mention for daily posts. | Manage Server |
| `!crossword config channel #channel` | Sets the channel to post daily crosswords into. | Manage Server |
| `!crossword config time 12:00` | Sets daily post time in Eastern Time (`12:00`, `12:00 PM`, etc.). | Manage Server |
| `!crossword config reset-post` | Resets last posted status so the bot can post again today for testing. | Manage Server |
| `!crossword config toggle` | Toggles automated daily posts ON/OFF. | Manage Server |
| `!crossword config status` | Displays current server configuration and active day overrides. | Everyone |

---

### 🗓️ Day-of-Week Search Overrides & Skipping

You can customize which puzzle is posted on specific days or **skip posting on certain days**:

```discord
!crossword config override saturday skip
!crossword config override sunday skip
!crossword config override monday search "ny times" offset -1
!crossword config override tuesday search "ny times" offset -3
!crossword config override wednesday search "la times" offset -4
```

| Override Command | Description |
| :--- | :--- |
| `!crossword config override <day> skip` | **Skips daily posting** on the specified day (e.g. `saturday skip`). |
| `!crossword config override <day> search "<query>" offset <offset>` | Set puzzle query & date offset for a given day. |
| `!crossword config override <day> clear` | Remove override for a day (reverts to default NY Times). |
| `!crossword config override list` | View all active day overrides for the server. |

---

## 🚀 Quick Setup Guide

1. **Invite your Discord Bot** with scopes `bot` and permissions `Send Messages`, `Embed Links`, `Mention Everyone`.
2. **Configure in Discord**:
   ```discord
   !crossword config notify @CROSSWORD in #crossword-lounge at 12:00
   !crossword config override saturday skip
   !crossword config override sunday skip
   !crossword config override monday search "ny times" offset -1
   ```
3. **Run `bot.py`**:
   ```bash
   pip install -r requirements.txt
   python bot.py
   ```

Configurations and day overrides are automatically saved to `guild_configs.db` (SQLite) and persist across bot restarts.

---

## 📜 License
MIT License.
