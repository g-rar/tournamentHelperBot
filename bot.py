from dataclasses import dataclass
import logging
import discord
from discord.ext.commands import Bot
from discord_slash import SlashCommand
from pymongo import MongoClient
from pymongo.database import Database

import os

testGuilds = list(map(lambda x: int(x), os.getenv("TEST_GUILDS").split(","))) if os.getenv("TEST_GUILDS") else []

@dataclass
class BotSettings:
    TOKEN = os.getenv("BOT_TOKEN")
    DEV_ID = os.getenv("DEV_USER_ID")
    PREFIX = os.getenv("BOT_PREFIX")
    DB_NAME = os.getenv("DB_NAME")
    TEST_GUILDS = testGuilds
    DEV = bool(os.getenv("DEV"))



bot = Bot(command_prefix=BotSettings.PREFIX, intents=discord.Intents.all())


CONF = BotSettings()
botGuilds = None if not CONF.DEV else CONF.TEST_GUILDS

client:MongoClient = MongoClient(os.getenv("DB_CONNECTIONSTR"))
db:Database = client.get_database(name=CONF.DB_NAME)
slash:SlashCommand = SlashCommand(bot,sync_commands=True)


@bot.listen('on_ready')
async def on_ready():
    logging.info("Connected to discord")

