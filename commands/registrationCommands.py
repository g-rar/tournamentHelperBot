from typing import List
from interactions import Channel, ChannelType, CommandContext, Guild, LibraryException, Message, Option, OptionType, Role
import interactions
from dataclasses import asdict
from pprint import pformat, pprint
from copy import deepcopy
import logging

from bot import bot, botGuilds
from contextExtentions.contextServer import ServerGuild, getServerGuild
from contextExtentions.customContext import ServerContext, customContext
from local.names import StringsNames

from models.tournamentModels import Tournament, TournamentStatus
from models.registrationModels import Participant, RegistrationField, RegistrationError

from controllers.adminContoller import adminCommand
from controllers.serverController import serverController
from controllers.tournamentController import tournamentController

from utils import OptionTypes, extractQuotedSubstrs


# structure follows {channelId: tournamentId}
openRegistrationChannels = {}

@bot.command(name="registration", scope=botGuilds)
async def registrationBase(ctx:CommandContext): pass

@registrationBase.subcommand(
    name="open_in_chat",
    options=[
        Option(name="tournament", description="Tournament to open registration",
            type=OptionType.STRING, required=True),
        Option(name="channel", description="Channel in which participants register",
            required=True, type=OptionType.CHANNEL),
        Option(name="participant_role", description="Role that registered players will be given once they register",
            type=OptionType.ROLE, required=False)
    ])
@adminCommand
@customContext
async def openRegistrationInChat(ctx:CommandContext, scx:ServerContext, tournament:str, channel:Channel, participant_role:Role = None):
    #check stuff is correct
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    if channel.type != ChannelType.GUILD_TEXT:
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_TEXT_CHANNEL, option="channel")
        return
    tournamentObj = tournamentController.getTournamentFromName(int(ctx.guild_id), tournament)
    if tournamentObj is None:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    if tournamentObj.registration.status == TournamentStatus.REGISTRATION_OPEN_BY_MSG:
        registrationChat:Channel = await interactions.get(bot, Channel, object_id=tournamentObj.registration.channelId)
        await scx.sendLocalized(StringsNames.REGISTRATION_OPEN_ALREADY, tournament=tournament, chat=registrationChat.mention)
        return
    # if tournamentObj.registrationTemplate.teamSize != 1:
    #     # TODO add logic for team games
    #     pass
    if participant_role:
        if not ctx.app_permissions.MANAGE_ROLES:
            await scx.sendLocalized(StringsNames.NEED_MANAGE_ROLES)
            return
        tournamentObj.registration.participantRole = int(participant_role.id)
    tournamentObj.registration.status = TournamentStatus.REGISTRATION_OPEN_BY_MSG
    tournamentObj.registration.channelId = int(channel.id)
    tournamentController.updateRegistrationForTournament(tournamentObj, tournamentObj.registration)

    await setupMessageRegistration(tournamentObj)

    # add listener for channel
    await scx.sendLocalized(StringsNames.REGISTRATION_OPEN_CHAT, tournament=tournamentObj.name, chat=channel.mention)


@registrationBase.subcommand(
    name="close",
    options=[
        Option(name="tournament", description="Tournament to close registration for",
            type=OptionType.STRING, required=True)
    ]
)
@adminCommand
@customContext
async def closeRegistration(ctx:CommandContext, scx:ServerContext, tournament:str):
    global openRegistrationChannels
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id, tournament)
    if tournamentObj is None:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    # TODO [multiple registration methods] get from obj the registrationMethod and remove correspondingly
    if tournamentObj.registration.status == TournamentStatus.REGISTRATION_CLOSED:
        await scx.sendLocalized(StringsNames.REGISTRATION_CLOSED_ALREADY, tournament=tournament)
        return

    listener = openRegistrationChannels.get(tournamentObj.registration.channelId)
    if listener:
        openRegistrationChannels.pop(tournamentObj.registration.channelId)
        tournamentObj.registration.status = TournamentStatus.REGISTRATION_CLOSED
        tournamentObj.registration.channelId = None
        tournamentController.updateRegistrationForTournament(tournamentObj, tournamentObj.registration)
    await scx.sendLocalized(StringsNames.REGISTRATION_CLOSED_MSG, tournament=tournament)


@bot.event(name='on_ready')
async def setListenersBackUp():
    #get tournaments
    tournaments = tournamentController.getOpenTournaments()
    if not tournaments:
        return
    logging.info("Setting up tournament listeners...")
    for tournament in tournaments:
        try:
            # TODO [multiple registration methods] add listener setup here
            if tournament.registration.status == TournamentStatus.REGISTRATION_OPEN_BY_MSG:
                regChannel:Channel = await interactions.get(bot, Channel, object_id=tournament.registration.channelId)
                if not regChannel: #channel got deleted or something
                    logging.error(f"Didnt find channel for tournament: {tournament.name}")
                    raise Exception()
                await setupMessageRegistration(tournament)
        except:
            logging.error(f"Closing registration for tournament: {tournament.name}")
            tournament.registration.status = TournamentStatus.REGISTRATION_CLOSED
            tournament.registration.channelId = None
            tournamentController.updateRegistrationForTournament(tournament, tournament.registration)
            s = serverController.getServer(tournament.hostServerId)
            guild:Guild = interactions.get(bot, Guild, object_id=s.serverId)
            server = await getServerGuild(s, guild)
            await server.sendLog(StringsNames.REG_CHANNEL_NOT_FOUND, tournament=tournament.name)
    logging.info("Tournament listeners ready!")
    pass


async def setupMessageRegistration(tournament:Tournament): # this asumes that registration is properly open in db 
    global openRegistrationChannels
    if tournament.registration.channelId in openRegistrationChannels: 
        #prevent from setting two identical listeners
        return
    openRegistrationChannels[tournament.registration.channelId] = tournament._id

def getWarningsMsg(server:ServerGuild, tournament:str, playerData:Participant, msg:Message = None):
    warnings: list[str] = playerData.playerData.warnings
    warning_msg = server.getStr(StringsNames.PARTICIPANT_HAS_WARNINGS, username=playerData.discordDisplayname, tournament=tournament)
    for warning in warnings:
        warning:str
        str_name, *args = warning.split(':')
        try:
            warning_item = server.getStr(str_name).format(*args)
            warning_msg += f"- {warning_item}\n"
        except Exception:
            warning_msg += f"- {str_name}\n" 
    if msg:
        warning_msg += "--> " + server.getStr(StringsNames.PARTICIPANT_REGISTRATION_MSG_LINK, username=playerData.discordDisplayname, msg_url=msg.url)
    return warning_msg

@bot.event(name="on_message_create")
async def on_message(msg:Message):
    if int(msg.channel_id) not in openRegistrationChannels:
        return
    if not msg.content:
        await msg.create_reaction("🤔")
        await msg.create_reaction("❓")
        return
    
    tournamentId = openRegistrationChannels.get(int(msg.channel_id))
    tournament = tournamentController.getTournamentFromId(tournamentId)

    guild = await msg.get_guild()
    s = serverController.getServer(guild.id)
    server = await getServerGuild(s, guild)
    role = await interactions.get(bot, Role, object_id=tournament.registration.participantRole, parent_id=guild.id) \
            if tournament.registration.participantRole \
            else None

    content = extractQuotedSubstrs(msg.content)
    fields: List[RegistrationField] = deepcopy(tournament.registrationTemplate.participantFields)
    try:
        if fields:
            for i in range(len(content)):
                fields[i].value = content[i]
        else:
            fields.append(RegistrationField("msg", OptionTypes.STRING, True, value=msg.content))
        playerData = await tournamentController.registerPlayer(tournament, fields, msg.author)
        if playerData:
            await msg.create_reaction("✅")
            if role:
                await msg.member.add_role(role)
            if len(playerData.playerData.warnings) != 0:
                warnings_msg = getWarningsMsg(server, tournament.name, playerData, msg=msg)
                await server.sendLog(warnings_msg, localize=False)
        else:
            logging.error("Failed to upload to db.")
            await server.sendLog(StringsNames.PARTICIPANT_REGISTRATION_FAILED, name=msg.member.name, tournament=tournament.name, reason="DB UPLOAD ERROR")
            await msg.create_reaction("🆘")
    except RegistrationError as e:
        await msg.create_reaction("❌")
        await server.sendLog(StringsNames.PARTICIPANT_REGISTRATION_FAILED, name=msg.member.name, tournament=tournament.name, reason=str(e))
    except IndexError as e:
        await msg.create_reaction("❌")
        await server.sendLog(StringsNames.PARTICIPANT_REGISTRATION_FAILED, name=msg.member.name, tournament=tournament.name, reason="Registration Fields don't match tournament template")
    except LibraryException as e:
        await msg.create_reaction("🤷‍♂️")
        if e.code == 50013: # 'Missing Permissions'
            await server.sendLog(StringsNames.CANT_ASSIGN_ROLE_TO_USER, username=msg.member.name, role=role.name)
        else:
            await server.sendLog(StringsNames.PARTICIPANT_REGISTRATION_FAILED, username=msg.member.name, tournament=tournament.name, reason=str(e))
