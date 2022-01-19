from discord.channel import TextChannel
from discord_slash import SlashContext
from contextExtentions.contextServer import ContextServer, getContextServerFromServer
from controllers.serverController import Server

import local.names as strs
from controllers import serverController

class CustomContext(SlashContext):

    server: ContextServer

    def getStr(ctx, s:str, **kwargs):
        return ctx.server.getStr(s, **kwargs)

    async def sendLocalized(ctx, s:str, _as_reply=True, **kwargs):
        send = ctx.send if _as_reply else ctx.channel.send
        msg:str = ctx.getStr(s, **kwargs)
        return await send(msg)
    
    async def sendLog(ctx, s:str, **kwargs):
        return await ctx.server.sendLog(ctx.guild, s, **kwargs)

        
def customContext(f):
    async def wrapper(ctx:SlashContext, *args, **kwargs):
        s = serverController.getServer(ctx.guild_id, upsert=True)
        ctx.server = getContextServerFromServer(s, ctx.guild)
        ctx.getStr = lambda s, **kargs: CustomContext.getStr(ctx, s, **kargs)
        ctx.sendLocalized = lambda s, **kargs: CustomContext.sendLocalized(ctx, s, **kargs)
        ctx.sendLog = lambda s, **kargs: CustomContext.sendLog(ctx, s, **kargs)
        await f(ctx, *args, **kwargs)
        return f
    return wrapper