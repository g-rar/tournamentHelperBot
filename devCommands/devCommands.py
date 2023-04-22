from interactions import CommandContext, Message, Option, OptionType
import interactions
from bot import bot, CONF, db, botGuilds, devGuilds
from contextExtentions.customContext import ServerContext, customContext
from local.names import StringsNames
from utils.utils import getQueryAsList

from pymongo.collection import Collection

from pprint import pformat

def devCommand(f):
    async def wrapper(ctx: CommandContext, *args, **kargs):
        if ctx.author.id != CONF.DEV_ID:
            return
        await f(ctx,*args, **kargs)
    return wrapper

@bot.command(
    name="ping",
    scope=devGuilds
)
@devCommand    
async def devTestCommand(ctx: CommandContext):
    await ctx.send("pong")


@bot.command(
    name = "test-database",
    scope=devGuilds,
    options=[
        Option(name="msg", description="Message to test db", type=OptionType.STRING)
    ]
)
@devCommand
async def devTest(ctx:CommandContext, msg:str):
    testCollection: Collection = db.get_collection("test")    
    testCollection.insert_one({"testMessage": msg if msg  else "Actually nothing"})
    insertedDoc = getQueryAsList(testCollection.find())
    await ctx.send("The message was " + insertedDoc[0]["testMessage"])
    testCollection.drop()


@bot.command(
    name="see_commands",
    description="see bot commands",
    scope=devGuilds
)
async def see_commands(ctx:CommandContext):
    interactions.get()
    await ctx.send(f'''
```py
{pformat(bot._commands)}
```
''')


@bot.command(
    name="test_local",
    description="test language diversity",
    scope=devGuilds,
    options=[]
)
@customContext
async def testLocalized(ctx:CommandContext, scx:ServerContext):
    await scx.sendLocalized(StringsNames.SERVER_REGISTERED)

@bot.command(
    name="test_logchannel",
    description="Test the log channel for this server",
    scope=botGuilds,
    options=[
        Option(name="msg", description="Message to send to the log channel", 
               type=OptionType.STRING, required=False)
    ]
)
@devCommand
@customContext
async def test_logChannel(ctx:CommandContext, scx:ServerContext, msg:str = None):
    if msg == None:
        msg = "Hello world"
    
    await scx.sendLog(msg)
    await ctx.send("If no message was sent to the channel, check that there's a log channel configured")