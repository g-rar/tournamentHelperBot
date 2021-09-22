import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext

from dotenv import load_dotenv
import pprint as pretty_print
from pprint import pprint
import os
load_dotenv()

import traceback
from bot import bot, slash
from tos import server, tournament

import devCommands



if __name__ == "__main__":
    bot.run(os.getenv("BOT_TOKEN"))
    