# import pandas as pd

# from typing import Callable
# import discord
# from discord.ext import commands
# from discord_slash import SlashCommand, SlashContext
# from discord_slash.model import BaseCommandObject, SubcommandObject

from dotenv import load_dotenv
import os
load_dotenv()

# import traceback
from bot import bot, botGuilds, CONF
# from controllers import serverController, tournamentController

# from devCommands.devCommands import devCommand, ping

# if CONF.DEV:
#     @devCommand
#     @slash.slash(
#         name="runTests",
#         description="Run testing procedure",
#         guild_ids=botGuilds,
#     )
#     async def runTests(ctx:SlashContext):
#         #use this context to run tests

#         await tournament.addTournamentPlus.invoke(ctx, **{"name":"TestTournament1", "rank_cap":None, "rank_floor":None})
#         assert tournament.tournamentController.getTournamentFromName(ctx.guild_id, "TestTournament1") is not None, "Tournament wasn't added"


# if __name__ == "__main__":
#     bot.run(os.getenv("BOT_TOKEN"))

import interactions

# bot = interactions.Client(os.getenv("BOT_TOKEN"))

# testGuilds = list(map(lambda x: int(x), os.getenv("TEST_GUILDS").split(","))) if os.getenv("TEST_GUILDS") else []

@bot.command(
    name="my_first_command",
    description="This is the first command I made!",
    scope=botGuilds,
)
async def my_first_command(ctx: interactions.CommandContext):
    await ctx.send("Hi there!")

bot.start()