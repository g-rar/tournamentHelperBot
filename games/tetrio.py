from dataclasses import dataclass
import datetime
import logging
from typing import List
import aiohttp
from interactions import CommandContext, Embed, Option
from ratelimit import RateLimitException, limits

import asyncio
from commands.tournamentCommands import tournamentBaseCommand

from games.factories import addModule
from games.base_game_classes import BaseGameController, BasePlayer

from baseModel import BaseModel
from contextExtentions.customContext import ServerContext, customContext
from local.names import StringsNames
from models.tournamentModels import Tournament
from models.registrationModels import (
    Participant,
    ParticipantRegistrationError,
    RegistrationException,
    RegistrationField,
    RegistrationTemplate
)
from controllers.tournamentController import tournamentController
from controllers.playerController import participantController
from controllers.adminContoller import adminCommand
from controllers.playerController import participantController

from bot import botGuilds

from utils.utils import OptionTypes

tetrioRanks = ["z","d","d+"] + [let + sign for let in "cbas" for sign in ["-","","+"]] + ["ss","u",'x']
tetrioNamePttr = (
    r"(?=^[a-z0-9\-_]{3,16}$)" # length of 3-16, only a-z, 0-9, dash and underscore
    r"(?=^(?!guest-.*$).*)"    # does not start with guest-
    r"(?=.*[a-z0-9].*)"        # has a letter or number somewhere
)

def _rankIndex(r:str):
    return tetrioRanks.index(r)

# tetrio api logging
api_logger = logging.getLogger("tetrio")
api_logger.setLevel(logging.INFO)
api_handler = logging.FileHandler("tetrio_api.log")
api_handler.setLevel(logging.INFO)
api_logger.addHandler(api_handler)

api_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s'))
api_logger.addHandler(api_handler)

@limits(calls=1, period=1)
async def callApi(url:str, session: aiohttp.ClientSession):
    async with session.get(url) as r:
        api_logger.info(f"{r.status} <- `{url}`")
        if r.status == 429:
            msg = await r.text()
            api_logger.error(f"Rate limited: {msg}")
            raise RegistrationException("🔥 Rate limited", msg)
        elif r.status == 403:
            msg = await r.text()
            api_logger.error(f"Forbidden: {msg}")
            raise RegistrationException("🔥 Forbidden", msg)
        return r.status, await r.json()


@dataclass
class TetrioLeague(BaseModel):
    rank:str
    prev_rank:str
    next_rank:str
    apm:float
    pps:float
    vs:float
    rating:float
    prev_at:int = 0
    next_at:int = 0
    standing:int = 0
    rd:float = 0.0
    decaying:bool = False
    bestrank:str = 'z'
    percentile_rank:str = 'z'

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
    latest_game:str = None
    game:str = "tetr.io"

    @staticmethod
    def fromDict(d):
        base = BaseModel.fromDict(d, TetrioPlayer)
        base._id = base.info._id
        return base


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
    TEAM_FIELDS:list = None
    TR_OVER_TOP:int = 100
    TR_UNDER_BOTTOM:int = 101
    OVERRANKED:int = 102
    UNDERRANKED:int = 103
    UNRANKED:int = 104
    INVALID_PLAYER:int = 105

    def __init__(self):
        super().__init__()
        self.PLAYER_FIELDS:list = [
            RegistrationField(name="Tetr.io username", fieldType=OptionTypes.STRING, required=True)
        ]


    def getParticipantView(self, p:Participant):
        base = super().getParticipantView(p)
        player:TetrioPlayer = p.playerData
        base["TR"] = round(player.info.league.rating, 2) if player.info.league.rating else None
        base["VS"] = round(player.info.league.vs, 2) if player.info.league.vs else None
        base["APM"] = round(player.info.league.apm, 2) if player.info.league.apm else None
        base["PPS"] = round(player.info.league.pps, 2) if player.info.league.pps else None
        base["Sprint"] = round(player.records.sprintTime, 2) if player.records.sprintTime else None
        base["Blitz"] = player.records.blitzScore
        base["Tetr.io_ID"] = player.info._id
        return base

    def addFieldsToEmbed(self, embed:Embed, tournament:TetrioTournament, lang:str):
        embed.add_field(
            name="Rank cap:",
            value=tournament.rankTop.upper() if tournament.rankTop else "N/A",
            inline=True
        )
        embed.add_field(
            name="Rank bottom:",
            value=tournament.rankBottom.upper() if tournament.rankBottom else "N/A",
            inline=True
        )
        embed.add_field(
            name="TR cap:",
            value=tournament.trTop if tournament.trTop else "N/A",
            inline=True
        )
        embed.add_field(
            name="TR bottom:",
            value=tournament.trBottom if tournament.trBottom else "N/A",
            inline=True
        )

    async def validateFields(self, fields:List[RegistrationField], tournament:TetrioTournament, review=False, session=None, override=False):
        newFields = []
        for field in fields:
            if field.name == "Tetr.io username":
                playerData = await self.validatePlayer(field.value, tournament, review, session=session, override=override)
            # if validation fails for some field throws error
            res = self.validateField(field, review)
            newFields.append(res[0])
        return (newFields, playerData)

    async def checkParticipants(self, participants: List[Participant], tournament:TetrioTournament):
        newParticipants = []
        failed = []
        async def validatePlayer(participant:Participant, tournament:TetrioTournament, session):
            try:
                # this is to catch possible name changes                 
                tetrioNameField = next(filter(lambda f: f.name == "Tetr.io username", participant.fields))
                # tetrioNameField.value = participant.playerData._id

                newFields, playerData = await self.validateFields(participant.fields, tournament, review=True, session=session)
                participant.playerData = playerData
                participant.fields = newFields

                # set the registration field back to the player name
                tetrioNameField = next(filter(lambda f: f.name == "Tetr.io username", newFields))
                tetrioNameField.value = participant.playerData.info.username
                 
                newParticipants.append(participant)
            except RegistrationException as e:
                raise e
            except Exception as e:
                failed.append((participant,str(e)))
        
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(participants)):
                await validatePlayer(participants[i], tournament, session)


        return newParticipants, failed

    async def validatePlayer(self, username:str, tournament:TetrioTournament, review=False, session=None, override=False) -> TetrioPlayer:
        try:
            player = await TetrioController.getTetrioPlayer(username, session)
        except RegistrationException as e:
            raise e
        except:
            raise ParticipantRegistrationError("Invalid playername", self.INVALID_PLAYER)
        
        if not override and any([tournament.trBottom, tournament.trTop, tournament.rankBottom, tournament.rankTop]) \
            and player.info.league.rank == 'z':
            raise ParticipantRegistrationError("Unranked", self.UNRANKED)

        if player is None:
            raise ParticipantRegistrationError("Invalid playername", self.INVALID_PLAYER)
        if not review and participantController.getParticipantFromData(tournament._id, {"info._id":player.info._id}):
            raise ParticipantRegistrationError("Tetrio account already registered", self.ALREADY_REGISTERED)
        if not override:
            if tournament.trTop or tournament.trBottom:
                maxTr = await TetrioController.getMaxTr(player.info._id)
                if maxTr is None:
                    raise ParticipantRegistrationError("Couldn't get maxTR", self.INVALID_PLAYER)               
            if tournament.trTop and maxTr >= tournament.trTop:
                raise ParticipantRegistrationError("Max TR over cap", self.TR_OVER_TOP)
            if tournament.trBottom and maxTr <= tournament.trBottom:
                raise ParticipantRegistrationError("Max TR under floor", self.TR_UNDER_BOTTOM)
        
        rankTop, rankBottom = tournament.rankTop, tournament.rankBottom
        if not override and (rankTop or rankBottom):
            achievedOverBottom = False
            if (tournament.rankTop and
                    _rankIndex(player.info.league.rank) > _rankIndex(tournament.rankTop)):
                raise ParticipantRegistrationError("Overranked", self.OVERRANKED)
            bestrank = player.info.league.bestrank
            if rankTop and _rankIndex(bestrank) > _rankIndex(rankTop):
                raise ParticipantRegistrationError("Overranked", self.OVERRANKED)
            if rankBottom and _rankIndex(bestrank) >= _rankIndex(rankBottom):
                achievedOverBottom = True                
            if (rankBottom and not achievedOverBottom and
                    _rankIndex(player.info.league.rank) < _rankIndex(rankBottom)):
                raise ParticipantRegistrationError("Underranked", self.UNDERRANKED)

        
        ####### get player warnings

        if ((tournament.rankTop or tournament.rankBottom or tournament.trTop or tournament.trBottom) 
                and player.info.league.rd > 90):
            # add RD warning if tournament has restrictions, otherwise not needed
            player.warnings.append(f"{StringsNames.TETRIO_HIGH_RD}:{player.info.league.rd}")

        if tournament.rankTop:
            if  (tournament.rankTop != "x" and
                    _rankIndex(player.info.league.rank) == _rankIndex(tournament.rankTop) and
                    _rankIndex(player.info.league.percentile_rank) > _rankIndex(player.info.league.rank)):
                player.warnings.append(f"{StringsNames.TETRIO_PROMOTION_INMINENT}:{player.info.league.percentile_rank.upper()}")
            
            if (_rankIndex(player.info.league.rank) == _rankIndex(tournament.rankTop) and
                    player.info.league.decaying):
                player.warnings.append(StringsNames.TETRIO_PLAYER_DECAYING)

            if (tournament.rankTop != "x" and
                    _rankIndex(player.info.league.rank) == _rankIndex(tournament.rankTop) and 
                    (player.info.league.standing - player.info.league.next_at 
                    < (player.info.league.prev_at - player.info.league.next_at) / 6 )):
                # add warning for standing 5/6'ths of the way to surpass top boundry
                player.warnings.append(StringsNames.TETRIO_NEAR_PROMOTION)
        
        return player
    
    async def getMaxTr(player_id:str) -> int:
        goats_api = "https://api.p1nkl0bst3r.xyz/"
        async with aiohttp.ClientSession() as session:
            async with session.get(goats_api + f"toptr/{player_id}") as r:
                if r.status == 200:
                    # returns and integer value in response body
                    return int(float(await r.text()))
                
    async def getTetrioPlayer(username:str, session):
        api = "https://ch.tetr.io/api/"

        if session:
            s = session
        else:
            s = aiohttp.ClientSession()

        async def callApiWithRetry(url:str, session:aiohttp.ClientSession):
            while True:
                try:
                    resCode, reqData = await callApi(url, session)
                    if resCode == 429:
                        print("rate limited")
                    return resCode, reqData
                except RateLimitException as e:
                    await asyncio.sleep(1)

        async def getPlayerProfile(username:str):
            return await callApiWithRetry(f"{api}users/{username}", s)

        async def getPlayerRecords(username:str):
            return await callApiWithRetry(f"{api}users/{username}/records", s)

        async def getPlayerLatestMatches(id:str):
            return await callApiWithRetry(f"{api}streams/league_userrecent_{id}", s)

        # async def getPlayerNews(id:str):
        #     async with s.get(api + f"news/user_{id}") as r:
        #         return r.status, await r.json()


        try:            
            usr = username.lower()
            resCode, reqData = await getPlayerProfile(usr)

            if resCode != 200:
                # await ctx.send(strs.ERROR.format(f"Error {resCode}"))
                raise ParticipantRegistrationError("Invalid playername", TetrioController.INVALID_PLAYER)

            if not reqData["success"]:
                # await ctx.send(f"⚠ The player '{username}' doesn't seem to exist in tetr.io :/")
                raise ParticipantRegistrationError("Invalid playername", TetrioController.INVALID_PLAYER)

            
            # get records, checks only to be sure
            resCode, reqRecData = await getPlayerRecords(usr)
            if resCode != 200:
                # await ctx.send(strs.ERROR.format(f"Error {resCode}"))
                raise ParticipantRegistrationError("Invalid playername", TetrioController.INVALID_PLAYER)

            if not reqRecData["success"]:
                # await ctx.send(f"⚠ The player '{username}' doesn't seem to exist in tetr.io :/")
                raise ParticipantRegistrationError("Invalid playername", TetrioController.INVALID_PLAYER)


            playerData = reqData["data"]["user"]
            playerRecords = reqRecData["data"]["records"]
            playerDict = {"info":playerData, "records":playerRecords}

            player:TetrioPlayer = TetrioPlayer.fromDict(playerDict)

            # get latest matches
            resCode, reqMatchData = await getPlayerLatestMatches(player.info._id)
            if len(reqMatchData["data"]["records"]):
                d = reqMatchData["data"]["records"][0]["ts"]
                now = datetime.datetime.utcnow()
                lastGame = datetime.datetime.strptime(d, '%Y-%m-%dT%H:%M:%S.%fZ')
                dl = now - lastGame
                if dl.days > 7:
                    player.warnings.append(f"{StringsNames.TETRIO_INACTIVE_FOR_A_WEEK}:{dl.days}")

            if not session:
                await s.close()
            return player
        except Exception as e:
            if not session:
                await s.close()
            raise e




@tournamentBaseCommand.subcommand(
    name="add_tetrio",
    description="Add a tournament for tetr.io integrated game.",
    options=[
        Option(  name="name", description="The tournament's name.",
                        type=OptionTypes.STRING, required=True),
        Option(  name="rank_cap", description="Maximum rank a player can have to register",
                        type=OptionTypes.STRING, required=False),
        Option(  name="rank_floor", description="Minimum rank a player can have to register",
                        type=OptionTypes.STRING, required=False),
        Option(  name="tr_cap", description="Maximum TR a player can have achieved to register",
                        type=OptionTypes.INTEGER, required=False),
        Option(  name="tr_floor", description="If a player has achieved a TR higher than this, they can register",
                        type=OptionTypes.INTEGER, required=False)
    ])
@adminCommand
@customContext
async def addTournamentTetrio(ctx:CommandContext, scx:ServerContext, name:str, rank_cap:str=None, rank_floor:str=None, tr_cap:int=None, tr_floor:int=None):
    game = "tetr.io"
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    if tournamentController.getTournamentFromName(ctx.guild_id, name):
        await scx.sendLocalized(StringsNames.TOURNAMENT_EXISTS_ALREADY, name=name)
        return
    
    #rank checks
    if rank_cap:
        rank_cap = rank_cap.lower()
        if rank_cap not in tetrioRanks:
            await scx.sendLocalized(StringsNames.UNEXISTING_TETRIORANK, rank=rank_cap)
            return
    if rank_floor:
        rank_floor = rank_floor.lower()
        if rank_floor not in tetrioRanks:
            await scx.sendLocalized(StringsNames.UNEXISTING_TETRIORANK, rank=rank_floor)
            return
    if (rank_cap and rank_floor) and _rankIndex(rank_floor) > _rankIndex(rank_cap):
        await scx.sendLocalized(StringsNames.TETRIORANKCAP_LOWERTHAN_RANKFLOOR, rank_cap=rank_cap, rank_floor=rank_floor)
        return
    
    #tr checks
    if (tr_cap and tr_floor) and tr_floor > tr_cap:
        await scx.sendLocalized(StringsNames.TETRIOTRCAP_LOWERTHAN_TRFLOOR, tr_cap=tr_cap, tr_floor=tr_floor)
        return

    controller = TetrioController()
    # uncomment on completing template implementation
    # customTemplate = templatesController.getTemplate(ctx.guild_id, template) # returns [] if doesnt exist
    # customTemplate.participantFields += controller.PLAYER_FIELDS
    templateFields = controller.PLAYER_FIELDS 
    regTemplate = RegistrationTemplate(name=name,serverId=int(ctx.guild_id),participantFields=templateFields)
    tournament = TetrioTournament(name=name, 
        game=game, 
        hostServerId=int(ctx.guild_id), 
        registrationTemplate=regTemplate, 
        rankTop=rank_cap, 
        rankBottom=rank_floor,
        trTop=tr_cap,
        trBottom=tr_floor
    )
    if tournamentController.addTournament(tournament):
        await scx.sendLocalized(StringsNames.TOURNAMENT_ADDED, name=name, game=game)
    else:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)



addModule(TetrioController, TetrioPlayer, TetrioTournament)