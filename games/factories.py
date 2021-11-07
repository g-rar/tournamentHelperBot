from games.default import BaseGameController, BasePlayer
from models.tournamentModels import Tournament
from typing import Dict, List, Union


gameControllers:Dict[str, BaseGameController] = { }

gameParticipants: Dict[str, BasePlayer] = { }

gameTournaments: Dict[str, Tournament] = { }

def addModule(gameController, gameParticipant, gameTournament):
    global gameControllers, gameTournaments, gameParticipants
    gameControllers[gameController.GAME] = gameController
    gameParticipants[gameParticipant.game] = gameParticipant
    gameTournaments[gameTournament.game] = gameTournament


def getControllerFor(tournament:Union[Tournament, str]) -> BaseGameController:
    global gameControllers
    tournamentGame = tournament.game if isinstance(tournament, Tournament) else tournament
    ctr = gameControllers.get(tournamentGame, BaseGameController)
    return ctr()

def getGameTournament(game:str, data:dict) -> Tournament:
    global gameTournaments
    ctr = gameTournaments.get(game, Tournament)
    return ctr.fromDict(data)

def getGamePlayerData(game:str, data:dict) -> Tournament:
    global gameParticipants
    ply = gameParticipants.get(game, None)
    return None if ply is None else ply.fromDict(data)
