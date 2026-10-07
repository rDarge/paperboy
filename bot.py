import os
import re
import logging
import asyncio
from datetime import datetime
import zoneinfo
import aiohttp
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

import config_db

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
DEFAULT_ROLE_ID = os.getenv("CROSSWORD_ROLE_ID", "CROSSWORD")
DEFAULT_SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR_ET", 12))
DEFAULT_SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE_ET", 0))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# CrossWithFriends API URL
API_URL = (
    "https://www.crosswithfriends.com/api/puzzle_list?"
    "page=0&pageSize=50"
    "&filter%5BnameOrTitleFilter%5D="
    "&filter%5BsizeFilter%5D%5BMini%5D=false"
    "&filter%5BsizeFilter%5D%5BMidi%5D=false"
    "&filter%5BsizeFilter%5D%5BStandard%5D=true"
    "&filter%5BsizeFilter%5D%5BLarge%5D=false"
    "&filter%5BtypeFilter%5D%5BStandard%5D=true"
    "&filter%5BtypeFilter%5D%5BCryptic%5D=false"
    "&filter%5BtypeFilter%5D%5BContest%5D=true"
    "&filter%5BdayOfWeekFilter%5D%5BMon%5D=true"
    "&filter%5BdayOfWeekFilter%5D%5BTue%5D=true"
    "&filter%5BdayOfWeekFilter%5D%5BWed%5D=true"
    "&filter%5BdayOfWeekFilter%5D%5BThu%5D=true"
    "&filter%5BdayOfWeekFilter%5D%5BFri%5D=true"
    "&filter%5BdayOfWeekFilter%5D%5BSat%5D=true"
    "&filter%5BdayOfWeekFilter%5D%5BSun%5D=true"
    "&filter%5BdayOfWeekFilter%5D%5BUnknown%5D=true"
    "&filter%5BminRating%5D=0"
    "&filter%5BsortBy%5D=default"
)

# Timezone configuration (Eastern Time)
ET_TZ = zoneinfo.ZoneInfo("America/New_York")

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cache for today's puzzle to avoid redundant API calls
cached_puzzle = None
cached_puzzle_date = None


async def fetch_nyt_puzzle(retries=3, delay=10):
    """
    Fetches today's NY Times regular crossword puzzle from crosswithfriends.com API.
    Caches result per date.
    """
    global cached_puzzle, cached_puzzle_date
    today_et = datetime.now(ET_TZ).date()

    if cached_puzzle_date == today_et and cached_puzzle is not None:
        return cached_puzzle

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        puzzles = data.get("puzzles", [])
                        puzzle = find_today_nyt_puzzle(puzzles)
                        if puzzle:
                            cached_puzzle = puzzle
                            cached_puzzle_date = today_et
                            return puzzle
                    else:
                        logging.warning(f"API returned status {resp.status} on attempt {attempt}")
        except Exception as e:
            logging.error(f"Error fetching puzzle list (attempt {attempt}/{retries}): {e}")

        if attempt < retries:
            await asyncio.sleep(delay)

    return None


def find_today_nyt_puzzle(puzzles):
    """Filters puzzle list for today's NY Times regular (Standard) puzzle."""
    today_et = datetime.now(ET_TZ).date()
    month_name = today_et.strftime("%B")
    short_month = today_et.strftime("%b")
    day_str = str(today_et.day)
    year_str = str(today_et.year)

    date_patterns = [
        rf"{month_name}\s+{day_str},?\s+{year_str}",
        rf"{short_month}\.?\s+{day_str},?\s+{year_str}",
    ]

    for p in puzzles:
        info = p.get("content", {}).get("info", {})
        title = info.get("title", "")
        title_override = info.get("titleOverride") or ""
        combined_title = f"{title} {title_override}"

        if not re.search(r"NY\s*Times|New\s*York\s*Times", combined_title, re.IGNORECASE):
            continue

        p_type = str(info.get("type", "")).lower()
        if "mini" in p_type or "midi" in p_type or "mini" in combined_title.lower() or "midi" in combined_title.lower():
            continue

        for pat in date_patterns:
            if re.search(pat, combined_title, re.IGNORECASE):
                return p

    for p in puzzles:
        info = p.get("content", {}).get("info", {})
        title = info.get("title", "")
        title_override = info.get("titleOverride") or ""
        combined_title = f"{title} {title_override}"

        if re.search(r"NY\s*Times|New\s*York\s*Times", combined_title, re.IGNORECASE):
            p_type = str(info.get("type", "")).lower()
            if "mini" not in p_type and "midi" not in p_type and "mini" not in combined_title.lower() and "midi" not in combined_title.lower():
                return p

    return None


def create_puzzle_embed(puzzle_data):
    """Creates a formatted Discord Embed for the puzzle."""
    pid = puzzle_data.get("pid")
    info = puzzle_data.get("content", {}).get("info", {})
    title = info.get("title", "NY Times Daily Crossword")
    author = info.get("author", "Unknown Author")
    puzzle_url = f"https://www.crosswithfriends.com/beta/puzzle/{pid}"

    embed = discord.Embed(
        title=f"🧩 {title}",
        url=puzzle_url,
        description=f"Today's NY Times regular crossword puzzle is ready to play on Cross With Friends!",
        color=discord.Color.blue(),
        timestamp=datetime.now(ET_TZ)
    )

    embed.add_field(name="✍️ Author / Editor", value=author, inline=False)
    embed.add_field(name="🔗 Play Link", value=f"[Click here to solve!]({puzzle_url})", inline=False)

    stats = puzzle_data.get("stats", {})
    if stats and isinstance(stats, dict):
        solves = stats.get("numSolves")
        rating = stats.get("ratingAverage")
        if solves is not None or rating is not None:
            embed.set_footer(text=f"Solves: {solves or 0} | Rating: {rating or 'N/A'}/5.0")
    else:
        embed.set_footer(text="Cross With Friends • NY Times Crossword")

    return embed


def resolve_role_mention(guild, role_id_or_name):
    """Formats role mention string from role ID or role name."""
    if not role_id_or_name:
        return "@CROSSWORD"
    if str(role_id_or_name).isdigit():
        return f"<@&{role_id_or_name}>"
    if role_id_or_name.startswith("<@&") and role_id_or_name.endswith(">"):
        return role_id_or_name
    if guild:
        clean_name = role_id_or_name.lstrip("@")
        role = discord.utils.get(guild.roles, name=clean_name)
        if role:
            return role.mention
    return f"@{role_id_or_name.lstrip('@')}"


def normalize_time(time_str: str) -> str:
    """Normalizes time strings like '12:00', '12:00 PM', '9:30 AM' into 24-hour 'HH:MM' format."""
    time_str = time_str.strip().upper()
    formats = ["%H:%M", "%I:%M %p", "%I:%M%p"]
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.strftime("%H:%M")
        except ValueError:
            pass
    return None


@tasks.loop(seconds=60)
async def minute_scheduler_task():
    """
    Checks every minute for guilds configured for the current time in Eastern Time (ET).
    """
    now_et = datetime.now(ET_TZ)
    current_time_hhmm = now_et.strftime("%H:%M")
    current_date_str = now_et.strftime("%Y-%m-%d")

    guilds_to_notify = config_db.get_guilds_to_notify(current_time_hhmm, current_date_str)
    if not guilds_to_notify:
        return

    puzzle = await fetch_nyt_puzzle()
    if not puzzle:
        logging.error("Failed to fetch puzzle for scheduled execution.")
        return

    embed = create_puzzle_embed(puzzle)

    for cfg in guilds_to_notify:
        guild_id = cfg["guild_id"]
        channel_id = cfg["channel_id"]
        role_id = cfg["role_id"]

        guild = bot.get_guild(int(guild_id))
        channel = bot.get_channel(int(channel_id)) if channel_id else None

        if not channel and channel_id and channel_id.isdigit():
            try:
                channel = await bot.fetch_channel(int(channel_id))
            except Exception as e:
                logging.error(f"Could not fetch channel {channel_id} for guild {guild_id}: {e}")

        if channel:
            try:
                role_mention = resolve_role_mention(guild, role_id)
                content = f"Hey {role_mention}, today's NY Times Crossword is live!"
                allowed_mentions = discord.AllowedMentions(roles=True, users=True)
                await channel.send(content=content, embed=embed, allowed_mentions=allowed_mentions)
                config_db.update_last_posted_date(guild_id, current_date_str)
                logging.info(f"Posted crossword to guild '{cfg['guild_name']}' ({guild_id}) channel {channel_id}.")
            except Exception as e:
                logging.error(f"Failed to post to channel {channel_id} in guild {guild_id}: {e}")


@minute_scheduler_task.before_loop
async def before_minute_scheduler_task():
    await bot.wait_until_ready()


@bot.event
async def on_guild_join(guild):
    """When joining a new guild, set up default config if environment variables exist."""
    logging.info(f"Joined new guild: {guild.name} ({guild.id})")
    default_time = f"{DEFAULT_SCHEDULE_HOUR:02d}:{DEFAULT_SCHEDULE_MINUTE:02d}"
    config_db.set_guild_config(
        guild_id=str(guild.id),
        guild_name=guild.name,
        channel_id=DEFAULT_CHANNEL_ID,
        role_id=DEFAULT_ROLE_ID,
        schedule_time=default_time,
        enabled=1
    )


@bot.event
async def on_ready():
    config_db.init_db()
    logging.info(f"Logged in as {bot.user.name} ({bot.user.id})")
    if not minute_scheduler_task.is_running():
        minute_scheduler_task.start()
        logging.info("Multi-guild minute scheduler loop started.")


# --- COMMAND GROUP: !crossword ---

@bot.group(name="crossword", aliases=["nyt"], invoke_without_command=True)
async def crossword_group(ctx):
    """Manually post today's NY Times crossword to the current channel."""
    async with ctx.typing():
        puzzle = await fetch_nyt_puzzle()
        if not puzzle:
            await ctx.send("⚠️ Could not find today's NY Times regular puzzle on Cross With Friends API.")
            return

        embed = create_puzzle_embed(puzzle)
        cfg = config_db.get_guild_config(str(ctx.guild.id)) if ctx.guild else None
        role_setting = cfg["role_id"] if cfg else DEFAULT_ROLE_ID

        role_mention = resolve_role_mention(ctx.guild, role_setting)
        content = f"Hey {role_mention}, today's NY Times Crossword is live!"
        allowed_mentions = discord.AllowedMentions(roles=True, users=True)
        await ctx.send(content=content, embed=embed, allowed_mentions=allowed_mentions)


@crossword_group.group(name="config", invoke_without_command=True)
@commands.has_permissions(manage_guild=True)
async def config_group(ctx, *, args: str = None):
    """
    Configures server crossword settings.
    Usage:
      !crossword config notify @role in #channel at 12:00
      !crossword config status
    """
    if not args:
        await show_config_status(ctx)
        return

    # Attempt natural text matching: notify <role> in <channel> at <time>
    match = re.search(
        r'notify\s+(?P<role><@&?\d+>|@?\S+)\s+in\s+(?P<channel><#\d+>|#?\S+)\s+at\s+(?P<time>\d{1,2}:\d{2}(?:\s*[AaPp][Mm])?)',
        args, re.IGNORECASE
    )

    if match:
        role_raw = match.group("role")
        chan_raw = match.group("channel")
        time_raw = match.group("time")

        norm_time = normalize_time(time_raw)
        if not norm_time:
            await ctx.send("❌ Invalid time format! Please use format like `12:00` or `12:00 PM`.")
            return

        # Resolve channel object
        channel_obj = None
        chan_id_match = re.search(r'\d+', chan_raw)
        if chan_id_match:
            channel_obj = ctx.guild.get_channel(int(chan_id_match.group()))
        if not channel_obj:
            clean_chan_name = chan_raw.lstrip('#')
            channel_obj = discord.utils.get(ctx.guild.text_channels, name=clean_chan_name)

        if not channel_obj:
            await ctx.send(f"❌ Could not find text channel `{chan_raw}` in this server.")
            return

        # Resolve role object
        role_obj_id = role_raw
        role_id_match = re.search(r'\d+', role_raw)
        if role_id_match:
            r = ctx.guild.get_role(int(role_id_match.group()))
            if r:
                role_obj_id = str(r.id)
        else:
            clean_role_name = role_raw.lstrip('@')
            r = discord.utils.get(ctx.guild.roles, name=clean_role_name)
            if r:
                role_obj_id = str(r.id)

        config_db.set_guild_config(
            guild_id=str(ctx.guild.id),
            guild_name=ctx.guild.name,
            channel_id=str(channel_obj.id),
            role_id=role_obj_id,
            schedule_time=norm_time,
            enabled=1
        )

        role_display = f"<@&{role_obj_id}>" if role_obj_id.isdigit() else role_raw
        await ctx.send(
            f"✅ **Configuration Saved!**\n"
            f"📢 **Channel**: {channel_obj.mention}\n"
            f"🏷️ **Role**: {role_display}\n"
            f"⏰ **Scheduled Time**: `{norm_time}` ET (Eastern Time)\n"
            f"🟢 **Daily Posts**: Enabled"
        )
    else:
        await ctx.send(
            "❓ **Unrecognized config syntax.**\n"
            "Example usage:\n"
            "`!crossword config notify @CROSSWORD in #general at 12:00`\n"
            "Or configure individual options:\n"
            "`!crossword config channel #channel` | `!crossword config role @role` | `!crossword config time 12:00` | `!crossword config status`"
        )


@config_group.command(name="channel")
@commands.has_permissions(manage_guild=True)
async def config_channel(ctx, channel: discord.TextChannel):
    """Set destination channel for daily crossword posts."""
    config_db.set_guild_config(guild_id=str(ctx.guild.id), guild_name=ctx.guild.name, channel_id=str(channel.id))
    await ctx.send(f"✅ Daily crossword channel updated to {channel.mention}.")


@config_group.command(name="role")
@commands.has_permissions(manage_guild=True)
async def config_role(ctx, role: discord.Role):
    """Set role to tag for daily crossword posts."""
    config_db.set_guild_config(guild_id=str(ctx.guild.id), guild_name=ctx.guild.name, role_id=str(role.id))
    await ctx.send(f"✅ Daily crossword notification role updated to {role.mention}.")


@config_group.command(name="time")
@commands.has_permissions(manage_guild=True)
async def config_time(ctx, time_str: str):
    """Set daily post time in Eastern Time (ET), e.g. 12:00 or 12:00 PM."""
    norm_time = normalize_time(time_str)
    if not norm_time:
        await ctx.send("❌ Invalid time format! Use `HH:MM` (e.g. `12:00` or `12:00 PM`).")
        return
    config_db.set_guild_config(guild_id=str(ctx.guild.id), guild_name=ctx.guild.name, schedule_time=norm_time)
    await ctx.send(f"✅ Daily post time set to `{norm_time}` ET (Eastern Time).")


@config_group.command(name="toggle")
@commands.has_permissions(manage_guild=True)
async def config_toggle(ctx):
    """Toggle automated daily posts on or off."""
    cfg = config_db.get_guild_config(str(ctx.guild.id))
    current_enabled = cfg["enabled"] if cfg else 1
    new_enabled = 0 if current_enabled == 1 else 1
    config_db.set_guild_config(guild_id=str(ctx.guild.id), guild_name=ctx.guild.name, enabled=new_enabled)
    status_str = "🟢 **Enabled**" if new_enabled == 1 else "🔴 **Disabled**"
    await ctx.send(f"✅ Automated daily posts are now {status_str}.")


@config_group.command(name="status", aliases=["view"])
async def config_status_subcommand(ctx):
    """Show current server configuration."""
    await show_config_status(ctx)


async def show_config_status(ctx):
    """Helper to render server configuration status embed."""
    cfg = config_db.get_guild_config(str(ctx.guild.id)) if ctx.guild else None
    if not cfg:
        await ctx.send("ℹ️ This server has not been configured yet. Use `!crossword config notify @role in #channel at 12:00` to set it up.")
        return

    chan_id = cfg.get("channel_id")
    role_id = cfg.get("role_id")
    sched_time = cfg.get("schedule_time", "12:00")
    is_enabled = cfg.get("enabled") == 1
    last_posted = cfg.get("last_posted_date", "None")

    channel_display = f"<#{chan_id}>" if chan_id else "Not Set"
    role_display = resolve_role_mention(ctx.guild, role_id)
    enabled_display = "🟢 Enabled" if is_enabled else "🔴 Disabled"

    now_et = datetime.now(ET_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")

    embed = discord.Embed(
        title=f"⚙️ Crossword Bot Configuration - {ctx.guild.name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="📢 Channel", value=channel_display, inline=True)
    embed.add_field(name="🏷️ Role Ping", value=role_display, inline=True)
    embed.add_field(name="⏰ Scheduled Time", value=f"`{sched_time}` ET", inline=True)
    embed.add_field(name="STATUS", value=enabled_display, inline=True)
    embed.add_field(name="📅 Last Posted Date", value=f"`{last_posted}`", inline=True)
    embed.set_footer(text=f"Current ET Time: {now_et}")

    await ctx.send(embed=embed)


@bot.command(name="check", aliases=["preview"])
async def check_crossword_command(ctx):
    """Check today's puzzle without pinging the role (dry run)."""
    async with ctx.typing():
        puzzle = await fetch_nyt_puzzle()
        if not puzzle:
            await ctx.send("⚠️ Could not find today's NY Times regular puzzle.")
            return

        embed = create_puzzle_embed(puzzle)
        await ctx.send(content="🔍 **Preview (No Ping)**:", embed=embed)


@bot.command(name="status")
async def status_command(ctx):
    """Check bot system status."""
    now_et = datetime.now(ET_TZ)
    await ctx.send(
        f"🤖 **Bot Status**: Online\n"
        f"🕒 **Current ET Time**: {now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
        f"💡 Server admins can run `!crossword config status` to view this server's schedule."
    )


# Error handler for missing permissions
@config_group.error
async def config_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ You need `Manage Server` permissions to change bot configurations.")


if __name__ == "__main__":
    if not DISCORD_TOKEN or DISCORD_TOKEN == "your_bot_token_here":
        print("ERROR: DISCORD_TOKEN is not set in .env file!")
        print("Please configure .env with your bot token before running.")
    else:
        bot.run(DISCORD_TOKEN)
