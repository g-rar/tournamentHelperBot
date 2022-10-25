from dataclasses import asdict, dataclass
from contextExtentions.contextServer import ServerGuild
from controllers.serverController import Server
from models.tournamentModels import Tournament

@dataclass
class ContexTournament(Tournament):

    server: ServerGuild = None

def createContextTournament(
    t:Tournament, 
    cserver:ServerGuild = None, 
    server:Server = None
) -> ContexTournament:
    d = asdict(t)
    if cserver:
        return ContexTournament(**d, server=cserver)
    if server:
        pass


def contextTournament(f):
    '''
    Makes all parameters of type 'Tournament' instances of 'ContextTournament'.
    '''
    async def wrapper(*args, **kwargs):
        for i in range(args):
            elem = args[i]
            if isinstance(elem, Tournament):
                args[i] = createContextTournament(elem)
        for k,v in kwargs.items():
            if isinstance(v, Tournament):
                kwargs[k] = createContextTournament(v)
        await f(*args, **kwargs)
        return f
    return wrapper