# from discord.channel import TextChannel
# from discord_slash import SlashContext
from dataclasses import dataclass
from interactions import CommandContext
from contextExtentions.contextServer import ServerGuild, getServerGuild
import logging
# from controllers.serverController import Server

import local.names as strs
from controllers import serverController

@dataclass
class ServerContext:

    server: ServerGuild
    context: CommandContext

    def getStr(self, s:str, **kwargs):
        return self.server.getStr(s,**kwargs)

    def send(self, *args, **kwargs):
        return self.context.send(*args, **kwargs)

    async def sendLocalized(self, s:str, _as_reply=True, **kwargs):
        send = self.context.send if _as_reply else self.context.channel.send
        msg:str = self.getStr(s, **kwargs)
        return await send(msg)
    
    async def sendLog(self, s:str, **kwargs):
        return await self.server.sendLog(s, **kwargs)

        
def customContext(f):
    async def wrapper(ctx:CommandContext, *args, **kwargs):
        s = serverController.getServer(int(ctx.guild_id), upsert=True)
        serverGuild = getServerGuild(s, ctx.guild)
        scx = ServerContext(server=serverGuild, context=ctx)
        await f(ctx, *args, scx=scx, **kwargs)
        return f
    return wrapper