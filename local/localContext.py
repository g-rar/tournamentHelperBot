from discord_slash import SlashContext
import discord

import local.strings as strs
from controllers import serverController

class CustomContext(SlashContext):
    async def sendLocalized(ctx:SlashContext, s:str, **kwargs):
        if s not in strs.StringsNames.__members__:
            await ctx.send(s)
            return
        server = serverController.getServer(ctx.guild_id)
        language = \
            strs.Languages.ENGLISH.value if not server \
            else strs.Languages[server.language].value
        await ctx.send(language[s].value.format(**kwargs))

def localized(f):
    async def wrapper(ctx:SlashContext, *args, **kwargs):
        ctx.sendLocalized = lambda s, **kargs: CustomContext.sendLocalized(ctx, s, **kargs)
        await f(ctx, *args, **kwargs)
        return f
    return wrapper