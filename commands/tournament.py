import asyncio
from discord import channel
import pandas as pd
from dataclasses import asdict
from datetime import datetime
from io import StringIO
from pprint import pformat
from typing import List

import discord
from discord.file import File
from discord.channel import TextChannel
from discord.message import Message
from discord_slash.context import SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

import requests

from bot import bot, botGuilds, slash

from models.tournament import Tournament, TournamentStatus
from models.registration import RegistrationField, RegistrationTemplate, RegistrationError

from controllers.admin import adminCommand
from controllers.player import participantController
from controllers.tournament import tournamentController
from games import factories
from games.tetrio import TetrioController, TetrioTournament

import strings as strs
from utils import OptionTypes, extractQuotedSubstrs


@slash.subcommand(
    base="add_tournament",
    name="tetrio",
    guild_ids= botGuilds,
    description="Add a tournament for tetr.io integrated game.",
    options=[
        create_option(
            name="name", description="The tournament's name.",
            option_type=OptionTypes.STRING, required=True
        ),
        create_option(
            name="rank_cap", description="Maximun TR a player can have to register",
            option_type=OptionTypes.INTEGER, required=False
        ),
        create_option(
            name="rank_floor", description="Minimum TR a player can have to register",
            option_type=OptionTypes.INTEGER, required=False
        )
    ])
@adminCommand
async def addTournamentTetrio(ctx:SlashContext, name:str, rank_cap:int=None, rank_floor:int=None):
    game = "tetr.io"
    if ctx.guild_id is None:
        await ctx.send(strs.SpanishStrs.NOT_FOR_DM)
        return
    if tournamentController.getTournamentFromName(ctx.guild_id, name):
        await ctx.send(strs.SpanishStrs.TOURNAMENT_EXISTS_ALREADY.format(name=name))
        return
    controller = TetrioController()
    # uncomment on completing template implementation
    # customTemplate = templatesController.getTemplate(ctx.guild_id, template) # returns [] if doesnt exist
    # customTemplate.participantFields += controller.PLAYER_FIELDS
    templateFields = controller.PLAYER_FIELDS 
    regTemplate = RegistrationTemplate(name=name,serverId=ctx.guild_id,participantFields=templateFields)
    tournament = TetrioTournament(name=name, game=game, hostServerId=ctx.guild_id, registrationTemplate=regTemplate, rankTop=rank_cap, rankBottom=rank_floor)
    if tournamentController.addTournament(tournament):
        await ctx.send(strs.SpanishStrs.TOURNAMENT_ADDED.format(name=name,game=game))
    else:
        await ctx.send(strs.SpanishStrs.DB_UPLOAD_ERROR)


# this is unlikely to scale very much
# follow {(serverId, tournamentName): coroutine}
registrationListeners = {}

@slash.subcommand(
    base="openRegistration",
    name="inChat",
    guild_ids= botGuilds,
    options=[
        create_option(
            name="tournament",
            description="Tournament to open registration",
            option_type=OptionTypes.STRING,
            required=True
        ),
        create_option(
            name="channel",
            description="Channel in which participants register",
            required=True,
            option_type=OptionTypes.CHANNEL
        )
    ])
@adminCommand
async def openRegistrationInChat(ctx:SlashContext,tournament:str,channel:discord.TextChannel):
    global registrationListeners
    #check stuff is correct
    if ctx.guild_id is None:
        await ctx.send(strs.SpanishStrs.NOT_FOR_DM)
        return
    if channel.type != discord.ChannelType.text:
        await ctx.send(strs.SpanishStrs.VALUE_SHOULD_BE_TEXT_CHANNEL.format(option="channel"))
        return
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id, tournament)
    if tournamentObj is None:
        await ctx.send(strs.SpanishStrs.TOURNAMENT_UNEXISTING.format(name=tournament))
        return
    # TODO
    # if tournamentObj.registrationOpen:
    #     await ctx.send("Ya hay registro abierto para este torneo")
    if tournamentObj.registrationTemplate.teamSize != 1:
        # TODO add logic for team games
        pass

    tournamentObj.registration.status = TournamentStatus.REGISTRATION_OPEN_BY_MSG
    tournamentObj.registration.channelId = channel.id
    tournamentController.updateRegistrationForTournament(tournamentObj, tournamentObj.registration)

    setupMessageRegistration(channel, tournamentObj)

    # add listener for channel
    await ctx.send(strs.SpanishStrs.REGISTRATION_OPEN_CHAT.format(tournament=tournamentObj.name, chat=channel.mention))

@slash.slash(
    name="closeRegistration",
    guild_ids=botGuilds,
    options=[
        create_option(
            name="tournament",
            description="Tournament to close registration for",
            option_type=OptionTypes.STRING,
            required=True
        )
    ]
)
@adminCommand
async def closeRegistration(ctx:SlashContext, tournament:str):
    global registrationListeners
    if ctx.guild_id is None:
        await ctx.send(strs.SpanishStrs.NOT_FOR_DM)
        return
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id, tournament)
    if tournamentObj is None:
        await ctx.send(strs.SpanishStrs.TOURNAMENT_UNEXISTING.format(name=tournament))
        return
    # TODO get from obj the registrationMethod and remove correspondingly
    if tournamentObj.registration.status == TournamentStatus.REGISTRATION_CLOSED:
        await ctx.send(strs.SpanishStrs.REGISTRATION_CLOSED_ALREADY.format(tournament=tournament))
        return

    listener = registrationListeners.get((ctx.guild_id, tournamentObj.name))
    if listener:
        bot.remove_listener(listener, "on_message")
        registrationListeners.pop((ctx.guild_id, tournamentObj.name))
        tournamentObj.registration.status = TournamentStatus.REGISTRATION_CLOSED
        tournamentController.updateRegistrationForTournament(tournamentObj, tournamentObj.registration)
    await ctx.send(strs.SpanishStrs.REGISTRATION_CLOSED.format(tournament=tournament))


@slash.slash(
    name="seeTournaments",
    guild_ids= botGuilds,
    description="Shows a list of the tournaments made by this server"
)
async def getTournaments(ctx: SlashContext):
    # TODO beautify this, since probably its going to get messy quickly
    tournaments = tournamentController.getTournamentsForServer(ctx.guild_id)
    tournamentStrs = list(map(lambda x: asdict(x), tournaments))
    for t in tournamentStrs:
        await ctx.send(strs.utilStrs.JS.format(pformat(t)))


@slash.slash(
    name="see_participants",
    description="See who's registered in your tournament",
    guild_ids=botGuilds,
    options=[
        create_option( 
            name="tournament", description="Tournament to check to registered players",
            option_type=OptionTypes.STRING, required=True
        )
    ]
)
async def getTournamentParticipants(ctx:SlashContext, tournament:str):
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id,tournament)
    tournamentCtrl = factories.getControllerFor(tournamentObj)
    if tournamentObj is None:
        await ctx.send(strs.SpanishStrs.TOURNAMENT_UNEXISTING)
        return
    participants = participantController.getParticipantsForTournament(tournamentObj._id)
    partList = []
    for p in participants:
        partList.append(tournamentCtrl.getParticipantView(p))
    df = pd.DataFrame(partList)
    await ctx.send(file=File(StringIO(df.to_csv()), filename= f"Participants_{datetime.utcnow()}.txt"))

@slash.slash(
    name="readCheckInFromReaction",
    description="Register people who reacted to a certain message as checked in",
    guild_ids=botGuilds,
    options= [
        create_option(
            name="tournament", description="The tournament for which this check in counts for.",
            option_type=OptionTypes.STRING, required=True
        ),
        # create_option(
        #     name="reaction", description="utf-8 emoji that counts for the check-in",
        #     option_type=OptionTypes.STRING, required=True
        # ),
        create_option(
            name="message_id", description="Message id at which users reacted for check-in, (you can get this by right clicking the message)",
            option_type=OptionTypes.STRING, required=True
        ),
        create_option(
            name="channel", description="The channel in which the specified message is",
            option_type=OptionTypes.CHANNEL, required=True
        )
    ]
)
@adminCommand
async def readCheckIns(ctx:SlashContext,
        tournament:str, 
        # reaction:str, 
        message_id:str,
        channel:TextChannel):
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id,tournament)
    tournamentCtrl = factories.getControllerFor(tournamentObj)
    if tournamentObj is None:
        await ctx.send(strs.SpanishStrs.TOURNAMENT_UNEXISTING)
        return
    if not message_id.isdecimal():
        await ctx.send(strs.SpanishStrs.VALUE_SHOULD_BE_DEC.format(option="message_id"))
        return
    messageId = int(message_id)
    if channel.type != discord.ChannelType.text:
        await ctx.send(strs.SpanishStrs.VALUE_SHOULD_BE_TEXT_CHANNEL.format(option="channel"))
        return
    try:
        msg:Message = await channel.fetch_message(messageId)
    except Exception as e:
        await ctx.send(strs.SpanishStrs.MESSAGE_NOT_FOUND.format(type(e).__name__))
        return
    
    def check(_, user):
        return user == ctx.author
    try:
        res1 = await ctx.send(strs.SpanishStrs.INPUT_CHECK_IN_REACTION)
        inputReaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send('👎')
        return
    reaction = list(filter(lambda x: x.emoji == inputReaction.emoji, msg.reactions))
    if reaction == []:
        await ctx.send(strs.SpanishStrs.NO_REACTION_IN_MSG.format(reaction=str(inputReaction.emoji)))
        return
    reaction = reaction[0]
    participants = []
    async for user in reaction.users():
        p = participantController.getParticipantFromDiscordId(user.id, tournamentObj._id)
        pData = tournamentCtrl.getParticipantView(p)
        participants.append(pData)

    df = pd.DataFrame(participants)    
    await ctx.send(file=File(StringIO(df.to_csv()), filename= f"Participants_{datetime.utcnow()}.txt"))

@slash.slash(
    name="seedBy",
    description="Seed a player file by the given column",
    guild_ids=botGuilds,
    options=[
        create_option(
            name="column", description="The column to seed by.",
            option_type=OptionTypes.STRING, required=True
        ),
        create_option(
            name="order", description="The order to aply",
            option_type=OptionTypes.STRING, required=True,
            choices=[
                create_choice(name="ascending", value="a"),
                create_choice(name="descending", value="")
            ]
        ),
        create_option(
            name="message_id", description="Message in which the file is",
            option_type=OptionTypes.STRING, required=True
        ),
    ]
)
async def seedBy(ctx:SlashContext, column:str, order:str, message_id:str):
    order = bool(order)
    if not message_id.isdecimal():
        await ctx.send(strs.SpanishStrs.VALUE_SHOULD_BE_DEC.format(option="message_id"))
        return
    messageId = int(message_id)
    chn:channel.TextChannel = ctx.channel
    try:
        msg:Message = await chn.fetch_message(messageId)
    except Exception as e:
        await ctx.send(strs.SpanishStrs.MESSAGE_NOT_FOUND.format(type(e).__name__))
        return
    
    try:
        csvs:str = await getCsvTextFromMsg(msg)
        playersDF:pd.DataFrame = pd.read_csv(StringIO(csvs))

        await ctx.send(strs.utilStrs.INFO.format("Seeding players..."))
        playersDF.sort_values(column, ascending=order, ignore_index=True, inplace=True)
        playersDF["Seed"] = playersDF.index + 1

        dfcsv = playersDF.to_csv(index=False)
        await ctx.send(
            content=strs.utilStrs.INFO.format("File generated"),
            file= File(fp=StringIO(dfcsv), filename="Seeding.csv")
        )
        
    except Exception as e:
        await ctx.send(strs.utilStrs.ERROR.format(e))




@bot.listen('on_ready')
async def setListenersBackUp():
    #get tournaments
    tournaments = tournamentController.getOpenTournaments()
    if not tournaments:
        return
    print("Setting up tournament listeners...")
    for tournament in tournaments:
        if tournament.registration.status == TournamentStatus.REGISTRATION_OPEN_BY_MSG:
            regChannel = bot.get_channel(tournament.registration.channelId)
            setupMessageRegistration(regChannel, tournament)
        # TODO when other registration method is implemented add listener setup here
    print("Tournament listeners ready!")
    pass

####################
# Helper functions #
####################

def setupMessageRegistration(channel:discord.TextChannel, tournament:Tournament):
    global registrationListeners
    @bot.listen()
    async def on_message(msg:discord.Message):
        if msg.channel.id != channel.id:
            return
        if not msg.content:
            await msg.add_reaction("🤔")
            await msg.add_reaction("❓")
            return
        content = extractQuotedSubstrs(msg.content)
        fields: List[RegistrationField] = tournament.registrationTemplate.participantFields
        for i in range(len(content)):
            fields[i].value = content[i]
        try:
            tournamentController.registerPlayer(msg.author, tournament, fields)
            await msg.add_reaction("✅")
        except RegistrationError as e:
            # TODO proper error message
            await msg.add_reaction("❌")
    registrationListeners[(channel.guild.id, tournament.name)] = on_message


async def getCsvTextFromMsg(msg:discord.Message):
    if msg.attachments:
        file_url = msg.attachments[0]
    else:
        raise Exception("Did not find any CSV file")
    req = requests.get(file_url)
    if req.status_code == 200:
        return req.content.decode('utf-8')
    else:
        raise Exception("Could not read CSV file")