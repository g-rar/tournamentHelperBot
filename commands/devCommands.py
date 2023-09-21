from dataclasses import asdict
from datetime import datetime
from bson import ObjectId
from interactions import Channel, ChannelType, Choice, CommandContext, Embed, Guild, Message, Option, OptionType
import interactions
from bot import devGuild, devLogChannel, CONF, bot, on_command_error
from contextExtentions.contextServer import ServerGuild, getServerGuild
from controllers.serverController import serverController
from contextExtentions.customContext import ServerContext, customContext
from games.tetrio import TetrioController, TetrioTournament
from local.names import StringsNames
from local.lang.utils import utilStrs
from models.registrationModels import Participant, RegistrationField, RegistrationException


def devCommand(f):
    async def wrapper(ctx:CommandContext, *args, **kargs):
        if ctx.author.id != CONF.DEV_ID:
            await ctx.send(utilStrs.ERROR.format("Ṡ̵͘Ö̴́͝L̸̹̽O̵͌͠ ̷̿̄Ė̶̚L̵̃̀ ̶̾̔D̸͂̎I̴̎̓Ȏ̸̇Ś̷̒ ̴̐͘D̷̒͝E̵̔͌S̵̄̉A̴͆͝R̵̊͛R̷͗̌O̴̔̄L̵͆̈́L̴͗̽Ä̶́̓D̸͑̄O̸̿̄R̴͐̕ ̴́̿P̵̋͠U̴̾͑É̴̾D̵̛̀Ě̵̆ ̷̅͆H̴͗͝A̷̋̕C̸̉̚E̵̒́Ŕ̷͝ ̸͛̈E̷͗̓S̸̃͝Õ̷̀"))
            return
        await f(ctx,*args, **kargs)
    return wrapper

@bot.command(name="servers", scope=devGuild)
async def serversBaseCommand(ctx:CommandContext): pass

@serversBaseCommand.subcommand(
    name="notify",
    description="Resend a development related message to all servers. Like updates and maintenance periods.",
    options=[
        Option(name="message_id", description="Message to be resend to the servers",
                        type=OptionType.STRING, required=True),
        Option(name="channel", description="The channel in which the specified message is",
                        type=OptionType.CHANNEL, required=True
        ),
        Option(name="language", description="If present, send the message only to servers cofigured in that language.",
                        type=OptionType.STRING, required=False, 
                        choices=[
                            Choice(name="English", value="ENGLISH"),
                            Choice(name="Español", value="SPANISH")
                        ]),
        Option(name="ping_operators", description="If True, it pings all the operator roles. No matter how many people that is.",
                        type=OptionType.BOOLEAN, required=False),
        Option(name="show_bmac", description="If present, displays the buymeacoffee page",
                        type=OptionType.BOOLEAN, required=False),
        Option(name="server_ids", description="If present, only send the notification to these servers (comma separated)",
                        type=OptionType.STRING, required=False),
    ]
)
@customContext
@devCommand
async def sendNotificationToServers(
        ctx:CommandContext,
        scx:ServerContext,
        message_id:str,
        channel:Channel,
        language:str = None,
        ping_operators:bool = False,
        show_bmac:bool = False,
        server_ids:str = ""):
    if channel.type != ChannelType.GUILD_TEXT:
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_TEXT_CHANNEL, option="channel")
        return
    if not message_id.isdecimal():
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    try:
        msg:Message = await channel.get_message(int(message_id))
    except Exception as e:
        await scx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    options = {"logChannel":{"$ne":None}}
    if language:
        options["language"] = language
    serverIds = server_ids.split(",")
    if server_ids and not all(map(lambda x: x.isdecimal(), serverIds)):
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    elif server_ids:
        options["serverId"] = {"$in":list(map(lambda x: int(x), serverIds))}
    servers = serverController.getServers(options=options)
    server_guilds = [
        await getServerGuild(server, server.serverId)
        for server in servers
    ]
    for server in server_guilds:
        content = msg.content
        if show_bmac and server.show_bmac:
            content += "\n" + "-"*5 + "\n" + server.getStr(StringsNames.BMAC_MSG)
        guild:Guild = await interactions.get(bot, Guild, object_id=server.serverId)
        if not guild:
            ctx.channel.send(f"Server with `id: {server.serverId}` not found!")
            continue
        chn:Channel = await interactions.get(bot, Channel, object_id=server.logChannel)
        if not chn:
            ctx.channel.send(f"Channel with `id: {server.logChannel}` for server with `id:{server.serverId}` not found!")
            continue
        operatorStr = ", ".join(f"<@&{rId}>" for rId in server.adminRoles)
        oprStr = f"[ {operatorStr} ]\n" if operatorStr and ping_operators else ""
        await chn.send(content=f"{oprStr}{str(content)}")
    await ctx.send("Finished sending messages.")

# server leave subcommand
@serversBaseCommand.subcommand(
    name="leave",
    description="Leave a server",
    options=[
        Option(name="server_id", description="The server to leave",
                        type=OptionType.STRING, required=True),
    ]
)
@customContext
@devCommand
async def leaveServer(
        ctx:CommandContext,
        scx:ServerContext,
        server_id:str):
    if not server_id.isdecimal():
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="server_id")
        return
    guild:Guild = await interactions.get(bot, Guild, object_id=int(server_id))
    if not guild:
        await scx.sendLocalized(StringsNames.SERVER_NOT_FOUND, id=server_id)
        return
    await guild.leave()
    # remove server from database
    if serverController.removeServer(server_id):
        await scx.sendLocalized(StringsNames.SERVER_LEFT, name=guild.name)
    else:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)

# server list subcommand
@serversBaseCommand.subcommand(
    name="list",
    description="List all servers the bot is in",
)
@customContext
@devCommand
async def listServers(
        ctx:CommandContext,
        scx:ServerContext):
    servers = serverController.getServers()
    server_guilds: list[ServerGuild] = []
    i = 0
    while i < len(servers):
        server = servers[i]
        try:
            server_guilds.append(await getServerGuild(server, server.serverId))
            i += 1
        except Exception as e:
            servers.remove(server)
            await on_command_error(ctx, e)
            
    embed = Embed(
        title="Servers",
        description="Servers the bot is in",
        color=0xFFBA00
    )
    for server in server_guilds:
        embed.add_field(
            name=f"{server.serverName}",
            value=f"Server id: {server.serverId}\n"
                  f"Language: {server.language}\n"
                  f"Log channel: {server.logChannel}\n"
                  f"Admin roles: {', '.join(map(str, server.adminRoles))}\n"
                  f"Show bmac: {server.show_bmac}\n"
                  f"Server Icon: https://cdn.discordapp.com/icons/{server.serverId}/{server.serverIcon}.png\n"
        )
    await ctx.send(embeds=embed)

# server update all subcommand 
@serversBaseCommand.subcommand(
    name="update_all",
    description="Update all servers",
)
@customContext
@devCommand
async def updateAllServers(
        ctx:CommandContext,
        scx:ServerContext):
    # get all servers, wher the "bot_left" field doesn't exist or is false
    servers = serverController.getServers()
    # get server guilds, considering a guild may not exist anymore
    server_guilds: list[ServerGuild] = []
    i = 0
    while i < len(servers):
        server = servers[i]
        try:
            server_guilds.append(await getServerGuild(server, server.serverId))
            i += 1
        except Exception as e:
            servers.remove(server)
            await on_command_error(ctx, e)
    # update data of guilds in database, like name, icon, etc
    for i in range(len(servers)):
        server = server_guilds[i]
        servers[i].serverName = server.guild.name
        servers[i].serverIcon = server.guild.icon
        serverController.updateServer(servers[i])

    await scx.sendLocalized(StringsNames.SERVERS_UPDATED)

# execption event handlers that send exception info to the dev guild


