from baseModel import BaseModel
from dataclasses import dataclass, field, asdict
from models.registrationModels import RegistrationTemplate
from datetime import datetime

from bson.objectid import ObjectId

@dataclass
class TournamentRegistration(BaseModel):
    status:int = 0
    channelId:int = None
    participantRole:int = None
    
    @staticmethod
    def fromDict(d):
        return BaseModel.fromDict(d, TournamentRegistration)

@dataclass
class TournamentCheckIn(BaseModel):
    status:int = 0
    messageId:int = None
    reaction:str = None
    
    @staticmethod
    def fromDict(d):
        return BaseModel.fromDict(d, TournamentCheckIn)

@dataclass
class Tournament(BaseModel):
    name: str
    hostServerId:int
    game:str
    _id: ObjectId = field(default_factory=ObjectId)
    registrationTemplate:RegistrationTemplate = None
    checkInOpen:int = 0
    createdAt:datetime = field(default_factory=datetime.utcnow)
    registration:TournamentRegistration = field(default_factory=TournamentRegistration)
    participants:list = field(default_factory=list)
    finished:bool=False
    started:bool=False

    @staticmethod
    def fromDict(d):
        base = BaseModel.fromDict(d, Tournament)
        if base.registrationTemplate:
            base.registrationTemplate = RegistrationTemplate.fromDict(base.registrationTemplate)
        return base

class TournamentStatus:
    # registration
    REGISTRATION_CLOSED = 0
    REGISTRATION_OPEN_BY_MSG = 1
    REGISTRATION_OPEN_BY_COMMAND = 2
    # check in
    CHECK_IN_CLOSED = 0
    CHECK_IN_OPEN_BY_REACTION = 1
    CHECK_IN_OPEN_BY_COMMAND = 2
    # idk others
