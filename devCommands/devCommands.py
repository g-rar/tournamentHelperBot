from discord.ext import commands
from discord_slash.context import SlashContext
from bot import bot, CONF, db, slash, botGuilds
from utils import OptionTypes, getQueryAsList

import discord
import discord.ext.commands as cmds
from discord.ext.commands import Bot
from discord import Message, Guild, TextChannel

from pymongo.collection import Collection

import strings as strs
from discord_slash.utils.manage_commands import create_choice, create_option
from pprint import pformat

def devCommand(f):
    async def wrapper(ctx: cmds.Context, *args, **kargs):
        if ctx.author.id != CONF.DEV_ID:
            return
        await f(ctx,*args, **kargs)
    return wrapper

@devCommand    
@bot.command(
    name="devTest"
)
async def devTestCommand(ctx: cmds.Context):
    await ctx.send("Hola mundo en dev")


@devCommand
@bot.command(
    name = "testDB"
)
async def devTest(ctx:cmds.Context):
    testCollection: Collection = db.get_collection("test")
    message:discord.Message = ctx.message
    
    testCollection.insert({"testMessage":message.content if message.content  else "Actually nothing"})
    insertedDoc = getQueryAsList(testCollection.find())
    await ctx.send("The message was " + insertedDoc[0]["testMessage"])
    testCollection.drop()

@slash.slash(
    name="ping",
    description="Test sending a message",
    guild_ids=botGuilds
)
async def ping(ctx:SlashContext):
    await ctx.send("pong")

@slash.slash(
    name="see_commands",
    description="see bot commands",
    guild_ids=botGuilds
)
async def see_commands(ctx:SlashContext):
    await ctx.send(f'''
```py
{pformat(slash.commands)}
```
''')

@slash.slash(
    name="see_subcommands",
    description="see bot subcommands",
    guild_ids=botGuilds
)
async def see_commands(ctx:SlashContext):
    await ctx.send(f'''
```py
{pformat(slash.subcommands)}
```
''')

@slash.slash(
    name="test_local",
    description="test language diversity",
    guild_ids=botGuilds,
    options=[]
)
@devCommand
# @localized
async def testLocalized(ctx:SlashContext):
    ...