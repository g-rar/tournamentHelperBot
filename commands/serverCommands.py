import asyncio
from datetime import datetime
from io import StringIO
from interactions import Channel, ChannelType, Choice, CommandContext, File, MessageReaction, Option, OptionType, Message
import interactions
from interactions.ext import wait_for
from controllers.adminContoller import adminCommand
from controllers.serverController import Server, serverController
from contextExtentions.customContext import customContext, ServerContext
from local.names import StringsNames

from bot import botGuilds, bot
from httpClient import getAllUsersFromReaction
import pandas as pd

@bot.command(name="config", scope=botGuilds)
async def botServerConfig(ctx: CommandContext): pass

@botServerConfig.subcommand(
    name="init",
    description="Make tournament helper feel welcome on your server.",
)
@customContext
@adminCommand
async def configRegisterServer(ctx:CommandContext, scx:ServerContext):
    i = 0
    guildId = int(ctx.guild_id)
    if guildId is None:
        await ctx.send(scx.getStr(StringsNames.CANT_REGISTER_DM))
        return
    if serverController.getServer(guildId) is not None:
        await scx.sendLocalized(StringsNames.SERVER_ALREADY_IN)
        return
    server = Server(serverId=guildId)
    if serverController.addServer(server):
        await scx.sendLocalized(StringsNames.SERVER_REGISTERED)
    else:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)

@botServerConfig.subcommand(
    name="language",
    description="Set the language for the responses on this server.",
    options=[
        Option(
            name="language", description="Language in to switch the bot to.",
            type=OptionType.STRING, required=True,
            choices=[
                Choice(name="English", value="ENGLISH"),
                Choice(name="Español", value="SPANISH")
            ]
        )
    ]
)
@adminCommand
@customContext
async def setServerLanguage(ctx: CommandContext, scx: ServerContext=None, language:str=None):
    guildId = int(ctx.guild_id)
    if guildId is None:
        await ctx.send(scx.getStr(StringsNames.NOT_FOR_DM))
        return
    server = serverController.getServer(guildId)
    if server is None:
        server = Server(serverId=guildId, language=language, serverName=ctx.guild.name)
        if not serverController.addServer(server):
            await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
        return
    server.language = language
    if serverController.updateServer(server):
        await scx.sendLocalized(StringsNames.LANGUAGE_CHANGED)
    else:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)


@botServerConfig.subcommand(
    name="log_channel",
    description="Set the log channel so the bot sends notifications. Such as dq reasons, or updates/maintenance.",
    options=[
        Option(name="channel", description="Channel to which send log messages",
                        type=OptionType.CHANNEL, required=True)
    ]
)
@adminCommand
@customContext
async def setLogChannel(ctx: CommandContext, scx:ServerContext, channel:Channel):
    guild_id = int(ctx.guild_id)
    if guild_id is None:
        await ctx.send(scx.getStr(StringsNames.NOT_FOR_DM))
        return

    channel_id = int(channel.id)
    if channel.type != ChannelType.GUILD_TEXT:
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_TEXT_CHANNEL, option="channel")
        return
    server:Server = serverController.getServer(guild_id)
    if not server:
        server = Server(serverId=guild_id, logChannel=channel_id, serverName=ctx.guild.name)
        if not serverController.addServer(server):
            await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
        return
    server.logChannel = channel_id
    if serverController.updateServer(server):
        await scx.sendLocalized(StringsNames.SERVER_UPDATED)
    else:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)

# TODO getreactions, probably will change with the library
@bot.command(
    name="get_reactions",
    description="Get the discord tags of the users who reacted to a message.",
    scope=botGuilds,
    options=[
        Option(
            name="channel", description="Channel in which the message is in.",
            type=OptionType.CHANNEL, required= True
        ),
        Option(
            name="message_id", description="Message id at which users reacted for check-in, (you can get this by right clicking the message)",
            type=OptionType.STRING, required=True
        ),
    ]
)
@customContext
async def getReactions(ctx: CommandContext, scx:ServerContext, channel:Channel, message_id:str):
    if channel.type != ChannelType.GUILD_TEXT:
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_TEXT_CHANNEL, option="channel")
        return
    if not message_id.isdecimal():
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    messageId = int(message_id)
    try:
        msg:Message = await channel.get_message(messageId)
    except Exception as e:
        await scx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    
    def check(reaction:MessageReaction):
        return int(reaction.user_id) == int(ctx.author.id)
    try:
        res1 = await ctx.send(scx.getStr(StringsNames.INPUT_CHECK_IN_REACTION))
        inputReaction:MessageReaction = await wait_for.wait_for(bot, 'on_message_reaction_add', timeout=20.0, check=check)
    except asyncio.TimeoutError:
        await scx.send(StringsNames.REACTION_TIMEOUT, time="60")
        return
    reactions = await getAllUsersFromReaction(
        int(channel.id), int(msg.id) , inputReaction.emoji.name
    )
    if reactions == []:
        await scx.sendLocalized(StringsNames.NO_REACTION_IN_MSG, reaction=str(inputReaction.emoji))
        return
    participants = []
    for user in reactions:
        participants.append(f"{user['username']}#{user['discriminator']}")
    df = pd.DataFrame(participants)
    await res1.delete()
    await ctx.channel.send( '-'*20 + f'[ {inputReaction.emoji.name} ]' + '-'*20,
        files=[
            File(filename=f"Reactions_{datetime.utcnow()}.csv", fp=StringIO(df.to_csv(index=False,header=False)))
        ]
    )
