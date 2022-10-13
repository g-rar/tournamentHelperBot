# from discord.channel import TextChannel
# from discord_slash import SlashContext
from dataclasses import dataclass
import functools
from interactions import BaseResult, CommandContext
from contextExtentions.contextServer import ServerGuild, getServerGuild
# from controllers.serverController import Server

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

        
def customContext(f, includeBaseResult=False): #gonna just filter out the BaseResult
    @functools.wraps(f)
    async def wrapper(ctx:CommandContext, *args, **kwargs):
        s = serverController.getServer(int(ctx.guild_id), upsert=True)
        serverGuild = await getServerGuild(s, ctx.guild)
        kwargs['scx'] = ServerContext(server=serverGuild, context=ctx)
        if not includeBaseResult: # in cas that I need it
            new_args = []
            for elem in args:
                if not isinstance(elem, BaseResult):
                    new_args.append(elem)
            args = new_args
        await f(ctx, *args, **kwargs)
        return f
    return wrapper