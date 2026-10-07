import os
import re
import logging
import asyncio
import urllib.parse
from datetime import datetime, timedelta
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

# Timezone configuration (Eastern Time)
ET_TZ = zoneinfo.ZoneInfo("America/New_York")
VALID_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cache for puzzle requests by (search_query, target_date_str)
puzzle_cache = {}


def build_api_url(search_query: str) -> str:
    """Builds crosswithfriends API URL with search query filter."""
    encoded_query = urllib.parse.quote(search_query)
    return (
        f"https://www.crosswithfriends.com/api/puzzle_list?"
        f"page=0&pageSize=50"
        f"&filter%5BnameOrTitleFilter%5D={encoded_query}"
        f"&filter%5BsizeFilter%5D%5BMini%5D=false"
        f"&filter%5BsizeFilter%5D%5BMidi%5D=false"
        f"&filter%5BsizeFilter%5D%5BStandard%5D=true"
        f"&filter%5BsizeFilter%5D%5BLarge%5D=false"
        f"&filter%5BtypeFilter%5D%5BStandard%5D=true"
        f"&filter%5BtypeFilter%5D%5BCryptic%5D=false"
        f"&filter%5BtypeFilter%5D%5BContest%5D=true"
        f"&filter%5BdayOfWeekFilter%5D%5BMon%5D=true"
        f"&filter%5BdayOfWeekFilter%5D%5BTue%5D=true"
        f"&filter%5BdayOfWeekFilter%5D%5BWed%5D=true"
        f"&filter%5BdayOfWeekFilter%5D%5BThu%5D=true"
        f"&filter%5BdayOfWeekFilter%5D%5BFri%5D=true"
        f"&filter%5BdayOfWeekFilter%5D%5BSat%5D=true"
        f"&filter%5BdayOfWeekFilter%5D%5BSun%5D=true"
        f"&filter%5BdayOfWeekFilter%5D%5BUnknown%5D=true"
        f"&filter%5BminRating%5D=0"
        f"&filter%5BsortBy%5D=default"
    )


async def fetch_puzzle_by_criteria(search_query: str, target_date, retries=3, delay=10):
    """
    Fetches puzzle from API matching search_query and target_date.
    Uses in-memory caching per search criteria.
    """
    cache_key = f"{search_query.lower()}:{target_date.strftime('%Y-%m-%d')}"
    if cache_key in puzzle_cache:
        return puzzle_cache[cache_key]

    api_url = build_api_url(search_query)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        puzzles = data.get("puzzles", [])
                        puzzle = match_puzzle_by_date(puzzles, search_query, target_date)
                        if puzzle:
                            puzzle_cache[cache_key] = puzzle
                            return puzzle
                    else:
                        logging.warning(f"API returned status {resp.status} on attempt {attempt}")
        except Exception as e:
            logging.error(f"Error fetching puzzle list (attempt {attempt}/{retries}): {e}")

        if attempt < retries:
            await asyncio.sleep(delay)

    return None


def match_puzzle_by_date(puzzles, search_query, target_date):
    """Filters returned puzzles for search query and target date."""
    month_fullname = target_date.strftime("%B")  # e.g., October
    month_short = target_date.strftime("%b")     # e.g., Oct
    day_str = str(target_date.day)
    year_str = str(target_date.year)

    date_patterns = [
        rf"{month_fullname}\s+{day_str},?\s+{year_str}",
        rf"{month_short}\.?\s+{day_str},?\s+{year_str}",
        rf"{target_date.month}/{target_date.day}/{target_date.year}",
        rf"{target_date.month}/{target_date.day}/{str(target_date.year)[2:]}"
    ]

    clean_q = search_query.strip().lower()
    if clean_q in ["la times", "l.a. times", "l. a. times"]:
        query_pattern = r"L\.?\s*A\.?\s*Times"
    elif clean_q in ["ny times", "n.y. times", "new york times"]:
        query_pattern = r"NY\s*Times|New\s*York\s*Times"
    else:
        query_pattern = re.escape(clean_q)

    for p in puzzles:
        info = p.get("content", {}).get("info", {})
        title = info.get("title", "")
        title_override = info.get("titleOverride") or ""
        combined = f"{title} {title_override}"

        if not re.search(query_pattern, combined, re.IGNORECASE):
            continue

        p_type = str(info.get("type", "")).lower()
        if "mini" in p_type or "midi" in p_type or "mini" in combined.lower() or "midi" in combined.lower():
            continue

        for pat in date_patterns:
            if re.search(pat, combined, re.IGNORECASE):
                return p

    for p in puzzles:
        info = p.get("content", {}).get("info", {})
        title = info.get("title", "")
        title_override = info.get("titleOverride") or ""
        combined = f"{title} {title_override}"

        if re.search(query_pattern, combined, re.IGNORECASE):
            p_type = str(info.get("type", "")).lower()
            if "mini" not in p_type and "midi" not in p_type and "mini" not in combined.lower() and "midi" not in combined.lower():
                return p

    return None


async def get_puzzle_for_guild(guild_id: str):
    """
    Determines search query and target date for a guild based on day of week & overrides.
    Returns (puzzle_dict, search_query, target_date).
    If day is skipped, search_query is 'SKIP'.
    """
    now_et = datetime.now(ET_TZ)
    current_day_name = now_et.strftime("%A").lower()  # e.g., 'monday'
    today_date = now_et.date()

    override = config_db.get_day_override(guild_id, current_day_name) if guild_id else None

    if override:
        query = override["search_query"]
        if query.upper() in ["SKIP", "NONE", "OFF", "DISABLED"]:
            return None, "SKIP", None
        offset = override["day_offset"]
        target_date = today_date + timedelta(days=offset)
        search_query = query
    else:
        search_query = "NY Times"
        target_date = today_date

    puzzle = await fetch_puzzle_by_criteria(search_query, target_date)
    return puzzle, search_query, target_date


def create_puzzle_embed(puzzle_data, search_query="NY Times", target_date=None):
    """Creates a formatted Discord Embed for the puzzle."""
    pid = puzzle_data.get("pid")
    info = puzzle_data.get("content", {}).get("info", {})
    title = info.get("title") or info.get("titleOverride") or f"{search_query} Crossword"
    author = info.get("author", "Unknown Author")
    puzzle_url = f"https://www.crosswithfriends.com/beta/puzzle/{pid}"

    date_str = target_date.strftime("%A, %B %d, %Y") if target_date else ""

    embed = discord.Embed(
        title=f"🧩 {title}",
        url=puzzle_url,
        description=f"Today's crossword ({search_query}) is ready to play on Cross With Friends!",
        color=discord.Color.blue(),
        timestamp=datetime.now(ET_TZ)
    )

    embed.add_field(name="✍️ Author / Editor", value=author, inline=False)
    if date_str:
        embed.add_field(name="📅 Target Puzzle Date", value=date_str, inline=True)
    embed.add_field(name="🔗 Play Link", value=f"[Click here to solve!]({puzzle_url})", inline=False)

    stats = puzzle_data.get("stats", {})
    if stats and isinstance(stats, dict):
        solves = stats.get("numSolves")
        rating = stats.get("ratingAverage")
        if solves is not None or rating is not None:
            embed.set_footer(text=f"Solves: {solves or 0} | Rating: {rating or 'N/A'}/5.0")
    else:
        embed.set_footer(text="Cross With Friends • Daily Crossword")

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
    """Normalizes time strings into 24-hour 'HH:MM' format."""
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
    """Checks every minute for guilds configured for the current time in ET."""
    now_et = datetime.now(ET_TZ)
    current_time_hhmm = now_et.strftime("%H:%M")
    current_date_str = now_et.strftime("%Y-%m-%d")

    guilds_to_notify = config_db.get_guilds_to_notify(current_time_hhmm, current_date_str)
    if not guilds_to_notify:
        return

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
                puzzle, query, target_date = await get_puzzle_for_guild(guild_id)

                # Handle day skip
                if query == "SKIP":
                    config_db.update_last_posted_date(guild_id, current_date_str)
                    logging.info(f"Daily post skipped today for guild '{cfg['guild_name']}' ({guild_id}) per day override setting.")
                    continue

                if puzzle:
                    embed = create_puzzle_embed(puzzle, query, target_date)
                    role_mention = resolve_role_mention(guild, role_id)
                    content = f"Hey {role_mention}, today's crossword ({query}) is live!"
                    allowed_mentions = discord.AllowedMentions(roles=True, users=True)
                    await channel.send(content=content, embed=embed, allowed_mentions=allowed_mentions)
                    config_db.update_last_posted_date(guild_id, current_date_str)
                    logging.info(f"Posted crossword to guild '{cfg['guild_name']}' ({guild_id}) channel {channel_id}.")
                else:
                    logging.error(f"No puzzle found for guild {guild_id} with query '{query}'.")
            except Exception as e:
                logging.error(f"Failed to post to channel {channel_id} in guild {guild_id}: {e}")


@minute_scheduler_task.before_loop
async def before_minute_scheduler_task():
    await bot.wait_until_ready()


@bot.event
async def on_guild_join(guild):
    """Set up default config when joining a new guild."""
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
    """Manually post today's crossword to the current channel."""
    async with ctx.typing():
        guild_id = str(ctx.guild.id) if ctx.guild else None
        puzzle, query, target_date = await get_puzzle_for_guild(guild_id)

        if query == "SKIP":
            now_day = datetime.now(ET_TZ).strftime("%A")
            await ctx.send(f"ℹ️ Automated daily posts are set to **SKIP** on **{now_day}s** for this server.")
            return

        if not puzzle:
            await ctx.send(f"⚠️ Could not find a matching crossword for '{query}'.")
            return

        embed = create_puzzle_embed(puzzle, query, target_date)
        cfg = config_db.get_guild_config(guild_id) if guild_id else None
        role_setting = cfg["role_id"] if cfg else DEFAULT_ROLE_ID

        role_mention = resolve_role_mention(ctx.guild, role_setting)
        content = f"Hey {role_mention}, today's crossword ({query}) is live!"
        allowed_mentions = discord.AllowedMentions(roles=True, users=True)
        await ctx.send(content=content, embed=embed, allowed_mentions=allowed_mentions)


@crossword_group.group(name="config", invoke_without_command=True)
@commands.has_permissions(manage_guild=True)
async def config_group(ctx, *, args: str = None):
    """
    Configures server crossword settings.
    Usage:
      !crossword config notify @role in #channel at 12:00
      !crossword config override monday search "ny times" offset -1
      !crossword config override saturday skip
      !crossword config status
    """
    if not args:
        await show_config_status(ctx)
        return

    # Natural sentence syntax: notify <role> in <channel> at <time>
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
            enabled=1,
            reset_posted=True
        )

        role_display = f"<@&{role_obj_id}>" if role_obj_id.isdigit() else role_raw
        await ctx.send(
            f"✅ **Configuration Saved!**\n"
            f"📢 **Channel**: {channel_obj.mention}\n"
            f"🏷️ **Role**: {role_display}\n"
            f"⏰ **Scheduled Time**: `{norm_time}` ET (Eastern Time)\n"
            f"🟢 **Daily Posts**: Enabled\n"
            f"🔄 *Last posted status reset for testing at `{norm_time}` ET.*"
        )
    else:
        await ctx.send(
            "❓ **Unrecognized config syntax.**\n"
            "Example usages:\n"
            "`!crossword config notify @CROSSWORD in #general at 12:00`\n"
            "`!crossword config override monday search \"ny times\" offset -1`\n"
            "`!crossword config override saturday skip`\n"
            "`!crossword config status`"
        )


# --- DAY OVERRIDES SUBCOMMAND ---

@config_group.command(name="override")
@commands.has_permissions(manage_guild=True)
async def config_override(ctx, *, args: str):
    """
    Set, skip, clear, or view day-of-week search overrides.
    Examples:
      !crossword config override saturday skip
      !crossword config override monday search "ny times" offset -1
      !crossword config override tuesday search "ny times" offset -3
      !crossword config override monday clear
      !crossword config override list
    """
    text = args.strip()
    guild_id = str(ctx.guild.id)

    # 1. List overrides
    if text.lower() in ["list", "status", "view", "show"]:
        overrides = config_db.get_all_day_overrides(guild_id)
        if not overrides:
            await ctx.send("ℹ️ No day-of-week search overrides configured for this server. (Using standard NY Times daily puzzle).")
            return

        embed = discord.Embed(
            title=f"🗓️ Day Search Overrides - {ctx.guild.name}",
            color=discord.Color.blue()
        )
        for ov in overrides:
            day_cap = ov["day_of_week"].capitalize()
            query = ov["search_query"]
            if query.upper() in ["SKIP", "NONE", "OFF", "DISABLED"]:
                embed.add_field(
                    name=f"📌 {day_cap}",
                    value="🚫 **Skipped** (No post on this day)",
                    inline=False
                )
            else:
                offset = ov["day_offset"]
                offset_str = f"{offset} days" if offset != 0 else "0 (Same day)"
                embed.add_field(
                    name=f"📌 {day_cap}",
                    value=f"🔍 **Search**: `{query}`\nrepr **Offset**: `{offset_str}`",
                    inline=False
                )
        await ctx.send(embed=embed)
        return

    # 2. Skip day pattern: e.g. 'saturday skip' or 'sunday disabled' or 'saturday off'
    skip_match = re.match(r'^(?P<day>' + '|'.join(VALID_DAYS) + r')\s+(?:skip|none|off|disabled)$', text, re.IGNORECASE)
    if skip_match:
        day_clean = skip_match.group("day").lower()
        config_db.set_day_override(guild_id, day_clean, "SKIP", 0)
        await ctx.send(f"🚫 **Day Override Saved!** Daily crossword posts will be **SKIPPED** on **{day_clean.capitalize()}s**.")
        return

    # 3. Clear override pattern: e.g. 'saturday clear'
    clear_match = re.match(r'^(?P<day>' + '|'.join(VALID_DAYS) + r')\s+(?:clear|delete|remove|reset)$', text, re.IGNORECASE)
    if clear_match:
        day_clean = clear_match.group("day").lower()
        deleted = config_db.delete_day_override(guild_id, day_clean)
        if deleted:
            await ctx.send(f"✅ Search override for **{day_clean.capitalize()}** has been removed (reverted to default NY Times).")
        else:
            await ctx.send(f"ℹ️ No override was configured for **{day_clean.capitalize()}**.")
        return

    # 4. Set search override pattern: <day> search "<query>" offset <offset>
    pattern = r'^(?P<day>' + '|'.join(VALID_DAYS) + r')\s+search\s+["\'`]?(.+?)["\'`]?\s+offset\s+([-+]?\d+)$'
    match = re.match(pattern, text, re.IGNORECASE)

    if match:
        day_raw, query_raw, offset_raw = match.group(1), match.group(2), match.group(3)
        day_clean = day_raw.lower()
        query_clean = query_raw.strip('"`\' ')
        offset_val = int(offset_raw)

        config_db.set_day_override(guild_id, day_clean, query_clean, offset_val)

        sample_today = datetime.now(ET_TZ).date()
        sample_target = sample_today + timedelta(days=offset_val)

        await ctx.send(
            f"✅ **Day Override Saved!**\n"
            f"📅 **Day**: `{day_clean.capitalize()}`\n"
            f"🔍 **Search Query**: `{query_clean}`\n"
            f"repr **Date Offset**: `{offset_val}` day(s)\n"
            f"💡 *Example*: If run today, it will search `{query_clean}` for date `{sample_target.strftime('%B %d, %Y')}`."
        )
    else:
        await ctx.send(
            "❌ **Invalid override command syntax.**\n"
            "Examples:\n"
            "`!crossword config override saturday skip`\n"
            "`!crossword config override monday search \"ny times\" offset -1`\n"
            "`!crossword config override tuesday search \"ny times\" offset -3`\n"
            "`!crossword config override monday clear`\n"
            "`!crossword config override list`"
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
    """Set daily post time in Eastern Time (ET). Resets last posted date for testing."""
    norm_time = normalize_time(time_str)
    if not norm_time:
        await ctx.send("❌ Invalid time format! Use `HH:MM` (e.g. `12:00` or `12:00 PM`).")
        return
    config_db.set_guild_config(guild_id=str(ctx.guild.id), guild_name=ctx.guild.name, schedule_time=norm_time, reset_posted=True)
    await ctx.send(f"✅ Daily post time set to `{norm_time}` ET (Eastern Time).\n🔄 *Last posted status reset so testing at `{norm_time}` ET will trigger!*")


@config_group.command(name="reset-post", aliases=["resetposted", "resetpost"])
@commands.has_permissions(manage_guild=True)
async def config_reset_post(ctx):
    """Reset last posted date so the bot can post again today for testing."""
    config_db.reset_last_posted_date(str(ctx.guild.id))
    await ctx.send("🔄 **Last posted status reset!** The bot will post again at its next scheduled run time today.")


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
    guild_id = str(ctx.guild.id) if ctx.guild else None
    cfg = config_db.get_guild_config(guild_id) if guild_id else None
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
    embed.add_field(name="📅 Last Posted Date", value=f"`{last_posted or 'None'}`", inline=True)

    overrides = config_db.get_all_day_overrides(guild_id)
    if overrides:
        ov_list = []
        for o in overrides:
            day_name = o["day_of_week"].capitalize()
            q = o["search_query"]
            if q.upper() in ["SKIP", "NONE", "OFF", "DISABLED"]:
                ov_list.append(f"• **{day_name}**: 🚫 *Skipped*")
            else:
                ov_list.append(f"• **{day_name}**: `{q}` (Offset: `{o['day_offset']}`)")
        embed.add_field(name="🗓️ Day Overrides", value="\n".join(ov_list), inline=False)
    else:
        embed.add_field(name="🗓️ Day Overrides", value="*None (Defaulting to today's NY Times)*", inline=False)

    embed.set_footer(text=f"Current ET Time: {now_et}")
    await ctx.send(embed=embed)


@bot.command(name="check", aliases=["preview"])
async def check_crossword_command(ctx):
    """Check today's puzzle without pinging the role (dry run)."""
    async with ctx.typing():
        guild_id = str(ctx.guild.id) if ctx.guild else None
        puzzle, query, target_date = await get_puzzle_for_guild(guild_id)

        if query == "SKIP":
            now_day = datetime.now(ET_TZ).strftime("%A")
            await ctx.send(f"ℹ️ Daily posts are set to **SKIP** on **{now_day}s** for this server.")
            return

        if not puzzle:
            await ctx.send(f"⚠️ Could not find today's puzzle matching query '{query}'.")
            return

        embed = create_puzzle_embed(puzzle, query, target_date)
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
