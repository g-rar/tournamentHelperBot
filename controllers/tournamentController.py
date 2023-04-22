# from discord.member import Member
# from discord.user import User
from dataclasses import asdict
from typing import List, Union
from interactions import Embed, EmbedField, Snowflake, User

from pymongo.collection import Collection
from pymongo.database import Database
from bson.objectid import ObjectId

from bot import db

from models.tournamentModels import Tournament, TournamentRegistration, TournamentStatus
from models.registrationModels import Participant, RegistrationError

from controllers.playerController import participantController
from games import factories

from local.names import StringsNames as strs

from utils.utils import getQueryAsList, getStr

class TournamentController:

    collectionStr:str = "TOURNAMENT"
    collection:Collection = db.get_collection(collectionStr)

    def __init__(self, database: Database) -> None:
        self.db = database

    def addTournament(self, tourney: Tournament):
        res = self.collection.insert_one(asdict(tourney))
        return res.acknowledged

    def getTournamentFromId(self, tourney: ObjectId) -> Tournament:
        c = self.collection.find_one({"_id":tourney})
        if c is None:
            return None
        obj = factories.getGameTournament(c.get("game"), c)
        return obj

    def getTournamentFromName(self, serverId: Union[int, Snowflake], name:str) -> Tournament:
        c = self.collection.find_one({"hostServerId":int(serverId),"name":name})
        if c is None:
            return None
        obj = factories.getGameTournament(c.get("game"), c)
        return obj

    def getTournamentsForServer(self, serverId:Union[int, Snowflake]) -> List[Tournament]:
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
        # make an aggregation with servers that the bot has not left
        c = self.collection.aggregate([
            {"$match":{"registration.status": {"$ne": TournamentStatus.REGISTRATION_CLOSED}}},
            {"$lookup":{"from":"SERVER","localField":"hostServerId","foreignField":"serverId","as":"server"}},
            {"$match":{"server.bot_left":{"$ne":True}}},
        ])
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

    async def checkPlayer(self, tournament:Tournament, participant:Participant, update:bool=False):
        gameController = factories.getControllerFor(tournament)
        newFields, playerData = await gameController.validateFields(participant.fields, tournament, review=True)
        participant.playerData = playerData
        participant.fields = newFields
        if update:
            participantController.updateParticipant(participant)
        return participant

    def getTournamentEmbed(self, tournament:Tournament, lang:str):
        base = Embed(title=tournament.name, color=0xFFBA00, fields=[
                EmbedField(
                    name=f" {getStr(strs.CREATED_AT, lang)}:", 
                    value=f"<t:{int((tournament.createdAt.timestamp()))}:f>", 
                    inline=False
                ),
                EmbedField(
                    name=f" {getStr(strs.REGISTRATION, lang)}:", 
                    value=getStr(strs.OPEN if tournament.registration.status else strs.CLOSED, lang), 
                    inline=True
                ),
                # EmbedField(name="\u200b", value="\u200b", inline=False),
                EmbedField(
                    name=f" {getStr(strs.PARTICIPANT_COUNT, lang)}:",
                    value= f"[   {participantController.getParticipantCountForTournament(tournament._id)}   ]", #TODO call tournament controller on this
                    inline=True
                ),
                EmbedField(
                    name=f"{getStr(strs.GAME, lang)}:",
                    value=tournament.game.capitalize() + "\n\u200b",
                    inline=True
                )
            ])
        gameController = factories.getControllerFor(tournament)
        gameController.addFieldsToEmbed(base, tournament, lang)
        return base

tournamentController = TournamentController(db)

