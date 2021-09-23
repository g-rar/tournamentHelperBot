import pandas as pd

from typing import Callable
import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.model import BaseCommandObject, SubcommandObject

from dotenv import load_dotenv
import pprint as pretty_print
from pprint import pprint
import os
load_dotenv()

import traceback
from bot import bot, slash, botGuilds
from controllers import server, tournament

from devCommands.devCommands import devCommand, ping


@devCommand
@slash.slash(
    name="runTests",
    description="Run testing procedure",
    guild_ids=botGuilds,
)
async def runTests(ctx:SlashContext):
    #use this context to run tests

    await tournament.addTournamentPlus.invoke(ctx, **{"name":"TestTournament1", "rank_cap":None, "rank_floor":None})
    assert tournament.tournamentController.getTournamentFromName(ctx.guild_id, "TestTournament1") is not None, "Tournament wasn't added"


if __name__ == "__main__":
    bot.run(os.getenv("BOT_TOKEN"))