import asyncio
from discord import channel
from discord.member import Member
import pandas as pd
from dataclasses import asdict
from datetime import datetime
from io import StringIO
from pprint import pformat
from typing import List
import logging

import discord
from discord.file import File
from discord.channel import TextChannel
from discord.message import Message
from discord_slash.context import SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

import requests

from bot import bot, botGuilds, slash
from local.lang.utils import utilStrs
from local.localContext import CustomContext, localized
from local.names import StringsNames

from models.tournamentModels import Tournament, TournamentRegistration, TournamentStatus
from models.registrationModels import RegistrationField, RegistrationTemplate, RegistrationError

from controllers.adminContoller import adminCommand
from controllers.playerController import participantController
from controllers.tournamentController import TournamentController, tournamentController
from games import factories

import strings as strs
from utils import OptionTypes, extractQuotedSubstrs, setupButtonNavigation


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
@localized
async def openRegistrationInChat(ctx:CustomContext,tournament:str,channel:discord.TextChannel):
    global registrationListeners
    #check stuff is correct
    if ctx.guild_id is None:
        await ctx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    if channel.type != discord.ChannelType.text:
        await ctx.sendLocalized(StringsNames.VALUE_SHOULD_BE_TEXT_CHANNEL, option="channel")
        return
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id, tournament)
    if tournamentObj is None:
        await ctx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    if tournamentObj.registration.status == TournamentStatus.REGISTRATION_OPEN_BY_MSG:
        registrationChat:TextChannel = await bot.fetch_channel(tournamentObj.registration.channelId)
        await ctx.sendLocalized(StringsNames.REGISTRATION_OPEN_ALREADY, tournament=tournament, chat=registrationChat.mention)
        return
    if tournamentObj.registrationTemplate.teamSize != 1:
        # TODO add logic for team games
        pass

    tournamentObj.registration.status = TournamentStatus.REGISTRATION_OPEN_BY_MSG
    tournamentObj.registration.channelId = channel.id
    tournamentController.updateRegistrationForTournament(tournamentObj, tournamentObj.registration)

    setupMessageRegistration(channel, tournamentObj)

    # add listener for channel
    await ctx.sendLocalized(StringsNames.REGISTRATION_OPEN_CHAT, tournament=tournamentObj.name, chat=channel.mention)


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
@localized
async def closeRegistration(ctx:CustomContext, tournament:str):
    global registrationListeners
    if ctx.guild_id is None:
        await ctx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id, tournament)
    if tournamentObj is None:
        await ctx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    # TODO get from obj the registrationMethod and remove correspondingly
    if tournamentObj.registration.status == TournamentStatus.REGISTRATION_CLOSED:
        await ctx.sendLocalized(StringsNames.REGISTRATION_CLOSED_ALREADY, tournament=tournament)
        return

    listener = registrationListeners.get((ctx.guild_id, tournamentObj.name))
    if listener:
        bot.remove_listener(listener, "on_message")
        registrationListeners.pop((ctx.guild_id, tournamentObj.name))
        tournamentObj.registration.status = TournamentStatus.REGISTRATION_CLOSED
        tournamentObj.registration.channelId = None
        tournamentController.updateRegistrationForTournament(tournamentObj, tournamentObj.registration)
    await ctx.sendLocalized(StringsNames.REGISTRATION_CLOSED, tournament=tournament)


@slash.slash(
    name="delete_tournament",
    options=[
        create_option(name="tournament",description="Tournament to delete",
                        option_type=OptionTypes.STRING, required=True)
    ],
    guild_ids=botGuilds,
    description="Deletes a tournament from existence"
)
@adminCommand
@localized
async def deleteTournament(ctx:CustomContext, tournament:str):
    if ctx.guild_id is None:
        await ctx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    guild:discord.Guild = ctx.guild
    tournamentData = tournamentController.getTournamentFromName(guild.id, tournament)
    if not tournamentData:
        await ctx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    if tournamentData.registration.status != TournamentStatus.REGISTRATION_CLOSED:
        await closeRegistration.invoke(ctx, tournament = tournament)
    if tournamentController.deleteTournament(tournamentData):
        await ctx.sendLocalized(StringsNames.TOURNAMENT_DELETED, name=tournament)
    else:
        await ctx.sendLocalized(StringsNames.DB_DROP_ERROR)
    

@slash.slash(
    name="see_tournaments",
    options=[
        create_option(name="tournament",description="Get the details for one tournament",
                        option_type=OptionTypes.STRING,required=False)
    ],
    guild_ids= botGuilds,
    description="Shows a list of the tournaments made by this server"
)
@localized
async def getTournaments(ctx: CustomContext, tournament:str = None):
    #TODO this can be further pretified
    guild:discord.Guild = ctx.guild
    if tournament:
        tournamentData = tournamentController.getTournamentFromName(guild.id, tournament)
        if tournamentData:
            await ctx.send(strs.utilStrs.JS.format(pformat(asdict(tournamentData))))
        else:
            await ctx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    tournaments = tournamentController.getTournamentsForServer(ctx.guild_id)
    if len(tournaments) > 20:
        embedList = []
        embedTournaments = []
        page = 1
        while len(tournaments) != 0:
            t = tournaments.pop(0)
            # ej. TAWS 15
            tournamentStr = t.name.replace("_","\\_")
            if t.registration.status != TournamentStatus.CHECK_IN_CLOSED:
                tournamentStr += "......( 📝 )"
            embedTournaments.append(tournamentStr)
            if len(embedTournaments) == 20 or len(tournaments) == 0:
                tournamentStr = "\n".join(embedTournaments)
                embed = discord.Embed(
                    title=f"{guild.name} (Page #{page})\n", 
                    colour=discord.Colour(0xFFBA00), 
                    description=f"Showing tournaments from {embedTournaments[0]} to {embedTournaments[-1]}:\n"+tournamentStr, 
                    timestamp=datetime.utcnow())
                embed.set_thumbnail(url=guild.icon_url)
                embed.set_footer(text="TournamentHelper Bot")
                embedList.append(embed)
                embedTournaments = []
                page += 1
        await setupButtonNavigation(ctx, embedList, bot)
    else:
        tournamentStr = ""
        for tournament in tournaments:
            tournamentStr += tournament.name
            if tournament.registration.status != TournamentStatus.CHECK_IN_CLOSED:
                tournamentStr += "......( 📝 )"
            tournamentStr += "\n"
        embed = discord.Embed(
            title=guild.name, 
            colour=discord.Colour(0xFFBA00), 
            description="The tournaments in this server are:\n"+tournamentStr, 
            timestamp=datetime.utcnow())
        embed.set_thumbnail(url=guild.icon_url)
        embed.set_footer(text="TournamentHelper Bot")
        await ctx.send(embed=embed)

@slash.subcommand(
    base="register_player_as",
    name="with_message",
    options=[
        create_option(name="tournament", description="Tournament to register player in",
                        option_type=OptionTypes.STRING, required=True),
        create_option(name="discord_id", description="Discord Id of the player to register",
                        option_type=OptionTypes.STRING, required=True),
        create_option(name="msg_content", description="Content of the message the player would input to register",
                        option_type=OptionTypes.STRING, required=True)
    ],
    guild_ids=botGuilds,
    description="Register a player as if they registered themselves with a message."
)
@adminCommand
@localized
async def registerPlayerWithDiscord(ctx:CustomContext, tournament:str, discord_id:str, msg_content:str):
    if ctx.guild_id is None:
        await ctx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    if not discord_id.isnumeric():
        await ctx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="discord_id")
        return
    userId = int(discord_id)
    member:Member = ctx.guild.get_member(userId)
    if member is None:
        await ctx.sendLocalized(StringsNames.MEMBER_NOT_FOUND_BY_ID, id=discord_id)
        return
    tournamentData = tournamentController.getTournamentFromName(ctx.guild_id, tournament)
    if not tournamentData:
        await ctx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    content = extractQuotedSubstrs(msg_content)
    fields:List[RegistrationField] = tournamentData.registrationTemplate.participantFields
    for i in range(len(content)):
        fields[i].value = content[i]
    try:
        if tournamentController.registerPlayer(tournamentData, fields, member):
            await ctx.sendLocalized(StringsNames.PLAYER_REGISTERED, username=member.display_name, tournament=tournament)
        else:
            await ctx.sendLocalized(StringsNames.DB_UPLOAD_ERROR)
    except Exception as e:
        await ctx.send(utilStrs.ERROR.format(e))

@slash.subcommand(
    base="delete_participant",
    name="with_discord_id",
    options=[
        create_option(name="tournament", description="Tournament in which participant is registered",
                        option_type=OptionTypes.STRING, required=True),
        create_option(name="discord_id", description="DiscordId of participant to be deleted",
                        option_type=OptionTypes.STRING, required=True)
    ],
    guild_ids=botGuilds,
    description="Delete a participant from a tournament. You get to decide why you do that."
)
@adminCommand
@localized
async def deleteParticipant(ctx:CustomContext, tournament:str, discord_id:str):
    if ctx.guild_id is None:
        await ctx.sendLocalized(StringsNames.NOT_FOR_DM)
        return
    if not discord_id.isnumeric():
        await ctx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="discord_id")
        return
    userId = int(discord_id)
    tournamentData = tournamentController.getTournamentFromName(ctx.guild_id, tournament)
    if not tournamentData:
        await ctx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    participant = participantController.deleteParticipant(tournamentData._id, userId)
    if participant:
        await ctx.sendLocalized(StringsNames.PARTICIPANT_DELETED, username=f"id: {discord_id}", tournament=tournament)
    else:
        await ctx.sendLocalized(StringsNames.PARTICIPANT_UNEXISTING, username=f"id: {discord_id}", tournament=tournament)

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
@localized
async def getTournamentParticipants(ctx:CustomContext, tournament:str):
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id,tournament)
    tournamentCtrl = factories.getControllerFor(tournamentObj)
    if tournamentObj is None:
        await ctx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
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
@localized
async def readCheckIns(ctx:CustomContext,
        tournament:str, 
        # reaction:str, 
        message_id:str,
        channel:TextChannel):
    tournamentObj = tournamentController.getTournamentFromName(ctx.guild_id,tournament)
    tournamentCtrl = factories.getControllerFor(tournamentObj)
    if tournamentObj is None:
        await ctx.sendLocalized(StringsNames.TOURNAMENT_UNEXISTING, name=tournament)
        return
    if not message_id.isdecimal():
        await ctx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    messageId = int(message_id)
    if channel.type != discord.ChannelType.text:
        await ctx.sendLocalized(StringsNames.VALUE_SHOULD_BE_TEXT_CHANNEL, option="channel")
        return
    try:
        msg:Message = await channel.fetch_message(messageId)
    except Exception as e:
        await ctx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    
    def check(_, user):
        return user == ctx.author
    try:
        res1 = await ctx.sendLocalized(StringsNames.INPUT_CHECK_IN_REACTION)
        inputReaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.sendLocalized(StringsNames.REACTION_TIMEOUT, time="60")
        return
    reaction = list(filter(lambda x: x.emoji == inputReaction.emoji, msg.reactions))
    if reaction == []:
        await ctx.sendLocalized(StringsNames.NO_REACTION_IN_MSG, reaction=str(inputReaction.emoji))
        return
    reaction = reaction[0]
    participants = []
    async for user in reaction.users():
        p = participantController.getParticipantFromDiscordId(user.id, tournamentObj._id)
        if p is None: continue
        pData = tournamentCtrl.getParticipantView(p)
        participants.append(pData)

    df = pd.DataFrame(participants)    
    await ctx.send(file=File(StringIO(df.to_csv()), filename= f"Participants_{datetime.utcnow()}.csv"))


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
@localized
async def seedBy(ctx:CustomContext, column:str, order:str, message_id:str):
    order = bool(order)
    if not message_id.isdecimal():
        await ctx.sendLocalized(StringsNames.VALUE_SHOULD_BE_DEC, option="message_id")
        return
    messageId = int(message_id)
    chn:channel.TextChannel = ctx.channel
    try:
        msg:Message = await chn.fetch_message(messageId)
    except Exception as e:
        await ctx.sendLocalized(StringsNames.MESSAGE_NOT_FOUND, data=type(e).__name__)
        return
    
    try:
        csvs:str = await getCsvTextFromMsg(msg)
        playersDF:pd.DataFrame = pd.read_csv(StringIO(csvs))

        await ctx.send(utilStrs.INFO.format("Seeding players..."))
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
    logging.info("Setting up tournament listeners...")
    for tournament in tournaments:
        try:
            # TODO when other registration method is implemented add listener setup here
            if tournament.registration.status == TournamentStatus.REGISTRATION_OPEN_BY_MSG:
                regChannel = bot.get_channel(tournament.registration.channelId)
                if not regChannel: #channel got deleted or something
                    #TODO send message to log channel in server
                    logging.error(f"Didnt find channel for tournament: {tournament.name}")
                    raise Exception()
                setupMessageRegistration(regChannel, tournament)
        except:
            logging.error(f"Closing registration for tournament: {tournament.name}")
            tournament.registration.status = TournamentStatus.REGISTRATION_CLOSED
            tournament.registration.channelId = None
            tournamentController.updateRegistrationForTournament(tournament, tournament.registration)

    logging.info("Tournament listeners ready!")
    pass

####################
# Helper functions #
####################

def setupMessageRegistration(channel:discord.TextChannel, tournament:Tournament):
    global registrationListeners
    if (channel.guild.id, tournament.name) in registrationListeners: 
        #prevent from setting two identical listeners
        return
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
            if tournamentController.registerPlayer(tournament, fields, msg.author):
                await msg.add_reaction("✅")
            else:
                logging.error("Failed to upload to db.")
                await msg.add_reaction("🆘")
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