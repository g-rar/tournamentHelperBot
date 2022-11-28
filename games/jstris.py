import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime
from json import JSONDecodeError
import json
import math
import aiohttp
from bson import ObjectId
from interactions import CommandContext, Embed, File, Guild, Option, OptionType
from interactions.ext import files
import pandas as pd
from io import StringIO
from functools import cmp_to_key

from baseModel import BaseModel
from bot import bot, botGuilds
from controllers.playerController import participantController
from games.base_game_classes import BaseGameController, BasePlayer
from games.factories import addModule
from models.registrationModels import Participant, RegistrationError, RegistrationField, RegistrationTemplate
from models.tournamentModels import Tournament

from local.names import StringsNames

from contextExtentions.customContext import ServerContext, customContext
from controllers.tournamentController import tournamentController
from controllers.adminContoller import adminCommand

from commands.tournamentCommands import tournamentBaseCommand
from utils import OptionTypes

# TODO make a more elegant way to implement this


@dataclass
class JstrisPlayer(BasePlayer):
    # should I add
    _id:str = None
    jstris_username:str = ""
    rating:float = 0
    rd:float = 0
    vol:float = 0

    @staticmethod
    def fromDict(d):
        return BaseModel.fromDict(d, JstrisPlayer)


@dataclass
class JstrisTournament(Tournament):
    game:str = "jstris"

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

    # use parents' getParticipantView

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
            player = await JstrisController.getJstrisPlayer(username, session)

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

    async def checkParticipants(self, participants: list[Participant], tournament):
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
            coros = [validatePlayer(p, tournament, session) for p in participants]
            await asyncio.gather(*coros)

        for participant in participants:
            try:
                newFields, playerData = self.validateFields(
                    participant.fields, tournament, review=True)
                participant.playerData = playerData
                participant.fields = newFields
                newParticipants.append(participant)
            except Exception as e:
                failed.append((participant, str(e)))
        return newParticipants, failed

    async def getJstrisPlayer(username:str, session) -> JstrisPlayer:
        # g.rar's instance is IP whitelisted for this API
        api = "https://jeague-dev.tali.software/api/MTTO"

        if session:
            s = session
        else:
            s = aiohttp.ClientSession()

        async def getJstrisMMData(username:str):
            async with s.get(f"{api}/{username}") as r:
                try:
                    return r.status, json.loads(await r.text())
                except JSONDecodeError as e:
                    return 404, {}        
        
        try:
            resCode, reqData = await getJstrisMMData(username)

            if resCode != 200:
                raise RegistrationError("Player not found", JstrisController.PLAYER_NOT_FOUND)
            
            player:JstrisPlayer = JstrisPlayer.fromDict({
                **reqData,
                "jstris_username": username
            })
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
    ])
@adminCommand
@customContext
async def addTournamentPlain(ctx: CommandContext, scx: ServerContext, name: str):
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
        registrationTemplate=regTemplate
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
    tournamentData = tournamentController.getTournamentFromName(guild.id, tournament)
    if tournamentData is None:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return

    if tournamentData.game != JstrisTournament.game:
        await scx.sendLocalized(StringsNames.TOURNAMENT_GAME_WRONG, name=tournament, game=JstrisTournament.game)
        return

    participants = participantController.getParticipantsForTournament(tournamentId=tournamentData._id)
    if len(participants) == 0:
        await scx.sendLocalized(StringsNames.NO_PARTICIPANTS_IN_TOURNAMENT, tournament=tournament)
        return
    
    def compare(p1:JstrisPlayer, p2:JstrisPlayer):
        rd1 = p1.rd / 173.7178
        rd2 = p2.rd / 173.7178
        rating1 = (p1.rating - 1500) / 173.7178
        rating2 = (p2.rating - 1500) / 173.7178
        mu = 1 / (1 + math.exp((rating2-rating1) / math.sqrt(1 + 3 * (rd1 ** 2 + rd2 ** 2) / (math.pi ** 2))))
        return .5 - mu # make it so its negative when loosing for p1
    
    seeding = sorted(participants, key=cmp_to_key(lambda p1, p2: compare(p1.playerData, p2.playerData)))
    players = [JstrisController.getParticipantView(p) for p in seeding]
    df = pd.DataFrame(players)
    await files.command_send(ctx, files=File(fp=StringIO(df.to_csv()), filename=f"Participants_{datetime.utcnow()}.csv"))

addModule(JstrisController, JstrisPlayer, JstrisPlayer)