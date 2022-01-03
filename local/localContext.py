from discord_slash import SlashContext

import local.names as strs
from controllers import serverController

class CustomContext(SlashContext):
    async def sendLocalized(ctx:SlashContext, s:str, _as_reply=True, **kwargs):
        send = ctx.send if _as_reply else ctx.channel.send
        if not hasattr(strs.StringsNames, s):
            await send(s)
            return
        server = serverController.getServer(ctx.guild_id)
        language =                              \
            strs.EnglishStrs if not server      \
            else strs.languages.get(server.language, strs.EnglishStrs)
        if s not in language.__members__:
            if s in strs.EnglishStrs.__members__:
                return await send(strs.EnglishStrs[s].value.format(**kwargs))
            else:
                return await send(s)
        return await send(language[s].value.format(**kwargs))

def localized(f):
    async def wrapper(ctx:SlashContext, *args, **kwargs):
        ctx.sendLocalized = lambda s, **kargs: CustomContext.sendLocalized(ctx, s, **kargs)
        await f(ctx, *args, **kwargs)
        return f
    return wrapper