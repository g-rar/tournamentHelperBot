import asyncio
from dataclasses import dataclass, asdict, fields, field
from tos.player import participantController
from typing import List

import requests

from games.factories import addModule

from models.tournament import Tournament
from baseModel import BaseModel
from games.default import BaseGameController, BasePlayer
from models.registration import Participant, RegistrationError, RegistrationField, RegistrationTemplate
from utils import OptionTypes

@dataclass
class TetrioLeague(BaseModel):
    rank:str
    prev_rank:str
    next_rank:str
    apm:float
    pps:float
    vs:float
    rating:float

    @staticmethod
    def fromDict(d):
        return BaseModel.fromDict(d, TetrioLeague)

@dataclass
class TetrioPlayerRecords(BaseModel):
    sprint:dict = None
    blitz:dict = None
    sprintTime:float = None
    sprintID:str = None
    sprintReplayID:str = None
    sprintTimeStamp:str = None
    blitzScore:int = None
    blitzID:str = None
    blitzReplayID:str = None
    blitzTimeStamp:str = None


    @staticmethod
    def fromDict(d):
        #check if this is from the api by checking if the sprint key exists
        if "sprint" in d.keys():
            return BaseModel.fromDict(d,TetrioPlayerRecords)
            
        #if its from the api grab only the fields we interested in
        spr = d.get("40l", {}).get("record", None)
        bltz = d.get("blitz", {}).get("record",None)
        ins = TetrioPlayerRecords()
        if spr:
            ins.sprintID = spr["_id"]
            ins.sprintReplayID = spr["replayid"]
            ins.sprintTime = spr["endcontext"]["finalTime"]
            ins.sprintTimeStamp = spr["ts"]
        if bltz:
            ins.blitzID = bltz["_id"]
            ins.blitzReplayID = bltz["replayid"]
            ins.blitzScore = bltz["endcontext"]["score"]
            ins.blitzTimeStamp = bltz["ts"]
        return ins        


@dataclass
class TetrioPlayerInfo(BaseModel):
    _id:str
    username: str
    country: str
    league: TetrioLeague
    avatar_revision:int = None

    @staticmethod
    def fromDict(d):
        return BaseModel.fromDict(d, TetrioPlayerInfo)


@dataclass
class TetrioPlayer(BasePlayer):
    _id:str = None
    info:TetrioPlayerInfo = None
    records:TetrioPlayerRecords = None
    game:str = "tetr.io"

    @staticmethod
    def fromDict(d):
        return BaseModel.fromDict(d, TetrioPlayer)


@dataclass
class TetrioTournament(Tournament):
    game:str = "tetr.io"
    rankTop:int = None
    rankBottom:int = None

    @staticmethod
    def fromDict(d):
        base = BaseModel.fromDict(d, TetrioTournament)
        if base.registrationTemplate:
            base.registrationTemplate = RegistrationTemplate.fromDict(base.registrationTemplate)
        return base

class TetrioController(BaseGameController):
    GAME:str = "tetr.io"
    PLAYER_FIELDS:list = [
        RegistrationField(name="Tetr.io username", fieldType=OptionTypes.STRING, required=True)
    ]
    TEAM_FIELDS:list = None
    TR_OVER_TOP:int = 100
    TR_UNDER_BOTTOM:int = 101
    INVALID_PLAYER:int = 102

    def __init__(self):
        super().__init__()

    def getParticipantView(self, p:Participant):
        base = super().getParticipantView(p)
        player:TetrioPlayer = p.playerData
        base["TR"] = round(player.info.league.rating, 2)
        base["VS"] = round(player.info.league.vs, 2)
        base["APM"] = round(player.info.league.apm, 2)
        base["PPS"] = round(player.info.league.pps, 2)
        base["Sprint"] = round(player.records.sprintTime, 2)
        base["Blitz"] = player.records.blitzScore
        return base

    def validateFields(self, fields:List[RegistrationField], tournament:TetrioTournament):
        newFields = []
        for field in fields:
            if field.name == "Tetr.io username":
                playerData = self.validatePlayer(field.value, tournament)
            # if validation fails for some field throws error
            res = self.validateField(field)
            newFields.append(res[0])
        return (newFields, playerData)

    def validatePlayer(self, username:str, tournament:TetrioTournament) -> TetrioPlayer:
        try:
            player:TetrioPlayer = TetrioController.getTetrioPlayer(username)
        except:
            raise RegistrationError("Invalid playername", self.INVALID_PLAYER)
        if tournament.rankTop and player.info.league.rating > tournament.rankTop:
            raise RegistrationError("TR over cap", self.TR_OVER_TOP)
        if participantController.getParticipantFromData(tournament._id, {"info._id":player.info._id}):
            #TODO some funky griefs could go on with this check
            raise RegistrationError("Tetrio account already registered", self.ALREADY_REGISTERED)
        if tournament.rankBottom and player.info.league.rating < tournament.rankBottom:
            raise RegistrationError("TR under floor", self.TR_OVER_TOP)
        return player

    def getTetrioPlayer(username:str):
        api = "https://ch.tetr.io/api/"

        def getPlayerProfile(username:str):
            return requests.get(api + f"users/{username}")

        def getPlayerRecords(username:str):
            return requests.get(api + f"users/{username}/records")

        def getPlayerNews(id:str):
            return requests.get(api + f"news/user_{id}")
        
        usr = username.lower()
        res = getPlayerProfile(usr)
        resCode, reqData = res.status_code, res.json()
        #TODO make this return errors properly

        if resCode != 200:
            # await ctx.send(strs.ERROR.format(f"Error {resCode}"))
            return
        if not reqData["success"]:
            # await ctx.send(f"⚠ The player '{username}' doesn't seem to exist in tetr.io :/")
            return
        
        # get records, checks only to be sure
        res = getPlayerRecords(usr)
        resCode, reqRecData  = res.status_code, res.json()
        if resCode != 200:
            # await ctx.send(strs.ERROR.format(f"Error {resCode}"))
            return
        if not reqRecData["success"]:
            # await ctx.send(f"⚠ The player '{username}' doesn't seem to exist in tetr.io :/")
            return

        playerData = reqData["data"]["user"]
        playerRecords = reqRecData["data"]["records"]
        playerDict = {"info":playerData, "records":playerRecords}

        player:TetrioPlayer = TetrioPlayer.fromDict(playerDict)
        return player

addModule(TetrioController, TetrioPlayer, TetrioTournament)