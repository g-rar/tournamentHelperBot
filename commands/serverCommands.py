import asyncio
from datetime import datetime
from io import StringIO

import interactions
from interactions import Channel, ChannelType, Choice, CommandContext, Embed, File, MessageReaction, Modal, Option, OptionType, Message, TextInput, TextStyleType
from interactions.ext import wait_for, files

from controllers.adminContoller import adminCommand
from controllers.serverController import Server, serverController
from contextExtentions.customContext import customContext, ServerContext
from local.names import StringsNames

from bot import botGuilds, bot, devReportChannel
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
                Choice(name="Español", value="SPANISH"),
                Choice(name="한국어", value="KOREAN")
            ]
        )
    ]
)
@adminCommand
@customContext
async def setServerLanguage(ctx:CommandContext, scx: ServerContext=None, language:str=None):
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
    scx.server.language = language
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
async def setLogChannel(ctx:CommandContext, scx:ServerContext, channel:Channel):
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

@botServerConfig.subcommand(
    name="show_coffee_page",
    description="Decide wether or not to show the buymeacoffe page on update messages.",
    options=[
        Option(name="enabled", description="If False, it will show the buymeacoffee.",
               type=OptionType.BOOLEAN, required=True)
    ]
)
@adminCommand
@customContext
async def no_coffee_sad(ctx:CommandContext, scx:ServerContext, enabled:bool):
    guildId = int(ctx.guild_id)
    if guildId is None:
        await ctx.send(scx.getStr(StringsNames.NOT_FOR_DM))
        return
    server = serverController.getServer(guildId)
    if server is None:
        server = Server(serverId=guildId, show_bmac=False, serverName=ctx.guild.name)
        if not serverController.addServer(server):
            await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
        return
    server.show_bmac = enabled
    if serverController.updateServer(server):
        await scx.sendLocalized(StringsNames.SERVER_UPDATED)
    else:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)


# server subcommand to display server config
@botServerConfig.subcommand(
    name="show",
    description="Show the current server configuration."
)
@adminCommand
@customContext
async def showServerConfig(ctx:CommandContext, scx:ServerContext):
    guildId = int(ctx.guild_id)
    if guildId is None:
        await ctx.send(scx.getStr(StringsNames.NOT_FOR_DM))
        return
    server = serverController.getServer(guildId)
    if server is None:
        await scx.sendLocalized(StringsNames.SERVER_NOT_REGISTERED)
        return
    embed = Embed(
        title=scx.getStr(StringsNames.SERVER_CONFIG_TITLE),
        color=0xFFBA00
    )
    embed.add_field(name=scx.getStr(StringsNames.LANGUAGE), value=server.language, inline=False)
    embed.add_field(
        name=scx.getStr(StringsNames.LOG_CHANNEL), 
        value=f"<#{server.logChannel}>" if server.logChannel else "None", 
        inline=False
    )
    embed.add_field(name=scx.getStr(StringsNames.SHOW_BMAC_PAGE), value=server.show_bmac, inline=False)
    server.adminRoles
    embed.add_field(
        name=scx.getStr(StringsNames.OPERATOR_ROLES), 
        value="\n".join(f"<@&{role}>" for role in server.adminRoles) if server.adminRoles else "None", 
        inline=False
    )

    await scx.send(embeds=embed)

@bot.command(
    name="buy_me_a_coffee",
    description="Show the link to the buymeacoffee page.",
    scope=botGuilds
)
@customContext
async def coffee_pls(ctx:CommandContext, scx:ServerContext):
    await scx.sendLocalized(StringsNames.BMAC_MSG)

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
async def getReactions(ctx:CommandContext, scx:ServerContext, channel:Channel, message_id:str):
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
    await files.command_send(ctx, content='-'*20 + f'[ {inputReaction.emoji.name} ]' + '-'*20,
        files=[
            File(filename=f"Reactions_{datetime.utcnow()}.csv", fp=StringIO(df.to_csv(index=False,header=False)))
        ]
    )


@bot.command(
    name="report_issue",
    description="Report an issue to the bot developer.",
    scope=botGuilds,
)
@adminCommand
@customContext
async def reportIssue(ctx:CommandContext, scx:ServerContext):
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    # create modal where user can input the issue in detail and send it to the developer
    modal = Modal(
        title=scx.getStr(StringsNames.REPORT_ISSUE_MODAL_TITLE),
        custom_id="issue_report_modal",
        components=[
            TextInput(
                style=TextStyleType.SHORT,
                label=scx.getStr(StringsNames.REPORT_ISSUE_TITLE),
                custom_id="issue_report_title",
                min_length=1,
                max_length=100,
            ),
            TextInput(
                style=TextStyleType.PARAGRAPH,
                label=scx.getStr(StringsNames.REPORT_ISSUE_DESC),
                custom_id="issue_report_description",
                min_length=1,
                max_length=2000,
            ),
        ],
    )

    await ctx.popup(modal)


@bot.modal("issue_report_modal")
@customContext
async def mod_app_form(ctx:CommandContext, title:str, description:str, scx:ServerContext):
    await scx.sendLocalized(StringsNames.REPORT_ISSUE_RECEIVED, title=title)
    # send the issue to the developer
    report_channel = await interactions.get(bot, Channel, object_id=devReportChannel)
    ctx_info = (
         "**"+"-+"*10 + "New Issue report!:" + "-+"*10 + "-**\n"
        f"**Guild**: {ctx.guild.name + ' (' + str(ctx.guild_id) + ')' if ctx.guild else 'DM'}\n"
        f"**User**: {ctx.author.name} ({ctx.author.id})\n"
        f"**Channel**: {ctx.channel.name if ctx.channel else 'DM'}\n"
        f"**Details:**\n"
        f"           -  {title}  -\n"
    )
    await report_channel.send(content=ctx_info)
    await report_channel.send(content=description)
