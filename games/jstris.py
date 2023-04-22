import asyncio
from dataclasses import dataclass
from datetime import datetime
from json import JSONDecodeError
import json
import math
from pprint import pformat
import aiohttp
from interactions import Channel, CommandContext, File, Guild, Message, Option, OptionType
from interactions.ext import files
import pandas as pd
from io import StringIO
from functools import cmp_to_key

from baseModel import BaseModel
from bot import bot, botGuilds
from commands.csvCommands import getCsvTextFromMsg
from controllers.playerController import participantController
from games.base_game_classes import BaseGameController, BasePlayer
from games.factories import addModule
from local.lang.utils import utilStrs
from models.registrationModels import Participant, RegistrationError, RegistrationField, RegistrationTemplate
from models.tournamentModels import Tournament

from local.names import StringsNames

from contextExtentions.customContext import ServerContext, customContext
from controllers.tournamentController import tournamentController
from controllers.adminContoller import adminCommand

from commands.tournamentCommands import tournamentBaseCommand
from utils.utils import OptionTypes

@dataclass
class JstrisPlayer(BasePlayer):
    # should I add
    _id:str = None
    jstris_username:str = ""
    sprintPB: float | None = None
    ultraPB: int | None = None
    rating:float = 0
    rd:float = 0
    vol:float = 0

    @staticmethod
    def fromDict(d):
        return BaseModel.fromDict(d, JstrisPlayer)

def compare(p1:JstrisPlayer, p2:JstrisPlayer):
    rd1 = p1.rd / 173.7178
    rd2 = p2.rd / 173.7178
    rating1 = (p1.rating - 1500) / 173.7178
    rating2 = (p2.rating - 1500) / 173.7178
    mu = 1 / (1 + math.exp((rating2-rating1) / math.sqrt(1 + 3 * (rd1 ** 2 + rd2 ** 2) / (math.pi ** 2))))
    return .5 - mu # make it so its negative when loosing for p1

@dataclass
class JstrisTournament(Tournament):
    game:str = "jstris"
    get_mm: bool = False
    get_sprint: bool = False
    get_ultra: bool = False

    @staticmethod
    def fromDict(d):
        base = BaseModel.fromDict(d, JstrisTournament)
        if base.registrationTemplate:
            base.registrationTemplate = RegistrationTemplate.fromDict(base.registrationTemplate)
        return base


class JstrisController(BaseGameController):
    GAME: str = "jstris"
    TEAM_FIELDS: list = None
    PLAYER_NOT_FOUND: int = 404

    def __init__(self):
        super().__init__()
        self.PLAYER_FIELDS.append(
            RegistrationField(name="Jstris username",
                              fieldType=OptionTypes.STRING,
                              required=True)
        )

    def getParticipantView(self, p:Participant):
        base = super().getParticipantView(p)
        player:JstrisPlayer = p.playerData
        if player.sprintPB:
            base["sprintPB"] = player.sprintPB
        if player.ultraPB:
            base["ultraPB"] = player.ultraPB
        return base

    async def validateFields(self, fields:list[RegistrationField], tournament:JstrisTournament, review=False, session=None, override=False):
        newFields = []
        for field in fields:
            if field.name == "Jstris username":
                playerData = await self.validatePlayer(field.value, tournament, review, session=session, override=override)
            # if validation fails for some field throws error
            res = self.validateField(field, review)
            newFields.append(res[0])

        return (newFields, playerData)

    async def validatePlayer(self, username:str, tournament:JstrisTournament, review=False, session=None, override=False) -> JstrisPlayer:
        # since atm we dont do restrictions on jstris tournaments, just return the player
        try:
            player = await JstrisController.getJstrisPlayer(username, session, tournament)

            if not review and participantController.getParticipantFromData(tournament._id, {"jstris_username":player.jstris_username}):
                raise RegistrationError("Jstris account already registered", self.ALREADY_REGISTERED)

            if player.rd > 100:
                player.warnings.append(f"{StringsNames.TETRIO_HIGH_RD}:{player.rd}")

        except RegistrationError as e:
            if e.errorType == self.ALREADY_REGISTERED:
                raise e
            raise RegistrationError("Player not found", self.PLAYER_NOT_FOUND)
        return player

    def validateField(self, field: RegistrationField, review: bool = False):
        ''' Validate that the value given in the field meets
        the field constraints'''
        try:
            t = self.getFieldType(field.fieldType)
            if field.value is None and field.required:
                raise RegistrationError(
                    field, BaseGameController.REQUIRED_FIELD)
            val = t(field.value)
            field.value = val
            return (field, True)
        except ValueError:
            raise RegistrationError(
                f"Wrong value type for {field.name}: '{field.value}'", BaseGameController.WRONG_TYPE)
        except RegistrationError as e:
            raise e

    async def checkParticipants(self, participants: list[Participant], tournament:JstrisTournament):
        newParticipants = []
        failed = []

        async def validatePlayer(participant:Participant, tournament, session):
            try:
                newFields, playerData = await self.validateFields(participant.fields, tournament, review=True, session=session)
                participant.playerData = playerData
                participant.fields = newFields
            except Exception as e:
                failed.append((participant,str(e)))

        async with aiohttp.ClientSession() as session:
            if not (tournament.get_sprint or tournament.get_ultra):
                coros = [validatePlayer(p, tournament, session) for p in participants]
                await asyncio.gather(*coros)
            else:
                for p in participants:
                    # prevent jstris API from putting cooldowns
                    await validatePlayer(p, tournament, session)
                    await asyncio.sleep(1)

        for participant in participants:
            try:
                newFields, playerData = await self.validateFields(
                    participant.fields, tournament, review=True)
                participant.playerData = playerData
                participant.fields = newFields
                newParticipants.append(participant)
            except Exception as e:
                failed.append((participant, str(e)))
        return newParticipants, failed

    @staticmethod
    async def getJstrisPlayer(username:str, session, tournament:JstrisTournament) -> JstrisPlayer:
        # g.rar's instance is IP whitelisted for this API
        plus_api = "https://jeague-dev.tali.software/api/MTTO"
        base_api = "https://jstris.jezevec10.com/api"

        if session:
            s = session
        else:
            s = aiohttp.ClientSession()

        async def getJstrisMMData(username:str):
            async with s.get(f"{plus_api}/{username}") as r:
                try:
                    return r.status, json.loads(await r.text())
                except JSONDecodeError as e:
                    return 404, {}

        async def getJstrisPredGlicko(username:str):
            async with s.get(f"{plus_api}/{username}?sprintseed=true") as r:
                try:
                    d:dict = json.loads(await r.text())
                    d = {
                        "rating": d.get("rating"),
                        "vol": 0.001,
                        "rd": 200,
                        "_id": "1"*24
                    }
                    return r.status, d
                except Exception as e:
                    return 404, {}

        async def getJstrisSprintData(username:str):
            rescode, data = 429, {}
            while rescode == 429:
                if (cooldown := data.get("headers", {}).get("Retry-After")):
                    await asyncio.sleep(cooldown)
                async with s.get(f"{base_api}/u/{username}/records/1?mode=1") as r:
                    try:
                        rescode, data = r.status, json.loads(await r.text())
                    except JSONDecodeError as e:
                        return 404, {}
            return rescode, data

        async def getJstrisUltraData(username:str):
            rescode, data = 429, {}
            while rescode == 429:
                async with s.get(f"{base_api}/u/{username}/records/5?mode=1") as r:
                    try:
                        rescode, data = r.status, json.loads(await r.text())
                    except JSONDecodeError as e:
                        return 404, {}
            return rescode, data

        try:
            playerRecords = {}
            resCode, reqData = await getJstrisMMData(username)
            predictedGlicko = False
            if resCode != 200:
                resCode, reqData = await getJstrisPredGlicko(username)
                predictedGlicko = True
                if resCode != 200:
                    raise RegistrationError("Player not found", JstrisController.PLAYER_NOT_FOUND)

            if tournament.get_sprint:
                sprint_resCode, sprint_reqData = await getJstrisSprintData(username)
                if sprint_resCode != 200:
                    raise RegistrationError("Player sprint data not found", JstrisController.PLAYER_NOT_FOUND)
                playerRecords["sprintPB"] = sprint_reqData["min"]
        
            if tournament.get_ultra:
                ultra_resCode, ultra_reqData = await getJstrisUltraData(username)
                if ultra_resCode != 200:
                    raise RegistrationError("Player sprint data not found", JstrisController.PLAYER_NOT_FOUND)
                playerRecords["ultraPB"] = ultra_reqData["max"]


            player:JstrisPlayer = JstrisPlayer.fromDict({
                **reqData,
                **playerRecords,
                "jstris_username": username
            })
            if predictedGlicko:
                player.warnings.append(StringsNames.JSTRIS_PREDICTED_GLICKO)
            return player

        except Exception as e:
            if not session:
                await s.close()
            raise e


@tournamentBaseCommand.subcommand(
    name="add_jstris",
    description="Run registration for jstris tournaments.",
    options=[
        Option(name="name", description="The tournament's name.",
               type=OptionType.STRING, required=True),
        # Option(name="get_plus", description="Adds jstris+ data to player data (+1 request on backend) (invisible)",
        #         type=OptionTypes.BOOLEAN, required=False),
        Option(name="get_sprint", description="Adds sprint data to player data (+1 request on backend)",
                type=OptionTypes.BOOLEAN, required=False),
        Option(name="get_ultra", description="Adds ultra data to player data (+1 request on backend)",
                type=OptionTypes.BOOLEAN, required=False)
    ])
@adminCommand
@customContext
async def addTournamentPlain(
        ctx: CommandContext,
        scx: ServerContext,
        name: str,
        # get_plus: bool = True,
        get_sprint: bool = False,
        get_ultra: bool = False
    ):
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    if tournamentController.getTournamentFromName(ctx.guild_id, name):
        await scx.sendLocalized(StringsNames.TOURNAMENT_EXISTS_ALREADY, name=name)
        return
    # uncomment on completing template implementation
    # customTemplate = templatesController.getTemplate(ctx.guild_id, template) # returns [] if doesnt exist
    # customTemplate.participantFields += controller.PLAYER_FIELDS
    controller = JstrisController()
    templateFields = controller.PLAYER_FIELDS
    regTemplate = RegistrationTemplate(name=name, serverId=int(ctx.guild_id), participantFields=templateFields)
    tournament = JstrisTournament(
        name=name,
        hostServerId=int(ctx.guild_id),
        registrationTemplate=regTemplate,
        # get_mm=get_plus,
        get_sprint=get_sprint,
        get_ultra=get_ultra
    )
    if tournamentController.addTournament(tournament):
        await scx.sendLocalized(StringsNames.TOURNAMENT_ADDED, name=name, game=tournament.game)
    else:
        await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)

@bot.command(name="jstris", scope=botGuilds)
async def jstrisBaseCommand(ctx:CommandContext): pass

@jstrisBaseCommand.subcommand(
    name="seed_tournament",
    description="Return players seeded using jstris matchmaking criteria.",
    options=[
        Option(name="tournament", description="The tournament's name.",
               type=OptionType.STRING, required=True),
    ]
)
@adminCommand
@customContext
async def jstrisSeed(ctx:CommandContext, scx:ServerContext, tournament:str):
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    guild:Guild = ctx.guild # this could be None
    tournamentData:JstrisTournament = tournamentController.getTournamentFromName(guild.id, tournament)
    if tournamentData is None:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return

    if tournamentData.game != JstrisTournament.game:
        await scx.sendLocalized(StringsNames.TOURNAMENT_GAME_WRONG, name=tournament, game=JstrisTournament.game)
        return

    # if not tournamentData.get_mm:
    #     await scx.sendLocalized(StringsNames.)
    
    participants = participantController.getParticipantsForTournament(tournamentId=tournamentData._id)
    if len(participants) == 0:
        await scx.sendLocalized(StringsNames.NO_PARTICIPANTS_IN_TOURNAMENT, tournament=tournament)
        return

    seeding = sorted(participants, key=cmp_to_key(lambda p1, p2: compare(p1.playerData, p2.playerData)))
    players = [JstrisController.getParticipantView(p) for p in seeding]
    df = pd.DataFrame(players)
    await files.command_send(ctx, files=File(fp=StringIO(df.to_csv()), filename=f"Participants_{datetime.utcnow()}.csv"))

@jstrisBaseCommand.subcommand(
    name="seed_file",
    description="Return rows of a csv file on this text channel sorted using jstris matchmaking criteria.",
    options=[
        Option(
            name="message_id", description="Message in which the file is",
            type=OptionType.STRING, required=True
        ),
        Option(
            name="player_col", description="Column name where the jstris players are",
            type=OptionType.STRING, required=True
        ),
    ]
)
@adminCommand
@customContext
async def jstrisSeed(ctx:CommandContext, scx:ServerContext, message_id:str, player_col:str):
    if not message_id.isdecimal():
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    messageId = int(message_id)
    chn:Channel = ctx.channel
    try:
        msg:Message = await chn.get_message(messageId)
    except Exception as e:
        await scx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    try:
        csvs:str = await getCsvTextFromMsg(msg)
        playersDF:pd.DataFrame = pd.read_csv(StringIO(csvs))
        players: list[JstrisPlayer] = []
        errors = []

        async def getPlayer(p, session):
            try:
                players.append(await JstrisController.getJstrisPlayer(p, session))
            except Exception as e:
                errors.append((p, str(e)))

        async with aiohttp.ClientSession() as session:
            coros = [
                getPlayer(p, session)
                for p in playersDF[player_col]
            ]
            await asyncio.gather(*coros)

        playersSorted = sorted(players, key=cmp_to_key(compare))
        playerSeeding = {
            playersSorted[i].jstris_username: i+1
            for i in range(len(playersSorted))
        }
        playersDF["Seeding"] = playersDF[player_col].map(playerSeeding)
        result = playersDF[~playersDF["Seeding"].isnull()]
        result = result.sort_values(by="Seeding")
        result.reset_index(inplace=True)
        result.drop(["index","Unnamed: 0", "Seeding"], axis=1, inplace=True)

        await files.command_send(ctx, files=File(fp=StringIO(result.to_csv()), filename=f"Participants_{datetime.utcnow()}.csv"))
        if len(errors):
            await files.command_send(ctx, files=File(fp=StringIO(pformat(errors)), filename=f"Errors_{datetime.utcnow()}.csv"))

    except Exception as e:
        await ctx.send(utilStrs.ERROR.format(e))


addModule(JstrisController, JstrisPlayer, JstrisTournament)