import discord
from discord.ext import commands
import dotenv
import os
import sys
import msvcrt
import asyncio
from datetime import datetime
import requests

dotenv.load_dotenv()
token = os.getenv("TOKEN")
prefix = os.getenv("PREFIX")
currentVersion = "1.0.0"

sinister = commands.Bot(command_prefix=prefix, self_bot=True, intents=discord.Intents.default())

current_task = None
promo_data = {}
blocked_users = set()

def get_latest_version():
    try:
        version = requests.get(
            "https://raw.githubusercontent.com/isnak/Selfbot/main/version.txt"
        )
        if version.status_code == 200:
            return version.text.strip()
        else:
            return None
    except requests.RequestException:
        return None

def check_version():
    latest_version = get_latest_version()

    if latest_version and latest_version != currentVersion:
        changes = requests.get(
            "https://raw.githubusercontent.com/isnak/your-repository/main/data/changelog.txt"
        )

        if "REQUIRED" in changes.text:
            print(f"\033[91mThere is a required update on the GitHub, you must update to continue using Avarice: https://github.com/isnak/your-repository\n\nChangelog:\n{changes.text}\033[0m")
            input("\nPress enter to exit...")
            os._exit(0)
        else:
            print(f"\033[93mThis version is outdated. Please update to version {latest_version} from https://github.com/isnak/your-repository\n\nChangelog:\n{changes.text}\033[0m")
    else:
        print("\033[92mYou're using the latest version!\033[0m")

@sinister.event
async def on_ready():
    print(f"""
        Successfully Logged In
        [Client] {sinister.user.name}
    """)
    check_version()

    async def check_exit():
        while True:
            await asyncio.sleep(0.1)
            if msvcrt.kbhit():
                try:
                    if msvcrt.getch() == b"\x1a":
                        await sinister.close()
                        sys.exit()
                except:
                    pass
    sinister.loop.create_task(check_exit())

@sinister.event
async def on_message(message):
    if message.author.id == sinister.user.id:
        if "start" in message.content.lower():
            await message.channel.send(f"The ``prefix`` is `{prefix}`")
    if isinstance(message.channel, discord.DMChannel):  
        if message.author.id in blocked_users:
            return
    await sinister.process_commands(message)

@sinister.event
async def on_command(ctx):
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"[{current_time}] ({ctx.command}) command used by {ctx.author.name}#{ctx.author.discriminator} in {ctx.guild.name if ctx.guild else 'DM'}")

@sinister.command()
async def block_dm(ctx, user: discord.User):
    blocked_users.add(user.id)
    await ctx.send(f"Blocked DMs from {user.name}.", delete_after=3)

@sinister.command()
async def unblock_dm(ctx, user: discord.User):
    blocked_users.discard(user.id)
    await ctx.send(f"Unblocked DMs from {user.name}.", delete_after=3)

@sinister.command()
async def ping(ctx):
    latency = round(sinister.latency * 1000)
    response = f"> Latency `{latency}`ms"
    await ctx.message.delete()
    await ctx.send(response, delete_after=3)

@sinister.command()
async def z(ctx, status: str, *, message: str):
    if status.lower() == "game" or status.lower() == "gaming":
        activity = discord.Game(name=message)
        await sinister.change_presence(activity=activity)
        await ctx.send(f"Status changed to ``Playing Game``: {message}", delete_after=5)
    elif status.lower() == "stream" or status.lower() == "streaming":
        activity = discord.Streaming(name=message, url="https://www.twitch.tv/404")
        await sinister.change_presence(activity=activity)
        await ctx.send(f"Status changed to ``Streaming``: {message}", delete_after=5)
    elif status.lower() == "watching":
        activity = discord.Activity(type=discord.ActivityType.watching, name=message)
        await sinister.change_presence(activity=activity)
        await ctx.send(f"Status changed to ``Watching``: {message}", delete_after=5)
    else:
        await ctx.send("Please specify the status as ``game``, ``stream``, or ``watching``.", delete_after=5)
    await ctx.message.delete()

@sinister.command()
async def d(ctx, *, message: str):
    try:
        count = int(message.split()[-1])
        message_text = " ".join(message.split()[:-1])
    except ValueError:
        await ctx.send("Must be a positive integer!", delete_after=3)
        return
    if count <= 0:
        await ctx.send("Must be a positive integer!", delete_after=3)
        return

    async def send_messages():
        for _ in range(count):
            if current_task is None:
                break
            await ctx.send(message_text)
    
    global current_task
    current_task = sinister.loop.create_task(send_messages())

    await ctx.message.delete()

@sinister.command()
async def ds(ctx):
    global current_task
    if current_task is not None:
        current_task.cancel()
        current_task = None
        await ctx.send("Message spamming has been stopped.", delete_after=3)
    else:
        await ctx.send("No active spamming task to stop.", delete_after=3)

    await ctx.message.delete()

@sinister.command()
async def c(ctx, amount: int):
    if amount <= 0:
        await ctx.send("Must be a positive integer!", delete_after=3)
        return

    deleted = 0
    messages_to_delete = []

    async for message in ctx.channel.history(limit=100):
        if len(messages_to_delete) >= amount:
            break

        if message.author == ctx.author:
            messages_to_delete.append(message)

    for message in messages_to_delete:
        try:
            await message.delete()
            deleted += 1
        except discord.errors.NotFound:
            continue

    await ctx.send(f"Deleted {deleted} messages", delete_after=3)

@sinister.command()
async def util(ctx):
    prefix = ctx.prefix
    help_text = f"""
    **Utils:**
    ``{prefix}h [Seconds]``: Promotion
    ``{prefix}c [Number of messages to delete]``: Delete Messages
    ``{prefix}z [Game,Watch,Stream] [Message]``: Change Discord status message
    ``{prefix}d [Message] [Count]``:Spam 
    ``{prefix}ds``: Stop Spaming
    ``{prefix}ping``: Check Ping
    ``{prefix}userinfo`` [@Mention]: Check User info
    ``{prefix}block_dm [@Mention]``: Block DMs from a user
    ``{prefix}unblock_dm [@Mention]``: Unblock DMs from a user
    """
    await ctx.send(help_text)

@sinister.command()
async def userinfo(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    if isinstance(member, discord.User):
        user_info = f"**User Info - {member}**\n\n"
        user_info += f"**ID**: {member.id}\n"
        user_info += f"**Account Created**: {member.created_at.strftime('%B %d, %Y')}\n"
        user_info += f"**Status**: {str(member.status).capitalize()}\n"
    else:
        user_info = f"**User Info - {member}**\n\n"
        user_info += f"**ID**: {member.id}\n"
        user_info += f"**Account Created**: {member.created_at.strftime('%B %d, %Y')}\n"
        user_info += f"**Nickname**: {member.nick if member.nick else member.name}\n"
        user_info += f"**Status**: {str(member.status).capitalize()}\n"
        user_info += f"**Joined Server**: {member.joined_at.strftime('%B %d, %Y')}\n"
        roles = [role.name for role in member.roles if role.name != "@everyone"]
        user_info += f"**Roles**: {', '.join(roles) if roles else 'None'}"
    user_info += f"\n**Profile Picture**: {member.avatar_url}"
    await ctx.send(user_info)

@sinister.command()
async def setprefix(ctx, new_prefix: str):
    """Change the bot's command prefix and update the .env file"""
    if len(new_prefix) > 3:
        await ctx.send("Prefix can't be longer than 3 characters.", delete_after=5)
        return

    with open('.env', 'r') as file:
        lines = file.readlines()

    with open('.env', 'w') as file:
        for line in lines:
            if line.startswith('PREFIX='):
                file.write(f'PREFIX={new_prefix}\n')
            else:
                file.write(line)
    
    global prefix
    prefix = new_prefix
    sinister.command_prefix = new_prefix

    await ctx.send(f"Prefix has been changed to `{new_prefix}`.", delete_after=5)

sinister.run(token, bot=False)
