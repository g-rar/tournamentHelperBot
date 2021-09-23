from dataclasses import dataclass
from dataclasses import field, asdict

from pymongo.collection import Collection
from pymongo.database import Database
from bson.objectid import ObjectId

from utils import getQueryAsList

from baseModel import BaseModel

from bot import db

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

    def getServer(self, serverId: int, upsert:bool = False) -> Server:
        c = self.collection.find_one({"serverId":serverId})
        if c is None:
            if not upsert:
                return None
            server = Server(serverId)
            wasAdded = self.addServer(server)
            return server if wasAdded else None
        obj = Server.fromDict(c)
        return obj

    def getServers(self):
        c = self.collection.find()
        d = getQueryAsList(c) if c is not None else []
        return d
    
    def updateServer(self, server:Server) -> bool:
        res = self.collection.find_one_and_replace({"_id":server._id}, asdict(server))
        return bool(res)


serverController = ServerController(db)


