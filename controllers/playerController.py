from baseModel import BaseModel
from dataclasses import asdict
from datetime import datetime
from games.factories import getGamePlayerData
from games.default import BaseGameController

from models.tournamentModels import Tournament
from models.registrationModels import Participant, RegistrationError, RegistrationField

from typing import List
from bson.objectid import ObjectId

from pymongo.collection import Collection
from pymongo.database import Database

from utils import getQueryAsList

from bot import db, bot


class ParticipantController:

    collectionStr:str = "PLAYERS"
    collection:Collection = db.get_collection(collectionStr)

    def __init__(self, database: Database) -> None:
        self.db = database

    def addParticipant(self, player: Participant):
        res = self.collection.insert_one(asdict(player))
        return res.acknowledged

    def getParticipantFromId(self, playerId: ObjectId):
        c = self.collection.find_one({"_id":playerId})
        if c is None:
            return None
        obj:Participant = Participant.fromDict(c)
        if obj.playerData:
            obj.playerData = getGamePlayerData(obj.playerData.get("game"), obj.playerData)
        return obj

    def getParticipantFromDiscordId(self, playerId: int, tournamentId:ObjectId) -> Participant:
        c = self.collection.find_one({"discordId":playerId,"tournament":tournamentId})
        if c is None:
            return None
        obj = Participant.fromDict(c)
        if obj.playerData:
            obj.playerData = getGamePlayerData(obj.playerData.get("game"), obj.playerData)
        return obj
    
    def getParticipantFromDisplayName(self, playerDisplayName:str, tournamentId:ObjectId) -> Participant:
        c = self.collection.find_one({"discordDisplayname":playerDisplayName,"tournament":tournamentId})
        if c is None:
            return None
        obj = Participant.fromDict(c)
        if obj.playerData:
            obj.playerData = getGamePlayerData(obj.playerData.get("game"), obj.playerData)
        return obj

    def getParticipantFromData(self, tournamentId:ObjectId , data:dict) -> Participant:
        playerData = {f"playerData.{key}":val for key,val in data.items()}
        c = self.collection.find_one({"tournament":tournamentId, **playerData})
        if c is None:
            return None
        obj = Participant.fromDict(c)
        if obj.playerData:
            obj.playerData = getGamePlayerData(obj.playerData.get("game"), obj.playerData)
        return obj

    def getParticipantsForTournament(self, tournamentId:ObjectId) -> List[Participant]:
        c = self.collection.find({"tournament":tournamentId})
        d = getQueryAsList(c) if c is not None else []
        res = list(map(lambda x: Participant.fromDict(x), d))
        for obj in res:
            if obj.playerData:
                obj.playerData = getGamePlayerData(obj.playerData.get("game"), obj.playerData)
        return res

    def getParticipants(self) -> List[Participant]:
        c = self.collection.find()
        d = getQueryAsList(c) if c is not None else []
        res = list(map(lambda x: Participant.fromDict(x), d))
        for obj in res:
            if obj.playerData:
                obj.playerData = getGamePlayerData(obj.playerData.get("game"), obj.playerData)
        return res

    def updateParticipant(self, participant:Participant) -> bool:
        res = self.collection.update_one({"_id":participant._id}, asdict(participant))
        return bool(res.modified_count)

    def registerPlayer(self, userId:int, userDisplayName:str, tournament:Tournament, fields:list, playerData):
        newParticipant = Participant(
            discordId=userId, 
            discordDisplayname=userDisplayName,
            tournament=tournament._id, 
            registeredTime=datetime.utcnow(), 
            template=tournament.registrationTemplate,
            fields=fields,
            playerData=playerData
        )
        return self.addParticipant(newParticipant)

participantController = ParticipantController(db)
