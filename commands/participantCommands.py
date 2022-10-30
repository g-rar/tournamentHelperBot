from typing import List
from interactions import CommandContext, File, Member, Option, OptionType, Role
import interactions
from interactions.ext import files
import pandas as pd
from dataclasses import asdict
from datetime import datetime
from io import StringIO
from copy import deepcopy

from bot import bot, botGuilds
from local.lang.utils import utilStrs
from contextExtentions.customContext import ServerContext, customContext
from local.names import StringsNames

from models.registrationModels import RegistrationField

from controllers.adminContoller import adminCommand
from controllers.playerController import participantController
from controllers.tournamentController import tournamentController
from games import factories

from utils import OptionTypes, extractQuotedSubstrs

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
    fields:List[RegistrationField] = deepcopy(tournamentData.registrationTemplate.participantFields)
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
