from dataclasses import asdict
from datetime import datetime

from interactions import Snowflake

from games.factories import getGamePlayerData

from models.tournamentModels import Tournament
from models.registrationModels import Participant

from typing import List, Union
from bson.objectid import ObjectId

from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.operations import DeleteOne, ReplaceOne

from utils import getQueryAsList

from bot import db


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

    def getParticipantFromDiscordId(self, playerId: Union[int, Snowflake], tournamentId:ObjectId) -> Participant:
        playerId = int(playerId)
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

    def updateParticipants(self, participants:List[Participant]) -> bool:
        if participants == []:
            return True
        res = self.collection.bulk_write([ReplaceOne({"_id": p._id}, asdict(p)) for p in participants])
        return bool(res.acknowledged)

    def registerPlayer(self, userId:Union[int, Snowflake], userDisplayName:str, tournament:Tournament, fields:list, playerData):
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

    def deleteParticipant(self, tournamentId:ObjectId, playerDiscordId:Union[int,Snowflake]) -> Participant:
        partDict = self.collection.find_one_and_delete({"discordId":int(playerDiscordId),"tournament":tournamentId})
        if not partDict:
            return None
        return Participant.fromDict(partDict)

    def deleteParticipants(self, participants:list[Participant]) -> bool:
        if participants == []:
            return True
        res = self.collection.bulk_write([DeleteOne({"_id": p._id}) for p in participants])
        return bool(res.acknowledged)

participantController = ParticipantController(db)
