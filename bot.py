from dataclasses import dataclass
import logging
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

bot = interactions.Client(token= BotSettings.TOKEN, intents=Intents.ALL)
httpClient = interactions.HTTPClient(BotSettings.TOKEN)
wait_for.setup(bot=bot)
files.setup(bot)

CONF = BotSettings()
botGuilds = interactions.MISSING if not CONF.DEV else CONF.TEST_GUILDS
devGuild = list(map(lambda x: int(x), os.getenv("DEV_GUILD").split(","))) if os.getenv("DEV_GUILD") else []
devLogChannel = int(os.getenv("DEV_LOG_CHANNEL")) if os.getenv("DEV_LOG_CHANNEL") else None


client:MongoClient = MongoClient(os.getenv("DB_CONNECTIONSTR"))
db:Database = client.get_database(name=CONF.DB_NAME)


@bot.event(name='on_ready')
async def on_ready():
    logging.info("Connected to discord")
    print("Connected to discord")

@bot.event(name='on_disconnect')
async def on_disconnect():
    logging.info("Disconnected from discord")
    print("Disconnected from discord")