from dataclasses import asdict, dataclass
from controllers.serverController import Server
from bot import bot
import local.names as strs
import logging
import interactions
from interactions import Guild, Channel
# from discord import Guild, TextChannel

@dataclass
class ServerGuild(Server):

    guild:Guild = None

    def getStr(self, s:str, **kwargs):
        if not hasattr(strs.StringsNames, s):
            return s
        language = strs.languages.get(self.language, strs.EnglishStrs)
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

    async def sendLog(self, s, **kwargs):
        if not self.logChannel:
            return
        logChannel:Channel = await interactions.get(bot, Channel, object_id=self.logChannel)
        msg = self.getStr(s, **kwargs)
        return await logChannel.send(msg)
    
def getServerGuild(server:Server, guild:Guild):
    res = ServerGuild(**asdict(server), guild=guild)
    return res