from dataclasses import dataclass
import logging
import traceback
import interactions
from interactions.ext import wait_for, files
from interactions.api.models.flags import Intents
from pymongo import MongoClient
from pymongo.database import Database

import os

testGuilds = list(map(lambda x: int(x), os.getenv("TEST_GUILDS").split(","))) if os.getenv("TEST_GUILDS") else []

@dataclass
class BotSettings:
    TOKEN = os.getenv("BOT_TOKEN")
    DEV_ID = int(os.getenv("DEV_USER_ID")) if os.getenv("DEV_USER_ID") else None
    PREFIX = os.getenv("BOT_PREFIX")
    DB_NAME = os.getenv("DB_NAME")
    TEST_GUILDS = testGuilds
    DEV = bool(os.getenv("DEV"))
    IGNORE_LISTENERS = bool(os.getenv("IGNORE_LISTENERS")) if os.getenv("IGNORE_LISTENERS") else False

bot = interactions.Client(token= BotSettings.TOKEN, intents=Intents.ALL)
httpClient = interactions.HTTPClient(BotSettings.TOKEN, cache=interactions.Cache())
wait_for.setup(bot=bot)
files.setup(bot)

CONF = BotSettings()
botGuilds = interactions.MISSING if not CONF.DEV else CONF.TEST_GUILDS
devGuild = list(map(lambda x: int(x), os.getenv("DEV_GUILD").split(","))) if os.getenv("DEV_GUILD") else []
devLogChannel = int(os.getenv("DEV_LOG_CHANNEL")) if os.getenv("DEV_LOG_CHANNEL") else None
devReportChannel = int(os.getenv("DEV_REPORT_CHANNEL")) if os.getenv("DEV_REPORT_CHANNEL") else None

client:MongoClient = MongoClient(os.getenv("DB_CONNECTIONSTR"))
db:Database = client.get_database(name=CONF.DB_NAME)
# check database connection
db.command("ping")


@bot.event(name='on_ready')
async def on_ready():
    logging.info("Connected to discord")
    print("Connected to discord")

@bot.event(name='on_disconnect')
async def on_disconnect():
    logging.info("Disconnected from discord")
    print("Disconnected from discord")

async def sendErrorWithMessage(msg:interactions.Message, error:str):
    error_msg = str(error)
    if error.__traceback__:
        error_msg = "".join(traceback.format_exception(type(error), error, error.__traceback__))

    logging.error(error_msg)

    if not devLogChannel:
        return
    dev_channel = await interactions.get(bot, interactions.Channel, object_id=devLogChannel)
    if not dev_channel:
        return
    guild = await msg.get_guild()
    if not guild:
        return
    author = msg.author
    channel = await msg.get_channel()
    ctx_info = (
         "-+"*10 + "New error log:" + "-+"*10 + "-\n"
        f"Command: -on message event-\n"
        f"Guild: {guild.name + ' (' + str(guild.id ) + ')' if guild else 'DM'}\n"
        f"User: {author.username} ({author.id})\n"
        f"Channel: {channel.name if channel else 'DM'}\n"
        f"Message: {msg.content if msg else 'N/A'}\n" 
    )
    await dev_channel.send(ctx_info)
    error_info = f"Error: ```fix\n{error_msg}```\n"
    if len(error_info) > 2000: # discord message limit, send messages with chunks of 1950 chars
        dots = ''
        for i in range(0, len(error_info), 1950):
            await dev_channel.send(f"Error: ```fix{dots}\n{error_msg[i:i+1950]}```\n")
            dots = '\n(...)'
    else:
        await dev_channel.send(f"Error: ```fix\n{error_msg}```\n")


@bot.event(name="on_command_error")
async def on_command_error(ctx:interactions.CommandContext, error):
    error_msg = str(error)
    if error.__traceback__:
        error_msg = "".join(traceback.format_exception(type(error), error, error.__traceback__))

    logging.error(error_msg)

    dev_channel = await interactions.get(bot, interactions.Channel, object_id=devLogChannel)

    if not dev_channel:
        return

    # make info of error using ctx: which command, which guild, who invoked it, etc
    ctx_info = (
         "-+"*10 + "New error log:" + "-+"*10 + "-\n"
        f"Command: {ctx.command.name}\n"
        f"Guild: {ctx.guild.name + ' (' + str(ctx.guild_id) + ')' if ctx.guild else 'DM'}\n"
        f"User: {ctx.author.name} ({ctx.author.id})\n"
        f"Channel: {ctx.channel.name if ctx.channel else 'DM'}\n"
        f"Message: {ctx.message.content if ctx.message else 'N/A'}\n" 
    )
    await dev_channel.send(ctx_info)
    error_info = f"Error: ```fix\n{error_msg}```\n"
    if len(error_info) > 2000: # discord message limit, send messages with chunks of 1950 chars
        dots = ''
        for i in range(0, len(error_info), 1950):
            await dev_channel.send(f"Error: ```fix{dots}\n{error_msg[i:i+1950]}```\n")
            dots = '\n(...)'
    else:
        await dev_channel.send(f"Error: ```fix\n{error_msg}```\n")
