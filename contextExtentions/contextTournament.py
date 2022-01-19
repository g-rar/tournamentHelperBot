from dataclasses import asdict, dataclass
from contextExtentions.contextServer import ContextServer
from controllers.serverController import Server
from models.tournamentModels import Tournament
import logging
import local.names as strs

@dataclass
class ContexTournament(Tournament):

    server: ContextServer = None

def createContextTournament(
    t:Tournament, 
    cserver:ContextServer = None, 
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