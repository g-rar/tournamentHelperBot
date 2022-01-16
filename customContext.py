import logging
from discord.channel import TextChannel
from discord_slash import SlashContext
from controllers.serverController import Server

import local.names as strs
from controllers import serverController

class CustomContext(SlashContext):

    server: Server

    def getStr(ctx, s:str, **kwargs):
        if not hasattr(strs.StringsNames, s):
            return s
        language =                                  \
            strs.EnglishStrs if not ctx.server      \
            else strs.languages.get(ctx.server.language, strs.EnglishStrs)
        if s not in language.__members__:
            if s in strs.EnglishStrs.__members__:
                return strs.EnglishStrs[s].value
            else:
                return s
        s = language[s].value
        if kwargs:
            try:
                s = s.format(**kwargs)
            except Exception as e:
                logging.error(f"Error when getting string '{s}' with kwargs '{kwargs}': ", e)
        return s

    async def sendLocalized(ctx, s:str, _as_reply=True, **kwargs):
        send = ctx.send if _as_reply else ctx.channel.send
        msg:str = ctx.getStr(s, **kwargs)
        return await send(msg)
    
    async def sendLog(ctx, s:str, **kwargs):
        if not ctx.server.logChannel:
            return
        logChannel:TextChannel = ctx.guild.get_channel(ctx.server.logChannel)
        msg = ctx.getStr(s)
        return await logChannel.send(msg)

        
def customContext(f):
    async def wrapper(ctx:SlashContext, *args, **kwargs):
        ctx.server = serverController.getServer(ctx.guild_id, upsert=True)
        ctx.getStr = lambda s, **kargs: CustomContext.getStr(ctx, s, **kargs)
        ctx.sendLocalized = lambda s, **kargs: CustomContext.sendLocalized(ctx, s, **kargs)
        ctx.sendLog = lambda s, **kargs: CustomContext.sendLog(ctx, s, **kargs)
        await f(ctx, *args, **kwargs)
        return f
    return wrapper