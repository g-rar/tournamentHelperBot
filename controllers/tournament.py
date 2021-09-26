import asyncio
from discord import channel
from discord.guild import Guild
from discord.member import Member
from discord.user import User
import pandas as pd
from dataclasses import asdict
from datetime import datetime
from io import StringIO
from pprint import pformat
from typing import List

import discord
from discord.file import File
from discord.channel import TextChannel
from discord.message import Message
from discord_slash.context import SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from pymongo.collection import Collection
from pymongo.database import Database
from bson.objectid import ObjectId
import requests

from bot import db, bot, botGuilds, slash

from models.tournament import Tournament, TournamentRegistration, TournamentStatus
from models.registration import RegistrationField, RegistrationTemplate, RegistrationError

from controllers.player import participantController
from controllers.admin import adminCommand
from games import factories
from games.tetrio import TetrioController, TetrioTournament

import strings as strs
from utils import getQueryAsList, OptionTypes, extractQuotedSubstrs

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

    def getTournamentFromName(self, serverId: int, name:str) -> Tournament:
        c = self.collection.find_one({"hostServerId":serverId,"name":name})
        if c is None:
            return None
        obj = factories.getGameTournament(c["game"], c)
        return obj

    def getTournamentsForServer(self, serverId:int) -> List[Tournament]:
        c = self.collection.find({"hostServerId":serverId})
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

    def registerPlayer(self, member:Member, tournament:Tournament, fields):
        gameController = factories.getControllerFor(tournament)
        newFields, playerData = gameController.validateFields(fields, tournament)
        usr:User = member._user
        displayName = f"{usr.display_name}#{usr.discriminator}"
        participantController.registerPlayer(usr.id, displayName, tournament, newFields, playerData)


tournamentController = TournamentController(db)

