# NY Times Daily Crossword Discord Bot 🧩

An automated Discord bot that fetches today's **NY Times Regular Crossword Puzzle** from [Cross With Friends](https://www.crosswithfriends.com/) every day at a scheduled time in **Eastern Time (ET)**, posts a play link in your Discord channel, and tags your server's crossword role.

---

## 🌟 Features

- ⚙️ **Per-Server Custom Configuration**: Server admins can configure their own notification role, channel, and daily post time directly in Discord.
- 🗣️ **Natural Setup Command**: Configure in a single line:  
  `!crossword config notify @CROSSWORD in #crossword-lounge at 12:00`
- ⏰ **Multi-Server Scheduler**: Automatically posts at each server's designated time in Eastern Time (supports EST/EDT).
- 🧩 **NY Times Regular Crossword Only**: Filters specifically for NY Times standard daily crosswords (skips Minis, Midis, WSJ, Universal, USA Today, etc.).
- 🎨 **Rich Embeds**: Displays puzzle title, author, edit info, direct play link, and solve stats.
- 🔒 **Permission Protected**: Server configuration commands require `Manage Server` permissions.

---

## ⚙️ Server Configuration Commands

| Command | Description | Permission |
| :--- | :--- | :--- |
| `!crossword config notify @role in #channel at 12:00` | Sets role, channel, and daily post time in one command. | Manage Server |
| `!crossword config role @role` | Sets the role to mention for daily posts. | Manage Server |
| `!crossword config channel #channel` | Sets the channel to post daily crosswords into. | Manage Server |
| `!crossword config time 12:00` | Sets daily post time in Eastern Time (`12:00`, `12:00 PM`, etc.). | Manage Server |
| `!crossword config toggle` | Toggles automated daily posts ON/OFF. | Manage Server |
| `!crossword config status` | Displays current server configuration and status. | Everyone |
| `!crossword` (or `!today`) | Manually posts today's NYT crossword immediately. | Everyone |
| `!check` | Previews today's crossword embed without pinging the role. | Everyone |
| `!status` | Checks bot online status and current Eastern Time. | Everyone |

---

## 🚀 Quick Setup Guide

### 1. Create & Invite your Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a **New Application** and go to the **Bot** tab.
3. Enable **Message Content Intent** under **Privileged Gateway Intents**.
4. Go to **OAuth2 -> URL Generator**, select `bot` scope and permissions:
   - `Send Messages`
   - `Embed Links`
   - `Mention Everyone`
5. Invite the bot to your server(s).

### 2. Configure in Discord

In any server where the bot is invited, a server administrator can type:
```discord
!crossword config notify @CROSSWORD in #crossword-lounge at 12:00
```
Or set individual options:
```discord
!crossword config channel #crossword-lounge
!crossword config role @CROSSWORD
!crossword config time 12:00 PM
```
Check configuration anytime with:
```discord
!crossword config status
```

---

## 💻 Running the Bot

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure `.env`**:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   ```
3. **Run `bot.py`**:
   ```bash
   python bot.py
   ```

Configurations are automatically saved to `guild_configs.db` (SQLite) and persist across bot restarts.

---

## 📜 License
MIT License.
