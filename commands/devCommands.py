import discord
from discord import message
from discord.channel import TextChannel
from discord_slash.utils.manage_commands import create_choice, create_option

from bot import slash, devGuilds, CONF, bot
from controllers.serverController import serverController
from contextExtentions.customContext import CustomContext, customContext
from local.names import StringsNames
from local.lang.utils import utilStrs
from utils import OptionTypes


def devCommand(f):
    async def wrapper(ctx, *args, **kargs):
        if ctx.author.id != CONF.DEV_ID:
            await ctx.send(utilStrs.ERROR.format("Ṡ̵͘Ö̴́͝L̸̹̽O̵͌͠ ̷̿̄Ė̶̚L̵̃̀ ̶̾̔D̸͂̎I̴̎̓Ȏ̸̇Ś̷̒ ̴̐͘D̷̒͝E̵̔͌S̵̄̉A̴͆͝R̵̊͛R̷͗̌O̴̔̄L̵͆̈́L̴͗̽Ä̶́̓D̸͑̄O̸̿̄R̴͐̕ ̴́̿P̵̋͠U̴̾͑É̴̾D̵̛̀Ě̵̆ ̷̅͆H̴͗͝A̷̋̕C̸̉̚E̵̒́Ŕ̷͝ ̸͛̈E̷͗̓S̸̃͝Õ̷̀"))
            return
        await f(ctx,*args, **kargs)
    return wrapper


@slash.subcommand(
    base="servers",
    name="notify",
    description="Resend a development related message to all servers. Like updates and maintenance periods.",
    guild_ids=devGuilds,
    options=[
        create_option(name="message_id", description="Message to be resend to the servers",
                        option_type=OptionTypes.STRING, required=True),
        create_option(name="channel", description="The channel in which the specified message is",
                        option_type=OptionTypes.CHANNEL, required=True
        ),
        create_option(name="language", description="If present, send the message only to servers cofigured in that language.",
                        option_type=OptionTypes.STRING, required=False, 
                        choices=[
                            create_choice(name="English", value="ENGLISH"),
                            create_choice(name="Español", value="SPANISH")
                        ]),
        create_option(name="ping_operators", description="If True, it pings all the operator roles. No matter how many people that is.",
                        option_type=OptionTypes.BOOLEAN, required=False),
        create_option(name="server_ids", description="If present, only send the notification to these servers (comma separated)",
                        option_type=OptionTypes.STRING, required=False)
    ]
)
@customContext
@devCommand
async def sendNotificationToServers(
        ctx:CustomContext,
        message_id:str,
        channel:TextChannel,
        language:str = None,
        ping_operators:bool = False,
        server_ids:str = ""):
    if channel.type != discord.ChannelType.text:
        await ctx.sendLocalized(StringsNames.VALUE_SHOULD_BE_TEXT_CHANNEL, option="channel")
        return
    if not message_id.isdecimal():
        await ctx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    try:
        msg:discord.Message = await channel.fetch_message(int(message_id))
    except Exception as e:
        await ctx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    options = {"logChannel":{"$ne":None}}
    if language:
        options["language"] = language
    serverIds = server_ids.split(",")
    if not all(map(lambda x: x.isdecimal(), serverIds)):
        await ctx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    elif server_ids:
        options["serverId"] = {"$in":list(map(lambda x: int(x), serverIds))}
    servers = serverController.getServers(options=options)
    for server in servers:
        guild:discord.Guild = bot.get_guild(server.serverId)
        if not guild:
            ctx.channel.send(f"Server with `id: {server.serverId}` not found!")
            continue
        chn:discord.TextChannel = guild.get_channel(server.logChannel)
        if not chn:
            ctx.channel.send(f"Channel with `id: {server.logChannel}` for server with `id:{server.serverId}` not found!")
            continue
        operatorStr = ", ".join(f"<@&{rId}>" for rId in server.adminRoles)
        oprStr = f"[ {operatorStr} ]\n" if operatorStr and ping_operators else ""
        await chn.send(content=f"{oprStr}{str(msg.content)}")
    await ctx.send("Finished sending messages.")
