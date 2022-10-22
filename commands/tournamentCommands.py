import asyncio
from interactions import Channel, ChannelType, Choice, CommandContext, Embed, File, Guild, LibraryException, Member, Message, MessageReaction, Option, OptionType, Role
import interactions
from interactions.ext.paginator import Page, Paginator
from interactions.ext import files, wait_for
import pandas as pd
from dataclasses import asdict
from datetime import datetime
from io import StringIO
from pprint import pformat, pprint
from copy import deepcopy
import logging

import requests

# import requests

from bot import bot, botGuilds
from contextExtentions.contextServer import getServerGuild
from httpClient import getAllUsersFromReaction
from local.lang.utils import utilStrs
from contextExtentions.customContext import ServerContext, customContext
from local.names import StringsNames

from models.tournamentModels import Tournament, TournamentRegistration, TournamentStatus
from models.registrationModels import Participant, RegistrationField, RegistrationTemplate, RegistrationError

from controllers.adminContoller import adminCommand
from controllers.playerController import participantController
from controllers.serverController import serverController
from controllers.tournamentController import tournamentController
from games import factories

from utils import OptionTypes, extractQuotedSubstrs


# this actaully scales better
# follow {channelId: tournamentId}
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
    # TODO get from obj the registrationMethod and remove correspondingly
    if tournamentObj.registration.status == TournamentStatus.REGISTRATION_CLOSED:
        await scx.sendLocalized(StringsNames.REGISTRATION_CLOSED_ALREADY, tournament=tournament)
        return

    listener = openRegistrationChannels.get(tournamentObj.registration.channelId)
    if listener:
        openRegistrationChannels.pop(tournamentObj.registration.channelId)
        tournamentObj.registration.status = TournamentStatus.REGISTRATION_CLOSED
        tournamentObj.registration.channelId = None
        tournamentController.updateRegistrationForTournament(tournamentObj, tournamentObj.registration)
    await scx.sendLocalized(StringsNames.REGISTRATION_CLOSED, tournament=tournament)

##############################################################################################
# ===================================== TOURNAMENTS ======================================== #
##############################################################################################

@bot.command(name="tournaments", scope=botGuilds)
async def tournamentBaseCommand(ctx:CommandContext): pass

@tournamentBaseCommand.subcommand(
    name="delete",
    options=[
        Option(name="tournament",description="Tournament to delete",
                type=OptionType.STRING, required=True)
    ],
    description="Deletes a tournament from existence"
)
@adminCommand
@customContext
async def deleteTournament(ctx:CommandContext, scx:ServerContext, tournament:str):
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    guild:Guild = ctx.guild # this could be None
    tournamentData = tournamentController.getTournamentFromName(guild.id, tournament)
    if not tournamentData:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    if tournamentData.registration.status != TournamentStatus.REGISTRATION_CLOSED:
        await registrationBase.coroutines['close'](ctx, scx=scx, tournament = tournament) #, scx, tournament)
    if tournamentController.deleteTournament(tournamentData):
        await scx.sendLocalized(StringsNames.TOURNAMENT_DELETED, name=tournament)
    else:
        await scx.sendLocalized(StringsNames.DB_DROP_ERROR)

@tournamentBaseCommand.subcommand(
    name="view",
    options=[
        Option(name="tournament", description="Get the details for one tournament",
               type=OptionType.STRING, required=False)
    ],
    description="Shows a list of the tournaments made by this server"
)
@customContext
async def getTournaments(ctx: CommandContext, scx: ServerContext, tournament:str = None):
    #TODO this can be further prettyfied
    guild:Guild = ctx.guild
    if tournament:
        tournamentData = tournamentController.getTournamentFromName(int(guild.id), tournament)
        if tournamentData:
            await ctx.send(utilStrs.JS.format(pformat(asdict(tournamentData))))
        else:
            await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    tournaments:list[Tournament] = tournamentController.getTournamentsForServer(ctx.guild_id)
    if len(tournaments) > 20:
        pageList = []
        embedTournaments = []
        page = 1
        while len(tournaments) != 0:
            tournament = tournaments.pop(0)
            tournamentStr = ' - `' + tournament.name.replace("_","\\_") + '`'
            if tournament.registration.status != TournamentStatus.CHECK_IN_CLOSED:
                tournamentStr += " [ 📝 ]"
            embedTournaments.append(tournamentStr)
            if len(embedTournaments) == 20 or len(tournaments) == 0:
                tournamentStr = "\n".join(embedTournaments)
                embed = Embed(
                    title=f"Showing tournaments from {embedTournaments[0]} to {embedTournaments[-1]}:", 
                    color=0xFFBA00, 
                    description="\n"+tournamentStr, 
                    timestamp=datetime.utcnow())
                embed.set_thumbnail(url=guild.icon_url)
                embed.set_footer(text="TournamentHelper Bot")
                pageList.append(Page(f"{guild.name} (P. #{page})", embed))
                embedTournaments = []
                page += 1
        await Paginator(bot, ctx, pageList).run()
    else:
        tournamentStr = ""
        for t in tournaments:
            t:Tournament
            tournamentStr += ' - `' + t.name .replace("_","\\_") + '`'
            if t.registration.status != TournamentStatus.CHECK_IN_CLOSED:
                tournamentStr += "[ 📝 ]"
            tournamentStr += "\n"
        embed = Embed(
            title=guild.name, 
            color=0xFFBA00, 
            description="The tournaments in this server are:\n"+tournamentStr, 
            timestamp=datetime.utcnow())
        embed.set_thumbnail(url=guild.icon_url)
        embed.set_footer(text="TournamentHelper Bot")
        await ctx.send(embed=embed)

###############################################################################################
# ===================================== PARTICIPANTS ======================================== #
###############################################################################################

@bot.command(name="participants", scope=botGuilds)
async def particpantsBaseCommand(ctx:CommandContext): pass

@particpantsBaseCommand.subcommand(
    name="register_as_with_message",
    options=[
        Option(name="tournament", description="Tournament to register player in",
                type=OptionType.STRING, required=True),
        Option(name="discord_id", description="Discord Id of the player to register",
                type=OptionType.STRING, required=True),
        Option(name="msg_content", description="Content of the message the player would input to register",
                type=OptionType.STRING, required=True),
        Option(name="override_req", description="If True, registers the player despite registration criteria",
                type=OptionType.BOOLEAN, required=False)
    ],
    description="Register a player as if they registered themselves with a message."
)
@adminCommand
@customContext
async def registerPlayerWithDiscord(ctx:CommandContext, scx:ServerContext, tournament:str, discord_id:str, msg_content:str, override_req:bool=False):
    # await ctx.send(utilStrs.ERROR.format("This is an error"))
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    if not discord_id.isnumeric():
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="discord_id")
        return
    userId = int(discord_id)
    member:Member = await ctx.guild.get_member(userId)
    if member is None:
        await scx.sendLocalized(StringsNames.MEMBER_NOT_FOUND_BY_ID, id=discord_id)
        return
    tournamentData = tournamentController.getTournamentFromName(ctx.guild_id, tournament)
    if not tournamentData:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    content = extractQuotedSubstrs(msg_content)
    fields:list[RegistrationField] = deepcopy(tournamentData.registrationTemplate.participantFields)
    if fields:
        for i in range(len(content)):
            fields[i].value = content[i]
    else:
        fields.append(RegistrationField("msg", OptionTypes.STRING, True, value=msg_content))
    try:
        if await tournamentController.registerPlayer(tournamentData, fields, member, overrideReq=override_req):
            if tournamentData.registration.participantRole:
                regRole: Role = await interactions.get(
                    bot, Role,
                    object_id=tournamentData.registration.participantRole,
                    parent_id=tournamentData.hostServerId
                )
                await member.add_role(regRole)
            await scx.sendLocalized(StringsNames.PLAYER_REGISTERED, username=member.nick, tournament=tournament)
        else:
            await scx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
    except Exception as e:
        await ctx.send(utilStrs.ERROR.format(e))

@particpantsBaseCommand.subcommand(
    name="delete_with_discord_id",
    options=[
        Option(name="tournament", description="Tournament in which participant is registered",
                        type=OptionType.STRING, required=True),
        Option(name="discord_id", description="DiscordId of participant to be deleted",
                        type=OptionType.STRING, required=True)
    ],
    description="Delete a participant from a tournament. You get to decide why you do that."
)
@adminCommand
@customContext
async def deleteParticipant(ctx:CommandContext, scx:ServerContext, tournament:str, discord_id:str):
    if ctx.guild_id is None:
        await scx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    if not discord_id.isnumeric():
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="discord_id")
        return
    userId = int(discord_id)
    tournamentData = tournamentController.getTournamentFromName(int(ctx.guild_id), tournament)
    if not tournamentData:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    participant = participantController.deleteParticipant(tournamentData._id, userId)
    if participant:
        await scx.sendLocalized(StringsNames.PARTICIPANT_DELETED, username=f"id: {discord_id}", tournament=tournament)
        if tournamentData.registration.participantRole:
            member:Member = await ctx.guild.get_member(participant.discordId)
            role = await ctx.guild.get_role(tournamentData.registration.participantRole)
            await member.remove_role(role, reason='Manually disqualified by TOs')
    else:
        await scx.sendLocalized(StringsNames.PARTICIPANT_UNEXISTING, username=f"id: {discord_id}", tournament=tournament)

@particpantsBaseCommand.subcommand(
    name="view",
    description="See who's registered in your tournament",
    options=[
        Option(name="tournament", description="Tournament to check to registered players",
               type=OptionType.STRING, required=True)
    ]
)
@customContext
async def getTournamentParticipants(ctx:CommandContext, scx:ServerContext, tournament:str):
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id,tournament)
    tournamentCtrl = factories.getControllerFor(tournamentObj)
    if tournamentObj is None:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    participants = participantController.getParticipantsForTournament(tournamentObj._id)
    partList = []
    for p in participants:
        partList.append(tournamentCtrl.getParticipantView(p))
    df = pd.DataFrame(partList)
    await files.command_send(ctx, files=[File(fp=StringIO(df.to_csv()), filename= f"Participants_{datetime.utcnow()}.csv")])

@particpantsBaseCommand.subcommand(
    name="refresh",
    description="View the latest registration criteria for participants. Useful with deeply integrated games.",
    options=[
        Option(name="tournament", description="Tournament for which check players",
            type=OptionType.STRING, required=True),
        Option(name="update", description="Wether to make player data permanent or not.",
            type=OptionType.BOOLEAN, required=False)
    ]
)
@adminCommand
@customContext
async def refreshParticipants(ctx:CommandContext, scx:ServerContext, tournament:str, update:bool = False):
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id,tournament)
    tournamentCtrl = factories.getControllerFor(tournamentObj)
    if tournamentObj is None:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    await scx.sendLocalized(StringsNames.MAY_TAKE_LONG)
    participants = participantController.getParticipantsForTournament(tournamentObj._id)
    async with ctx.channel.typing:
        newParticipants, failed = await tournamentCtrl.checkParticipants(participants, tournamentObj)
    pViews = list(map(lambda p: tournamentCtrl.getParticipantView(p), newParticipants))
    fViews = [{'reason':r, **tournamentCtrl.getParticipantView(p)} for p,r in failed]
    participantViews = pd.DataFrame(pViews)
    failedViews = pd.DataFrame(fViews)
    await files.command_edit(ctx, content="", files=[File(fp=StringIO(participantViews.to_csv()), filename= f"Participants_{datetime.utcnow()}.csv")])
    if update:
        participantController.updateParticipants(newParticipants)
        participantController.deleteParticipants([p for p,_ in failed])
    if len(failed) != 0:
        if update:
            await scx.sendLocalized(StringsNames.PARTICIPANTS_DELETED, _as_reply=False, amount=len(failed))
            if tournamentObj.registration.participantRole:
                role:Role = await interactions.get(bot, Role, object_id=tournamentObj.registration.participantRole, parent_id=ctx.guild_id)
                for p,r in failed:
                    member:Member = await ctx.guild.get_member(p.discordId)
                    await member.remove_role(role, reason=f"Disquialified for: {r}")
                await scx.sendLocalized(StringsNames.PARTICIPANTS_ROLE_REMOVED, _as_reply=False, rolename=role.name)
        await ctx.channel.send(files=[File(fp=StringIO(failedViews.to_csv()), filename= f"Disqualified_{datetime.utcnow()}.csv")])

@bot.command(name="check-in", scope=botGuilds)
async def checkInBaseCommand(ctx:CommandContext): pass

@checkInBaseCommand.subcommand(
    name="read_from_reaction",
    description="Register people who reacted to a certain message as checked in",
    options= [
        Option(name="tournament", description="The tournament for which this check in counts for.",
               type=OptionType.STRING, required=True),
        Option(name="message_id", description="Message id at which users reacted for check-in, (you can get this by right clicking the message)",
               type=OptionType.STRING, required=True),
        Option(name="channel", description="The channel in which the specified message is",
               type=OptionType.CHANNEL, required=True)
    ]
)
@adminCommand
@customContext
async def readCheckIns(ctx:CommandContext,
        tournament:str, 
        scx:ServerContext,
        message_id:str,
        channel:Channel):
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id,tournament)
    tournamentCtrl = factories.getControllerFor(tournamentObj)
    if tournamentObj is None:
        await scx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    if not message_id.isdecimal():
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    messageId = int(message_id)
    if channel.type != ChannelType.GUILD_TEXT:
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_TEXT_CHANNEL, option="channel")
        return
    try:
        msg:Message = await channel.get_message(messageId)
    except Exception as e:
        await scx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    
    def check(reaction:MessageReaction):
        return int(reaction.user_id) == int(ctx.author.id)
    try:
        res1 = await scx.sendLocalized(StringsNames.INPUT_CHECK_IN_REACTION)
        inputReaction:MessageReaction= await wait_for.wait_for(bot, 'on_message_reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await scx.sendLocalized(StringsNames.REACTION_TIMEOUT, time="60")
        return
    reaction = await getAllUsersFromReaction(
        int(channel.id), int(msg.id) , inputReaction.emoji.name
    )
    if reaction == []:
        await scx.sendLocalized(StringsNames.NO_REACTION_IN_MSG, reaction=str(inputReaction.emoji))
        return
    participants = []
    for user in reaction:
        p = participantController.getParticipantFromDiscordId(int(user.get('id')), tournamentObj._id)
        if p is None: continue
        pData = tournamentCtrl.getParticipantView(p)
        participants.append(pData)

    df = pd.DataFrame(participants)
    await files.command_send(ctx, files=[File(fp=StringIO(df.to_csv()), filename= f"Participants_{datetime.utcnow()}.csv")])

@bot.command(name="csv", scope=botGuilds)
async def csvBaseCommand(ctx:CommandContext): pass

@csvBaseCommand.subcommand(
    name="sort_by",
    description="Sort a csv file by the given column",
    options=[
        Option(
            name="column", description="The column to seed by.",
            type=OptionType.STRING, required=True
        ),
        Option(
            name="order", description="The order to aply",
            type=OptionType.STRING, required=True,
            choices=[
                Choice(name="ascending", value="a"),
                Choice(name="descending", value="")
            ]
        ),
        Option(
            name="message_id", description="Message in which the file is",
            type=OptionType.STRING, required=True
        ),
        Option(
            name="get_columns", description="If present, show only specified columns. Sepparate with commas.",
            type=OptionType.STRING, required=False
        )
    ]
)
@customContext
async def seedBy(ctx:CommandContext, scx:ServerContext, column:str, order:str, message_id:str, get_columns:str = None):
    order = bool(order)
    if not message_id.isdecimal():
        await scx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    messageId = int(message_id)
    chn:Channel = ctx.channel
    try:
        msg:Message = await chn.get_message(message_id=messageId)
    except Exception as e:
        await scx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    
    try:
        csvs:str = await getCsvTextFromMsg(msg)
        playersDF:pd.DataFrame = pd.read_csv(StringIO(csvs))

        await ctx.send(utilStrs.INFO.format("Seeding players..."))
        playersDF.sort_values(column, ascending=order, ignore_index=True, inplace=True)
        playersDF["Seed"] = playersDF.index + 1

        columnsList = None if not get_columns else get_columns.split(",")
        dfcsv = playersDF.to_csv(
            index=False,
            columns=columnsList,
            header= not columnsList or len(columnsList)!=1
        )
        await files.command_send(ctx, content= utilStrs.INFO.format("File generated"), files=[File(fp=StringIO(dfcsv), filename="Seeding.csv")])
        
    except Exception as e:
        await ctx.send(utilStrs.ERROR.format(e))
        raise e

@csvBaseCommand.subcommand(
    name="get_columns",
    description="Given a csv file in this text channel, get the columns as a sepparate file",
    options=[
        Option(
            name="columns", description="The columns to get. Sepparate using commas.",
            type=OptionType.STRING, required=True
        ),
        Option(
            name="message_id", description="Message in which the file is",
            type=OptionType.STRING, required=True
        ),
    ]
)
@customContext
async def getColumn(ctx:CommandContext, scx:ServerContext, columns:str, message_id:str):
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
        columnList = columns.split(",")
        dfcsv = playersDF.to_csv(index=False, columns=columnList, header=(len(columnList)!=1))
        await files.command_send(ctx,
            content=utilStrs.INFO.format("File generated"),
            files=[File(fp=StringIO(dfcsv), filename="Seeding.csv")]
        )
    except Exception as e:
        await ctx.send(utilStrs.ERROR.format(e))


@bot.event(name='on_ready')
async def setListenersBackUp():
    #get tournaments
    tournaments = tournamentController.getOpenTournaments()
    if not tournaments:
        return
    logging.info("Setting up tournament listeners...")
    for tournament in tournaments:
        try:
            # TODO when other registration method is implemented add listener setup here
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

####################
# Helper functions #
####################

async def setupMessageRegistration(tournament:Tournament): # this asumes that registration is properly open in db 
    global openRegistrationChannels
    if tournament.registration.channelId in openRegistrationChannels: 
        #prevent from setting two identical listeners
        return
    openRegistrationChannels[tournament.registration.channelId] = tournament._id
    pprint(openRegistrationChannels)

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
    fields: list[RegistrationField] = deepcopy(tournament.registrationTemplate.participantFields)
    try:
        if fields:
            for i in range(len(content)):
                fields[i].value = content[i]
        else:
            fields.append(RegistrationField("msg", OptionTypes.STRING, True, value=msg.content))
        if await tournamentController.registerPlayer(tournament, fields, msg.author):
            await msg.create_reaction("✅")
            if role:
                await msg.member.add_role(role)
        else:
            logging.error("Failed to upload to db.")
            await server.sendLog(StringsNames.PARTICIPANT_REGISTRATION_FAILED, name=msg.member.nick, tournament=tournament.name, reason="DB UPLOAD ERROR")
            await msg.create_reaction("🆘")
    except RegistrationError as e:
        await msg.create_reaction("❌")
        await server.sendLog(StringsNames.PARTICIPANT_REGISTRATION_FAILED, name=msg.member.nick, tournament=tournament.name, reason=str(e))
    except IndexError as e:
        await msg.create_reaction("❌")
        await server.sendLog(StringsNames.PARTICIPANT_REGISTRATION_FAILED, name=msg.member.nick, tournament=tournament.name, reason="Registration Fields don't match tournament template")
    except LibraryException as e:
        await msg.create_reaction("🤷‍♂️")
        if e.code == 50013: # 'Missing Permissions'
            await server.sendLog(StringsNames.CANT_ASSIGN_ROLE_TO_USER, username=msg.member.nick, role=role.name)
        else:
            await server.sendLog(StringsNames.PARTICIPANT_REGISTRATION_FAILED, username=msg.member.nick, tournament=tournament.name, reason=str(e))


async def getCsvTextFromMsg(msg:Message):
    if not msg.attachments:
        raise Exception("Did not find any CSV file")
    file_url = msg.attachments[0].url
    req = requests.get(file_url)
    if req.status_code == 200:
        return req.content.decode('utf-8')
    else:
        raise Exception("Could not read CSV file")