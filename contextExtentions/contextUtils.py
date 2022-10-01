
import logging
from interactions import CommandContext
import local.names as strs

from contextExtentions.contextServer import getServerGuild

# still need an abstraction to bundle the Guild and Server...
# im picturing still a decorator

def getStr(ctx:CommandContext, s:str, **kwargs):
    if not hasattr(strs.StringsNames, s):
        return s
    language = strs.languages.get(ctx.language, strs.EnglishStrs)
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

def getStr(ctx:CommandContext, s:str, **kwargs):
    getServerGuild(s, ctx.guild)
    return ctx.server.getCtxStr(s, **kwargs)


async def sendLocalized(ctx:CommandContext, s:str, _as_reply=True, **kwargs):
    
    send = ctx.send if _as_reply else ctx.channel.send
    msg:str = getStr(ctx, s, **kwargs)
    return await send(msg)
