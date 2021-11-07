import asyncio
import pandas as pd
from io import StringIO
from datetime import datetime
from controllers.adminContoller import adminCommand
from controllers.serverController import Server, serverController

import strings as strs

import discord
from discord.file import File
from discord.message import Message
from discord.user import User
from discord.member import Member
from discord.channel import TextChannel
from discord_slash.utils.manage_commands import create_option
from discord_slash.context import SlashContext

from bot import botGuilds, slash, bot
from devCommands.devCommands import devCommand
from utils import OptionTypes



@slash.slash(
    name="registerServer",
    description="Make tournament helper feel welcome on your server.",
    guild_ids = botGuilds
)
@adminCommand
async def slashRegisterServer(ctx:SlashContext):
    guildId = ctx.guild_id
    if guildId is None:
        await ctx.send(strs.SpanishStrs.CANT_REGISTER_DM)
        return
    if serverController.getServer(guildId) is not None:
        await ctx.send(strs.SpanishStrs.SERVER_ALREADY_IN)
        return
    server = Server(serverId=guildId)
    if serverController.addServer(server):
        await ctx.send(strs.SpanishStrs.SERVER_REGISTERED)
    else:
        await ctx.send(strs.SpanishStrs.DB_UPLOAD_ERROR)

@slash.slash(
    name="get_reactions",
    description="Get the discord tags of the users who reacted to a message.",
    guild_ids = botGuilds,
    options= [
        create_option(
            name="channel", description="Channel in which the message is in.",
            option_type=OptionTypes.CHANNEL, required= True
        ),
        create_option(
            name="message_id", description="Message id at which users reacted for check-in, (you can get this by right clicking the message)",
            option_type=OptionTypes.STRING, required=True
        ),
    ]
)
async def getReactions(ctx:SlashContext, channel:TextChannel, message_id:str):
    if channel.type != discord.ChannelType.text:
        await ctx.send(strs.SpanishStrs.VALUE_SHOULD_BE_TEXT_CHANNEL.format(option="channel"))
        return
    if ctx.guild_id is None:
        await ctx.send(strs.SpanishStrs.NOT_FOR_DM)
        return
    messageId = int(message_id)
    try:
        msg:Message = await channel.fetch_message(messageId)
    except Exception as e:
        await ctx.send(strs.SpanishStrs.MESSAGE_NOT_FOUND.format(data =type(e).__name__))
        return
    
    def check(_, user):
        return user == ctx.author
    try:
        res1 = await ctx.send(strs.SpanishStrs.INPUT_CHECK_IN_REACTION)
        inputReaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send(strs.SpanishStrs.REACTION_TIMEOUT.format(time="60"))
        return
    reaction = list(filter(lambda x: x.emoji == inputReaction.emoji, msg.reactions))
    if reaction == []:
        await ctx.send(strs.SpanishStrs.NO_REACTION_IN_MSG.format(reaction=str(inputReaction.emoji)))
        return
    reaction = reaction[0]
    participants = []
    async for user in reaction.users():
        usr:User = user._user
        participants.append(f"{usr.name}#{user.discriminator}")
    df = pd.DataFrame(participants)
    await ctx.send(file=File(StringIO(df.to_csv(index=False,header=False)), filename= f"Participants_{datetime.utcnow()}.txt"))
