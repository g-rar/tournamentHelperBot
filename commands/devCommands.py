from interactions import Channel, ChannelType, Choice, CommandContext, Guild, Message, Option, OptionType
import interactions
from bot import devGuilds, CONF, bot
from controllers.serverController import serverController
from contextExtentions.customContext import ServerContext, customContext
from local.names import StringsNames
from local.lang.utils import utilStrs


def devCommand(f):
    async def wrapper(ctx:CommandContext, *args, **kargs):
        if ctx.author.id != CONF.DEV_ID:
            await ctx.send(utilStrs.ERROR.format("Ṡ̵͘Ö̴́͝L̸̹̽O̵͌͠ ̷̿̄Ė̶̚L̵̃̀ ̶̾̔D̸͂̎I̴̎̓Ȏ̸̇Ś̷̒ ̴̐͘D̷̒͝E̵̔͌S̵̄̉A̴͆͝R̵̊͛R̷͗̌O̴̔̄L̵͆̈́L̴͗̽Ä̶́̓D̸͑̄O̸̿̄R̴͐̕ ̴́̿P̵̋͠U̴̾͑É̴̾D̵̛̀Ě̵̆ ̷̅͆H̴͗͝A̷̋̕C̸̉̚E̵̒́Ŕ̷͝ ̸͛̈E̷͗̓S̸̃͝Õ̷̀"))
            return
        await f(ctx,*args, **kargs)
    return wrapper

@bot.command(name="servers", scope=devGuilds)
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
        Option(name="server_ids", description="If present, only send the notification to these servers (comma separated)",
                        type=OptionType.STRING, required=False)
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
    for server in servers:
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
        await chn.send(content=f"{oprStr}{str(msg.content)}")
    await ctx.send("Finished sending messages.")
