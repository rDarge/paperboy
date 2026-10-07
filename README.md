# NY Times & Custom Daily Crossword Discord Bot 🧩

An automated Discord bot that fetches daily crossword puzzles from [Cross With Friends](https://www.crosswithfriends.com/) at a scheduled time in **Eastern Time (ET)**, posts a dedicated **multiplayer room play link** in your Discord channel, and tags your server's crossword role.

---

## 🌟 Features

- 🎮 **Shared Multiplayer Rooms**: Automatically generates a dedicated room link (`/beta/game/<gid>`) for each post so all server members solve together in the exact same room!
- ⚙️ **Per-Server Custom Configuration**: Set notification role, channel, and daily post time directly in Discord.
- 🗓️ **Day-of-Week Search Overrides & Skipping**: Configure search sources/offsets or **skip specific days** (e.g. skip weekends).
- 🔒 **Permission Protected**: All configuration changes require `Manage Server` permissions.
- 🗣️ **Natural Setup Syntax**: Configure settings with simple Discord commands.
- 🧩 **Flexible Puzzle Search**: Supports NY Times, LA Times, WSJ, Universal, and custom crossword searches.
- 🐳 **Docker & Docker Compose Ready**: Easily run 24/7 on a TinyPC, Raspberry Pi, or home server.
- 🎨 **Rich Embeds**: Displays puzzle title, author, target puzzle date, multiplayer room link, and solve stats.

---

## ⚙️ Server Configuration Commands

> [!IMPORTANT]
> All `!crossword config` modification commands require **Manage Server** (or **Administrator**) permissions in Discord. Regular server members cannot alter bot settings.

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
| `!check` (or `!preview`) | Previews today's multiplayer crossword embed without pinging the role. | Everyone |
| `!crossword` (or `!today`) | Manually triggers today's multiplayer crossword post with role ping. | Everyone |

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

| Override Command | Description | Permission |
| :--- | :--- | :--- |
| `!crossword config override <day> skip` | **Skips daily posting** on the specified day (e.g. `saturday skip`). | Manage Server |
| `!crossword config override <day> search "<query>" offset <offset>` | Set puzzle query & date offset for a given day. | Manage Server |
| `!crossword config override <day> clear` | Remove override for a day (reverts to default NY Times). | Manage Server |
| `!crossword config override list` | View all active day overrides for the server. | Everyone |

---

## 🎮 How Multiplayer Game Rooms Work

When the bot posts a daily crossword or when `!crossword` / `!check` is called:
1. The bot queries Cross With Friends API to fetch today's puzzle.
2. It requests a new unique Game ID (`gid`) from `/api/counters/gid` and registers a room via `POST /api/game`.
3. It posts the dedicated multiplayer room link (`https://www.crosswithfriends.com/beta/game/<gid>`).
4. **Result**: Everyone in your Discord server who clicks the link joins the **same shared room** to play together!

---

## 🐳 Running with Docker Compose (TinyPC / Server Setup)

Running with Docker Compose ensures the bot runs 24/7 and automatically restarts when your TinyPC reboots:

### Initial Setup & Launch
1. **Clone the repository and set your `.env`**:
   ```bash
   cp .env.example .env
   # Edit .env and set your DISCORD_TOKEN=...
   ```

2. **Start the bot with Docker Compose**:
   ```bash
   docker compose up -d
   ```

3. **Check container logs**:
   ```bash
   docker compose logs -f
   ```

---

### 🔄 Rebuilding & Updating After Code Changes

Whenever you modify `bot.py` or pull code updates, the Python code running inside Docker will not update until you rebuild the container image.

```bash
# Rebuild the Docker image and restart the container in one command:
docker compose up -d --build

# Or for a complete teardown and fresh rebuild:
docker compose down
docker compose build --no-cache
docker compose up -d
```

> [!NOTE]
> Rebuilding or restarting Docker will **NOT** delete your server settings! Database data is persisted in `./data/guild_configs.db` on your TinyPC disk.

---

## 💻 Running Directly with Python

If you prefer to run directly without Docker:

```bash
pip install -r requirements.txt
python bot.py
```

---

## 📜 License
MIT License.
