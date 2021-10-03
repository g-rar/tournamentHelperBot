import asyncio
from dataclasses import dataclass, asdict, fields, field
from controllers.player import participantController
from typing import List

import requests

from games.factories import addModule

from models.tournament import Tournament
from baseModel import BaseModel
from games.default import BaseGameController, BasePlayer
from models.registration import Participant, RegistrationError, RegistrationField, RegistrationTemplate
from utils import OptionTypes

tetrioRanks = ["z","d","d+"] + [let + sign for let in "cbas" for sign in ["-","","+"]] + ["ss","u",'x']
tetrioNamePttr = (
    r"(?=^[a-z0-9\-_]{3,16}$)" # length of 3-16, only a-z, 0-9, dash and underscore
    r"(?=^(?!guest-.*$).*)"    # does not start with guest-
    r"(?=.*[a-z0-9].*)"        # has a letter or number somewhere
)

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
    rankTop:str = None
    rankBottom:str = None
    trTop:int = None
    trBottom:int = None

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
    OVERRANKED:int = 102
    UNDERRANKED:int = 103
    INVALID_PLAYER:int = 105

    def __init__(self):
        super().__init__()

    def getParticipantView(self, p:Participant):
        base = super().getParticipantView(p)
        player:TetrioPlayer = p.playerData
        base["TR"] = round(player.info.league.rating, 2)
        base["VS"] = round(player.info.league.vs, 2)
        base["APM"] = round(player.info.league.apm, 2)
        base["PPS"] = round(player.info.league.pps, 2)
        base["Sprint"] = round(player.records.sprintTime, 2) if player.records.sprintTime else None
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
            player:TetrioPlayer  
            news:dict 
            player, news = TetrioController.getTetrioPlayer(username)
        except:
            raise RegistrationError("Invalid playername", self.INVALID_PLAYER)
        if player is None:
            raise RegistrationError("Invalid playername", self.INVALID_PLAYER)
        if participantController.getParticipantFromData(tournament._id, {"info._id":player.info._id}):
            #TODO some funky griefs could go on with this check
            raise RegistrationError("Tetrio account already registered", self.ALREADY_REGISTERED)
        if tournament.trTop and player.info.league.rating > tournament.trTop:
            raise RegistrationError("TR over cap", self.TR_OVER_TOP)
        if tournament.trBottom and player.info.league.rating < tournament.trBottom:
            raise RegistrationError("TR under floor", self.TR_UNDER_BOTTOM)
        
        if tournament.rankTop or tournament.rankBottom:
            achievedOverBottom = False
            if (tournament.rankTop and
                    tetrioRanks.index(player.info.league.rank) > tetrioRanks.index(tournament.rankTop)):
                raise RegistrationError("Overranked", self.OVERRANKED)
            for new in news:
                if new["type"] == "rankup" and tetrioRanks.index(new["data"]["rank"]) > tetrioRanks.index(tournament.rankTop):
                    raise RegistrationError("Overranked", self.OVERRANKED)
                if new["type"] == "rankup" and tetrioRanks.index(new["data"]["rank"]) >= tetrioRanks.index(tournament.rankBottom):
                    achievedOverBottom = True
            if (tournament.rankBottom and not achievedOverBottom and
                    tetrioRanks.index(player.info.league.rank) < tetrioRanks.index(tournament.rankBottom)):
                raise RegistrationError("Underranked", self.UNDERRANKED)

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
            raise RegistrationError("Invalid playername", TetrioController.INVALID_PLAYER)

        if not reqData["success"]:
            # await ctx.send(f"⚠ The player '{username}' doesn't seem to exist in tetr.io :/")
            raise RegistrationError("Invalid playername", TetrioController.INVALID_PLAYER)

        
        # get records, checks only to be sure
        res = getPlayerRecords(usr)
        resCode, reqRecData  = res.status_code, res.json()
        if resCode != 200:
            # await ctx.send(strs.ERROR.format(f"Error {resCode}"))
            raise RegistrationError("Invalid playername", TetrioController.INVALID_PLAYER)

        if not reqRecData["success"]:
            # await ctx.send(f"⚠ The player '{username}' doesn't seem to exist in tetr.io :/")
            raise RegistrationError("Invalid playername", TetrioController.INVALID_PLAYER)


        playerData = reqData["data"]["user"]
        playerRecords = reqRecData["data"]["records"]
        playerDict = {"info":playerData, "records":playerRecords}

        player:TetrioPlayer = TetrioPlayer.fromDict(playerDict)

        res = getPlayerNews(player._id)
        resCode, reqRecData  = res.status_code, res.json()

        playerNews = reqRecData["data"]["news"]
        
        return player, playerNews

addModule(TetrioController, TetrioPlayer, TetrioTournament)