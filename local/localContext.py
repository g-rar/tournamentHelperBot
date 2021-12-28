from discord_slash import SlashContext
import discord

import local.names as strs
from controllers import serverController

class CustomContext(SlashContext):
    async def sendLocalized(ctx:SlashContext, s:str, **kwargs):
        if not hasattr(strs.StringsNames, s):
            await ctx.send(s)
            return
        server = serverController.getServer(ctx.guild_id)
        language = \
            strs.EnglishStrs if not server \
            else strs.languages.get(server.language, strs.EnglishStrs)
        if s not in language.__members__:
            await ctx.send(s)
            return
        return await ctx.send(language[s].value.format(**kwargs))

def localized(f):
    async def wrapper(ctx:SlashContext, *args, **kwargs):
        ctx.sendLocalized = lambda s, **kargs: CustomContext.sendLocalized(ctx, s, **kargs)
        await f(ctx, *args, **kwargs)
        return f
    return wrapper