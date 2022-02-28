from typing import Any
from baseModel import BaseModel
from dataclasses import dataclass
from dataclasses import field, asdict
from bson.objectid import ObjectId
from datetime import datetime

@dataclass
class RegistrationTemplate:
    name:str
    serverId:int
    _id:ObjectId = field(default_factory=ObjectId)
    participantFields:list = field(default_factory=list)
    teamFields:list = field(default_factory=list)
    teamSize = 1
    members:list = field(default_factory=list)

    @staticmethod
    def fromDict(d):
        base = BaseModel.fromDict(d, RegistrationTemplate)
        if base.participantFields:
            base.participantFields = list(map(lambda x: BaseModel.fromDict(x, RegistrationField), base.participantFields))
        if base.teamFields:
            base.teamFields = list(map(lambda x: BaseModel.fromDict(x, RegistrationField), base.teamFields))
        return base

@dataclass
class Participant(BaseModel):
    """"Represents a registered player in a tournament"""
    # TODO need to make discordId not required,
    discordId:int
    discordDisplayname:str
    registeredTime:datetime
    tournament:ObjectId
    _id:ObjectId = field(default_factory=ObjectId)
    template:ObjectId = None
    checkedIn:datetime = None
    position:int = None
    fields:list = field(default_factory=list)
    overrideChecks:bool = False
    playerData:Any = field(default_factory=dict) # this is for game specific data, actually should type BasePlayer

    @staticmethod
    def fromDict(d):
        base = BaseModel.fromDict(d, Participant)
        if base.fields:
            base.fields = list(map(lambda x: BaseModel.fromDict(x, RegistrationField), base.fields))
        return base
    

@dataclass
class RegistrationField:
    name:str
    fieldType:int
    required:bool
    value:Any = None

    @staticmethod
    def fromDict(d):
        base = BaseModel.fromDict(d, RegistrationField)
        base.value = d.get("value",None)
        return base




class RegistrationError(Exception):
    def __init__(self, data, errorType:int):    
        self.data = data
        self.errorType = errorType
    def __str__(self):
        return repr(self.data)
