# from discord.member import Member
# from discord.user import User
from dataclasses import asdict
from typing import List, Union
from interactions import Member, Snowflake, User

from pymongo.collection import Collection
from pymongo.database import Database
from bson.objectid import ObjectId

from bot import db

from models.tournamentModels import Tournament, TournamentRegistration, TournamentStatus
from models.registrationModels import Participant, RegistrationError, RegistrationField

from controllers.playerController import participantController
from games import factories

from utils import getQueryAsList

# TODO for plus games there are mandatory fields and custom field validation
# TODO if its not plus game theres a default valitador (for data types at least)
# TODO if theres no template it only asks for the plus game fields and/or discord info.


class TournamentController:

    collectionStr:str = "TOURNAMENT"
    collection:Collection = db.get_collection(collectionStr)

    def __init__(self, database: Database) -> None:
        self.db = database

    def addTournament(self, tourney: Tournament):
        res = self.collection.insert_one(asdict(tourney))
        return res.acknowledged

    def getTournamentFromId(self, tourney: ObjectId):
        c = self.collection.find_one({"_id":tourney})
        if c is None:
            return None
        obj = Tournament.fromDict(c)
        return obj

    def getTournamentFromName(self, serverId: Union[int, Snowflake], name:str) -> Tournament:
        c = self.collection.find_one({"hostServerId":int(serverId),"name":name})
        if c is None:
            return None
        obj = factories.getGameTournament(c["game"], c)
        return obj

    def getTournamentsForServer(self, serverId:Union[int, Snowflake]) -> list[Tournament]:
        c = self.collection.find({"hostServerId":int(serverId)}, sort=[("createdAt", -1)])
        d = getQueryAsList(c) if c is not None else []
        res = list(map(lambda x: factories.getGameTournament(x.get("game"), x), d))
        return res

    def getTournaments(self) -> List[Tournament]:
        c = self.collection.find()
        d = getQueryAsList(c) if c is not None else []
        res = list(map(lambda x: Tournament.fromDict(x), d))
        return res

    def getOpenTournaments(self) -> List[Tournament]:
        c = self.collection.find({"registration.status":{"$ne":0}})
        d = getQueryAsList(c) if c is not None else []
        res = list(map(lambda x: factories.getGameTournament(x["game"], x), d))
        return res 

    def updateTournament(self, tournament:Tournament) -> bool:
        res = self.collection.find_one_and_replace({"_id":tournament._id}, asdict(tournament))
        return bool(res)

    def updateRegistrationForTournament(self, tournament:Tournament, reg:TournamentRegistration) -> bool:
        regDict = asdict(reg)
        res = self.collection.find_one_and_update({"_id":tournament._id}, {"$set":{"registration":regDict}})
        return bool(res)

    def deleteTournament(self, tournament:Tournament) -> bool:
        res = self.collection.find_one_and_delete({"_id":tournament._id})
        return bool(res)

    # TODO need to add method to register player without it being discord member

    async def registerPlayer(self, tournament:Tournament, fields:list, member:User = None, displayName:str = None, overrideReq:bool = False):
        if tournament.registration.status == TournamentStatus.REGISTRATION_CLOSED:
            raise RegistrationError("Registration for this tournament is currently closed",4)
        gameController = factories.getControllerFor(tournament)
        newFields, playerData = await gameController.validateFields(fields, tournament, override=overrideReq)
        if member:
            if participantController.getParticipantFromDiscordId(int(member.id), tournament._id):
                raise RegistrationError("Discord user already registered in tournament", 3)
            usr_id = int(member.id)
            displayName = f"{member.username}#{member.discriminator}"
        elif displayName:
            usr_id = None
        else:
            raise RegistrationError("Either a discord member or displayName are required to register a player!", 2)
        return participantController.registerPlayer(usr_id, displayName, tournament, newFields, playerData)

    def checkPlayer(self, tournament:Tournament, participant:Participant, update:bool=False):
        gameController = factories.getControllerFor(tournament)
        newFields, playerData = gameController.validateFields(participant.fields, tournament, review=True)
        participant.playerData = playerData
        participant.fields = newFields
        if update:
            participantController.updateParticipant(participant)
        return participant

tournamentController = TournamentController(db)

