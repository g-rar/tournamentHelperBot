import asyncio
import pandas as pd
from io import StringIO
from datetime import datetime
from controllers.adminContoller import adminCommand
from controllers.serverController import Server, serverController
from local.localContext import localized, CustomContext
from local.names import StringsNames

import discord
from discord.file import File
from discord.message import Message
from discord.user import User
from discord.role import Role
from discord.channel import TextChannel
from discord_slash.utils.manage_commands import create_choice, create_option

from bot import botGuilds, slash, bot
from utils import OptionTypes

@slash.slash(
    name="register_server",
    description="Make tournament helper feel welcome on your server.",
    guild_ids = botGuilds,
    options=[]
)
@localized
@adminCommand
async def slashRegisterServer(ctx:CustomContext):
    guildId = ctx.guild_id
    if guildId is None:
        await ctx.sendLocalized(StringsNames.CANT_REGISTER_DM)
        return
    if serverController.getServer(guildId) is not None:
        await ctx.sendLocalized(StringsNames.SERVER_ALREADY_IN)
        return
    server = Server(serverId=guildId)
    if serverController.addServer(server):
        await ctx.sendLocalized(StringsNames.SERVER_REGISTERED)
    else:
        await ctx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)

@slash.subcommand(
    base="config",
    name="language",
    description="Set the language for the responses on this server.",
    guild_ids=botGuilds,
    options=[
        create_option(
            name="language", description="Language in to switch the bot to.",
            option_type=OptionTypes.STRING, required=True,
            choices=[
                create_choice(name="English", value="ENGLISH"),
                create_choice(name="Español", value="SPANISH")
            ]
        )
    ]
)
@adminCommand
@localized
async def setServerLanguage(ctx: CustomContext, language:str):
    guildId = ctx.guild_id
    if guildId is None:
        await ctx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    server = serverController.getServer(guildId)
    if server is None:
        server = Server(serverId=guildId, language=language)
        if not serverController.addServer(server):
            await ctx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
        return
    server.language = language
    if serverController.updateServer(server):
        await ctx.sendLocalized(StringsNames.LANGUAGE_CHANGED)
    else:
        await ctx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)


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
@localized
async def getReactions(ctx:CustomContext, channel:TextChannel, message_id:str):
    if channel.type != discord.ChannelType.text:
        await ctx.sendLocalized(StringsNames.VALUE_SHOULD_BE_TEXT_CHANNEL, option="channel")
        return
    if not message_id.isdecimal():
        await ctx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    if ctx.guild_id is None:
        await ctx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    messageId = int(message_id)
    try:
        msg:Message = await channel.fetch_message(messageId)
    except Exception as e:
        await ctx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    
    def check(_, user):
        return user == ctx.author
    try:
        res1 = await ctx.sendLocalized(StringsNames.INPUT_CHECK_IN_REACTION)
        inputReaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send(StringsNames.REACTION_TIMEOUT, time="60")
        return
    reaction = list(filter(lambda x: x.emoji == inputReaction.emoji, msg.reactions))
    if reaction == []:
        await ctx.sendLocalized(StringsNames.NO_REACTION_IN_MSG, reaction=str(inputReaction.emoji))
        return
    reaction = reaction[0]
    participants = []
    async for user in reaction.users():
        usr:User = user._user
        participants.append(f"{usr.name}#{user.discriminator}")
    df = pd.DataFrame(participants)
    await ctx.send(file=File(StringIO(df.to_csv(index=False,header=False)), filename= f"Participants_{datetime.utcnow()}.txt"))
