from dataclasses import dataclass
from dataclasses import field, asdict

from pymongo.collection import Collection
from pymongo.database import Database
from bson.objectid import ObjectId

import strings as strs
from utils import getQueryAsList

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord_slash.context import SlashContext
from baseModel import BaseModel

from bot import db, bot, botGuilds, slash, CONF
from devCommands.devCommands import devCommand

@dataclass
class Server(BaseModel):
    serverId: int
    _id: ObjectId = field(default_factory=ObjectId)
    guildTournaments: list = field(default_factory=list)
    players: list = field(default_factory=list)
    participantRegFields: list = field(default_factory=list)
    teamRegFields: list = field(default_factory=list)
    adminRoles: list = field(default_factory=list)
    adminUsers: list = field(default_factory=list)

    @staticmethod
    def fromDict(d):
        return BaseModel.fromDict(d, Server)

class ServerController:

    collectionStr:str = "SERVER"
    collection:Collection = db.get_collection(collectionStr)

    def __init__(self, database: Database) -> None:
        self.db = database

    def addServer(self, server: Server):
        res = self.collection.insert_one(asdict(server))
        return res.acknowledged

    def getServer(self, serverId: int) -> Server:
        c = self.collection.find_one({"serverId":serverId})
        if c is None:
            return None
        obj = Server.fromDict(c)
        return obj

    def getServers(self):
        c = self.collection.find()
        d = getQueryAsList(c) if c is not None else []
        return d

serverController = ServerController(db)


@slash.slash(
    name="registerServer",
    guild_ids= botGuilds
)
async def slashRegisterServer(ctx:SlashContext):
    guildId = ctx.guild_id
    if guildId is None:
        await ctx.send(strs.SpanishStrs.CANT_REGISTER_DM)
        return
    if serverController.getServer(guildId) is not None:
        await ctx.send(strs.SpanishStrs.SERVER_ALREADY_IN)
        return
    server = Server(serverId=guildId)
    if serverController.addServer(server):
        await ctx.send(strs.SpanishStrs.SERVER_REGISTERED)
    else:
        await ctx.send(strs.SpanishStrs.DB_UPLOAD_ERROR)





