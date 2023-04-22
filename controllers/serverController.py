from dataclasses import dataclass
from dataclasses import field, asdict
from typing import List, Union
from interactions import Snowflake

from pymongo.collection import Collection
from pymongo.database import Database
from bson.objectid import ObjectId

from utils.utils import getQueryAsList
from utils.encryption import encrypt_value, decrypt_value

from baseModel import BaseModel

from bot import db, CONF

@dataclass
class Server(BaseModel):
    serverId: int
    serverName: str = ""
    logChannel: int = None
    language: str = "ENGLISH"
    _id: ObjectId = field(default_factory=ObjectId)
    guildTournaments: list = field(default_factory=list)
    players: list = field(default_factory=list)
    participantRegFields: list = field(default_factory=list)
    teamRegFields: list = field(default_factory=list)
    adminRoles: list = field(default_factory=list)
    adminUsers: list = field(default_factory=list)
    _salt: str = None
    _challongeEncryptedApiKey: str = None

    @staticmethod
    def fromDict(d):
        return BaseModel.fromDict(d, Server)

class ServerController:

    collectionStr:str = "SERVER"
    collection:Collection = db.get_collection(collectionStr)

    def __init__(self, database: Database) -> None:
        self.db = database

    def addServer(self, server: Server) -> bool:
        res = self.collection.insert_one(asdict(server))
        return res.acknowledged

    def getServer(self, serverId: Union[int, Snowflake], upsert:bool = False) -> Server:
        serverId = int(serverId)
        c = self.collection.find_one({"serverId":serverId})
        if c is None:
            if not upsert:
                return None
            server = Server(serverId)
            wasAdded = self.addServer(server)
            return server if wasAdded else None
        obj = Server.fromDict(c)
        return obj

    def getServers(self, options={}) -> List[Server]:
        c = self.collection.find(options)
        d = getQueryAsList(c) if c is not None else []
        res = list(map(lambda x: Server.fromDict(x), d))
        return res
    
    def updateServer(self, server:Server) -> bool:
        res = self.collection.find_one_and_replace({"_id":server._id}, asdict(server))
        return bool(res)


serverController = ServerController(db)


